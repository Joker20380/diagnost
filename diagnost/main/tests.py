from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from .models import ContactRequest, Subscriber
from diagnostics.models import DiagnosticSession
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
    def test_parser_failure_does_not_leave_session(self, mocked_parser):
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
        self.assertFalse(DiagnosticSession.objects.exists())
        mocked_parser.assert_called_once()
