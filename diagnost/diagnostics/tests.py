from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from users.models import UserProfile

from .forms import DiagnosticUploadForm
from .models import DiagnosticSession


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
