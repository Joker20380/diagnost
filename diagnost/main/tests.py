from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from .models import ContactRequest, Subscriber
from diagnostics.models import DiagnosticSession, QAEvent, SuspensionPartType
from users.models import UserProfile


class PublicFormProtectionTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_contact_form_validates_email(self):
        response = self.client.post(reverse('contacts'), {
            'name': 'Test',
            'email': 'not-an-email',
            'message': 'Question',
        }, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ContactRequest.objects.exists())

    def test_contact_honeypot_is_silently_ignored(self):
        response = self.client.post(reverse('contacts'), {
            'name': 'Bot',
            'email': 'bot@example.com',
            'message': 'Spam',
            'website': 'https://spam.invalid',
        }, secure=True)
        self.assertRedirects(response, reverse('contacts'), fetch_redirect_response=False)
        self.assertFalse(ContactRequest.objects.exists())

    def test_contact_rate_limit_blocks_immediate_repeat(self):
        payload = {
            'name': 'Test',
            'email': 'test@example.com',
            'message': 'Question',
        }
        self.client.post(reverse('contacts'), payload, secure=True)
        self.client.post(reverse('contacts'), payload, secure=True)
        self.assertEqual(ContactRequest.objects.count(), 1)

    def test_resubscribe_reactivates_existing_subscriber(self):
        subscriber = Subscriber.objects.create(email='user@example.com', is_active=False)
        response = self.client.post(
            reverse('subscribe'),
            {'email': 'USER@example.com'},
            secure=True,
        )
        self.assertRedirects(response, reverse('index'), fetch_redirect_response=False)
        subscriber.refresh_from_db()
        self.assertTrue(subscriber.is_active)
        self.assertEqual(Subscriber.objects.count(), 1)


class DiagnosticUploadFailureTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='upload-user',
            password='test-password',
        )
        UserProfile.objects.get_or_create(user=self.user)
        self.client.force_login(self.user)

    @patch(
        'diagnostics.launch_pdf_parser.parse_and_apply_launch_pdf',
        side_effect=ValueError('broken report'),
    )
    def test_parser_failure_preserves_auditable_session(self, mocked_parser):
        report = SimpleUploadedFile(
            'launch.pdf',
            b'%PDF-1.4\n%%EOF\n',
            content_type='application/pdf',
        )
        response = self.client.post(
            reverse('diagnostic_upload'),
            {
                'vin': 'TESTVIN',
                'vehicle_model': 'Test vehicle',
                'raw_file': report,
            },
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Не удалось прочитать отчёт Launch')
        session = DiagnosticSession.objects.get()
        self.assertEqual(session.status, "parse_failed")
        event = QAEvent.objects.get(session=session)
        self.assertEqual(event.code, "LAUNCH_PDF_PARSE_FAILED")
        self.assertEqual(event.details["error_class"], "ValueError")
        mocked_parser.assert_called_once()

class SuspensionQAEventTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("qa-inspector")
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.client.force_login(self.user)
        self.session = DiagnosticSession.objects.create(
            user_profile=self.profile,
            raw_file=SimpleUploadedFile(
                "qa.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf"
            ),
        )
        self.part_type = SuspensionPartType.objects.create(name="Ball joint")

    def test_high_wear_without_replacement_creates_qa_event(self):
        response = self.client.post(
            reverse("suspension_inspection", args=[self.session.pk]),
            {
                "inspector": self.profile.pk,
                "mileage_km": 100000,
                "lift_used": "on",
                "overall_risk": "high",
                "comment": "Play detected",
                "parts-TOTAL_FORMS": "1",
                "parts-INITIAL_FORMS": "0",
                "parts-MIN_NUM_FORMS": "0",
                "parts-MAX_NUM_FORMS": "1000",
                "parts-0-part_type": self.part_type.pk,
                "parts-0-wear_percent": "70",
                "parts-0-severity": "crit",
                "parts-0-reason": "play",
                "parts-0-evidence": "Measured play",
                "parts-0-part_number": "",
                "action": "save",
            },
            secure=True,
        )

        self.assertRedirects(
            response,
            reverse("diagnostic_detail", args=[self.session.pk]),
            fetch_redirect_response=False,
        )
        event = QAEvent.objects.get(session=self.session)
        self.assertEqual(event.code, "SUSPENSION_REPLACEMENT_MISMATCH")
        self.assertEqual(event.details["wear_percent"], 70)
