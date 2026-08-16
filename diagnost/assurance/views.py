from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from users.models import TechnicianProfile

from .forms import CompletionForm, EvidenceSubmissionForm, ExpertDecisionForm, RepairCaseCreateForm
from .models import CaseOperation, RepairCase
from .services import (
    complete_operation,
    decide_operation,
    create_repair_case,
    submit_evidence,
    verify_repair_case,
)


def _technician(request):
    profile = getattr(request.user, "userprofile", None)
    technician = getattr(profile, "technician_profile", None) if profile else None
    if technician is None or not technician.is_active:
        raise PermissionDenied
    return technician


def _visible_cases(request):
    technician = _technician(request)
    queryset = RepairCase.objects.filter(organization=technician.organization)
    if technician.role not in {
        TechnicianProfile.Role.SENIOR_EXPERT,
        TechnicianProfile.Role.TECHNICAL_MANAGER,
    }:
        queryset = queryset.filter(technician_assignments__technician=technician)
    return queryset.distinct()


@login_required
def case_list(request):
    cases = _visible_cases(request).select_related("vehicle", "procedure_version__procedure")
    return render(request, "assurance/case_list.html", {"cases": cases})


@login_required
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
                messages.success(request, "Repair case created.")
                return redirect("assurance:case_detail", case_id=repair_case.pk)
    else:
        form = RepairCaseCreateForm(technician=technician)
    return render(request, "assurance/case_create.html", {"form": form})


def case_detail(request, case_id):
    repair_case = get_object_or_404(
        _visible_cases(request).select_related("vehicle", "procedure_version__procedure"),
        pk=case_id,
    )
    operations = repair_case.case_operations.select_related(
        "operation", "assigned_to"
    ).prefetch_related(
        "operation__reference_media",
        "operation__evidence_requirements",
        "evidence",
        "expert_decisions",
    )
    return render(
        request,
        "assurance/case_detail.html",
        {"repair_case": repair_case, "operations": operations},
    )


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
                messages.success(request, "Evidence recorded.")
                return redirect("assurance:case_detail", case_id=execution.repair_case_id)
    else:
        form = EvidenceSubmissionForm(case_operation=execution)
    return render(
        request,
        "assurance/evidence_form.html",
        {"form": form, "execution": execution},
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
                messages.success(request, "Operation processed.")
    return redirect("assurance:case_detail", case_id=execution.repair_case_id)


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
                    evidence=execution.evidence.all(),
                )
            except (ValidationError, PermissionDenied) as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, "Expert decision recorded.")
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
            messages.success(request, f"Verification: {verification.get_status_display()}.")
    return redirect("assurance:case_detail", case_id=repair_case.pk)
