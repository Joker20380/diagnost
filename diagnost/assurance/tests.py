import uuid

from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from diagnostics.models import Vehicle
from users.models import Organization, TechnicianProfile, UserProfile, Workshop

from .models import (
    CaseOperation,
    EvidenceRequirement,
    ExpertReviewNotification,
    ExpertDecision,
    Operation,
    OperationDependency,
    ProcedureVersion,
    RepairProcedure,
    Skill,
    TechnicianSkill,
    WorkshopWalkthroughObservation,
)
from .notifications import dispatch_expert_review_notifications
from .services import (
    cancel_repair_case,
    complete_operation,
    create_repair_case,
    decide_operation,
    publish_procedure_version,
    skip_case_operation,
    submit_evidence,
    supersede_evidence,
    verify_repair_case,
)


class RepairAssuranceExecutionTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Assurance Garage", slug="assurance-garage"
        )
        self.workshop = Workshop.objects.create(
            organization=self.organization, name="Main", code="main"
        )
        self.senior_user = User.objects.create_user(
            "assurance-senior", email="senior@example.com"
        )
        self.junior_user = User.objects.create_user("assurance-junior")
        self.outsider_user = User.objects.create_user("assurance-outsider")
        self.senior_profile, _ = UserProfile.objects.get_or_create(user=self.senior_user)
        self.junior_profile, _ = UserProfile.objects.get_or_create(user=self.junior_user)
        self.outsider_profile, _ = UserProfile.objects.get_or_create(user=self.outsider_user)
        self.senior = TechnicianProfile.objects.create(
            user_profile=self.senior_profile,
            organization=self.organization,
            workshop=self.workshop,
            role=TechnicianProfile.Role.SENIOR_EXPERT,
        )
        self.junior = TechnicianProfile.objects.create(
            user_profile=self.junior_profile,
            organization=self.organization,
            workshop=self.workshop,
            role=TechnicianProfile.Role.JUNIOR_TECHNICIAN,
        )
        self.outsider = TechnicianProfile.objects.create(
            user_profile=self.outsider_profile,
            organization=self.organization,
            workshop=self.workshop,
            role=TechnicianProfile.Role.JUNIOR_TECHNICIAN,
        )
        self.vehicle = Vehicle.objects.create(
            organization=self.organization,
            vin="WBAJR71010B123456",
            make="BMW",
            model="5 Series",
            generation="G30",
            year=2020,
        )
        self.skill = Skill.objects.create(
            organization=self.organization,
            code="critical-fasteners",
            name="Critical fasteners",
        )
        TechnicianSkill.objects.create(
            technician=self.junior,
            skill=self.skill,
            level=2,
            verified_by=self.senior_profile,
        )
        self.procedure = RepairProcedure.objects.create(
            organization=self.organization,
            code="steering-rack-replacement",
            name="Steering rack replacement",
            created_by=self.senior_profile,
        )
        self.version = ProcedureVersion.objects.create(
            procedure=self.procedure,
            version=1,
            created_by=self.senior_profile,
        )
        self.scan = Operation.objects.create(
            version=self.version,
            key="pre-scan",
            sequence=1,
            title="Pre-repair diagnostic scan",
            description="Capture diagnostic scan.",
            operation_type=Operation.Type.DIAGNOSTIC_SCAN,
            minimum_role=TechnicianProfile.Role.JUNIOR_TECHNICIAN,
        )
        self.scan_requirement = EvidenceRequirement.objects.create(
            operation=self.scan,
            evidence_type=EvidenceRequirement.Type.DIAGNOSTIC_SCAN,
            description="Diagnostic result",
        )
        self.torque = Operation.objects.create(
            version=self.version,
            key="critical-torque",
            sequence=2,
            title="Critical fastener torque",
            description="Tighten the critical fastener.",
            operation_type=Operation.Type.MEASUREMENT,
            required_skill=self.skill,
            required_skill_level=2,
            minimum_role=TechnicianProfile.Role.JUNIOR_TECHNICIAN,
            approval_required=True,
            approval_minimum_role=TechnicianProfile.Role.SENIOR_EXPERT,
            specification={"target": "105", "unit": "Nm"},
        )
        OperationDependency.objects.create(
            operation=self.torque, depends_on=self.scan
        )
        self.torque_requirement = EvidenceRequirement.objects.create(
            operation=self.torque,
            evidence_type=EvidenceRequirement.Type.MEASUREMENT,
            description="Recorded torque",
            unit="Nm",
            minimum_value=Decimal("105"),
            maximum_value=Decimal("105"),
        )
        self.qc = Operation.objects.create(
            version=self.version,
            key="road-test",
            sequence=3,
            title="Road test",
            description="Perform final road test.",
            operation_type=Operation.Type.QC,
            qc_operation=True,
            minimum_role=TechnicianProfile.Role.JUNIOR_TECHNICIAN,
        )
        OperationDependency.objects.create(operation=self.qc, depends_on=self.torque)
        self.qc_requirement = EvidenceRequirement.objects.create(
            operation=self.qc,
            evidence_type=EvidenceRequirement.Type.CONFIRMATION,
            description="Road test passed",
        )
        publish_procedure_version(self.version, self.senior_user)
        self.version.refresh_from_db()
        self.case = create_repair_case(
            vehicle=self.vehicle,
            procedure_version=self.version,
            title="BMW G30 steering rack",
            complaint="Steering play",
            user=self.senior_user,
            workshop=self.workshop,
            technicians=[self.junior, self.senior],
        )

    def execution(self, operation):
        return self.case.case_operations.get(operation=operation)

    def test_assigned_mechanic_sees_simple_case_screen(self):
        self.client.force_login(self.junior_user)
        response = self.client.get(
            reverse("assurance:case_detail", args=[self.case.pk]),
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pre-repair diagnostic scan")
        self.assertContains(response, "BLOCKED")

    def test_unassigned_mechanic_cannot_open_case_screen(self):
        self.client.force_login(self.outsider_user)
        response = self.client.get(
            reverse("assurance:case_detail", args=[self.case.pk]),
            secure=True,
        )
        self.assertEqual(response.status_code, 404)

    def test_assigned_mechanic_records_workshop_observation(self):
        self.client.force_login(self.junior_user)
        response = self.client.post(
            reverse("assurance:record_walkthrough_observation", args=[self.case.pk]),
            {
                "case_operation": self.execution(self.scan).pk,
                "category": WorkshopWalkthroughObservation.Category.USABILITY,
                "severity": WorkshopWalkthroughObservation.Severity.HIGH,
                "description": "Evidence button was difficult to find on a tablet.",
                "expected_behavior": "Primary action remains visible while scrolling.",
            },
            secure=True,
        )
        self.assertRedirects(
            response,
            reverse("assurance:case_detail", args=[self.case.pk]),
            fetch_redirect_response=False,
        )
        observation = self.case.walkthrough_observations.get()
        self.assertEqual(observation.recorded_by, self.junior_profile)
        self.assertEqual(observation.case_operation, self.execution(self.scan))

    def test_outsider_cannot_record_workshop_observation(self):
        self.client.force_login(self.outsider_user)
        response = self.client.post(
            reverse("assurance:record_walkthrough_observation", args=[self.case.pk]),
            {
                "category": WorkshopWalkthroughObservation.Category.WORKFLOW,
                "severity": WorkshopWalkthroughObservation.Severity.LOW,
                "description": "Should not be accepted.",
            },
            secure=True,
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.case.walkthrough_observations.exists())

    def test_walkthrough_observation_is_append_only(self):
        observation = WorkshopWalkthroughObservation.objects.create(
            repair_case=self.case,
            category=WorkshopWalkthroughObservation.Category.SAFETY,
            severity=WorkshopWalkthroughObservation.Severity.BLOCKER,
            description="Safety instruction was ambiguous.",
            recorded_by=self.senior_profile,
        )
        observation.description = "Changed"
        with self.assertRaises(ValidationError):
            observation.save()

    def test_superuser_without_technician_profile_can_open_case_list(self):
        admin = User.objects.create_superuser(
            username="assurance-admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin)
        response = self.client.get(reverse("assurance:case_list"), secure=True)
        self.assertEqual(response.status_code, 200)

    def test_published_specification_is_immutable(self):
        self.scan.title = "Changed after publication"
        with self.assertRaises(ValidationError):
            self.scan.save()

    def test_case_creation_screen_is_manager_only(self):
        self.client.force_login(self.senior_user)
        response = self.client.get(reverse("assurance:case_create"), secure=True)
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.junior_user)
        response = self.client.get(reverse("assurance:case_create"), secure=True)
        self.assertEqual(response.status_code, 403)

    def test_direct_status_change_cannot_bypass_publication_service(self):
        draft = ProcedureVersion.objects.create(
            procedure=self.procedure,
            version=2,
            created_by=self.senior_profile,
        )
        draft.status = ProcedureVersion.Status.PUBLISHED
        with self.assertRaises(ValidationError):
            draft.save()

    def test_unassigned_technician_is_rejected_server_side(self):
        with self.assertRaises(PermissionDenied):
            submit_evidence(
                case_operation=self.execution(self.scan),
                user=self.outsider_user,
                requirement=self.scan_requirement,
                evidence_type=EvidenceRequirement.Type.DIAGNOSTIC_SCAN,
                text="scan",
            )

    def test_senior_can_filter_and_export_case_audit(self):
        self.client.force_login(self.senior_user)
        response = self.client.get(
            reverse("assurance:case_audit", args=[self.case.pk]),
            {"action": "case_created"},
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Audit trail")
        self.assertContains(response, "case_created")

        json_response = self.client.get(
            reverse(
                "assurance:case_audit_export",
                args=[self.case.pk, "json"],
            ),
            {"action": "case_created"},
            secure=True,
        )
        self.assertEqual(json_response.status_code, 200)
        self.assertEqual(
            [event["action"] for event in json_response.json()["events"]],
            ["case_created"],
        )
        self.assertIn("attachment;", json_response["Content-Disposition"])

        csv_response = self.client.get(
            reverse(
                "assurance:case_audit_export",
                args=[self.case.pk, "csv"],
            ),
            secure=True,
        )
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("case_created", csv_response.content.decode())
        self.assertEqual(csv_response["X-Content-Type-Options"], "nosniff")

    def test_junior_cannot_view_or_export_case_audit(self):
        self.client.force_login(self.junior_user)
        audit_url = reverse("assurance:case_audit", args=[self.case.pk])
        export_url = reverse(
            "assurance:case_audit_export",
            args=[self.case.pk, "csv"],
        )
        self.assertEqual(self.client.get(audit_url, secure=True).status_code, 403)
        self.assertEqual(self.client.get(export_url, secure=True).status_code, 403)

    def test_unknown_repair_certificate_is_not_disclosed(self):
        response = self.client.get(
            reverse("assurance:repair_certificate", args=[uuid.uuid4()]),
            secure=True,
        )
        self.assertEqual(response.status_code, 404)


    def test_evidence_supersession_preserves_history_and_active_count(self):
        execution = self.execution(self.scan)
        original = submit_evidence(
            case_operation=execution,
            user=self.junior_user,
            requirement=self.scan_requirement,
            evidence_type=EvidenceRequirement.Type.DIAGNOSTIC_SCAN,
            text="Incorrect scan result",
        )

        replacement = supersede_evidence(
            evidence=original,
            user=self.junior_user,
            text="Corrected scan result",
            reason="Wrong vehicle report was selected.",
        )

        original.refresh_from_db()
        self.assertEqual(original.text, "Incorrect scan result")
        self.assertEqual(replacement.supersedes, original)
        self.assertEqual(
            replacement.metadata["supersession"]["reason"],
            "Wrong vehicle report was selected.",
        )
        self.assertTrue(original.is_superseded)
        self.assertFalse(replacement.is_superseded)
        self.assertEqual(
            execution.evidence.filter(superseded_by__isnull=True).count(),
            1,
        )
        event = self.case.audit_events.get(action="evidence_superseded")
        self.assertEqual(event.payload["superseded_evidence_id"], original.pk)
        self.assertEqual(event.payload["evidence_id"], replacement.pk)

        with self.assertRaisesMessage(
            ValidationError, "Evidence has already been superseded."
        ):
            supersede_evidence(
                evidence=original,
                user=self.junior_user,
                text="Conflicting branch",
                reason="Must not create a second replacement.",
            )

        complete_operation(execution, self.junior_user)
        execution.refresh_from_db()
        self.assertEqual(execution.status, CaseOperation.Status.COMPLETED)

    def test_only_senior_can_approve_skip_and_it_unlocks_dependents(self):
        scan_execution = self.execution(self.scan)
        torque_execution = self.execution(self.torque)

        with self.assertRaises(PermissionDenied):
            skip_case_operation(
                case_operation=scan_execution,
                user=self.junior_user,
                rationale="Diagnostic tool is unavailable.",
            )

        approved_exception = skip_case_operation(
            case_operation=scan_execution,
            user=self.senior_user,
            rationale="Diagnostic tool is unavailable; manager approved manual checks.",
        )

        scan_execution.refresh_from_db()
        torque_execution.refresh_from_db()
        self.assertEqual(scan_execution.status, CaseOperation.Status.SKIPPED)
        self.assertEqual(torque_execution.status, CaseOperation.Status.AVAILABLE)
        self.assertEqual(
            approved_exception.authorized_by,
            self.senior_profile,
        )
        self.assertTrue(
            self.case.audit_events.filter(
                action="operation_exception_approved",
                case_operation=scan_execution,
            ).exists()
        )

    def test_case_cancellation_is_controlled_and_closes_all_execution(self):
        with self.assertRaises(PermissionDenied):
            cancel_repair_case(
                case=self.case,
                user=self.junior_user,
                rationale="Customer withdrew authorization.",
            )

        cancel_repair_case(
            case=self.case,
            user=self.senior_user,
            rationale="Customer withdrew authorization.",
        )

        self.case.refresh_from_db()
        self.assertEqual(self.case.status, self.case.Status.CANCELLED)
        self.assertFalse(
            self.case.case_operations.exclude(
                status=CaseOperation.Status.SKIPPED
            ).exists()
        )
        with self.assertRaisesMessage(ValidationError, "repair case is closed"):
            submit_evidence(
                case_operation=self.execution(self.scan),
                user=self.junior_user,
                requirement=self.scan_requirement,
                evidence_type=EvidenceRequirement.Type.DIAGNOSTIC_SCAN,
                text="Late evidence",
            )
        self.assertTrue(self.case.audit_events.filter(action="case_cancelled").exists())

    def test_complete_repair_with_gates_approval_verification_and_record(self):
        scan_execution = self.execution(self.scan)
        torque_execution = self.execution(self.torque)
        qc_execution = self.execution(self.qc)
        self.assertEqual(scan_execution.status, CaseOperation.Status.AVAILABLE)
        self.assertEqual(torque_execution.status, CaseOperation.Status.LOCKED)
        self.assertEqual(qc_execution.status, CaseOperation.Status.LOCKED)

        with self.assertRaises(ValidationError):
            complete_operation(scan_execution, self.junior_user)

        scan_evidence = submit_evidence(
            case_operation=scan_execution,
            user=self.junior_user,
            requirement=self.scan_requirement,
            evidence_type=EvidenceRequirement.Type.DIAGNOSTIC_SCAN,
            text="No active steering faults",
        )
        complete_operation(scan_execution, self.junior_user)
        torque_execution.refresh_from_db()
        self.assertEqual(torque_execution.status, CaseOperation.Status.AVAILABLE)

        measurement = submit_evidence(
            case_operation=torque_execution,
            user=self.junior_user,
            requirement=self.torque_requirement,
            evidence_type=EvidenceRequirement.Type.MEASUREMENT,
            numeric_value=Decimal("105"),
            unit="Nm",
        )
        complete_operation(torque_execution, self.junior_user)
        torque_execution.refresh_from_db()
        qc_execution.refresh_from_db()
        self.assertEqual(torque_execution.status, CaseOperation.Status.REQUIRES_REVIEW)
        self.assertEqual(qc_execution.status, CaseOperation.Status.LOCKED)
        notification = ExpertReviewNotification.objects.get(
            case_operation=torque_execution,
            recipient=self.senior_profile,
        )
        self.assertEqual(notification.status, ExpertReviewNotification.Status.QUEUED)
        self.assertTrue(
            self.case.audit_events.filter(action="expert_review_queued").exists()
        )
        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            ASSURANCE_REVIEW_BASE_URL="https://diagnost.example",
        ):
            result = dispatch_expert_review_notifications()
        self.assertEqual(result, {"sent": 1, "failed": 0})
        notification.refresh_from_db()
        self.assertEqual(notification.status, ExpertReviewNotification.Status.SENT)
        self.assertIn("https://diagnost.example", mail.outbox[0].body)


        decision = decide_operation(
            case_operation=torque_execution,
            user=self.senior_user,
            decision=ExpertDecision.Decision.APPROVE,
            rationale="Torque evidence is within specification.",
            evidence=[measurement],
        )
        self.assertEqual(decision.authorized_operation_keys, ["road-test"])
        qc_execution.refresh_from_db()
        self.assertEqual(qc_execution.status, CaseOperation.Status.AVAILABLE)

        confirmation = submit_evidence(
            case_operation=qc_execution,
            user=self.junior_user,
            requirement=self.qc_requirement,
            evidence_type=EvidenceRequirement.Type.CONFIRMATION,
            text="Road test passed; steering centered.",
        )
        complete_operation(qc_execution, self.junior_user)
        verification = verify_repair_case(self.case, self.senior_user)
        self.case.refresh_from_db()

        self.assertEqual(
            verification.status, self.case.VerificationStatus.VERIFIED
        )
        self.assertEqual(self.case.status, self.case.Status.COMPLETED)
        self.assertTrue(hasattr(self.case, "repair_record"))
        self.assertEqual(
            self.case.repair_record.snapshot["procedure"]["version"], 1
        )
        self.assertGreaterEqual(self.case.audit_events.count(), 10)

        self.client.logout()
        certificate_response = self.client.get(
            reverse(
                "assurance:repair_certificate",
                args=[self.case.repair_record.public_id],
            ),
            secure=True,
        )
        self.assertEqual(certificate_response.status_code, 200)
        self.assertContains(certificate_response, "Repair Certificate")
        self.assertContains(certificate_response, "***********123456")
        self.assertNotContains(certificate_response, "WBAJR71010B123456")
        self.assertNotContains(
            certificate_response, "Torque evidence is within specification."
        )

        scan_evidence.text = "mutated"
        with self.assertRaises(ValidationError):
            scan_evidence.save()
        with self.assertRaises(ValidationError):
            confirmation.delete()
