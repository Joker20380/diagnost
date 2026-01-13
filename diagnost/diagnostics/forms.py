from __future__ import annotations

from django import forms
from django.forms import inlineformset_factory

from .models import DiagnosticSession, SuspensionInspection, SuspensionPart


class DiagnosticUploadForm(forms.ModelForm):
    class Meta:
        model = DiagnosticSession
        fields = ["vin", "vehicle_model", "raw_file"]
        labels = {
            "vin": "VIN автомобиля",
            "vehicle_model": "Модель автомобиля",
            "raw_file": "Файл отчёта",
        }
        widgets = {
            "vin": forms.TextInput(attrs={"class": "form-control"}),
            "vehicle_model": forms.TextInput(attrs={"class": "form-control"}),
            "raw_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class SuspensionForm(forms.ModelForm):
    """
    Осмотр подвески (верх формы).
    - Включаем новые поля контекста осмотра (если они уже в модели).
    - Если осмотр подписан -> форма read-only.
    """
    class Meta:
        model = SuspensionInspection
        fields = [
            "inspector",
            "mileage_km",
            "lift_used",
            "test_drive",
            "overall_risk",
            "comment",
        ]
        widgets = {
            "inspector": forms.Select(attrs={"class": "form-control"}),
            "mileage_km": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "lift_used": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "test_drive": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "overall_risk": forms.Select(attrs={"class": "form-control"}),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        labels = {
            "inspector": "Мастер",
            "mileage_km": "Пробег (км)",
            "lift_used": "Подъёмник использовался",
            "test_drive": "Тест-драйв выполнялся",
            "overall_risk": "Общий риск по подвеске",
            "comment": "Комментарий",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ Если осмотр подписан — блокируем редактирование
        if self.instance and getattr(self.instance, "status", None) == "signed":
            for f in self.fields.values():
                f.disabled = True


class SuspensionPartForm(forms.ModelForm):
    """
    Строка таблицы деталей (formset).
    - Добавляем severity/reason/evidence.
    - Если осмотр подписан -> строка read-only.
    """
    class Meta:
        model = SuspensionPart
        fields = [
            "part_type",
            "wear_percent",
            "severity",
            "reason",
            "evidence",
            "part_number",
            "needs_replacement",
        ]
        widgets = {
            "part_type": forms.Select(attrs={"class": "form-control"}),
            "wear_percent": forms.NumberInput(attrs={"class": "form-control", "min": 0, "max": 100}),
            "severity": forms.Select(attrs={"class": "form-control"}),
            "reason": forms.TextInput(attrs={"class": "form-control", "placeholder": "люфт / трещины / потёк..."}),
            "evidence": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "что увидели/услышали/померили"}),
            "part_number": forms.TextInput(attrs={"class": "form-control"}),
            "needs_replacement": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "part_type": "Деталь",
            "wear_percent": "Износ (%)",
            "severity": "Критичность",
            "reason": "Причина",
            "evidence": "Признаки/замеры",
            "part_number": "Каталожный №",
            "needs_replacement": "Замена",
        }

    def __init__(self, *args, **kwargs):
        # instance у formset-формы — это SuspensionPart
        super().__init__(*args, **kwargs)

        # ✅ Пробуем достать родительский inspection через instance
        inspection = getattr(self.instance, "inspection", None)
        if inspection and getattr(inspection, "status", None) == "signed":
            for f in self.fields.values():
                f.disabled = True

    def clean_wear_percent(self):
        v = self.cleaned_data.get("wear_percent")
        if v is None:
            return v
        if v < 0 or v > 100:
            raise forms.ValidationError("Износ должен быть в диапазоне 0–100.")
        return v


SuspensionPartFormSet = inlineformset_factory(
    parent_model=SuspensionInspection,
    model=SuspensionPart,
    form=SuspensionPartForm,
    fields=[
        "part_type",
        "wear_percent",
        "severity",
        "reason",
        "evidence",
        "part_number",
        "needs_replacement",
    ],
    extra=0,
    can_delete=True,
)
