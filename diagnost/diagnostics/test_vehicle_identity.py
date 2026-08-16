from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from users.models import Organization, TechnicianProfile, UserProfile, Workshop

from .launch_pdf_parser import apply_launch_parse_to_session
from .vehicle_identity import assess_vehicle_completeness
from .models import (
    DiagnosticSession,
    Vehicle,
    VehicleConfiguration,
    VehicleIdentityObservation,
)


class VehicleIdentityWorkflowTests(TestCase):
    def setUp(self):
        self.org_a = Organization.objects.create(name="Garage A", slug="garage-a")
        self.org_b = Organization.objects.create(name="Garage B", slug="garage-b")
        self.workshop_a = Workshop.objects.create(
            organization=self.org_a, name="A", code="a"
        )
        self.workshop_b = Workshop.objects.create(
            organization=self.org_b, name="B", code="b"
        )
        self.user_a = User.objects.create_user("vehicle-a", password="pass")
        self.user_b = User.objects.create_user("vehicle-b", password="pass")
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
            raw_file=SimpleUploadedFile("vehicle.pdf", b"%PDF-1.4\n%%EOF"),
        )
        apply_launch_parse_to_session(
            self.session,
            {
                "vehicle": {
                    "vin": "WVWZZZ1JZXW000001",
                    "brand": "Volkswagen",
                    "model": "Golf",
                    "year": "2021",
                    "mileage": "42 000 км",
                },
                "faults": [],
            },
        )

    def test_parser_preserves_original_without_creating_vehicle(self):
        observation = self.session.vehicle_identity_observation
        self.assertEqual(observation.original_data["model"], "Golf")
        self.assertEqual(observation.status, VehicleIdentityObservation.Status.PENDING)
        self.assertFalse(Vehicle.objects.exists())

    def test_technician_confirms_and_correction_is_separate(self):
        self.client.force_login(self.user_a)
        response = self.client.post(
            reverse("vehicle_identity_confirm", args=[self.session.pk]),
            {
                "vin": "WVWZZZ1JZXW000001",
                "brand": "Volkswagen",
                "model": "Golf VIII",
                "year": 2021,
                "engine_code": "DACA",
                "mileage": 42000,
            },
            secure=True,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("diagnostic_detail", args=[self.session.pk]))
        self.session.refresh_from_db()
        observation = self.session.vehicle_identity_observation
        self.assertEqual(observation.original_data["model"], "Golf")
        self.assertEqual(observation.corrections["model"], "Golf VIII")
        self.assertEqual(observation.status, VehicleIdentityObservation.Status.CONFIRMED)
        self.assertEqual(self.session.vehicle.organization, self.org_a)
        self.assertEqual(self.session.vehicle_configuration.engine_code, "DACA")
        self.assertEqual(
            self.session.vehicle_configuration.completeness_status,
            VehicleConfiguration.CompletenessStatus.INCOMPLETE,
        )
        self.assertIn("variant_or_generation", self.session.vehicle_configuration.missing_fields)

    def test_complete_configuration_is_explicit(self):
        assessment = assess_vehicle_completeness(
            {
                "vin": "WVWZZZ1JZXW000001",
                "brand": "Volkswagen",
                "model": "Golf",
                "year": "2021",
                "engine_code": "DACA",
                "variant": "GTI",
            }
        )
        self.assertEqual(
            assessment.status, VehicleConfiguration.CompletenessStatus.COMPLETE
        )
        self.assertEqual(assessment.missing_fields, [])
        self.assertEqual(assessment.review_reasons, [])

    def test_invalid_vin_requires_review(self):
        assessment = assess_vehicle_completeness(
            {
                "vin": "INVALID",
                "brand": "Volkswagen",
                "model": "Golf",
                "year": "2021",
                "engine_code": "DACA",
                "generation": "VIII",
            }
        )
        self.assertEqual(
            assessment.status,
            VehicleConfiguration.CompletenessStatus.NEEDS_REVIEW,
        )
        self.assertEqual(assessment.review_reasons, ["vin_format_requires_review"])

    def test_other_tenant_cannot_open_confirmation(self):
        self.client.force_login(self.user_b)
        response = self.client.get(
            reverse("vehicle_identity_confirm", args=[self.session.pk])
            , secure=True
        )
        self.assertEqual(response.status_code, 404)

    def test_same_vin_is_scoped_per_organization(self):
        Vehicle.objects.create(
            organization=self.org_a, vin="WVWZZZ1JZXW000001"
        )
        Vehicle.objects.create(
            organization=self.org_b, vin="WVWZZZ1JZXW000001"
        )
        self.assertEqual(Vehicle.objects.count(), 2)

    def test_parser_rerun_does_not_overwrite_confirmed_identity(self):
        self.client.force_login(self.user_a)
        self.client.post(
            reverse("vehicle_identity_confirm", args=[self.session.pk]),
            {
                "vin": "WVWZZZ1JZXW000001",
                "brand": "Volkswagen",
                "model": "Golf VIII",
                "year": 2021,
                "mileage": 42000,
            },
            secure=True,
        )
        apply_launch_parse_to_session(
            self.session,
            {"vehicle": {"vin": "WRONG", "model": "Wrong"}, "faults": []},
        )
        observation = self.session.vehicle_identity_observation
        observation.refresh_from_db()
        self.assertEqual(observation.original_data["model"], "Golf")
        self.assertEqual(observation.corrections["model"], "Golf VIII")
