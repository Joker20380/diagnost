from __future__ import annotations

import hashlib
import json

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .models import (
    DiagnosticApproval,
    DiagnosticMeasurement,
    DiagnosticRecord,
    QAEvent,
)
from users.models import UserProfile


def diagnostic_record_snapshot(record: DiagnosticRecord) -> dict:
    measurements = [
        {
            "id": measurement.id,
            "parameter": measurement.parameter,
            "value_text": measurement.value_text,
            "numeric_value": (
                str(measurement.numeric_value)
                if measurement.numeric_value is not None
                else None
            ),
            "unit": measurement.unit,
            "reference_min": (
                str(measurement.reference_min)
                if measurement.reference_min is not None
                else None
            ),
            "reference_max": (
                str(measurement.reference_max)
                if measurement.reference_max is not None
                else None
            ),
            "result": measurement.result,
            "method": measurement.method,
            "tool_name": measurement.tool_name,
            "evidence_note": measurement.evidence_note,
            "measured_by_id": measurement.measured_by_id,
            "measured_at": measurement.measured_at.isoformat(),
        }
        for measurement in record.measurements.select_related("measured_by").all()
    ]
    return {
        "session_id": record.session_id,
        "revision": record.revision,
        "previous_revision_id": record.previous_revision_id,
        "created_by_id": record.created_by_id,
        "summary": record.summary,
        "confirmed_cause": record.confirmed_cause,
        "recommended_work": record.recommended_work,
        "safety_notes": record.safety_notes,
        "measurements": measurements,
    }


def diagnostic_record_checksum(record: DiagnosticRecord) -> str:
    payload = json.dumps(
        diagnostic_record_snapshot(record),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def submit_diagnostic_record(record: DiagnosticRecord) -> DiagnosticRecord:
    record = DiagnosticRecord.objects.get(pk=record.pk)
    if record.status not in {
        DiagnosticRecord.Status.DRAFT,
        DiagnosticRecord.Status.REJECTED,
    }:
        raise ValidationError("Only a draft or rejected record can be submitted.")
    if not record.summary.strip() or not record.confirmed_cause.strip():
        QAEvent.objects.create(
            session=record.session,
            record=record,
            code="DIAGNOSTIC_RECORD_INCOMPLETE",
            severity=QAEvent.Severity.ERROR,
            message="Summary and confirmed cause are required before review.",
        )
        raise ValidationError("Summary and confirmed cause are required before review.")
    if not record.measurements.exists():
        QAEvent.objects.create(
            session=record.session,
            record=record,
            code="DIAGNOSTIC_RECORD_NO_MEASUREMENTS",
            severity=QAEvent.Severity.ERROR,
            message="At least one control measurement is required before review.",
        )
        raise ValidationError("At least one control measurement is required before review.")

    record.status = DiagnosticRecord.Status.IN_REVIEW
    record.submitted_at = timezone.now()
    record.content_sha256 = diagnostic_record_checksum(record)
    record.save(
        update_fields=["status", "submitted_at", "content_sha256", "updated_at"]
    )
    return record


def review_diagnostic_record(
    record: DiagnosticRecord,
    reviewer: UserProfile,
    decision: str,
    comment: str = "",
) -> DiagnosticApproval:
    record = DiagnosticRecord.objects.get(pk=record.pk)
    if record.status != DiagnosticRecord.Status.IN_REVIEW:
        raise ValidationError("Only a record in review can receive a decision.")
    if reviewer.pk == record.created_by_id:
        QAEvent.objects.create(
            session=record.session,
            record=record,
            code="DIAGNOSTIC_SELF_APPROVAL_BLOCKED",
            severity=QAEvent.Severity.ERROR,
            message="The author cannot approve their own diagnostic record.",
        )
        raise ValidationError("The author cannot review their own diagnostic record.")
    if decision not in DiagnosticApproval.Decision.values:
        raise ValidationError("Unsupported review decision.")

    current_checksum = diagnostic_record_checksum(record)
    if current_checksum != record.content_sha256:
        QAEvent.objects.create(
            session=record.session,
            record=record,
            code="DIAGNOSTIC_RECORD_CHECKSUM_MISMATCH",
            severity=QAEvent.Severity.CRITICAL,
            message="Diagnostic record changed after submission.",
            details={
                "submitted_checksum": record.content_sha256,
                "current_checksum": current_checksum,
            },
        )
        raise ValidationError("Diagnostic record changed after submission.")

    approval = DiagnosticApproval.objects.create(
        record=record,
        reviewer=reviewer,
        decision=decision,
        comment=comment,
        snapshot_sha256=current_checksum,
    )
    if decision == DiagnosticApproval.Decision.APPROVE:
        record.status = DiagnosticRecord.Status.APPROVED
        record.approved_at = approval.decided_at
    else:
        record.status = DiagnosticRecord.Status.REJECTED
        record.approved_at = None
    record.save(update_fields=["status", "approved_at", "updated_at"])
    return approval


@transaction.atomic
def create_diagnostic_record_revision(
    approved_record: DiagnosticRecord,
    created_by: UserProfile,
) -> DiagnosticRecord:
    approved_record = DiagnosticRecord.objects.select_for_update().get(
        pk=approved_record.pk
    )
    if approved_record.status != DiagnosticRecord.Status.APPROVED:
        raise ValidationError("Only an approved record can be corrected by revision.")

    highest_revision = (
        DiagnosticRecord.objects.filter(session=approved_record.session)
        .aggregate(value=Max("revision"))["value"]
        or 0
    )
    revision = DiagnosticRecord.objects.create(
        session=approved_record.session,
        revision=highest_revision + 1,
        previous_revision=approved_record,
        created_by=created_by,
        summary=approved_record.summary,
        confirmed_cause=approved_record.confirmed_cause,
        recommended_work=approved_record.recommended_work,
        safety_notes=approved_record.safety_notes,
    )
    DiagnosticMeasurement.objects.bulk_create(
        [
            DiagnosticMeasurement(
                record=revision,
                parameter=item.parameter,
                value_text=item.value_text,
                numeric_value=item.numeric_value,
                unit=item.unit,
                reference_min=item.reference_min,
                reference_max=item.reference_max,
                result=item.result,
                method=item.method,
                tool_name=item.tool_name,
                evidence_note=item.evidence_note,
                measured_by=item.measured_by,
                measured_at=item.measured_at,
            )
            for item in approved_record.measurements.all()
        ]
    )
    return revision
