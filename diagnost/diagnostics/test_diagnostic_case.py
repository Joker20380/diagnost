from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from users.models import Organization, TechnicianProfile, UserProfile, Workshop

from .case_workflow import (
    ensure_diagnostic_case,
    transition_diagnostic_case,
)
from .launch_pdf_parser import apply_launch_parse_to_session
from .models import DiagnosticCase, DiagnosticSession


class DiagnosticCaseWorkflowTests(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(name="Case Garage A", slug="case-a")
        self.org_b = Organization.objects.create(name="Case Garage B", slug="case-b")
        self.workshop_a = Workshop.objects.create(
            organization=self.org_a, name="A", code="a"
        )
        self.workshop_b = Workshop.objects.create(
            organization=self.org_b, name="B", code="b"
        )
        self.user_a = User.objects.create_user("case-user-a", password="pass")
        self.user_b = User.objects.create_user("case-user-b", password="pass")
        self.profile_a, _ = UserProfile.objects.get_or_create(user=self.user_a)
        self.profile_b, _ = UserProfile.objects.get_or_create(user=self.user_b)
        TechnicianProfile.objects.create(
            user_profile=self.profile_a,
            organization=self.org_a,
            workshop=self.workshop_a,
        )
        TechnicianProfile.objects.create(
            user_profile=self.profile_b,
            organization=self.org_b,
            workshop=self.workshop_b,
        )
        self.session = DiagnosticSession.objects.create(
            user_profile=self.profile_a,
            organization=self.org_a,
            workshop=self.workshop_a,
            raw_file=SimpleUploadedFile("case.pdf", b"%PDF-1.4\n%%EOF"),
        )
        self.case = ensure_diagnostic_case(self.session, self.user_a)
        apply_launch_parse_to_session(
            self.session,
            {
                "vehicle": {
                    "vin": "WVWZZZ1JZXW000002",
                    "brand": "Volkswagen",
                    "model": "Golf",
                    "year": "2021",
                },
                "faults": [
                    {
                        "code": "P0100",
                        "description": "Mass air flow circuit",
                        "module_code": "ECM",
                        "module_name": "Engine",
                        "status": "Current",
                    }
                ],
            },
        )

    def test_intake_creates_structured_facts_and_waits_for_identity(self):
        self.client.force_login(self.user_a)
        response = self.client.post(
            reverse("diagnostic_case_intake", args=[self.session.pk]),
            {
                "complaint": "Engine loses power",
                "customer_words": "Не едет в гору",
                "onset": "Two days ago",
                "frequency": "Every trip",
                "symptoms": "Loss of power\nCheck engine lamp",
                "recent_repairs": "Fuel filter replaced",
                "operating_conditions": "Warm engine, uphill",
                "intermittent": "on",
            },
            secure=True,
        )
        self.assertEqual(response.status_code, 302)
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, DiagnosticCase.Status.IDENTITY_PENDING)
        self.assertEqual(self.case.symptoms.count(), 2)
        self.assertEqual(self.case.recent_repairs.count(), 1)
        self.assertEqual(
            self.case.customer_complaint.description, "Engine loses power"
        )
        self.assertTrue(self.case.operating_conditions.intermittent)
        self.session.refresh_from_db()
        self.assertEqual(self.session.recommendation, "")
        self.assertIsNone(self.session.analysis_generated_at)

    def test_confirmed_identity_promotes_completed_intake_to_ready(self):
        self.client.force_login(self.user_a)
        self.client.post(
            reverse("diagnostic_case_intake", args=[self.session.pk]),
            {"complaint": "No start", "symptoms": "Starter turns"},
            secure=True,
        )
        self.client.post(
            reverse("vehicle_identity_confirm", args=[self.session.pk]),
            {
                "vin": "WVWZZZ1JZXW000002",
                "brand": "Volkswagen",
                "model": "Golf",
                "year": 2021,
            },
            secure=True,
        )
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, DiagnosticCase.Status.READY)
        self.session.refresh_from_db()
        self.assertIn("P0100", self.session.recommendation)
        self.assertIsNotNone(self.session.analysis_generated_at)
        self.assertEqual(self.session.analysis_method, "rules")

    def test_cannot_start_before_intake_and_identity_are_ready(self):
        with self.assertRaises(ValidationError):
            transition_diagnostic_case(
                case=self.case,
                user=self.user_a,
                target_status=DiagnosticCase.Status.IN_PROGRESS,
            )

    def test_ready_case_can_start(self):
        self.client.force_login(self.user_a)
        self.client.post(
            reverse("diagnostic_case_intake", args=[self.session.pk]),
            {"complaint": "No start", "symptoms": "Starter turns"},
            secure=True,
        )
        self.client.post(
            reverse("vehicle_identity_confirm", args=[self.session.pk]),
            {
                "vin": "WVWZZZ1JZXW000002",
                "brand": "Volkswagen",
                "model": "Golf",
                "year": 2021,
            },
            secure=True,
        )
        transition_diagnostic_case(
            case=self.case,
            user=self.user_a,
            target_status=DiagnosticCase.Status.IN_PROGRESS,
        )
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, DiagnosticCase.Status.IN_PROGRESS)
        self.assertIsNotNone(self.case.started_at)

    def test_other_tenant_cannot_open_intake(self):
        self.client.force_login(self.user_b)
        response = self.client.get(
            reverse("diagnostic_case_intake", args=[self.session.pk]),
            secure=True,
        )
        self.assertEqual(response.status_code, 404)

    def test_identity_needing_review_does_not_unlock_analysis(self):
        self.client.force_login(self.user_a)
        self.client.post(
            reverse("diagnostic_case_intake", args=[self.session.pk]),
            {"complaint": "No start", "symptoms": "Starter turns"},
            secure=True,
        )
        self.client.post(
            reverse("vehicle_identity_confirm", args=[self.session.pk]),
            {
                "vin": "INVALID",
                "brand": "Volkswagen",
                "model": "Golf",
                "year": 2021,
                "engine_code": "DACA",
                "generation": "VIII",
            },
            secure=True,
        )
        self.case.refresh_from_db()
        self.session.refresh_from_db()
        self.assertEqual(self.case.status, DiagnosticCase.Status.IDENTITY_PENDING)
        self.assertEqual(self.session.recommendation, "")
        self.assertIsNone(self.session.analysis_generated_at)
