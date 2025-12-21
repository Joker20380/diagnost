from django.db import models
from users.models import UserProfile


class DiagnosticSession(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    vin = models.CharField(max_length=64, blank=True)
    vehicle_model = models.CharField(max_length=128, blank=True)
    raw_file = models.FileField(upload_to="diagnostic_reports/")
    recommendation = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    # Новые поля:
    STATUS_CHOICES = [
        ('engine_done', 'Диагностика двигателя завершена'),
        ('suspension_pending', 'Ожидает осмотра подвески'),
        ('suspension_done', 'Диагностика подвески завершена'),
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='engine_done')
    handover_time = models.DateTimeField(null=True, blank=True)
    suspension_comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.vin or 'Unknown VIN'} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"



class DiagnosticCode(models.Model):
    session = models.ForeignKey(DiagnosticSession, on_delete=models.CASCADE, related_name='codes')
    code = models.CharField(max_length=10)
    description = models.CharField(max_length=255, blank=True)
    is_known = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} ({self.session.vin})"


class SensorReading(models.Model):
    session = models.ForeignKey(DiagnosticSession, on_delete=models.CASCADE, related_name='readings')
    timestamp = models.FloatField(help_text="Время в секундах от начала записи")
    name = models.CharField(max_length=64)
    value = models.FloatField()

    def __str__(self):
        return f"{self.name}: {self.value} at {self.timestamp}s"
        

class SuspensionInspection(models.Model):
    session = models.OneToOneField(DiagnosticSession, on_delete=models.CASCADE, related_name='suspension_inspection')
    created_at = models.DateTimeField(auto_now_add=True)
    inspector = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"Осмотр подвески для сессии {self.session.id}"


class SuspensionPartType(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class SuspensionPart(models.Model):
    inspection = models.ForeignKey(SuspensionInspection, on_delete=models.CASCADE, related_name='parts')
    part_type = models.ForeignKey(SuspensionPartType, on_delete=models.PROTECT, null=True)
    wear_percent = models.PositiveSmallIntegerField()
    part_number = models.CharField(max_length=64, blank=True)
    needs_replacement = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.part_type.name} ({self.wear_percent}% износа)"
