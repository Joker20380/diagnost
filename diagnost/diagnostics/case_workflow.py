from __future__ import annotations

from typing import Iterable

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    CustomerComplaint,
    DiagnosticCase,
    DiagnosticSession,
    OperatingConditions,
    RecentRepair,
    Symptom,
    VehicleIdentityObservation,
)


ALLOWED_TRANSITIONS = {
    DiagnosticCase.Status.INTAKE: {
        DiagnosticCase.Status.IDENTITY_PENDING,
        DiagnosticCase.Status.READY,
        DiagnosticCase.Status.CANCELLED,
    },
    DiagnosticCase.Status.IDENTITY_PENDING: {
        DiagnosticCase.Status.READY,
        DiagnosticCase.Status.CANCELLED,
    },
    DiagnosticCase.Status.READY: {
        DiagnosticCase.Status.IN_PROGRESS,
        DiagnosticCase.Status.CANCELLED,
    },
    DiagnosticCase.Status.IN_PROGRESS: {
        DiagnosticCase.Status.ESCALATED,
        DiagnosticCase.Status.RESOLVED,
        DiagnosticCase.Status.CANCELLED,
    },
    DiagnosticCase.Status.ESCALATED: {
        DiagnosticCase.Status.IN_PROGRESS,
        DiagnosticCase.Status.RESOLVED,
        DiagnosticCase.Status.CANCELLED,
    },
    DiagnosticCase.Status.RESOLVED: {DiagnosticCase.Status.CLOSED},
    DiagnosticCase.Status.CLOSED: set(),
    DiagnosticCase.Status.CANCELLED: set(),
}


def _technician_profile(session: DiagnosticSession, user):
    profile = getattr(user, "userprofile", None)
    technician = getattr(profile, "technician_profile", None) if profile else None
    if (
        technician is None
        or not technician.is_active
        or technician.organization_id != session.organization_id
    ):
        raise PermissionDenied("An active technician in this organization is required.")
    return profile


def ensure_diagnostic_case(session: DiagnosticSession, user) -> DiagnosticCase:
    profile = _technician_profile(session, user)
    case, _ = DiagnosticCase.objects.get_or_create(
        session=session,
        defaults={
            "organization": session.organization,
            "workshop": session.workshop,
            "created_by": profile,
            "assigned_to": profile,
        },
    )
    return case


def _nonempty_lines(value: str) -> Iterable[str]:
    return (line.strip() for line in (value or "").splitlines() if line.strip())


@transaction.atomic
def update_case_intake(
    *,
    case: DiagnosticCase,
    user,
    complaint: str,
    customer_words: str = "",
    onset: str = "",
    frequency: str = "",
    symptoms: str,
    recent_repairs: str = "",
    operating_conditions: str = "",
    intermittent: bool = False,
) -> DiagnosticCase:
    profile = _technician_profile(case.session, user)
    case = DiagnosticCase.objects.select_for_update().get(pk=case.pk)
    if case.status not in {
        DiagnosticCase.Status.INTAKE,
        DiagnosticCase.Status.IDENTITY_PENDING,
        DiagnosticCase.Status.READY,
    }:
        raise ValidationError("Intake cannot be changed after diagnostics have started.")
    if not complaint.strip():
        raise ValidationError({"complaint": "Customer complaint is required."})
    symptom_lines = list(_nonempty_lines(symptoms))
    if not symptom_lines:
        raise ValidationError({"symptoms": "At least one symptom is required."})

    CustomerComplaint.objects.update_or_create(
        case=case,
        defaults={
            "description": complaint.strip(),
            "customer_words": customer_words.strip(),
            "onset": onset.strip(),
            "frequency": frequency.strip(),
            "recorded_by": profile,
        },
    )
    case.symptoms.all().delete()
    Symptom.objects.bulk_create(
        [
            Symptom(case=case, description=line, recorded_by=profile)
            for line in symptom_lines
        ]
    )
    case.recent_repairs.all().delete()
    RecentRepair.objects.bulk_create(
        [
            RecentRepair(case=case, description=line, recorded_by=profile)
            for line in _nonempty_lines(recent_repairs)
        ]
    )
    OperatingConditions.objects.update_or_create(
        case=case,
        defaults={
            "description": operating_conditions.strip(),
            "intermittent": intermittent,
            "recorded_by": profile,
        },
    )
    identity_confirmed = VehicleIdentityObservation.objects.filter(
        session=case.session,
        status=VehicleIdentityObservation.Status.CONFIRMED,
    ).exists()
    case.status = (
        DiagnosticCase.Status.READY
        if identity_confirmed
        else DiagnosticCase.Status.IDENTITY_PENDING
    )
    case.save(update_fields=["status", "updated_at"])
    return case


@transaction.atomic
def transition_diagnostic_case(
    *, case: DiagnosticCase, user, target_status: str
) -> DiagnosticCase:
    _technician_profile(case.session, user)
    case = DiagnosticCase.objects.select_for_update().get(pk=case.pk)
    if target_status not in ALLOWED_TRANSITIONS.get(case.status, set()):
        raise ValidationError(
            f"Transition from {case.status} to {target_status} is not allowed."
        )
    if target_status == DiagnosticCase.Status.READY:
        if not case.intake_complete:
            raise ValidationError("Complaint and at least one symptom are required.")
        if not VehicleIdentityObservation.objects.filter(
            session=case.session,
            status=VehicleIdentityObservation.Status.CONFIRMED,
        ).exists():
            raise ValidationError("Vehicle identity must be confirmed.")
    now = timezone.now()
    case.status = target_status
    update_fields = ["status", "updated_at"]
    if target_status == DiagnosticCase.Status.IN_PROGRESS:
        case.started_at = now
        update_fields.append("started_at")
    elif target_status == DiagnosticCase.Status.RESOLVED:
        case.resolved_at = now
        update_fields.append("resolved_at")
    elif target_status == DiagnosticCase.Status.CLOSED:
        case.closed_at = now
        update_fields.append("closed_at")
    case.save(update_fields=update_fields)
    return case
