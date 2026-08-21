from __future__ import annotations

import socket
import struct

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from .models import EvidenceRequirement


ALLOWED_MIME_TYPES = {
    EvidenceRequirement.Type.PHOTO: {"image/jpeg", "image/png"},
    EvidenceRequirement.Type.VIDEO: {"video/mp4"},
    EvidenceRequirement.Type.DOCUMENT: {"application/pdf"},
    EvidenceRequirement.Type.DIAGNOSTIC_SCAN: {"application/pdf", "text/plain"},
    EvidenceRequirement.Type.TEXT: {"application/pdf", "text/plain"},
    EvidenceRequirement.Type.CONFIRMATION: {
        "application/pdf", "image/jpeg", "image/png"
    },
}


def detect_mime_type(header: bytes) -> str | None:
    if header.startswith(b"%PDF-"):
        return "application/pdf"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(header) >= 12 and header[4:8] == b"ftyp":
        return "video/mp4"
    if header and b"\x00" not in header:
        try:
            header.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            return "text/plain"
    return None


def _read_clamd_response(connection) -> str:
    chunks = []
    while True:
        chunk = connection.recv(4096)
        if not chunk:
            break
        chunks.append(chunk)
        if b"\x00" in chunk:
            break
    return b"".join(chunks).rstrip(b"\x00").decode("utf-8", errors="replace")


def scan_with_clamd(uploaded_file) -> str:
    position = uploaded_file.tell()
    try:
        with socket.create_connection(
            (settings.ASSURANCE_CLAMD_HOST, settings.ASSURANCE_CLAMD_PORT),
            timeout=settings.ASSURANCE_CLAMD_TIMEOUT_SECONDS,
        ) as connection:
            connection.settimeout(settings.ASSURANCE_CLAMD_TIMEOUT_SECONDS)
            connection.sendall(b"zINSTREAM\x00")
            while True:
                chunk = uploaded_file.read(64 * 1024)
                if not chunk:
                    break
                connection.sendall(struct.pack("!I", len(chunk)))
                connection.sendall(chunk)
            connection.sendall(struct.pack("!I", 0))
            response = _read_clamd_response(connection)
    except (OSError, socket.timeout) as exc:
        raise ValidationError(_("Malware scanner is unavailable; the file was not accepted.")) from exc
    finally:
        uploaded_file.seek(position)

    if response.endswith(" OK"):
        return response
    if " FOUND" in response:
        raise ValidationError(_("Malware was detected; the file was not accepted."))
    raise ValidationError(_("Malware scan failed; the file was not accepted."))


def inspect_evidence_file(uploaded_file, evidence_type: str) -> dict:
    maximum_size = settings.ASSURANCE_EVIDENCE_MAX_FILE_SIZE
    if uploaded_file.size > maximum_size:
        raise ValidationError(
            _("Evidence file exceeds the %(limit)s MB limit.")
            % {"limit": maximum_size // (1024 * 1024)}
        )

    position = uploaded_file.tell()
    header = uploaded_file.read(4096)
    uploaded_file.seek(position)
    detected_mime = detect_mime_type(header)
    if detected_mime not in ALLOWED_MIME_TYPES.get(evidence_type, set()):
        raise ValidationError(_("Evidence file format is not allowed for this evidence type."))

    claimed_mime = (getattr(uploaded_file, "content_type", "") or "").lower()
    if claimed_mime and claimed_mime != detected_mime:
        raise ValidationError(_("Evidence file content does not match its declared MIME type."))

    scan_result = scan_with_clamd(uploaded_file)
    return {
        "detected_mime_type": detected_mime,
        "file_size": uploaded_file.size,
        "malware_scan": "clean",
        "malware_scanner": "clamd",
        "malware_scan_result": scan_result,
        "retention_days": settings.ASSURANCE_EVIDENCE_RETENTION_DAYS,
    }
