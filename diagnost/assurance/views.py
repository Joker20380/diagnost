import csv
import json
from io import StringIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from users.models import TechnicianProfile

from .forms import (
    CompletionForm,
    CompetencyReviewForm,
    EvidenceSubmissionForm,
    EvidenceSupersessionForm,
    ExpertDecisionForm,
    ReasonForm,
    RepairCaseCreateForm,
    WorkshopWalkthroughObservationForm,
)
from .models import CaseOperation, Evidence, RepairCase, RepairRecord
from .services import (
    cancel_repair_case,
    complete_operation,
    decide_operation,
    create_repair_case,
    review_competency,
    skip_case_operation,
    submit_evidence,
    supersede_evidence,
    verify_repair_case,
)


def _technician(request):
    profile = getattr(request.user, "userprofile", None)
    technician = getattr(profile, "technician_profile", None) if profile else None
    if technician is None or not technician.is_active:
        raise PermissionDenied
    return technician


def _visible_cases(request):
    if request.user.is_superuser:
        return RepairCase.objects.all()
    technician = _technician(request)
    queryset = RepairCase.objects.filter(organization=technician.organization)
    if technician.role not in {
        TechnicianProfile.Role.AUDITOR,
        TechnicianProfile.Role.SENIOR_EXPERT,
        TechnicianProfile.Role.TECHNICAL_MANAGER,
    }:
        queryset = queryset.filter(technician_assignments__technician=technician)
    return queryset.distinct()


def _auditable_cases(request):
    if request.user.is_superuser:
        return RepairCase.objects.all()
    technician = _technician(request)
    if technician.role not in {
        TechnicianProfile.Role.AUDITOR,
        TechnicianProfile.Role.SENIOR_EXPERT,
        TechnicianProfile.Role.TECHNICAL_MANAGER,
    }:
        raise PermissionDenied
    return RepairCase.objects.filter(organization=technician.organization)


def _filtered_audit_events(request, repair_case):
    events = repair_case.audit_events.select_related(
        "actor__user", "case_operation__operation"
    )
    action = request.GET.get("action", "").strip()
    operation_id = request.GET.get("operation", "").strip()
    if action:
        events = events.filter(action=action)
    if operation_id.isdigit():
        events = events.filter(case_operation_id=int(operation_id))
    return events.order_by("-occurred_at", "-id"), action, operation_id


def _audit_event_payload(event):
    return {
        "id": event.pk,
        "occurred_at": event.occurred_at.isoformat(),
        "action": event.action,
        "operation_key": event.case_operation.operation.key if event.case_operation_id else None,
        "actor_id": event.actor_id,
        "actor": str(event.actor),
        "before_status": event.before_status,
        "after_status": event.after_status,
        "payload": event.payload,
    }


def _repair_certificate_projection(record):
    snapshot = record.snapshot
    vehicle = snapshot["vehicle"]
    vin = vehicle.get("vin", "")
    public_vin = f"{'*' * max(len(vin) - 6, 0)}{vin[-6:]}" if vin else ""
    definitions = {
        item["key"]: item for item in snapshot["procedure"]["operations"]
    }
    operations = []
    for execution in snapshot["operations"]:
        definition = definitions[execution["operation_key"]]
        operations.append(
            {
                "sequence": definition["sequence"],
                "title": definition["title"],
                "status": execution["status"],
                "completed_at": execution["completed_at"],
                "evidence_count": sum(
                    not evidence["is_superseded"]
                    for evidence in execution["evidence"]
                ),
                "approved_exception": execution.get("approved_exception") is not None,
            }
        )
    return {
        "public_id": record.public_id,
        "created_at": record.created_at,
        "content_sha256": record.content_sha256,
        "vehicle": {
            "make": vehicle.get("make", ""),
            "model": vehicle.get("model", ""),
            "year": vehicle.get("year"),
            "vin": public_vin,
        },
        "procedure_name": snapshot["procedure"]["procedure_name"],
        "procedure_version": snapshot["procedure"]["version"],
        "verification_status": snapshot["verification_status"],
        "operations": operations,
    }


@login_required
def case_list(request):
    cases = _visible_cases(request).select_related("vehicle", "procedure_version__procedure")
    profile = getattr(request.user, "userprofile", None)
    technician = getattr(profile, "technician_profile", None) if profile else None
    can_review_competency = bool(technician and technician.is_active and technician.role in {
        TechnicianProfile.Role.SENIOR_EXPERT,
        TechnicianProfile.Role.TECHNICAL_MANAGER,
    })
    return render(request, "assurance/case_list.html", {
        "cases": cases, "can_review_competency": can_review_competency,
    })


@login_required
def competency_review_create(request):
    reviewer = _technician(request)
    if reviewer.role not in {
        TechnicianProfile.Role.SENIOR_EXPERT,
        TechnicianProfile.Role.TECHNICAL_MANAGER,
    }:
        raise PermissionDenied
    if request.method == "POST":
        form = CompetencyReviewForm(request.POST, reviewer=reviewer)
        if form.is_valid():
            try:
                review = review_competency(
                    technician=form.cleaned_data["technician"],
                    skill=form.cleaned_data["skill"],
                    requested_level=form.cleaned_data["requested_level"],
                    decision=form.cleaned_data["decision"],
                    rationale=form.cleaned_data["rationale"],
                    evidence=form.cleaned_data["evidence"],
                    user=request.user,
                )
            except (ValidationError, PermissionDenied) as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, _("Competency decision #%(id)s recorded.") % {"id": review.pk})
                return redirect("assurance:case_list")
    else:
        form = CompetencyReviewForm(reviewer=reviewer)
    return render(request, "assurance/competency_review_form.html", {"form": form})

def repair_certificate(request, public_id):
    record = get_object_or_404(RepairRecord, public_id=public_id)
    response = render(
        request,
        "assurance/repair_certificate.html",
        {"certificate": _repair_certificate_projection(record)},
    )
    response["Cache-Control"] = "public, max-age=300"
    response["Referrer-Policy"] = "no-referrer"
    response["X-Content-Type-Options"] = "nosniff"
    response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response



@login_required
def case_create(request):
    technician = _technician(request)
    if technician.role not in {
        TechnicianProfile.Role.SENIOR_EXPERT,
        TechnicianProfile.Role.TECHNICAL_MANAGER,
    }:
        raise PermissionDenied
    if request.method == "POST":
        form = RepairCaseCreateForm(request.POST, technician=technician)
        if form.is_valid():
            try:
                repair_case = create_repair_case(
                    vehicle=form.cleaned_data["vehicle"],
                    procedure_version=form.cleaned_data["procedure_version"],
                    title=form.cleaned_data["title"],
                    complaint=form.cleaned_data["complaint"],
                    user=request.user,
                    workshop=technician.workshop,
                    technicians=form.cleaned_data["technicians"] or [technician],
                )
            except (ValidationError, PermissionDenied) as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, _("Repair case created."))
                return redirect("assurance:case_detail", case_id=repair_case.pk)
    else:
        form = RepairCaseCreateForm(technician=technician)
    return render(request, "assurance/case_create.html", {"form": form})


@login_required
def case_detail(request, case_id):
    repair_case = get_object_or_404(
        _visible_cases(request).select_related(
            "vehicle", "procedure_version__procedure", "repair_record"
        ),
        pk=case_id,
    )
    operations = repair_case.case_operations.select_related(
        "operation", "assigned_to", "approved_exception"
    ).prefetch_related(
        "operation__reference_media",
        "operation__evidence_requirements",
        "evidence",
        "evidence__superseded_by",
        "expert_decisions",
    )
    profile = getattr(request.user, "userprofile", None)
    technician = getattr(profile, "technician_profile", None) if profile else None
    can_control = bool(
        technician
        and technician.is_active
        and technician.role in {
            TechnicianProfile.Role.SENIOR_EXPERT,
            TechnicianProfile.Role.TECHNICAL_MANAGER,
        }
    )
    can_audit = bool(
        request.user.is_superuser
        or technician
        and technician.is_active
        and technician.role
        in {
            TechnicianProfile.Role.AUDITOR,
            TechnicianProfile.Role.SENIOR_EXPERT,
            TechnicianProfile.Role.TECHNICAL_MANAGER,
        }
    )
    return render(
        request,
        "assurance/case_detail.html",
        {
            "repair_case": repair_case,
            "operations": operations,
            "can_control": can_control,
            "can_audit": can_audit,
            "walkthrough_observations": repair_case.walkthrough_observations.select_related(
                "case_operation__operation", "recorded_by__user"
            ).order_by("-recorded_at", "-id"),
            "walkthrough_form": WorkshopWalkthroughObservationForm(repair_case=repair_case),
        },
    )


@login_required

@login_required
def record_walkthrough_observation(request, case_id):
    repair_case = get_object_or_404(_visible_cases(request), pk=case_id)
    if request.method != "POST":
        return redirect("assurance:case_detail", case_id=repair_case.pk)
    form = WorkshopWalkthroughObservationForm(request.POST, repair_case=repair_case)
    if form.is_valid():
        observation = form.save(commit=False)
        observation.repair_case = repair_case
        observation.recorded_by = request.user.userprofile
        observation.save()
        messages.success(request, _("Workshop observation recorded."))
    else:
        messages.error(request, _("Workshop observation was not recorded. Check the fields."))
    return redirect("assurance:case_detail", case_id=repair_case.pk)

def case_audit(request, case_id):
    repair_case = get_object_or_404(
        _auditable_cases(request).select_related(
            "vehicle", "procedure_version__procedure"
        ),
        pk=case_id,
    )
    events, selected_action, selected_operation = _filtered_audit_events(
        request, repair_case
    )
    action_choices = (
        repair_case.audit_events.order_by("action")
        .values_list("action", flat=True)
        .distinct()
    )
    operations = repair_case.case_operations.select_related("operation").order_by(
        "operation__sequence"
    )
    page = Paginator(events, 50).get_page(request.GET.get("page"))
    return render(
        request,
        "assurance/case_audit.html",
        {
            "repair_case": repair_case,
            "page": page,
            "action_choices": action_choices,
            "operations": operations,
            "selected_action": selected_action,
            "selected_operation": selected_operation,
        },
    )


@login_required
def case_audit_export(request, case_id, export_format):
    repair_case = get_object_or_404(_auditable_cases(request), pk=case_id)
    events, _, _ = _filtered_audit_events(request, repair_case)
    filename = f"repair-case-{repair_case.pk}-audit.{export_format}"
    if export_format == "json":
        response = JsonResponse(
            {
                "repair_case_id": repair_case.pk,
                "events": [_audit_event_payload(event) for event in events],
            },
            json_dumps_params={"indent": 2},
        )
    elif export_format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "occurred_at", "action", "operation_key", "actor_id", "actor", "before_status", "after_status", "payload"])
        for event in events:
            item = _audit_event_payload(event)
            writer.writerow([item["id"], item["occurred_at"], item["action"], item["operation_key"], item["actor_id"], item["actor"], item["before_status"], item["after_status"], json.dumps(item["payload"], sort_keys=True)])
        response = HttpResponse(
            output.getvalue(), content_type="text/csv; charset=utf-8"
        )
    else:
        raise PermissionDenied
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def submit_operation_evidence(request, execution_id):
    execution = get_object_or_404(
        CaseOperation.objects.select_related("repair_case", "operation"),
        pk=execution_id,
        repair_case__in=_visible_cases(request),
    )
    if request.method == "POST":
        form = EvidenceSubmissionForm(
            request.POST, request.FILES, case_operation=execution
        )
        if form.is_valid():
            requirement = form.cleaned_data["requirement"]
            try:
                submit_evidence(
                    case_operation=execution,
                    user=request.user,
                    requirement=requirement,
                    evidence_type=requirement.evidence_type,
                    file=form.cleaned_data["file"],
                    text=form.cleaned_data["text"],
                    numeric_value=form.cleaned_data["numeric_value"],
                    unit=form.cleaned_data["unit"],
                )
            except (ValidationError, PermissionDenied) as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, _("Evidence recorded."))
                return redirect("assurance:case_detail", case_id=execution.repair_case_id)
    else:
        form = EvidenceSubmissionForm(case_operation=execution)
    return render(
        request,
        "assurance/evidence_form.html",
        {"form": form, "execution": execution},
    )


@login_required
def supersede_operation_evidence(request, evidence_id):
    evidence = get_object_or_404(
        Evidence.objects.select_related(
            "repair_case",
            "case_operation__operation",
            "requirement",
        ),
        pk=evidence_id,
        repair_case__in=_visible_cases(request),
        superseded_by__isnull=True,
    )
    if request.method == "POST":
        form = EvidenceSupersessionForm(
            request.POST,
            request.FILES,
            evidence=evidence,
        )
        if form.is_valid():
            try:
                replacement = supersede_evidence(
                    evidence=evidence,
                    user=request.user,
                    file=form.cleaned_data["file"],
                    text=form.cleaned_data["text"],
                    numeric_value=form.cleaned_data["numeric_value"],
                    unit=form.cleaned_data["unit"],
                    reason=form.cleaned_data["reason"],
                )
            except (ValidationError, PermissionDenied) as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(
                    request,
                    _("Evidence #%(old_id)s replaced by #%(new_id)s.") % {"old_id": evidence.pk, "new_id": replacement.pk},
                )
                return redirect(
                    "assurance:case_detail",
                    case_id=evidence.repair_case_id,
                )
    else:
        form = EvidenceSupersessionForm(evidence=evidence)
    return render(
        request,
        "assurance/evidence_form.html",
        {"form": form, "execution": evidence.case_operation, "supersedes": evidence},
    )


@login_required
def complete_case_operation(request, execution_id):
    execution = get_object_or_404(
        CaseOperation.objects.select_related("repair_case", "operation"),
        pk=execution_id,
        repair_case__in=_visible_cases(request),
    )
    if request.method == "POST":
        form = CompletionForm(request.POST)
        if form.is_valid():
            try:
                complete_operation(
                    execution,
                    request.user,
                    result={"note": form.cleaned_data["result_note"]},
                )
            except (ValidationError, PermissionDenied) as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, _("Operation processed."))
    return redirect("assurance:case_detail", case_id=execution.repair_case_id)


@login_required
def skip_operation(request, execution_id):
    execution = get_object_or_404(
        CaseOperation.objects.select_related("repair_case", "operation"),
        pk=execution_id,
        repair_case__in=_visible_cases(request),
    )
    if request.method == "POST":
        form = ReasonForm(request.POST)
        if form.is_valid():
            try:
                skip_case_operation(
                    case_operation=execution,
                    user=request.user,
                    rationale=form.cleaned_data["rationale"],
                )
            except (ValidationError, PermissionDenied) as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, _("Operation exception approved."))
    return redirect("assurance:case_detail", case_id=execution.repair_case_id)


@login_required
def cancel_case(request, case_id):
    repair_case = get_object_or_404(_visible_cases(request), pk=case_id)
    if request.method == "POST":
        form = ReasonForm(request.POST)
        if form.is_valid():
            try:
                cancel_repair_case(
                    case=repair_case,
                    user=request.user,
                    rationale=form.cleaned_data["rationale"],
                )
            except (ValidationError, PermissionDenied) as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, _("Repair case cancelled."))
        else:
            messages.error(request, _("A meaningful cancellation rationale is required."))
    return redirect("assurance:case_detail", case_id=repair_case.pk)


@login_required
def review_case_operation(request, execution_id):
    execution = get_object_or_404(
        CaseOperation.objects.select_related("repair_case", "operation"),
        pk=execution_id,
        repair_case__in=_visible_cases(request),
    )
    if request.method == "POST":
        form = ExpertDecisionForm(request.POST)
        if form.is_valid():
            try:
                decide_operation(
                    case_operation=execution,
                    user=request.user,
                    decision=form.cleaned_data["decision"],
                    rationale=form.cleaned_data["rationale"],
                    evidence=execution.evidence.filter(
                        superseded_by__isnull=True
                    ),
                )
            except (ValidationError, PermissionDenied) as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, _("Expert decision recorded."))
    return redirect("assurance:case_detail", case_id=execution.repair_case_id)


@login_required
def verify_case(request, case_id):
    repair_case = get_object_or_404(_visible_cases(request), pk=case_id)
    if request.method == "POST":
        try:
            verification = verify_repair_case(repair_case, request.user)
        except (ValidationError, PermissionDenied) as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, _("Verification: %(status)s.") % {"status": verification.get_status_display()})
    return redirect("assurance:case_detail", case_id=repair_case.pk)
