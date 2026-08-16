from __future__ import annotations

from django.utils import timezone

from .models import DiagnosticCase, DiagnosticSession, VehicleIdentityObservation


ANALYSIS_READY_STATUSES = {
    DiagnosticCase.Status.READY,
    DiagnosticCase.Status.IN_PROGRESS,
    DiagnosticCase.Status.ESCALATED,
    DiagnosticCase.Status.RESOLVED,
    DiagnosticCase.Status.CLOSED,
}


def session_facts_are_confirmed(session: DiagnosticSession) -> bool:
    try:
        case = session.diagnostic_case
    except DiagnosticCase.DoesNotExist:
        return True  # Compatibility for legacy sessions created before DiagnosticCase.

    if case.status not in ANALYSIS_READY_STATUSES or not case.intake_complete:
        return False
    return VehicleIdentityObservation.objects.filter(
        session=session,
        status=VehicleIdentityObservation.Status.CONFIRMED,
    ).exists()


def _recommendation_for_code(code) -> str:
    description = code.description.strip()
    if not description and code.reference_id:
        description = code.reference.title_ru
    description = description or "Описание отсутствует"
    return (
        f"{code.code} — {description}\n"
        f"→ Модуль: {code.module_code or '—'} {code.module_name or ''}. "
        f"Статус: {code.status_text or '—'}. "
        "Сначала проверить питание, массу, разъёмы, проводку и сопутствующие ошибки."
    )


def sync_session_analysis_gate(session: DiagnosticSession) -> bool:
    session = DiagnosticSession.objects.get(pk=session.pk)
    if not session_facts_are_confirmed(session):
        session.recommendation = ""
        session.analysis_method = ""
        session.analysis_engine = ""
        session.analysis_version = ""
        session.analysis_generated_at = None
        session.ai_generated_at = None
        session.save(
            update_fields=[
                "recommendation",
                "analysis_method",
                "analysis_engine",
                "analysis_version",
                "analysis_generated_at",
                "ai_generated_at",
            ]
        )
        return False

    current_parse_run = session.parse_runs.filter(
        status="succeeded", is_current=True
    ).first()
    codes = (
        session.codes.filter(parse_run=current_parse_run)
        if current_parse_run
        else session.codes.filter(parse_run__isnull=True)
    ).select_related("reference")
    parser = (session.system_report or {}).get("parser") or {}
    session.recommendation = "\n\n".join(
        _recommendation_for_code(code) for code in codes
    )
    session.analysis_method = DiagnosticSession.AnalysisMethod.RULES
    session.analysis_engine = parser.get("name") or "launch_all_system_dtc_pdf"
    session.analysis_version = parser.get("version") or "2.0.0"
    session.analysis_generated_at = timezone.now()
    session.ai_generated_at = None
    session.save(
        update_fields=[
            "recommendation",
            "analysis_method",
            "analysis_engine",
            "analysis_version",
            "analysis_generated_at",
            "ai_generated_at",
        ]
    )
    return True
