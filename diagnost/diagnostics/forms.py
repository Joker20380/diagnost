from django import forms
from django.forms import inlineformset_factory
from .models import SuspensionInspection, SuspensionPart, DiagnosticSession


class DiagnosticUploadForm(forms.ModelForm):
    class Meta:
        model = DiagnosticSession
        fields = ['vin', 'vehicle_model', 'raw_file']
        labels = {
            'vin': 'VIN автомобиля',
            'vehicle_model': 'Модель автомобиля',
            'raw_file': 'Файл отчёта',
        }


class SuspensionForm(forms.ModelForm):
    class Meta:
        model = SuspensionInspection
        fields = ['inspector', 'comment']


SuspensionPartFormSet = inlineformset_factory(
    parent_model=SuspensionInspection,
    model=SuspensionPart,
    fields=['part_type', 'wear_percent', 'part_number', 'needs_replacement'],
    extra=0,
    can_delete=True
)
