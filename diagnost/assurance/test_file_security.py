from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from .file_security import inspect_evidence_file, scan_with_clamd
from .models import EvidenceRequirement


@override_settings(
    LANGUAGE_CODE="en",
    ASSURANCE_EVIDENCE_MAX_FILE_SIZE=1024,
    ASSURANCE_EVIDENCE_RETENTION_DAYS=2555,
)
class EvidenceFileSecurityTests(SimpleTestCase):
    @patch(
        "assurance.file_security.scan_with_clamd",
        return_value="stream: OK",
    )
    def test_clean_pdf_is_scanned_and_security_metadata_is_returned(self, scanner):
        uploaded = SimpleUploadedFile(
            "scan.pdf",
            b"%PDF-1.7\nclean diagnostic report",
            content_type="application/pdf",
        )

        result = inspect_evidence_file(
            uploaded, EvidenceRequirement.Type.DIAGNOSTIC_SCAN
        )

        scanner.assert_called_once_with(uploaded)
        self.assertEqual(result["detected_mime_type"], "application/pdf")
        self.assertEqual(result["malware_scan"], "clean")
        self.assertEqual(result["retention_days"], 2555)
        self.assertEqual(uploaded.tell(), 0)

    @patch("assurance.file_security.scan_with_clamd")
    def test_oversized_file_is_rejected_before_scanning(self, scanner):
        uploaded = SimpleUploadedFile(
            "scan.txt", b"x" * 1025, content_type="text/plain"
        )

        with self.assertRaisesMessage(ValidationError, "exceeds the 0 MB limit"):
            inspect_evidence_file(
                uploaded, EvidenceRequirement.Type.DIAGNOSTIC_SCAN
            )

        scanner.assert_not_called()

    @patch("assurance.file_security.scan_with_clamd")
    def test_declared_mime_must_match_file_signature(self, scanner):
        uploaded = SimpleUploadedFile(
            "fake.jpg",
            b"%PDF-1.7\nnot an image",
            content_type="image/jpeg",
        )

        with self.assertRaisesMessage(ValidationError, "declared MIME type"):
            inspect_evidence_file(uploaded, EvidenceRequirement.Type.CONFIRMATION)

        scanner.assert_not_called()

    @override_settings(
        ASSURANCE_CLAMD_HOST="clamav",
        ASSURANCE_CLAMD_PORT=3310,
        ASSURANCE_CLAMD_TIMEOUT_SECONDS=1,
    )
    @patch("assurance.file_security.socket.create_connection")
    def test_scanner_unavailable_fails_closed(self, connection):
        connection.side_effect = OSError("connection refused")
        uploaded = SimpleUploadedFile(
            "scan.pdf", b"%PDF-1.7\nclean", content_type="application/pdf"
        )

        with self.assertRaisesMessage(
            ValidationError, "Malware scanner is unavailable"
        ):
            scan_with_clamd(uploaded)

        self.assertEqual(uploaded.tell(), 0)
