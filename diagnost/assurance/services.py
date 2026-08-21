from __future__ import annotations

import hashlib
import json
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from users.models import TechnicianProfile, UserProfile

from .file_security import inspect_evidence_file
from .models import (
    CaseOperation,
    Evidence,
    EvidenceRequirement,
    ExpertDecision,
    ExpertDecisionEvidence,
    Operation,
    ProcedureVersion,
    RepairAuditEvent,
    RepairCase,
    RepairCaseTechnician,
    RepairRecord,
    Verification,
)


ROLE_LEVEL = {
    TechnicianProfile.Role.SERVICE_ADVISOR: 0,
    TechnicianProfile.Role.JUNIOR_TECHNICIAN: 1,
    TechnicianProfile.Role.DIAGNOSTIC_TECHNICIAN: 2,
    TechnicianProfile.Role.SENIOR_EXPERT: 3,
    TechnicianProfile.Role.TECHNICAL_MANAGER: 4,
    TechnicianProfile.Role.AUDITOR: 0,
}


def _profile(user) -> UserProfile:
    profile = getattr(user, "userprofile", None)
    if profile is None:
        raise PermissionDenied("User profile is required.")
    return profile


def _technician(user, organization_id) -> TechnicianProfile:
    profile = _profile(user)
    technician = getattr(profile, "technician_profile", None)
    if (
        technician is None
        or not technician.is_active
        or technician.organization_id != organization_id
    ):
        raise PermissionDenied("Active technician in this organization is required.")
    return technician


def _audit(case, actor, action, *, case_operation=None, before="", after="", payload=None):
    return RepairAuditEvent.objects.create(
        repair_case=case,
        case_operation=case_operation,
        actor=actor,
        action=action,
        before_status=before,
        after_status=after,
        payload=payload or {},
    )


def procedure_snapshot(version: ProcedureVersion) -> dict:
    operations = []
    for operation in version.operations.prefetch_related(
        "dependencies__depends_on", "evidence_requirements", "reference_media"
    ).select_related("required_skill"):
        operations.append(
            {
                "key": operation.key,
                "sequence": operation.sequence,
                "title": operation.title,
                "description": operation.description,
                "operation_type": operation.operation_type,
                "mandatory": operation.mandatory,
                "blocking": operation.blocking,
                "qc_operation": operation.qc_operation,
                "expected_result": operation.expected_result,
                "technical_requirements": operation.technical_requirements,
                "required_tools": operation.required_tools,
                "specification": operation.specification,
                "required_skill": operation.required_skill.code if operation.required_skill else "",
                "required_skill_level": operation.required_skill_level,
                "minimum_role": operation.minimum_role,
                "approval_required": operation.approval_required,
                "approval_minimum_role": operation.approval_minimum_role,
                "dependencies": sorted(item.depends_on.key for item in operation.dependencies.all()),
                "evidence_requirements": [
                    {
                        "type": requirement.evidence_type,
                        "required": requirement.required,
                        "minimum_count": requirement.minimum_count,
                        "unit": requirement.unit,
                        "minimum_value": str(requirement.minimum_value) if requirement.minimum_value is not None else None,
                        "maximum_value": str(requirement.maximum_value) if requirement.maximum_value is not None else None,
                        "description": requirement.description,
                    }
                    for requirement in operation.evidence_requirements.all()
                ],
                "reference_media": [
                    {
                        "source_type": media.source_type,
                        "provider": media.provider,
                        "provider_asset_id": media.provider_asset_id,
                        "source_url": media.source_url,
                        "start_seconds": media.start_seconds,
                        "end_seconds": media.end_seconds,
                    }
                    for media in operation.reference_media.all()
                ],
            }
        )
    return {
        "procedure_id": version.procedure_id,
        "procedure_code": version.procedure.code,
        "procedure_name": version.procedure.name,
        "version": version.version,
        "operations": operations,
    }


def _checksum(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


@transaction.atomic
def publish_procedure_version(version: ProcedureVersion, user) -> ProcedureVersion:
    profile = _profile(user)
    version = ProcedureVersion.objects.select_for_update().select_related("procedure").get(pk=version.pk)
    technician = _technician(user, version.procedure.organization_id)
    if ROLE_LEVEL.get(technician.role, -1) < 3:
        raise PermissionDenied("Senior or technical manager role is required.")
    if version.status != ProcedureVersion.Status.DRAFT:
        raise ValidationError("Only a draft version can be published.")
    operations = list(version.operations.prefetch_related("dependencies"))
    if not operations:
        raise ValidationError("Procedure version must contain operations.")
    for operation in operations:
        for dependency in operation.dependencies.all():
            if dependency.depends_on.sequence >= operation.sequence:
                raise ValidationError("Dependencies must point to an earlier operation.")
    snapshot = procedure_snapshot(version)
    ProcedureVersion.objects.filter(pk=version.pk).update(
        status=ProcedureVersion.Status.PUBLISHED,
        content_sha256=_checksum(snapshot),
        published_at=timezone.now(),
    )
    version.refresh_from_db()
    return version


@transaction.atomic
def create_repair_case(
    *,
    vehicle,
    procedure_version: ProcedureVersion,
    title: str,
    complaint: str,
    user,
    workshop=None,
    technicians=(),
) -> RepairCase:
    creator = _technician(user, vehicle.organization_id)
    profile = creator.user_profile
    procedure_version = ProcedureVersion.objects.select_related("procedure").get(pk=procedure_version.pk)
    if procedure_version.status != ProcedureVersion.Status.PUBLISHED:
        raise ValidationError("Repair cases require a published procedure version.")
    if procedure_version.procedure.organization_id != vehicle.organization_id:
        raise ValidationError("Vehicle and procedure belong to different organizations.")
    case = RepairCase.objects.create(
        organization=vehicle.organization,
        workshop=workshop,
        vehicle=vehicle,
        procedure_version=procedure_version,
        title=title,
        complaint=complaint,
        status=RepairCase.Status.IN_PROGRESS,
        created_by=profile,
        started_at=timezone.now(),
    )
    assigned = list(technicians) or [creator]
    for technician in assigned:
        RepairCaseTechnician.objects.create(
            repair_case=case, technician=technician, assigned_by=profile
        )
    operations = list(procedure_version.operations.prefetch_related("dependencies"))
    executions = []
    for operation in operations:
        initial = (
            CaseOperation.Status.AVAILABLE
            if not operation.dependencies.exists()
            else CaseOperation.Status.LOCKED
        )
        executions.append(
            CaseOperation(repair_case=case, operation=operation, status=initial)
        )
    CaseOperation.objects.bulk_create(executions)
    _audit(case, profile, "case_created", before="", after=case.status, payload={"procedure_version_id": procedure_version.pk})
    return case


def assert_operation_authorized(case_operation: CaseOperation, user) -> TechnicianProfile:
    technician = _technician(user, case_operation.repair_case.organization_id)
    if not RepairCaseTechnician.objects.filter(
        repair_case=case_operation.repair_case, technician=technician
    ).exists():
        raise PermissionDenied("Technician is not assigned to this repair case.")
    operation = case_operation.operation
    required_role_level = ROLE_LEVEL.get(operation.minimum_role, 0)
    if ROLE_LEVEL.get(technician.role, -1) < required_role_level:
        raise PermissionDenied("Technician role is insufficient for this operation.")
    if operation.required_skill_id:
        skill = technician.assurance_skills.filter(
            skill=operation.required_skill,
            level__gte=operation.required_skill_level,
        ).first()
        if skill is None:
            raise PermissionDenied("Required verified skill level is missing.")
    return technician


def _validate_evidence_payload(requirement, evidence_type, file, text, numeric_value, unit):
    if requirement and requirement.evidence_type != evidence_type:
        raise ValidationError("Evidence type does not match the requirement.")
    if evidence_type in {
        EvidenceRequirement.Type.PHOTO,
        EvidenceRequirement.Type.VIDEO,
        EvidenceRequirement.Type.DOCUMENT,
    } and not file:
        raise ValidationError("This evidence type requires a file.")
    if evidence_type in {
        EvidenceRequirement.Type.TEXT,
        EvidenceRequirement.Type.CONFIRMATION,
        EvidenceRequirement.Type.DIAGNOSTIC_SCAN,
    } and not (text or file):
        raise ValidationError("Text or file evidence is required.")
    if evidence_type == EvidenceRequirement.Type.MEASUREMENT:
        if numeric_value is None:
            raise ValidationError("Measurement value is required.")
        if requirement and requirement.unit and unit != requirement.unit:
            raise ValidationError("Measurement unit does not match the requirement.")


@transaction.atomic
def submit_evidence(
    *,
    case_operation: CaseOperation,
    user,
    evidence_type: str,
    requirement=None,
    file=None,
    text="",
    numeric_value=None,
    unit="",
    metadata=None,
) -> Evidence:
    case_operation = CaseOperation.objects.select_for_update().select_related(
        "repair_case", "operation"
    ).get(pk=case_operation.pk)
    technician = assert_operation_authorized(case_operation, user)
    if case_operation.status not in {CaseOperation.Status.AVAILABLE, CaseOperation.Status.IN_PROGRESS}:
        raise ValidationError("Evidence can only be submitted for an available operation.")
    if requirement and requirement.operation_id != case_operation.operation_id:
        raise ValidationError("Evidence requirement belongs to another operation.")
    _validate_evidence_payload(requirement, evidence_type, file, text, numeric_value, unit)
    evidence_metadata = dict(metadata or {})
    if file:
        evidence_metadata["file_security"] = inspect_evidence_file(
            file, evidence_type
        )
    digest = ""
    if file:
        position = file.tell()
        digest = hashlib.sha256(file.read()).hexdigest()
        file.seek(position)
    evidence = Evidence.objects.create(
        repair_case=case_operation.repair_case,
        case_operation=case_operation,
        operation=case_operation.operation,
        requirement=requirement,
        evidence_type=evidence_type,
        file=file,
        text=text,
        numeric_value=numeric_value,
        unit=unit,
        metadata=evidence_metadata,
        content_sha256=digest,
        submitted_by=technician.user_profile,
    )
    before = case_operation.status
    if before == CaseOperation.Status.AVAILABLE:
        case_operation.status = CaseOperation.Status.IN_PROGRESS
        case_operation.started_at = timezone.now()
        case_operation.save(update_fields=["status", "started_at"])
    _audit(case_operation.repair_case, technician.user_profile, "evidence_submitted", case_operation=case_operation, before=before, after=case_operation.status, payload={"evidence_id": evidence.pk, "type": evidence_type})
    return evidence


def _missing_requirements(case_operation):
    missing = []
    for requirement in case_operation.operation.evidence_requirements.filter(required=True):
        count = case_operation.evidence.filter(requirement=requirement).count()
        if count < requirement.minimum_count:
            missing.append(requirement)
    return missing


def _measurement_out_of_range(case_operation):
    failures = []
    for evidence in case_operation.evidence.filter(evidence_type=EvidenceRequirement.Type.MEASUREMENT).select_related("requirement"):
        requirement = evidence.requirement
        if not requirement or evidence.numeric_value is None:
            continue
        if requirement.minimum_value is not None and evidence.numeric_value < requirement.minimum_value:
            failures.append(evidence)
        if requirement.maximum_value is not None and evidence.numeric_value > requirement.maximum_value:
            failures.append(evidence)
    return failures


def _unlock_dependents(case_operation, actor):
    case = case_operation.repair_case
    for candidate in case.case_operations.filter(status=CaseOperation.Status.LOCKED).select_related("operation"):
        dependency_ids = candidate.operation.dependencies.values_list("depends_on_id", flat=True)
        if not dependency_ids:
            continue
        if not case.case_operations.filter(
            operation_id__in=dependency_ids
        ).exclude(status=CaseOperation.Status.COMPLETED).exists():
            before = candidate.status
            candidate.status = CaseOperation.Status.AVAILABLE
            candidate.save(update_fields=["status"])
            _audit(case, actor, "operation_unlocked", case_operation=candidate, before=before, after=candidate.status)


@transaction.atomic
def complete_operation(case_operation: CaseOperation, user, result=None) -> CaseOperation:
    case_operation = CaseOperation.objects.select_for_update().select_related(
        "repair_case", "operation"
    ).get(pk=case_operation.pk)
    technician = assert_operation_authorized(case_operation, user)
    if case_operation.status not in {CaseOperation.Status.AVAILABLE, CaseOperation.Status.IN_PROGRESS}:
        raise ValidationError("Operation is not available for completion.")
    missing = _missing_requirements(case_operation)
    if missing:
        raise ValidationError({"evidence": [item.pk for item in missing]})
    before = case_operation.status
    case_operation.result = result or {}
    case_operation.completed_by = technician.user_profile
    case_operation.completed_at = timezone.now()
    failures = _measurement_out_of_range(case_operation)
    if failures or case_operation.operation.approval_required:
        case_operation.status = CaseOperation.Status.REQUIRES_REVIEW
        case_operation.repair_case.status = RepairCase.Status.BLOCKED
        case_operation.repair_case.save(update_fields=["status"])
    else:
        case_operation.status = CaseOperation.Status.COMPLETED
    case_operation.save(update_fields=["status", "result", "completed_by", "completed_at"])
    _audit(case_operation.repair_case, technician.user_profile, "operation_completed", case_operation=case_operation, before=before, after=case_operation.status, payload={"out_of_range_evidence": [item.pk for item in failures]})
    if case_operation.status == CaseOperation.Status.COMPLETED:
        _unlock_dependents(case_operation, technician.user_profile)
    return case_operation


@transaction.atomic
def decide_operation(*, case_operation: CaseOperation, user, decision: str, rationale: str, evidence=()) -> ExpertDecision:
    case_operation = CaseOperation.objects.select_for_update().select_related("repair_case", "operation").get(pk=case_operation.pk)
    reviewer = _technician(user, case_operation.repair_case.organization_id)
    required = ROLE_LEVEL.get(case_operation.operation.approval_minimum_role, 3)
    if ROLE_LEVEL.get(reviewer.role, -1) < required:
        raise PermissionDenied("Reviewer role is insufficient.")
    if reviewer.user_profile_id == case_operation.completed_by_id:
        raise PermissionDenied("An operation cannot approve itself.")
    if case_operation.status != CaseOperation.Status.REQUIRES_REVIEW:
        raise ValidationError("Operation is not awaiting expert review.")
    authorized_keys = (
        list(case_operation.operation.unlocks.values_list("operation__key", flat=True))
        if decision == ExpertDecision.Decision.APPROVE else []
    )
    expert_decision = ExpertDecision.objects.create(
        repair_case=case_operation.repair_case,
        case_operation=case_operation,
        decision=decision,
        rationale=rationale,
        authorized_operation_keys=authorized_keys,
        reviewer=reviewer.user_profile,
    )
    for item in evidence:
        if item.case_operation_id != case_operation.pk:
            raise ValidationError("Decision evidence belongs to another operation.")
        ExpertDecisionEvidence.objects.create(decision=expert_decision, evidence=item)
    before = case_operation.status
    unlock = False
    if decision == ExpertDecision.Decision.APPROVE:
        case_operation.status = CaseOperation.Status.COMPLETED
        case_operation.repair_case.status = RepairCase.Status.IN_PROGRESS
        case_operation.repair_case.save(update_fields=["status"])
        unlock = True
    elif decision == ExpertDecision.Decision.REWORK:
        case_operation.status = CaseOperation.Status.AVAILABLE
        case_operation.repair_case.status = RepairCase.Status.IN_PROGRESS
        case_operation.repair_case.save(update_fields=["status"])
    else:
        case_operation.status = CaseOperation.Status.FAILED
    case_operation.save(update_fields=["status"])
    if unlock:
        _unlock_dependents(case_operation, reviewer.user_profile)
    _audit(case_operation.repair_case, reviewer.user_profile, "expert_decision", case_operation=case_operation, before=before, after=case_operation.status, payload={"decision_id": expert_decision.pk, "decision": decision})
    return expert_decision


def repair_record_snapshot(case: RepairCase) -> dict:
    return {
        "case_id": case.pk,
        "vehicle": {
            "id": case.vehicle_id,
            "vin": case.vehicle.vin_normalized,
            "make": case.vehicle.make,
            "model": case.vehicle.model,
            "year": case.vehicle.year,
        },
        "procedure": procedure_snapshot(case.procedure_version),
        "operations": [
            {
                "operation_key": execution.operation.key,
                "status": execution.status,
                "completed_by_id": execution.completed_by_id,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "result": execution.result,
                "evidence": [
                    {
                        "id": item.pk,
                        "type": item.evidence_type,
                        "numeric_value": str(item.numeric_value) if item.numeric_value is not None else None,
                        "unit": item.unit,
                        "content_sha256": item.content_sha256,
                        "submitted_by_id": item.submitted_by_id,
                        "submitted_at": item.submitted_at.isoformat(),
                    }
                    for item in execution.evidence.all()
                ],
                "decisions": [
                    {
                        "decision": item.decision,
                        "reviewer_id": item.reviewer_id,
                        "decided_at": item.decided_at.isoformat(),
                        "rationale": item.rationale,
                    }
                    for item in execution.expert_decisions.all()
                ],
            }
            for execution in case.case_operations.select_related("operation", "completed_by").prefetch_related("evidence", "expert_decisions")
        ],
        "verification_status": case.verification_status,
        "audit_event_ids": list(case.audit_events.values_list("id", flat=True)),
    }


@transaction.atomic
def verify_repair_case(case: RepairCase, user) -> Verification:
    reviewer = _technician(user, case.organization_id)
    case = RepairCase.objects.select_for_update().select_related("vehicle", "procedure_version__procedure").get(pk=case.pk)
    executions = list(case.case_operations.select_related("operation"))
    failed = [item.operation.key for item in executions if item.status == CaseOperation.Status.FAILED]
    incomplete = [item.operation.key for item in executions if item.operation.mandatory and item.status != CaseOperation.Status.COMPLETED]
    review = [item.operation.key for item in executions if item.status == CaseOperation.Status.REQUIRES_REVIEW]
    if failed:
        status = RepairCase.VerificationStatus.FAILED
    elif review:
        status = RepairCase.VerificationStatus.REQUIRES_REVIEW
    elif incomplete:
        status = RepairCase.VerificationStatus.INCOMPLETE
    else:
        status = RepairCase.VerificationStatus.VERIFIED
    details = {"failed": failed, "incomplete": incomplete, "requires_review": review}
    verification = Verification.objects.create(
        repair_case=case,
        status=status, details=details, performed_by=reviewer.user_profile,
    )
    before = case.status
    case.verification_status = status
    case.status = RepairCase.Status.COMPLETED if status == RepairCase.VerificationStatus.VERIFIED else RepairCase.Status.VERIFICATION
    if status == RepairCase.VerificationStatus.VERIFIED:
        case.completed_at = timezone.now()
    case.save(update_fields=["verification_status", "status", "completed_at"])
    _audit(case, reviewer.user_profile, "case_verified", before=before, after=case.status, payload=details | {"verification_status": status})
    if status == RepairCase.VerificationStatus.VERIFIED and not hasattr(case, "repair_record"):
        snapshot = repair_record_snapshot(case)
        RepairRecord.objects.create(repair_case=case, snapshot=snapshot, content_sha256=_checksum(snapshot))
    return verification
