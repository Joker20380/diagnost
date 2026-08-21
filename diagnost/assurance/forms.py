from django import forms

from diagnostics.models import Vehicle
from users.models import TechnicianProfile

from .models import EvidenceRequirement, ExpertDecision, ProcedureVersion


class RepairCaseCreateForm(forms.Form):
    vehicle = forms.ModelChoiceField(queryset=Vehicle.objects.none())
    procedure_version = forms.ModelChoiceField(queryset=ProcedureVersion.objects.none())
    title = forms.CharField(max_length=255)
    complaint = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    technicians = forms.ModelMultipleChoiceField(
        queryset=TechnicianProfile.objects.none(), required=False
    )

    def __init__(self, *args, technician, **kwargs):
        super().__init__(*args, **kwargs)
        organization = technician.organization
        self.fields["vehicle"].queryset = Vehicle.objects.filter(organization=organization)
        self.fields["procedure_version"].queryset = ProcedureVersion.objects.filter(
            procedure__organization=organization,
            status=ProcedureVersion.Status.PUBLISHED,
        )
        self.fields["technicians"].queryset = TechnicianProfile.objects.filter(
            organization=organization, is_active=True
        )
        self.fields["technicians"].initial = [technician.pk]
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class EvidenceSubmissionForm(forms.Form):
    requirement = forms.ModelChoiceField(queryset=EvidenceRequirement.objects.none())
    file = forms.FileField(required=False)
    text = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    numeric_value = forms.DecimalField(required=False, max_digits=16, decimal_places=4)
    unit = forms.CharField(required=False, max_length=32)

    def __init__(self, *args, case_operation, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["requirement"].queryset = case_operation.operation.evidence_requirements.all()
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class EvidenceSupersessionForm(EvidenceSubmissionForm):
    reason = forms.CharField(
        min_length=5,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Explain why the previous evidence must be replaced.",
    )

    def __init__(self, *args, evidence, **kwargs):
        super().__init__(*args, case_operation=evidence.case_operation, **kwargs)
        self.fields["requirement"].queryset = EvidenceRequirement.objects.filter(
            pk=evidence.requirement_id
        )
        self.fields["requirement"].initial = evidence.requirement_id
        self.fields["requirement"].disabled = True
        self.fields["unit"].initial = evidence.unit


class ExpertDecisionForm(forms.Form):
    decision = forms.ChoiceField(choices=ExpertDecision.Decision.choices)
    rationale = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))


class CompletionForm(forms.Form):
    result_note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
