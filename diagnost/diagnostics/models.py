# main/models.py
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
import re
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from users.models import UserProfile


class VehicleBrand(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Марка автомобиля"
        verbose_name_plural = "Марки автомобилей"

    def __str__(self):
        return self.name


class DTCImportBatch(models.Model):
    source_name = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(blank=True)
    file_name = models.CharField(max_length=255, blank=True)

    rows_total = models.PositiveIntegerField(default=0)
    rows_created = models.PositiveIntegerField(default=0)
    rows_updated = models.PositiveIntegerField(default=0)
    rows_skipped = models.PositiveIntegerField(default=0)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Пакет импорта DTC"
        verbose_name_plural = "Пакеты импорта DTC"

    def __str__(self):
        return f"{self.source_name or 'DTC import'} — {self.created_at:%Y-%m-%d %H:%M}"


class DTCReference(models.Model):
    class System(models.TextChoices):
        POWERTRAIN = "P", _("Двигатель / трансмиссия")
        CHASSIS = "C", _("Ходовая часть")
        BODY = "B", _("Кузовная электроника")
        NETWORK = "U", _("Сеть / CAN")
        OEM = "O", _("OEM / заводской код")

    class Scope(models.TextChoices):
        GENERIC = "generic", _("Универсальный OBD-II")
        MANUFACTURER = "manufacturer", _("Бренд-специфичный")
        UNKNOWN = "unknown", _("Неизвестно")

    class Severity(models.TextChoices):
        INFO = "info", _("Информационный")
        LOW = "low", _("Низкий")
        MEDIUM = "medium", _("Средний")
        HIGH = "high", _("Высокий")
        CRITICAL = "critical", _("Критический")

    code = models.CharField(max_length=32, db_index=True)
    system = models.CharField(max_length=1, choices=System.choices, db_index=True)
    scope = models.CharField(
        max_length=32,
        choices=Scope.choices,
        default=Scope.UNKNOWN,
        db_index=True,
    )

    manufacturer = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="Пусто для generic OBD-II. Для бренд-специфичных кодов — Toyota, BMW, Hyundai и т.п.",
    )
    brand = models.ForeignKey(
        VehicleBrand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dtc_references",
    )

    title_ru = models.CharField(max_length=500, blank=True)
    title_en = models.CharField(max_length=500, blank=True)

    description_ru = models.TextField(blank=True)
    description_en = models.TextField(blank=True)

    symptoms = models.TextField(blank=True)
    possible_causes = models.TextField(blank=True)
    diagnostic_notes = models.TextField(blank=True)
    recommended_checks = models.TextField(blank=True)

    severity = models.CharField(
        max_length=32,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )

    source_name = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(blank=True)

    is_active = models.BooleanField(default=True)
    import_batch = models.ForeignKey(
        DTCImportBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dtc_references",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code", "manufacturer"]
        constraints = [
            models.UniqueConstraint(
                fields=["code", "manufacturer"],
                name="unique_dtc_reference_per_manufacturer",
            )
        ]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["system", "scope"]),
            models.Index(fields=["manufacturer"]),
        ]
        verbose_name = "Справочник DTC"
        verbose_name_plural = "Справочник DTC"

    def save(self, *args, **kwargs):
        self.code = (self.code or "").upper().strip()

        if self.code:
            if self.code[0] in ["P", "C", "B", "U"]:
                self.system = self.code[0]
            else:
                self.system = self.System.OEM

        self.manufacturer = (self.manufacturer or "").strip()

        if not self.scope or self.scope == self.Scope.UNKNOWN:
            self.scope = self.Scope.MANUFACTURER if self.manufacturer else self.Scope.GENERIC

        super().save(*args, **kwargs)

    def __str__(self):
        if self.manufacturer:
            return f"{self.code} [{self.manufacturer}]"
        return self.code

    @property
    def localized_title(self):
        if (get_language() or "ru").split("-", 1)[0] == "ru":
            return self.title_ru or self.title_en
        return self.title_en or self.title_ru

    @property
    def localized_description(self):
        if (get_language() or "ru").split("-", 1)[0] == "ru":
            return self.description_ru or self.description_en
        return self.description_en or self.description_ru


class OBDLiveDataPIDReference(models.Model):
    pid = models.CharField(max_length=20, unique=True)
    name_ru = models.CharField(max_length=255, blank=True)
    name_en = models.CharField(max_length=255, blank=True)
    unit = models.CharField(max_length=50, blank=True)

    description_ru = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    diagnostic_value = models.TextField(
        blank=True,
        help_text="Чем этот PID полезен при диагностике.",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["pid"]
        verbose_name = "Справочник PID Live Data"
        verbose_name_plural = "Справочник PID Live Data"

    def __str__(self):
        return f"{self.pid} — {self.name_ru or self.name_en}"





class Vehicle(models.Model):
    organization = models.ForeignKey(
        "users.Organization", on_delete=models.PROTECT, related_name="vehicles"
    )
    vin = models.CharField(max_length=64, blank=True)
    vin_normalized = models.CharField(max_length=64, blank=True, db_index=True)
    make = models.CharField(max_length=120, blank=True)
    model = models.CharField(max_length=120, blank=True)
    generation = models.CharField(max_length=120, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["make", "model", "vin_normalized"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "vin_normalized"],
                condition=~models.Q(vin_normalized=""),
                name="unique_vehicle_vin_per_organization",
            )
        ]

    def save(self, *args, **kwargs):
        self.vin = (self.vin or "").strip().upper()
        self.vin_normalized = re.sub(r"[^A-Z0-9]", "", self.vin)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.vin_normalized or f"{self.make} {self.model}".strip() or f"Vehicle #{self.pk}"


class VehicleConfiguration(models.Model):
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.PROTECT, related_name="configurations"
    )
    engine_code = models.CharField(max_length=120, blank=True)
    transmission = models.CharField(max_length=120, blank=True)
    fuel_type = models.CharField(max_length=64, blank=True)
    ecu_hardware = models.CharField(max_length=255, blank=True)
    ecu_software = models.CharField(max_length=255, blank=True)
    mileage_km = models.PositiveIntegerField(null=True, blank=True)
    market = models.CharField(max_length=64, blank=True)
    is_current = models.BooleanField(default=True, db_index=True)
    confirmed_by = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        related_name="confirmed_vehicle_configurations",
    )
    confirmed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-confirmed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=models.Q(is_current=True),
                name="unique_current_configuration_per_vehicle",
            )
        ]

    def __str__(self):
        return f"{self.vehicle} configuration"

class DiagnosticSessionQuerySet(models.QuerySet):
    def visible_to(self, user):
        if not getattr(user, "is_authenticated", False):
            return self.none()
        if user.is_superuser:
            return self

        profile = getattr(user, "userprofile", None)
        if profile is None:
            return self.none()

        technician = getattr(profile, "technician_profile", None)
        if (
            technician is not None
            and technician.is_active
            and technician.organization.is_active
        ):
            return self.filter(
                models.Q(organization=technician.organization)
                | models.Q(organization__isnull=True, user_profile=profile)
            )
        return self.filter(organization__isnull=True, user_profile=profile)

class DiagnosticSession(models.Model):
    class AnalysisMethod(models.TextChoices):
        RULES = "rules", _("Правила")
        KNOWLEDGE_BASE = "knowledge_base", _("База знаний")
        LLM = "llm", _("Языковая модель")
        HYBRID = "hybrid", _("Гибридный анализ")

    user_profile = models.ForeignKey(
        UserProfile, on_delete=models.SET_NULL, null=True, blank=True
    )
    organization = models.ForeignKey(
        "users.Organization",
        on_delete=models.PROTECT,
        related_name="diagnostic_sessions",
        null=True,
        blank=True,
    )
    workshop = models.ForeignKey(
        "users.Workshop",
        on_delete=models.PROTECT,
        related_name="diagnostic_sessions",
        null=True,
        blank=True,
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.PROTECT,
        related_name="diagnostic_sessions",
        null=True,
        blank=True,
    )
    vehicle_configuration = models.ForeignKey(
        VehicleConfiguration,
        on_delete=models.PROTECT,
        related_name="diagnostic_sessions",
        null=True,
        blank=True,
    )
    objects = DiagnosticSessionQuerySet.as_manager()
    created_at = models.DateTimeField(auto_now_add=True)

    vin = models.CharField(max_length=64, blank=True)
    vehicle_model = models.CharField(max_length=128, blank=True)

    raw_file = models.FileField(upload_to="diagnostic_reports/")
    recommendation = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    # --- Прозрачный отчёт по системам (факты → гипотезы → план проверки)
    system_report = models.JSONField(default=dict, blank=True)

    # --- Прозрачность генерации подсказок (если используешь ИИ/правила)
    ai_generated_at = models.DateTimeField(null=True, blank=True)
    ai_disclaimer_version = models.CharField(max_length=32, blank=True, default="v1")
    analysis_method = models.CharField(
        max_length=32,
        choices=AnalysisMethod.choices,
        blank=True,
        default="",
    )
    analysis_engine = models.CharField(max_length=64, blank=True, default="")
    analysis_version = models.CharField(max_length=32, blank=True, default="")
    analysis_generated_at = models.DateTimeField(null=True, blank=True)

    # --- Финальное решение специалиста (human-in-the-loop)
    expert_conclusion = models.TextField(blank=True)
    expert_name = models.CharField(max_length=128, blank=True)
    expert_signed_at = models.DateTimeField(null=True, blank=True)

    # --- Pipeline/статусы
    STATUS_CHOICES = [
        ("parse_failed", _("Ошибка обработки отчёта")),
        ("engine_done", _("Диагностика двигателя завершена")),
        ("suspension_pending", _("Ожидает осмотра подвески")),
        ("suspension_done", _("Диагностика подвески завершена")),
        # можно расширять: brakes_pending, brakes_done, transmission_done и т.д.
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="engine_done")

    handover_time = models.DateTimeField(null=True, blank=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.workshop_id and self.organization_id is None:
            raise ValidationError(
                {"organization": "Organization is required when workshop is set."}
            )
        if (
            self.workshop_id
            and self.organization_id
            and self.workshop.organization_id != self.organization_id
        ):
            raise ValidationError(
                {"workshop": "Workshop must belong to the diagnostic organization."}
            )
        if self.vehicle_id and self.organization_id != self.vehicle.organization_id:
            raise ValidationError(
                {"vehicle": "Vehicle must belong to the diagnostic organization."}
            )
        if (
            self.vehicle_configuration_id
            and self.vehicle_configuration.vehicle_id != self.vehicle_id
        ):
            raise ValidationError(
                {"vehicle_configuration": "Configuration must belong to the selected vehicle."}
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


    # ⚠️ У тебя есть SuspensionInspection.comment — это поле можно считать legacy,
    # но оставляем ради совместимости, чтобы не ломать код/миграции.
    suspension_comment = models.TextField(blank=True, null=True)

    def __str__(self):
        vin = self.vin or "Unknown VIN"
        return f"{vin} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    @property
    def is_signed(self) -> bool:
        return bool(self.expert_signed_at)

    def sign_expert(self, name: str, conclusion: str = "") -> None:
        """Фиксация финального решения специалиста."""
        self.expert_name = name or self.expert_name
        self.expert_conclusion = conclusion or self.expert_conclusion
        self.expert_signed_at = timezone.now()
        self.save(update_fields=["expert_name", "expert_conclusion", "expert_signed_at"])

class VehicleIdentityObservation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending confirmation")
        CONFIRMED = "confirmed", _("Confirmed")
        REJECTED = "rejected", _("Rejected")

    session = models.OneToOneField(
        DiagnosticSession,
        on_delete=models.PROTECT,
        related_name="vehicle_identity_observation",
    )
    parse_run = models.ForeignKey(
        "DiagnosticParseRun",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vehicle_identity_observations",
    )
    original_data = models.JSONField(default=dict)
    corrections = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    observed_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="confirmed_vehicle_identities",
    )

    @property
    def effective_data(self):
        return {**(self.original_data or {}), **(self.corrections or {})}

    def __str__(self):
        return f"Vehicle identity for session {self.session_id}"


class DiagnosticCaseQuerySet(models.QuerySet):
    def visible_to(self, user):
        session_ids = DiagnosticSession.objects.visible_to(user).values("pk")
        return self.filter(session_id__in=session_ids)


class DiagnosticCase(models.Model):
    class Status(models.TextChoices):
        INTAKE = "intake", _("Intake")
        IDENTITY_PENDING = "identity_pending", _("Vehicle identity pending")
        READY = "ready", _("Ready for diagnostics")
        IN_PROGRESS = "in_progress", _("Diagnostics in progress")
        ESCALATED = "escalated", _("Escalated")
        RESOLVED = "resolved", _("Resolved")
        CLOSED = "closed", _("Closed")
        CANCELLED = "cancelled", _("Cancelled")

    session = models.OneToOneField(
        DiagnosticSession, on_delete=models.PROTECT, related_name="diagnostic_case"
    )
    organization = models.ForeignKey(
        "users.Organization", on_delete=models.PROTECT, related_name="diagnostic_cases"
    )
    workshop = models.ForeignKey(
        "users.Workshop", on_delete=models.PROTECT, related_name="diagnostic_cases",
        null=True, blank=True,
    )
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.INTAKE, db_index=True
    )
    created_by = models.ForeignKey(
        UserProfile, on_delete=models.PROTECT, related_name="created_diagnostic_cases"
    )
    assigned_to = models.ForeignKey(
        UserProfile, on_delete=models.PROTECT, related_name="assigned_diagnostic_cases",
        null=True, blank=True,
    )
    opened_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DiagnosticCaseQuerySet.as_manager()

    class Meta:
        ordering = ["-opened_at"]

    def clean(self):
        if self.session.organization_id != self.organization_id:
            raise ValidationError("Case and session must belong to the same organization.")
        if self.workshop_id and self.workshop.organization_id != self.organization_id:
            raise ValidationError("Case workshop must belong to the case organization.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def intake_complete(self):
        complaint = getattr(self, "customer_complaint", None)
        return bool(complaint and complaint.description.strip() and self.symptoms.exists())

    def __str__(self):
        return f"Diagnostic case #{self.pk or 'new'}"


class CustomerComplaint(models.Model):
    case = models.OneToOneField(
        DiagnosticCase, on_delete=models.PROTECT, related_name="customer_complaint"
    )
    description = models.TextField()
    customer_words = models.TextField(blank=True)
    onset = models.CharField(max_length=255, blank=True)
    frequency = models.CharField(max_length=120, blank=True)
    recorded_by = models.ForeignKey(
        UserProfile, on_delete=models.PROTECT, related_name="recorded_complaints"
    )
    recorded_at = models.DateTimeField(auto_now_add=True)


class Symptom(models.Model):
    case = models.ForeignKey(
        DiagnosticCase, on_delete=models.PROTECT, related_name="symptoms"
    )
    description = models.TextField()
    subsystem = models.CharField(max_length=120, blank=True)
    occurrence_conditions = models.TextField(blank=True)
    severity = models.CharField(max_length=32, blank=True)
    recorded_by = models.ForeignKey(
        UserProfile, on_delete=models.PROTECT, related_name="recorded_symptoms"
    )
    recorded_at = models.DateTimeField(auto_now_add=True)


class RecentRepair(models.Model):
    case = models.ForeignKey(
        DiagnosticCase, on_delete=models.PROTECT, related_name="recent_repairs"
    )
    description = models.TextField()
    performed_at = models.DateField(null=True, blank=True)
    mileage_km = models.PositiveIntegerField(null=True, blank=True)
    recorded_by = models.ForeignKey(
        UserProfile, on_delete=models.PROTECT, related_name="recorded_recent_repairs"
    )
    recorded_at = models.DateTimeField(auto_now_add=True)


class OperatingConditions(models.Model):
    case = models.OneToOneField(
        DiagnosticCase, on_delete=models.PROTECT, related_name="operating_conditions"
    )
    description = models.TextField(blank=True)
    ambient_temperature_c = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True
    )
    engine_temperature = models.CharField(max_length=64, blank=True)
    vehicle_speed = models.CharField(max_length=64, blank=True)
    engine_load = models.CharField(max_length=64, blank=True)
    intermittent = models.BooleanField(default=False)
    recorded_by = models.ForeignKey(
        UserProfile, on_delete=models.PROTECT, related_name="recorded_operating_conditions"
    )
    recorded_at = models.DateTimeField(auto_now_add=True)


class DiagnosticRecord(models.Model):
    """Versioned diagnostic act. Approved revisions are immutable."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        IN_REVIEW = "in_review", _("In review")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    session = models.ForeignKey(DiagnosticSession, on_delete=models.PROTECT, related_name="records")
    revision = models.PositiveIntegerField(default=1)
    previous_revision = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="corrections"
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    created_by = models.ForeignKey(
        UserProfile, on_delete=models.PROTECT, related_name="created_diagnostic_records"
    )
    summary = models.TextField(blank=True)
    confirmed_cause = models.TextField(blank=True)
    recommended_work = models.TextField(blank=True)
    safety_notes = models.TextField(blank=True)
    content_sha256 = models.CharField(max_length=64, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["session_id", "-revision"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "revision"], name="unique_diagnostic_record_revision"
            )
        ]

    def __str__(self):
        return f"Diagnostic act #{self.session_id}/r{self.revision}"

    @property
    def is_locked(self) -> bool:
        return self.status == self.Status.APPROVED

    def save(self, *args, **kwargs):
        if self.pk:
            stored = type(self).objects.filter(pk=self.pk).values("status").first()
            if stored and stored["status"] == self.Status.APPROVED:
                raise ValidationError(
                    "Approved diagnostic records are immutable; create a new revision."
                )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_locked:
            raise ValidationError("Approved diagnostic records cannot be deleted.")
        return super().delete(*args, **kwargs)


class DiagnosticMeasurement(models.Model):
    class Result(models.TextChoices):
        NORMAL = "normal", _("Normal")
        OUT_OF_RANGE = "out_of_range", _("Out of range")
        NOT_EVALUATED = "not_evaluated", _("Not evaluated")

    record = models.ForeignKey(
        DiagnosticRecord, on_delete=models.PROTECT, related_name="measurements"
    )
    parameter = models.CharField(max_length=255)
    value_text = models.CharField(max_length=255, blank=True)
    numeric_value = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    unit = models.CharField(max_length=32, blank=True)
    reference_min = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    reference_max = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    result = models.CharField(
        max_length=20, choices=Result.choices, default=Result.NOT_EVALUATED
    )
    method = models.CharField(max_length=255, blank=True)
    tool_name = models.CharField(max_length=255, blank=True)
    evidence_note = models.TextField(blank=True)
    measured_by = models.ForeignKey(
        UserProfile, on_delete=models.PROTECT, related_name="diagnostic_measurements"
    )
    measured_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["measured_at", "id"]

    def clean(self):
        if self.numeric_value is None and not self.value_text.strip():
            raise ValidationError("A numeric or text measurement value is required.")

    def save(self, *args, **kwargs):
        if self.record_id and self.record.is_locked:
            raise ValidationError("Measurements of an approved record are immutable.")
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.record.is_locked:
            raise ValidationError("Measurements of an approved record cannot be deleted.")
        return super().delete(*args, **kwargs)


class DiagnosticApproval(models.Model):
    class Decision(models.TextChoices):
        APPROVE = "approve", _("Approve")
        REJECT = "reject", _("Reject")
        REQUEST_CHANGES = "request_changes", _("Request changes")

    record = models.ForeignKey(
        DiagnosticRecord, on_delete=models.PROTECT, related_name="approvals"
    )
    reviewer = models.ForeignKey(
        UserProfile, on_delete=models.PROTECT, related_name="diagnostic_approvals"
    )
    decision = models.CharField(max_length=24, choices=Decision.choices)
    comment = models.TextField(blank=True)
    snapshot_sha256 = models.CharField(max_length=64)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["decided_at", "id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Approval decisions are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Approval decisions are append-only.")


class QAEvent(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", _("Information")
        WARNING = "warning", _("Warning")
        ERROR = "error", _("Error")
        CRITICAL = "critical", _("Critical")

    session = models.ForeignKey(
        DiagnosticSession, on_delete=models.PROTECT, related_name="qa_events"
    )
    record = models.ForeignKey(
        DiagnosticRecord,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="qa_events",
    )
    code = models.CharField(max_length=64, db_index=True)
    severity = models.CharField(
        max_length=16, choices=Severity.choices, default=Severity.WARNING, db_index=True
    )
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="resolved_qa_events",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["session", "severity", "resolved_at"])]


class DiagnosticParseRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("В обработке")
        SUCCEEDED = "succeeded", _("Успешно")
        FAILED = "failed", _("Ошибка")

    session = models.ForeignKey(
        DiagnosticSession,
        on_delete=models.CASCADE,
        related_name="parse_runs",
    )
    source_type = models.CharField(max_length=32, default="launch_pdf")
    parser_name = models.CharField(max_length=64)
    parser_version = models.CharField(max_length=32)
    content_sha256 = models.CharField(max_length=64, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    is_current = models.BooleanField(default=False, db_index=True)
    parsed_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    fault_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-parsed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "parser_name", "parser_version", "content_sha256"],
                name="unique_parse_run_per_session_parser_content",
            ),
            models.UniqueConstraint(
                fields=["session"],
                condition=models.Q(is_current=True),
                name="unique_current_parse_run_per_session",
            ),
        ]
        indexes = [
            models.Index(fields=["session", "status"]),
            models.Index(fields=["parser_name", "parser_version"]),
        ]
        verbose_name = "Запуск парсера диагностики"
        verbose_name_plural = "Запуски парсера диагностики"

    def __str__(self):
        return f"{self.parser_name} {self.parser_version} — session {self.session_id}"


class DiagnosticCode(models.Model):
    session = models.ForeignKey(
        DiagnosticSession, on_delete=models.CASCADE, related_name="codes"
    )
    code = models.CharField(max_length=32)
    description = models.CharField(max_length=500, blank=True)

    module_code = models.CharField(max_length=64, blank=True)
    module_name = models.CharField(max_length=255, blank=True)
    status_text = models.CharField(max_length=64, blank=True)
    raw_text = models.TextField(blank=True)
    is_known = models.BooleanField(default=True)

    reference = models.ForeignKey(
        DTCReference,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="session_codes",
        help_text="Связь с глобальным справочником DTC.",
    )
    parse_run = models.ForeignKey(
        DiagnosticParseRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="code_observations",
        help_text="Запуск парсера, создавший это наблюдение.",
    )

    def save(self, *args, **kwargs):
        self.code = (self.code or "").upper().strip()

        if self.reference_id is None and self.code:
            self.reference = (
                DTCReference.objects.filter(code=self.code, manufacturer="")
                .first()
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} ({self.session.vin})"


class SensorReading(models.Model):
    session = models.ForeignKey(
        DiagnosticSession, on_delete=models.CASCADE, related_name="readings"
    )
    timestamp = models.FloatField(help_text="Время в секундах от начала записи")
    name = models.CharField(max_length=64)
    value = models.FloatField()

    def __str__(self):
        return f"{self.name}: {self.value} at {self.timestamp}s"


class SuspensionInspection(models.Model):
    session = models.OneToOneField(
        DiagnosticSession, on_delete=models.CASCADE, related_name="suspension_inspection"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    inspector = models.ForeignKey(
        UserProfile, on_delete=models.SET_NULL, null=True, blank=True
    )
    comment = models.TextField(blank=True)

    # --- Подпись/аудит (чтобы “ИИ не рулит”: финальный факт = подпись мастера)
    STATUS_CHOICES = [
        ("draft", _("Черновик")),
        ("signed", _("Подписан мастером")),
    ]
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")
    signed_at = models.DateTimeField(null=True, blank=True)

    # --- Контекст осмотра (опционально, но полезно)
    mileage_km = models.PositiveIntegerField(null=True, blank=True)
    test_drive = models.BooleanField(default=False)
    lift_used = models.BooleanField(default=True)

    OVERALL_RISK_CHOICES = [
        ("low", _("Низкий")),
        ("medium", _("Средний")),
        ("high", _("Высокий")),
    ]
    overall_risk = models.CharField(
        max_length=10, choices=OVERALL_RISK_CHOICES, default="medium"
    )

    def __str__(self):
        return f"Осмотр подвески для сессии {self.session.id}"

    @property
    def is_signed(self) -> bool:
        return self.status == "signed" and bool(self.signed_at)

    def sign(self, inspector: UserProfile | None = None) -> None:
        """Подписать осмотр: после этого запись должна стать read-only на уровне UI."""
        if inspector and not self.inspector:
            self.inspector = inspector
        self.status = "signed"
        self.signed_at = timezone.now()
        self.save(update_fields=["inspector", "status", "signed_at"])

    def save(self, *args, **kwargs):
        if self.pk:
            stored_status = (
                type(self).objects.filter(pk=self.pk).values_list("status", flat=True).first()
            )
            if stored_status == "signed":
                raise ValidationError(
                    "Signed suspension inspections are immutable."
                )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_signed:
            raise ValidationError("Signed suspension inspections cannot be deleted.")
        return super().delete(*args, **kwargs)


class SuspensionPartType(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class SuspensionPart(models.Model):
    inspection = models.ForeignKey(
        SuspensionInspection, on_delete=models.CASCADE, related_name="parts"
    )
    part_type = models.ForeignKey(SuspensionPartType, on_delete=models.PROTECT, null=True)

    wear_percent = models.PositiveSmallIntegerField()
    part_number = models.CharField(max_length=64, blank=True)
    needs_replacement = models.BooleanField(default=False)

    # --- Усиление фактологии: что именно не так и насколько критично
    SEVERITY_CHOICES = [
        ("ok", _("Ок")),
        ("warn", _("Внимание")),
        ("crit", _("Критично")),
    ]
    severity = models.CharField(max_length=8, choices=SEVERITY_CHOICES, default="warn")

    reason = models.CharField(
        max_length=64,
        blank=True,
        help_text="Основание: люфт, трещины, потёк, стук, коррозия, деформация и т.п.",
    )
    evidence = models.TextField(
        blank=True,
        help_text="Наблюдения/замеры: что именно увидели/услышали/померили",
    )

    def __str__(self):
        pt = self.part_type.name if self.part_type else "Деталь"
        return f"{pt} ({self.wear_percent}% износа)"

    def save(self, *args, **kwargs):
        if self.inspection_id and self.inspection.is_signed:
            raise ValidationError("Parts of a signed inspection are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.inspection.is_signed:
            raise ValidationError(
                "Parts of a signed inspection cannot be deleted."
            )
        return super().delete(*args, **kwargs)


class SuspensionAttachment(models.Model):
    """Фото/файлы как доказательная база осмотра (опционально, но полезно)."""
    inspection = models.ForeignKey(
        SuspensionInspection, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="inspections/suspension/")
    caption = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.caption or f"Attachment #{self.id}"

    def save(self, *args, **kwargs):
        if self.inspection_id and self.inspection.is_signed:
            raise ValidationError("Attachments of a signed inspection are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.inspection.is_signed:
            raise ValidationError(
                "Attachments of a signed inspection cannot be deleted."
            )
        return super().delete(*args, **kwargs)
