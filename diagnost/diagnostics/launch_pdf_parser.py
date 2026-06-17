from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from django.utils import timezone

from diagnostics.models import DiagnosticCode, DTCReference


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


def get_or_create_dtc_reference_from_launch_fault(fault: dict[str, str]) -> DTCReference:
    code = normalize_code(fault.get("code"))
    description = (fault.get("description") or "").strip()
    module_code = (fault.get("module_code") or "").strip()
    module_name = (fault.get("module_name") or "").strip()

    system = detect_system(code)

    title = description[:500] if description else f"Код неисправности {code}"

    ref, _ = DTCReference.objects.update_or_create(
        code=code,
        manufacturer="",
        defaults={
            "system": system,
            "scope": DTCReference.Scope.MANUFACTURER if system == "O" else DTCReference.Scope.GENERIC,
            "title_ru": title,
            "description_ru": (
                f"Код {code} найден в отчёте Launch."
                + (f" Модуль: {module_code} ({module_name})." if module_code or module_name else "")
                + (f" Описание: {description}" if description else "")
            ),
            "diagnostic_notes": (
                "Код получен из отчёта Launch AllSystemDTC. "
                "Для точного вывода нужно учитывать модуль, статус ошибки, сопутствующие коды, "
                "питание, массу, проводку, разъёмы и фактические симптомы автомобиля."
            ),
            "recommended_checks": (
                "Проверить модуль, указанный в отчёте; считать сопутствующие блоки; "
                "проверить питание, массу, разъёмы, проводку и условия появления ошибки. "
                "Не менять блок или деталь только по одному коду."
            ),
            "severity": DTCReference.Severity.MEDIUM,
            "source_name": "Launch diagnostic report",
            "is_active": True,
        },
    )

    return ref


def apply_launch_parse_to_session(session, parsed: dict[str, Any]) -> int:
    vehicle = parsed.get("vehicle") or {}
    faults = parsed.get("faults") or []

    if vehicle.get("vin"):
        session.vin = vehicle["vin"]

    model_parts = []
    if vehicle.get("brand"):
        model_parts.append(vehicle["brand"])
    if vehicle.get("model"):
        model_parts.append(vehicle["model"])

    if model_parts:
        session.vehicle_model = " ".join(model_parts)

    session.system_report = {
        "source": "launch_pdf",
        "vehicle": vehicle,
        "abnormal_systems": parsed.get("abnormal_systems") or [],
        "ok_systems": parsed.get("ok_systems") or [],
    }

    DiagnosticCode.objects.filter(session=session).delete()

    created = 0
    recommendation_lines = []

    for fault in faults:
        code = normalize_code(fault.get("code"))
        description = (fault.get("description") or "").strip()

        if not code:
            continue

        ref = get_or_create_dtc_reference_from_launch_fault(fault)

        DiagnosticCode.objects.create(
            session=session,
            code=code,
            description=description[:500],
            module_code=(fault.get("module_code") or "")[:64],
            module_name=(fault.get("module_name") or "")[:255],
            status_text=(fault.get("status") or "")[:64],
            raw_text=description,
            reference=ref,
        )

        created += 1

        recommendation_lines.append(
            f"{code} — {description or ref.title_ru}\n"
            f"→ Модуль: {fault.get('module_code') or '—'} {fault.get('module_name') or ''}. "
            f"Статус: {fault.get('status') or '—'}. "
            f"Сначала проверить питание, массу, разъёмы, проводку и сопутствующие ошибки."
        )

    if recommendation_lines:
        session.recommendation = "\n\n".join(recommendation_lines)
        session.ai_generated_at = timezone.now()

    session.save(update_fields=[
        "vin",
        "vehicle_model",
        "system_report",
        "recommendation",
        "ai_generated_at",
    ])

    return created


def parse_and_apply_launch_pdf(session) -> int:
    if not session.raw_file:
        return 0

    path = session.raw_file.path

    if not str(path).lower().endswith(".pdf"):
        return 0

    parsed = parse_launch_pdf(path)
    return apply_launch_parse_to_session(session, parsed)
