from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from django.db import transaction
from django.utils import timezone

from diagnostics.analysis_gate import session_facts_are_confirmed, sync_session_analysis_gate
from diagnostics.models import (
    DiagnosticCode,
    DiagnosticParseRun,
    DiagnosticSession,
    VehicleIdentityObservation,
    QAEvent,
    DTCReference,
)


PARSER_NAME = "launch_all_system_dtc_pdf"
PARSER_VERSION = "2.0.0"


STATUS_WORDS = {
    "Permanent",
    "Intermittent",
    "Current",
    "History",
    "Stored",
    "Pending",
    "Present",
}


def normalize_code(value: str) -> str:
    value = (value or "").strip().upper()
    value = re.sub(r"\s+", "", value)
    return value


def detect_system(code: str) -> str:
    code = normalize_code(code)

    if code and code[0] in ["P", "C", "B", "U"]:
        return code[0]

    return "O"


def extract_pdf_text(path: str | Path) -> str:
    path = Path(path)

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is not installed. Run: pip install pypdf") from exc

    reader = PdfReader(str(path))
    parts = []

    for page in reader.pages:
        text = page.extract_text() or ""
        parts.append(text)

    return "\n".join(parts)


def extract_field(text: str, label: str) -> str:
    pattern = rf"{re.escape(label)}\s*:?\s*([^\n\r]+)"
    m = re.search(pattern, text, flags=re.I)

    if not m:
        return ""

    return m.group(1).strip()


def parse_vehicle_info(text: str) -> dict[str, str]:
    return {
        "test_time": extract_field(text, "Время испытания"),
        "year": extract_field(text, "Год выпуска"),
        "brand": extract_field(text, "Серии а/м"),
        "model": extract_field(text, "Модель"),
        "vin": extract_field(text, "VIN"),
        "mileage": extract_field(text, "Пробег"),
        "vehicle_software": extract_field(text, "Версия ПО а/м"),
        "diagnostic_app_version": extract_field(text, "Версия диагностической прикладной программы"),
        "diagnostic_path": extract_field(text, "Диагностический путь"),
        "serial_number": extract_field(text, "Серийный номер"),
    }


def parse_ok_systems(text: str) -> list[dict[str, str]]:
    marker = "Следующие системы в порядке:"
    if marker not in text:
        return []

    tail = text.split(marker, 1)[1]
    systems = []

    for raw_line in tail.splitlines():
        line = raw_line.strip()

        m = re.match(r"^\s*(\d+)\.([A-Z0-9/\-]+)\s+\((.+?)\)\s*$", line)
        if m:
            systems.append({
                "index": m.group(1),
                "module_code": m.group(2).strip(),
                "module_name": m.group(3).strip(),
            })

    return systems


def parse_fault_start(line: str) -> tuple[str, str] | None:
    """
    Examples:
    1.930AB2 Контрольная лампа ...
    2.D90D38 Функциональный центр ...
    1.S 0248 Нет связи с ...
    """
    m = re.match(r"^\s*\d+\.(.+?)\s*$", line)
    if not m:
        return None

    rest = m.group(1).strip()

    code_match = re.match(
        r"^("
        r"[PCBU][0-9A-Z]{4,8}"
        r"|[A-Z][0-9A-F]{4,8}"
        r"|[0-9A-F]{4,8}"
        r"|S\s*[0-9A-F]{4,8}"
        r")\s*(.*)$",
        rest,
        flags=re.I,
    )

    if not code_match:
        return None

    code = normalize_code(code_match.group(1))
    description = (code_match.group(2) or "").strip()

    return code, description


def parse_abnormal_systems(text: str) -> list[dict[str, Any]]:
    start_marker = "The following systems is abnormal:"
    end_marker = "Следующие системы в порядке:"

    if start_marker not in text:
        return []

    block = text.split(start_marker, 1)[1]

    if end_marker in block:
        block = block.split(end_marker, 1)[0]

    lines = [line.strip() for line in block.splitlines() if line.strip()]

    systems: list[dict[str, Any]] = []
    current_system: dict[str, Any] | None = None
    current_fault: dict[str, Any] | None = None

    module_pattern = re.compile(
        r"^([A-Z0-9/\-]+)\s+\((.+?)\)\s+(\d+)\s+Существуют проблемы",
        flags=re.I,
    )

    def flush_fault():
        nonlocal current_fault, current_system

        if current_fault and current_system:
            desc_lines = current_fault.pop("_desc_lines", [])
            full_description = " ".join(x.strip() for x in desc_lines if x.strip())
            current_fault["description"] = re.sub(r"\s+", " ", full_description).strip()
            current_system["faults"].append(current_fault)

        current_fault = None

    for line in lines:
        module_match = module_pattern.match(line)

        if module_match:
            flush_fault()

            current_system = {
                "module_code": module_match.group(1).strip(),
                "module_name": module_match.group(2).strip(),
                "declared_fault_count": int(module_match.group(3)),
                "faults": [],
            }
            systems.append(current_system)
            continue

        fault_start = parse_fault_start(line)

        if fault_start:
            flush_fault()

            code, first_description = fault_start
            current_fault = {
                "code": code,
                "status": "",
                "_desc_lines": [first_description] if first_description else [],
            }
            continue

        if current_fault:
            if line in STATUS_WORDS:
                current_fault["status"] = line
                flush_fault()
            else:
                current_fault["_desc_lines"].append(line)

    flush_fault()

    return systems


def parse_launch_pdf(path: str | Path) -> dict[str, Any]:
    text = extract_pdf_text(path)
    vehicle = parse_vehicle_info(text)
    abnormal_systems = parse_abnormal_systems(text)
    ok_systems = parse_ok_systems(text)

    faults = []

    for system in abnormal_systems:
        for fault in system["faults"]:
            faults.append({
                "code": fault["code"],
                "description": fault["description"],
                "status": fault.get("status", ""),
                "module_code": system["module_code"],
                "module_name": system["module_name"],
            })

    return {
        "vehicle": vehicle,
        "abnormal_systems": abnormal_systems,
        "ok_systems": ok_systems,
        "faults": faults,
        "raw_text": text,
    }


def calculate_file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_dtc_reference(code: str, manufacturer: str = "") -> DTCReference | None:
    """Resolve verified knowledge without promoting a case observation into it."""
    code = normalize_code(code)
    manufacturer = (manufacturer or "").strip()
    if not code:
        return None

    if manufacturer:
        reference = DTCReference.objects.filter(
            code=code,
            manufacturer__iexact=manufacturer,
            is_active=True,
        ).first()
        if reference:
            return reference

    return DTCReference.objects.filter(
        code=code,
        manufacturer="",
        is_active=True,
    ).first()


def apply_launch_parse_to_session(
    session: DiagnosticSession,
    parsed: dict[str, Any],
    parse_run: DiagnosticParseRun | None = None,
) -> int:
    vehicle = parsed.get("vehicle") or {}
    faults = parsed.get("faults") or []
    manufacturer = (vehicle.get("brand") or "").strip()

    with transaction.atomic():
        observation, created = VehicleIdentityObservation.objects.get_or_create(
            session=session,
            defaults={
                "parse_run": parse_run,
                "original_data": vehicle,
            },
        )
        if not created and observation.status == VehicleIdentityObservation.Status.PENDING:
            observation.parse_run = parse_run
            observation.original_data = vehicle
            observation.save(
                update_fields=["parse_run", "original_data"]
            )
        identity_confirmed = (
            observation.status == VehicleIdentityObservation.Status.CONFIRMED
        )

        if not identity_confirmed and vehicle.get("vin"):
            session.vin = vehicle["vin"]

        model_parts = []
        if manufacturer:
            model_parts.append(manufacturer)
        if vehicle.get("model"):
            model_parts.append(vehicle["model"])

        if not identity_confirmed and model_parts:
            session.vehicle_model = " ".join(model_parts)

        session.system_report = {
            "source": "launch_pdf",
            "parser": {
                "name": PARSER_NAME,
                "version": PARSER_VERSION,
                "parse_run_id": parse_run.pk if parse_run else None,
            },
            "vehicle": vehicle,
            "abnormal_systems": parsed.get("abnormal_systems") or [],
            "ok_systems": parsed.get("ok_systems") or [],
        }

        observations = DiagnosticCode.objects.filter(session=session)
        if parse_run:
            observations.filter(parse_run=parse_run).delete()
        else:
            observations.filter(parse_run__isnull=True).delete()

        created = 0
        recommendation_lines = []

        for fault in faults:
            code = normalize_code(fault.get("code"))
            description = (fault.get("description") or "").strip()
            if not code:
                continue

            reference = find_dtc_reference(code, manufacturer)
            display_description = description or (
                reference.title_ru if reference else "Описание отсутствует"
            )

            DiagnosticCode.objects.create(
                session=session,
                code=code,
                description=description[:500],
                module_code=(fault.get("module_code") or "")[:64],
                module_name=(fault.get("module_name") or "")[:255],
                status_text=(fault.get("status") or "")[:64],
                raw_text=description,
                is_known=reference is not None,
                reference=reference,
                parse_run=parse_run,
            )
            created += 1

            recommendation_lines.append(
                f"{code} — {display_description}\n"
                f"→ Модуль: {fault.get('module_code') or '—'} {fault.get('module_name') or ''}. "
                f"Статус: {fault.get('status') or '—'}. "
                "Сначала проверить питание, массу, разъёмы, проводку и сопутствующие ошибки."
            )

        analysis_allowed = session_facts_are_confirmed(session)
        session.recommendation = (
            "\n\n".join(recommendation_lines) if analysis_allowed else ""
        )
        session.analysis_method = (
            DiagnosticSession.AnalysisMethod.RULES if analysis_allowed else ""
        )
        session.analysis_engine = PARSER_NAME if analysis_allowed else ""
        session.analysis_version = PARSER_VERSION if analysis_allowed else ""
        session.analysis_generated_at = timezone.now() if analysis_allowed else None
        session.ai_generated_at = None
        session.save(update_fields=[
            "vin",
            "vehicle_model",
            "system_report",
            "recommendation",
            "analysis_method",
            "analysis_engine",
            "analysis_version",
            "analysis_generated_at",
            "ai_generated_at",
        ])

    return created


def parse_and_apply_launch_pdf(session: DiagnosticSession) -> int:
    if not session.raw_file:
        return 0

    path = session.raw_file.path
    if not str(path).lower().endswith(".pdf"):
        return 0

    content_sha256 = calculate_file_sha256(path)
    parse_run, created = DiagnosticParseRun.objects.get_or_create(
        session=session,
        parser_name=PARSER_NAME,
        parser_version=PARSER_VERSION,
        content_sha256=content_sha256,
        defaults={
            "source_type": "launch_pdf",
            "status": DiagnosticParseRun.Status.PENDING,
        },
    )

    if not created and parse_run.status == DiagnosticParseRun.Status.SUCCEEDED:
        return parse_run.code_observations.count()

    if not created:
        parse_run.status = DiagnosticParseRun.Status.PENDING
        parse_run.error_message = ""
        parse_run.completed_at = None
        parse_run.save(update_fields=["status", "error_message", "completed_at"])

    try:
        parsed = parse_launch_pdf(path)
        fault_count = apply_launch_parse_to_session(session, parsed, parse_run=parse_run)
    except Exception as exc:
        parse_run.status = DiagnosticParseRun.Status.FAILED
        parse_run.error_message = str(exc)[:2000]
        parse_run.completed_at = timezone.now()
        parse_run.save(update_fields=["status", "error_message", "completed_at"])
        QAEvent.objects.create(
            session=session,
            code="LAUNCH_PDF_PARSE_FAILED",
            severity=QAEvent.Severity.ERROR,
            message="Launch PDF parsing failed.",
            details={
                "parse_run_id": parse_run.pk,
                "parser_name": PARSER_NAME,
                "parser_version": PARSER_VERSION,
                "content_sha256": content_sha256,
                "error_class": type(exc).__name__,
                "error_message": str(exc)[:2000],
            },
        )
        raise

    with transaction.atomic():
        DiagnosticParseRun.objects.filter(
            session=session,
            is_current=True,
        ).exclude(pk=parse_run.pk).update(is_current=False)
        parse_run.status = DiagnosticParseRun.Status.SUCCEEDED
        parse_run.is_current = True
        parse_run.fault_count = fault_count
        parse_run.completed_at = timezone.now()
        parse_run.metadata = {
            "vehicle_fields_present": sorted(
                key for key, value in (parsed.get("vehicle") or {}).items() if value
            ),
            "abnormal_system_count": len(parsed.get("abnormal_systems") or []),
            "ok_system_count": len(parsed.get("ok_systems") or []),
        }
        parse_run.save(update_fields=[
            "status",
            "is_current",
            "fault_count",
            "completed_at",
            "metadata",
        ])
    sync_session_analysis_gate(session)
    return fault_count
