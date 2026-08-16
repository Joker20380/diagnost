from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from users.models import UserProfile

from .forms import DiagnosticUploadForm
from .launch_pdf_parser import (
    PARSER_NAME,
    PARSER_VERSION,
    apply_launch_parse_to_session,
    parse_and_apply_launch_pdf,
)
from .models import (
    DiagnosticApproval,
    DiagnosticCode,
    DiagnosticMeasurement,
    DiagnosticParseRun,
    DiagnosticRecord,
    DiagnosticSession,
    DTCReference,
    QAEvent,
)
from .services import (
    create_diagnostic_record_revision,
    review_diagnostic_record,
    submit_diagnostic_record,
)


class DiagnosticSessionAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="test-pass")
        self.other = User.objects.create_user("other", password="test-pass")
        self.staff = User.objects.create_user(
            "staff",
            password="test-pass",
            is_staff=True,
        )
        self.owner_profile, _ = UserProfile.objects.get_or_create(user=self.owner)
        UserProfile.objects.get_or_create(user=self.other)
        UserProfile.objects.get_or_create(user=self.staff)
        self.session = DiagnosticSession.objects.create(
            user_profile=self.owner_profile,
            raw_file=SimpleUploadedFile(
                "report.pdf",
                b"%PDF-1.4\n%%EOF",
                content_type="application/pdf",
            ),
        )

    def test_owner_can_open_own_session(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("diagnostic_detail", args=[self.session.pk]),
            secure=True,
        )
        self.assertEqual(response.status_code, 200)

    def test_other_user_cannot_open_session(self):
        self.client.force_login(self.other)
        response = self.client.get(
            reverse("diagnostic_detail", args=[self.session.pk]),
            secure=True,
        )
        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_edit_suspension(self):
        self.client.force_login(self.other)
        response = self.client.get(
            reverse("suspension_inspection", args=[self.session.pk]),
            secure=True,
        )
        self.assertEqual(response.status_code, 404)

    def test_staff_can_open_any_session(self):
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("diagnostic_detail", args=[self.session.pk]),
            secure=True,
        )
        self.assertEqual(response.status_code, 200)


class DiagnosticUploadValidationTests(TestCase):
    def build_form(self, name, content, content_type):
        return DiagnosticUploadForm(
            data={"vin": "TESTVIN", "vehicle_model": "Test"},
            files={
                "raw_file": SimpleUploadedFile(
                    name,
                    content,
                    content_type=content_type,
                )
            },
        )

    def test_rejects_non_pdf_extension(self):
        form = self.build_form("report.txt", b"%PDF-1.4", "application/pdf")
        self.assertFalse(form.is_valid())
        self.assertIn("формате PDF", form.errors["raw_file"][0])

    def test_rejects_fake_pdf_content(self):
        form = self.build_form("report.pdf", b"not a pdf", "application/pdf")
        self.assertFalse(form.is_valid())
        self.assertIn("не является", form.errors["raw_file"][0])

    def test_accepts_pdf(self):
        form = self.build_form(
            "report.pdf",
            b"%PDF-1.4\n%%EOF",
            "application/pdf",
        )
        self.assertTrue(form.is_valid(), form.errors)


class LaunchObservationProvenanceTests(TestCase):
    def create_session(self):
        session = DiagnosticSession.objects.create(
            raw_file=SimpleUploadedFile(
                "launch-report.pdf",
                b"%PDF-1.4\nprovenance-test\n%%EOF",
                content_type="application/pdf",
            ),
        )
        self.addCleanup(lambda: session.raw_file.delete(save=False))
        return session

    def parsed_fault(self, *, code="P9999", brand="TestBrand", description="Observed text"):
        fault = {
            "code": code,
            "description": description,
            "status": "Stored",
            "module_code": "ECM",
            "module_name": "Engine control",
        }
        return {
            "vehicle": {"vin": "TESTVIN123", "brand": brand, "model": "Model X"},
            "abnormal_systems": [{"module_code": "ECM", "faults": [fault]}],
            "ok_systems": [],
            "faults": [fault],
            "raw_text": "source observation",
        }

    def test_unknown_observation_does_not_create_canonical_reference(self):
        session = self.create_session()

        created = apply_launch_parse_to_session(session, self.parsed_fault())

        self.assertEqual(created, 1)
        self.assertFalse(DTCReference.objects.filter(code="P9999").exists())
        observation = DiagnosticCode.objects.get(session=session)
        self.assertIsNone(observation.reference)
        self.assertFalse(observation.is_known)
        session.refresh_from_db()
        self.assertEqual(session.analysis_method, DiagnosticSession.AnalysisMethod.RULES)
        self.assertEqual(session.analysis_engine, PARSER_NAME)
        self.assertEqual(session.analysis_version, PARSER_VERSION)
        self.assertIsNone(session.ai_generated_at)

    def test_verified_manufacturer_reference_is_linked_but_not_modified(self):
        reference = DTCReference.objects.create(
            code="930AB2",
            system=DTCReference.System.OEM,
            scope=DTCReference.Scope.MANUFACTURER,
            manufacturer="BMW",
            title_ru="Verified title",
            description_ru="Verified description",
        )
        session = self.create_session()

        apply_launch_parse_to_session(
            session,
            self.parsed_fault(code="930AB2", brand="BMW", description="Case text"),
        )

        observation = DiagnosticCode.objects.get(session=session)
        self.assertEqual(observation.reference, reference)
        self.assertTrue(observation.is_known)
        reference.refresh_from_db()
        self.assertEqual(reference.title_ru, "Verified title")
        self.assertEqual(reference.description_ru, "Verified description")

    @patch("diagnostics.launch_pdf_parser.parse_launch_pdf")
    def test_same_file_and_parser_version_are_replayed_idempotently(self, parse_mock):
        parse_mock.return_value = self.parsed_fault()
        session = self.create_session()

        first_count = parse_and_apply_launch_pdf(session)
        second_count = parse_and_apply_launch_pdf(session)

        self.assertEqual(first_count, 1)
        self.assertEqual(second_count, 1)
        parse_mock.assert_called_once()
        self.assertEqual(DiagnosticParseRun.objects.filter(session=session).count(), 1)
        parse_run = DiagnosticParseRun.objects.get(session=session)
        self.assertEqual(parse_run.status, DiagnosticParseRun.Status.SUCCEEDED)
        self.assertTrue(parse_run.is_current)
        self.assertEqual(parse_run.fault_count, 1)
        self.assertEqual(len(parse_run.content_sha256), 64)
        observation = DiagnosticCode.objects.get(session=session)
        self.assertEqual(observation.parse_run, parse_run)
        session.refresh_from_db()
        self.assertEqual(session.system_report["parser"]["version"], PARSER_VERSION)


    @patch("diagnostics.launch_pdf_parser.parse_launch_pdf")
    def test_new_parser_run_preserves_previous_observations(self, parse_mock):
        parse_mock.return_value = self.parsed_fault(code="P1111")
        session = self.create_session()
        first_count = parse_and_apply_launch_pdf(session)
        first_run = DiagnosticParseRun.objects.get(session=session)

        with patch("diagnostics.launch_pdf_parser.PARSER_VERSION", "2.1.0"):
            parse_mock.return_value = self.parsed_fault(code="P2222")
            second_count = parse_and_apply_launch_pdf(session)

        self.assertEqual((first_count, second_count), (1, 1))
        self.assertEqual(DiagnosticParseRun.objects.filter(session=session).count(), 2)
        self.assertEqual(DiagnosticCode.objects.filter(session=session).count(), 2)
        first_run.refresh_from_db()
        self.assertFalse(first_run.is_current)
        current_run = DiagnosticParseRun.objects.get(session=session, is_current=True)
        self.assertEqual(
            DiagnosticCode.objects.get(parse_run=current_run).code,
            "P2222",
        )

    @patch("diagnostics.launch_pdf_parser.parse_launch_pdf", side_effect=ValueError("broken parser input"))
    def test_failed_parse_run_retains_failure_provenance(self, _parse_mock):
        session = self.create_session()

        with self.assertRaisesMessage(ValueError, "broken parser input"):
            parse_and_apply_launch_pdf(session)

        parse_run = DiagnosticParseRun.objects.get(session=session)
        self.assertEqual(parse_run.status, DiagnosticParseRun.Status.FAILED)
        self.assertIn("broken parser input", parse_run.error_message)
        self.assertIsNotNone(parse_run.completed_at)

class VerifiedDiagnosticRecordTests(TestCase):
    def setUp(self):
        author_user = User.objects.create_user("junior")
        reviewer_user = User.objects.create_user("senior")
        self.author, _ = UserProfile.objects.get_or_create(user=author_user)
        self.reviewer, _ = UserProfile.objects.get_or_create(user=reviewer_user)
        self.session = DiagnosticSession.objects.create(
            raw_file=SimpleUploadedFile(
                "record.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf"
            )
        )
        self.record = DiagnosticRecord.objects.create(
            session=self.session,
            created_by=self.author,
            summary="Engine does not start.",
            confirmed_cause="No fuel pressure.",
            recommended_work="Test pump supply and replace failed pump.",
        )
        DiagnosticMeasurement.objects.create(
            record=self.record,
            parameter="Fuel rail pressure",
            numeric_value="0.4000",
            unit="bar",
            reference_min="3.0000",
            result=DiagnosticMeasurement.Result.OUT_OF_RANGE,
            method="Cranking test",
            tool_name="Pressure gauge",
            measured_by=self.author,
        )

    def test_submit_and_independent_approval_lock_record(self):
        submit_diagnostic_record(self.record)
        approval = review_diagnostic_record(
            self.record,
            self.reviewer,
            DiagnosticApproval.Decision.APPROVE,
            "Evidence verified.",
        )

        self.record.refresh_from_db()
        self.assertEqual(self.record.status, DiagnosticRecord.Status.APPROVED)
        self.assertEqual(approval.snapshot_sha256, self.record.content_sha256)
        self.assertEqual(len(self.record.content_sha256), 64)

        self.record.summary = "Changed after approval"
        with self.assertRaises(ValidationError):
            self.record.save()
        measurement = self.record.measurements.get()
        measurement.value_text = "changed"
        with self.assertRaises(ValidationError):
            measurement.save()
        with self.assertRaises(ValidationError):
            approval.delete()

    def test_approved_record_correction_creates_revision(self):
        submit_diagnostic_record(self.record)
        review_diagnostic_record(
            self.record,
            self.reviewer,
            DiagnosticApproval.Decision.APPROVE,
        )

        revision = create_diagnostic_record_revision(self.record, self.author)

        self.assertEqual(revision.revision, 2)
        self.assertEqual(revision.previous_revision, self.record)
        self.assertEqual(revision.status, DiagnosticRecord.Status.DRAFT)
        self.assertEqual(revision.measurements.count(), 1)
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, DiagnosticRecord.Status.APPROVED)

    def test_incomplete_submission_creates_qa_event(self):
        incomplete = DiagnosticRecord.objects.create(
            session=self.session,
            revision=2,
            created_by=self.author,
        )

        with self.assertRaises(ValidationError):
            submit_diagnostic_record(incomplete)

        event = QAEvent.objects.get(record=incomplete)
        self.assertEqual(event.code, "DIAGNOSTIC_RECORD_INCOMPLETE")

    def test_self_approval_is_blocked_and_audited(self):
        submit_diagnostic_record(self.record)

        with self.assertRaises(ValidationError):
            review_diagnostic_record(
                self.record,
                self.author,
                DiagnosticApproval.Decision.APPROVE,
            )

        self.assertTrue(
            QAEvent.objects.filter(
                record=self.record,
                code="DIAGNOSTIC_SELF_APPROVAL_BLOCKED",
            ).exists()
        )

    def test_checksum_detects_changes_during_review(self):
        submit_diagnostic_record(self.record)
        DiagnosticRecord.objects.filter(pk=self.record.pk).update(
            summary="Tampered while in review"
        )

        with self.assertRaises(ValidationError):
            review_diagnostic_record(
                self.record,
                self.reviewer,
                DiagnosticApproval.Decision.APPROVE,
            )

        event = QAEvent.objects.get(
            record=self.record,
            code="DIAGNOSTIC_RECORD_CHECKSUM_MISMATCH",
        )
        self.assertEqual(event.severity, QAEvent.Severity.CRITICAL)
