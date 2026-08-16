from __future__ import annotations

from pathlib import Path

from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from .models import DiagnosticSession, SuspensionInspection, SuspensionPart


class DiagnosticCaseIntakeForm(forms.Form):
    complaint = forms.CharField(
        label=_("Жалоба клиента"), widget=forms.Textarea(attrs={"rows": 3})
    )
    customer_words = forms.CharField(
        label=_("Формулировка клиента"),
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    onset = forms.CharField(label=_("Когда началось"), max_length=255, required=False)
    frequency = forms.CharField(
        label=_("Частота проявления"), max_length=120, required=False
    )
    symptoms = forms.CharField(
        label=_("Наблюдаемые симптомы"),
        help_text=_("Один симптом на строку."),
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    recent_repairs = forms.CharField(
        label=_("Недавние ремонты"),
        required=False,
        help_text=_("Один ремонт на строку."),
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    operating_conditions = forms.CharField(
        label=_("Условия проявления"),
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    intermittent = forms.BooleanField(label=_("Неисправность плавающая"), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class VehicleIdentityConfirmationForm(forms.Form):
    vin = forms.CharField(label=_("VIN"), max_length=64)
    brand = forms.CharField(label=_("Марка"), max_length=120, required=False)
    model = forms.CharField(label=_("Модель"), max_length=120, required=False)
    generation = forms.CharField(label=_("Поколение"), max_length=120, required=False)
    year = forms.IntegerField(label=_("Год"), min_value=1886, max_value=2200, required=False)
    engine_code = forms.CharField(label=_("Код двигателя"), max_length=120, required=False)
    transmission = forms.CharField(label=_("Трансмиссия"), max_length=120, required=False)
    fuel_type = forms.CharField(label=_("Тип топлива"), max_length=64, required=False)
    ecu_hardware = forms.CharField(label=_("ECU hardware"), max_length=255, required=False)
    ecu_software = forms.CharField(label=_("ECU software"), max_length=255, required=False)
    mileage = forms.IntegerField(label=_("Пробег, км"), min_value=0, required=False)
    market = forms.CharField(label=_("Рынок"), max_length=64, required=False)

    def __init__(self, *args, observation=None, **kwargs):
        if observation is not None and "initial" not in kwargs:
            kwargs["initial"] = observation.effective_data
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class DiagnosticUploadForm(forms.ModelForm):
    max_upload_size = 10 * 1024 * 1024
    allowed_content_types = {
        "application/pdf",
        "application/x-pdf",
    }

    class Meta:
        model = DiagnosticSession
        fields = ["vin", "vehicle_model", "raw_file"]
        labels = {
            "vin": _("VIN автомобиля"),
            "vehicle_model": _("Модель автомобиля"),
            "raw_file": _("Файл отчёта"),
        }
        widgets = {
            "vin": forms.TextInput(attrs={"class": "form-control"}),
            "vehicle_model": forms.TextInput(attrs={"class": "form-control"}),
            "raw_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean_raw_file(self):
        uploaded_file = self.cleaned_data["raw_file"]

        if uploaded_file.size > self.max_upload_size:
            raise forms.ValidationError(
                _("Размер PDF-файла не должен превышать 10 МБ.")
            )

        if Path(uploaded_file.name).suffix.lower() != ".pdf":
            raise forms.ValidationError(
                _("Поддерживаются только диагностические отчёты в формате PDF.")
            )

        content_type = getattr(uploaded_file, "content_type", "")
        if content_type not in self.allowed_content_types:
            raise forms.ValidationError(_("Некорректный MIME-тип PDF-файла."))

        signature = uploaded_file.read(5)
        uploaded_file.seek(0)
        if signature != b"%PDF-":
            raise forms.ValidationError(
                _("Файл не является корректным PDF-документом.")
            )

        return uploaded_file


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
            "inspector": _("Мастер"),
            "mileage_km": _("Пробег (км)"),
            "lift_used": _("Подъёмник использовался"),
            "test_drive": _("Тест-драйв выполнялся"),
            "overall_risk": _("Общий риск по подвеске"),
            "comment": _("Комментарий"),
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
            "reason": forms.TextInput(attrs={"class": "form-control", "placeholder": _("люфт / трещины / потёк...")}),
            "evidence": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": _("что увидели/услышали/померили")}),
            "part_number": forms.TextInput(attrs={"class": "form-control"}),
            "needs_replacement": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "part_type": _("Деталь"),
            "wear_percent": _("Износ (%)"),
            "severity": _("Критичность"),
            "reason": _("Причина"),
            "evidence": _("Признаки/замеры"),
            "part_number": _("Каталожный №"),
            "needs_replacement": _("Замена"),
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
            raise forms.ValidationError(_("Износ должен быть в диапазоне 0–100."))
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
