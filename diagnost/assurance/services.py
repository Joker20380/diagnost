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
    CaseOperationException,
    CompetencyReview,
    CompetencyReviewEvidence,
    Evidence,
    EvidenceRequirement,
    ExpertDecision,
    ExpertDecisionEvidence,
    ExpertReviewNotification,
    Operation,
    ProcedureVersion,
    RepairAuditEvent,
    RepairCase,
    RepairCaseTechnician,
    TechnicianSkill,
    Skill,
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


def _manager_technician(user, organization_id) -> TechnicianProfile:
    technician = _technician(user, organization_id)
    if ROLE_LEVEL.get(technician.role, -1) < 3:
        raise PermissionDenied("Senior or technical manager role is required.")
    return technician


def _assert_case_open(case: RepairCase):
    if case.status in {
        RepairCase.Status.COMPLETED,
        RepairCase.Status.CANCELLED,
    }:
        raise ValidationError("The repair case is closed.")


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


def _queue_expert_review(case_operation: CaseOperation, actor: UserProfile) -> int:
    required_level = ROLE_LEVEL.get(
        case_operation.operation.approval_minimum_role,
        ROLE_LEVEL[TechnicianProfile.Role.SENIOR_EXPERT],
    )
    eligible_roles = [
        role
        for role, level in ROLE_LEVEL.items()
        if level >= required_level and role != TechnicianProfile.Role.AUDITOR
    ]
    reviewers = TechnicianProfile.objects.filter(
        organization_id=case_operation.repair_case.organization_id,
        role__in=eligible_roles,
        is_active=True,
        user_profile__user__is_active=True,
    ).exclude(user_profile_id=case_operation.completed_by_id).exclude(
        user_profile__user__email=""
    ).select_related("user_profile__user")
    queued = [
        ExpertReviewNotification(
            repair_case=case_operation.repair_case,
            case_operation=case_operation,
            recipient=reviewer.user_profile,
            recipient_email=reviewer.user_profile.user.email,
            review_requested_at=case_operation.completed_at,
        )
        for reviewer in reviewers
    ]
    ExpertReviewNotification.objects.bulk_create(queued, ignore_conflicts=True)
    count = len(queued)
    _audit(
        case_operation.repair_case, actor, "expert_review_queued",
        case_operation=case_operation,
        payload={"recipient_count": count, "operation_key": case_operation.operation.key},
    )
    return count


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
    supersedes=None,
    supersession_reason="",
) -> Evidence:
    case_operation = CaseOperation.objects.select_for_update().select_related(
        "repair_case", "operation"
    ).get(pk=case_operation.pk)
    technician = assert_operation_authorized(case_operation, user)
    _assert_case_open(case_operation.repair_case)
    if case_operation.status not in {CaseOperation.Status.AVAILABLE, CaseOperation.Status.IN_PROGRESS}:
        raise ValidationError("Evidence can only be submitted for an available operation.")
    if requirement and requirement.operation_id != case_operation.operation_id:
        raise ValidationError("Evidence requirement belongs to another operation.")
    if supersedes:
        if supersedes.case_operation_id != case_operation.pk:
            raise ValidationError("Superseded evidence belongs to another operation.")
        if supersedes.requirement_id != getattr(requirement, "pk", None):
            raise ValidationError("Replacement must use the same evidence requirement.")
        if supersedes.evidence_type != evidence_type:
            raise ValidationError("Replacement must use the same evidence type.")
        if not supersession_reason.strip():
            raise ValidationError("A supersession reason is required.")

    _validate_evidence_payload(requirement, evidence_type, file, text, numeric_value, unit)
    evidence_metadata = dict(metadata or {})
    if supersedes:
        evidence_metadata["supersession"] = {
            "previous_evidence_id": supersedes.pk,
            "reason": supersession_reason.strip(),
        }
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
        supersedes=supersedes,
    )
    before = case_operation.status
    if before == CaseOperation.Status.AVAILABLE:
        case_operation.status = CaseOperation.Status.IN_PROGRESS
        case_operation.started_at = timezone.now()
        case_operation.save(update_fields=["status", "started_at"])
    action = "evidence_superseded" if supersedes else "evidence_submitted"
    payload = {"evidence_id": evidence.pk, "type": evidence_type}
    if supersedes:
        payload.update({
            "superseded_evidence_id": supersedes.pk,
            "reason": supersession_reason.strip(),
        })
    _audit(
        case_operation.repair_case,
        technician.user_profile,
        action,
        case_operation=case_operation,
        before=before,
        after=case_operation.status,
        payload=payload,
    )
    return evidence


@transaction.atomic
def supersede_evidence(
    *,
    evidence: Evidence,
    user,
    file=None,
    text="",
    numeric_value=None,
    unit="",
    reason: str,
    metadata=None,
) -> Evidence:
    evidence = Evidence.objects.select_for_update().select_related(
        "case_operation__repair_case",
        "case_operation__operation",
    ).get(pk=evidence.pk)
    if evidence.superseded_by.exists():
        raise ValidationError("Evidence has already been superseded.")
    return submit_evidence(
        case_operation=evidence.case_operation,
        user=user,
        requirement=evidence.requirement,
        evidence_type=evidence.evidence_type,
        file=file,
        text=text,
        numeric_value=numeric_value,
        unit=unit,
        metadata=metadata,
        supersedes=evidence,
        supersession_reason=reason,
    )


def _missing_requirements(case_operation):
    missing = []
    for requirement in case_operation.operation.evidence_requirements.filter(required=True):
        count = case_operation.evidence.filter(
            requirement=requirement, superseded_by__isnull=True
        ).count()
        if count < requirement.minimum_count:
            missing.append(requirement)
    return missing


def _measurement_out_of_range(case_operation):
    failures = []
    for evidence in case_operation.evidence.filter(
        evidence_type=EvidenceRequirement.Type.MEASUREMENT,
        superseded_by__isnull=True,
    ).select_related("requirement"):
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
        ).exclude(status__in=[CaseOperation.Status.COMPLETED, CaseOperation.Status.SKIPPED]).exists():
            before = candidate.status
            candidate.status = CaseOperation.Status.AVAILABLE
            candidate.save(update_fields=["status"])
            _audit(case, actor, "operation_unlocked", case_operation=candidate, before=before, after=candidate.status)


@transaction.atomic
def skip_case_operation(
    *, case_operation: CaseOperation, user, rationale: str
) -> CaseOperationException:
    case_operation = CaseOperation.objects.select_for_update().select_related(
        "repair_case", "operation"
    ).get(pk=case_operation.pk)
    authorizer = _manager_technician(
        user, case_operation.repair_case.organization_id
    )
    _assert_case_open(case_operation.repair_case)
    if case_operation.status not in {
        CaseOperation.Status.AVAILABLE,
        CaseOperation.Status.IN_PROGRESS,
    }:
        raise ValidationError("Only an available operation can be skipped.")
    if not case_operation.operation.escalation_allowed:
        raise ValidationError("This operation does not allow an exception.")
    rationale = rationale.strip()
    if len(rationale) < 5:
        raise ValidationError("A meaningful exception rationale is required.")

    approved_exception = CaseOperationException.objects.create(
        case_operation=case_operation,
        rationale=rationale,
        authorized_by=authorizer.user_profile,
    )
    before = case_operation.status
    case_operation.status = CaseOperation.Status.SKIPPED
    case_operation.completed_by = authorizer.user_profile
    case_operation.completed_at = timezone.now()
    case_operation.result = {
        "exception_id": approved_exception.pk,
        "exception_rationale": rationale,
    }
    case_operation.save(
        update_fields=["status", "completed_by", "completed_at", "result"]
    )
    _audit(
        case_operation.repair_case,
        authorizer.user_profile,
        "operation_exception_approved",
        case_operation=case_operation,
        before=before,
        after=case_operation.status,
        payload={"exception_id": approved_exception.pk, "rationale": rationale},
    )
    _unlock_dependents(case_operation, authorizer.user_profile)
    return approved_exception


@transaction.atomic
def cancel_repair_case(*, case: RepairCase, user, rationale: str) -> RepairCase:
    case = RepairCase.objects.select_for_update().get(pk=case.pk)
    authorizer = _manager_technician(user, case.organization_id)
    _assert_case_open(case)
    rationale = rationale.strip()
    if len(rationale) < 5:
        raise ValidationError("A meaningful cancellation rationale is required.")

    cancelled_at = timezone.now()
    unfinished = case.case_operations.exclude(
        status__in=[CaseOperation.Status.COMPLETED, CaseOperation.Status.SKIPPED]
    )
    operation_ids = list(unfinished.values_list("id", flat=True))
    unfinished.update(
        status=CaseOperation.Status.SKIPPED,
        completed_by=authorizer.user_profile,
        completed_at=cancelled_at,
        result={"cancelled": True, "rationale": rationale},
    )
    before = case.status
    case.status = RepairCase.Status.CANCELLED
    case.completed_at = cancelled_at
    case.save(update_fields=["status", "completed_at"])
    _audit(
        case,
        authorizer.user_profile,
        "case_cancelled",
        before=before,
        after=case.status,
        payload={"rationale": rationale, "cancelled_operation_ids": operation_ids},
    )
    return case


@transaction.atomic
def complete_operation(case_operation: CaseOperation, user, result=None) -> CaseOperation:
    case_operation = CaseOperation.objects.select_for_update().select_related(
        "repair_case", "operation"
    ).get(pk=case_operation.pk)
    technician = assert_operation_authorized(case_operation, user)
    _assert_case_open(case_operation.repair_case)
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
    if case_operation.status == CaseOperation.Status.REQUIRES_REVIEW:
        _queue_expert_review(case_operation, technician.user_profile)
    if case_operation.status == CaseOperation.Status.COMPLETED:
        _unlock_dependents(case_operation, technician.user_profile)
    return case_operation


@transaction.atomic
def decide_operation(*, case_operation: CaseOperation, user, decision: str, rationale: str, evidence=()) -> ExpertDecision:
    case_operation = CaseOperation.objects.select_for_update().select_related("repair_case", "operation").get(pk=case_operation.pk)
    reviewer = _technician(user, case_operation.repair_case.organization_id)
    _assert_case_open(case_operation.repair_case)
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
                "approved_exception": (
                    {
                        "id": execution.approved_exception.pk,
                        "rationale": execution.approved_exception.rationale,
                        "authorized_by_id": execution.approved_exception.authorized_by_id,
                        "authorized_at": execution.approved_exception.authorized_at.isoformat(),
                    }
                    if hasattr(execution, "approved_exception")
                    else None
                ),
                "evidence": [
                    {
                        "id": item.pk,
                        "type": item.evidence_type,
                        "numeric_value": str(item.numeric_value) if item.numeric_value is not None else None,
                        "unit": item.unit,
                        "content_sha256": item.content_sha256,
                        "submitted_by_id": item.submitted_by_id,
                        "submitted_at": item.submitted_at.isoformat(),
                        "supersedes_id": item.supersedes_id,
                        "is_superseded": item.is_superseded,
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
            for execution in case.case_operations.select_related(
                "operation", "completed_by", "approved_exception"
            ).prefetch_related("evidence", "expert_decisions")
        ],
        "verification_status": case.verification_status,
        "audit_event_ids": list(case.audit_events.values_list("id", flat=True)),
    }


@transaction.atomic


@transaction.atomic
def review_competency(*, technician, skill: Skill, requested_level: int, decision: str, rationale: str, evidence, user) -> CompetencyReview:
    reviewer = _manager_technician(user, skill.organization_id)
    if technician.organization_id != skill.organization_id:
        raise ValidationError("Technician and skill must belong to one organization.")
    if reviewer.pk == technician.pk:
        raise PermissionDenied("Reviewers cannot approve their own competency.")
    if requested_level < 1 or requested_level > skill.max_level:
        raise ValidationError("Requested competency level is invalid.")
    if decision not in CompetencyReview.Decision.values:
        raise ValidationError("Unsupported competency decision.")
    if len(rationale.strip()) < 5:
        raise ValidationError("A substantive competency rationale is required.")

    evidence_items = list(Evidence.objects.select_for_update().select_related(
        "case_operation__operation", "repair_case"
    ).filter(pk__in=[item.pk for item in evidence]))
    if not evidence_items:
        raise ValidationError("Competency review requires evidence.")
    if len(evidence_items) != len({item.pk for item in evidence}):
        raise ValidationError("Some competency evidence does not exist.")
    for item in evidence_items:
        if item.repair_case.organization_id != skill.organization_id:
            raise ValidationError("Competency evidence belongs to another organization.")
        if item.submitted_by_id != technician.user_profile_id:
            raise ValidationError("Competency evidence was not submitted by this technician.")
        if item.case_operation.operation.required_skill_id != skill.pk:
            raise ValidationError("Competency evidence does not demonstrate this skill.")
        if item.case_operation.status != CaseOperation.Status.COMPLETED:
            raise ValidationError("Competency evidence must come from a completed operation.")
        if item.is_superseded:
            raise ValidationError("Superseded evidence cannot support competency.")

    review = CompetencyReview.objects.create(
        technician=technician, skill=skill, requested_level=requested_level,
        decision=decision, rationale=rationale.strip(), reviewer=reviewer.user_profile,
    )
    CompetencyReviewEvidence.objects.bulk_create([
        CompetencyReviewEvidence(review=review, evidence=item) for item in evidence_items
    ])
    if decision == CompetencyReview.Decision.APPROVE:
        TechnicianSkill.objects.update_or_create(
            technician=technician, skill=skill,
            defaults={"level": requested_level, "verified_by": reviewer.user_profile, "verified_at": timezone.now()},
        )
    return review
def verify_repair_case(case: RepairCase, user) -> Verification:
    reviewer = _technician(user, case.organization_id)
    case = RepairCase.objects.select_for_update().select_related("vehicle", "procedure_version__procedure").get(pk=case.pk)
    _assert_case_open(case)
    executions = list(
        case.case_operations.select_related("operation", "approved_exception")
    )
    failed = [item.operation.key for item in executions if item.status == CaseOperation.Status.FAILED]
    incomplete = [
        item.operation.key
        for item in executions
        if item.operation.mandatory
        and item.status != CaseOperation.Status.COMPLETED
        and not (
            item.status == CaseOperation.Status.SKIPPED
            and hasattr(item, "approved_exception")
        )
    ]
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
