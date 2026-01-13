# main/models.py
from __future__ import annotations

from django.db import models
from django.utils import timezone

from users.models import UserProfile


class DiagnosticSession(models.Model):
    user_profile = models.ForeignKey(
        UserProfile, on_delete=models.SET_NULL, null=True, blank=True
    )
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

    # --- Финальное решение специалиста (human-in-the-loop)
    expert_conclusion = models.TextField(blank=True)
    expert_name = models.CharField(max_length=128, blank=True)
    expert_signed_at = models.DateTimeField(null=True, blank=True)

    # --- Pipeline/статусы
    STATUS_CHOICES = [
        ("engine_done", "Диагностика двигателя завершена"),
        ("suspension_pending", "Ожидает осмотра подвески"),
        ("suspension_done", "Диагностика подвески завершена"),
        # можно расширять: brakes_pending, brakes_done, transmission_done и т.д.
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="engine_done")

    handover_time = models.DateTimeField(null=True, blank=True)

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


class DiagnosticCode(models.Model):
    session = models.ForeignKey(
        DiagnosticSession, on_delete=models.CASCADE, related_name="codes"
    )
    code = models.CharField(max_length=10)
    description = models.CharField(max_length=255, blank=True)
    is_known = models.BooleanField(default=True)

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
        ("draft", "Черновик"),
        ("signed", "Подписан мастером"),
    ]
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")
    signed_at = models.DateTimeField(null=True, blank=True)

    # --- Контекст осмотра (опционально, но полезно)
    mileage_km = models.PositiveIntegerField(null=True, blank=True)
    test_drive = models.BooleanField(default=False)
    lift_used = models.BooleanField(default=True)

    OVERALL_RISK_CHOICES = [
        ("low", "Низкий"),
        ("medium", "Средний"),
        ("high", "Высокий"),
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
        ("ok", "Ок"),
        ("warn", "Внимание"),
        ("crit", "Критично"),
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
