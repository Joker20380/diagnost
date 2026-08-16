from django import forms

from .models import EvidenceRequirement, ExpertDecision


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


class ExpertDecisionForm(forms.Form):
    decision = forms.ChoiceField(choices=ExpertDecision.Decision.choices)
    rationale = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))


class CompletionForm(forms.Form):
    result_note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
