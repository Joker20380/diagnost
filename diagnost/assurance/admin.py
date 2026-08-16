from django.contrib import admin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .services import publish_procedure_version

from .models import (
    CaseOperation,
    Evidence,
    EvidenceRequirement,
    ExpertDecision,
    Operation,
    OperationDependency,
    ProcedureVersion,
    ReferenceMedia,
    RepairAuditEvent,
    RepairCase,
    RepairProcedure,
    RepairRecord,
    Skill,
    TechnicianSkill,
    Verification,
)


FIELD_LABELS = {
    "organization": "Организация", "workshop": "Автосервис", "code": "Код", "name": "Название",
    "description": "Описание", "technician": "Специалист", "skill": "Компетенция", "level": "Уровень",
    "verified_by": "Подтвердил", "verified_at": "Подтверждено", "created_by": "Создал", "created_at": "Создано",
    "procedure": "Процедура", "version": "Версия", "status": "Статус", "change_summary": "Описание изменений",
    "published_at": "Опубликовано", "sequence": "Порядок", "title": "Название", "operation_type": "Тип операции",
    "mandatory": "Обязательная", "blocking": "Блокирующая", "qc_operation": "Контроль качества",
    "expected_result": "Ожидаемый результат", "technical_requirements": "Технические требования",
    "required_tools": "Необходимые инструменты", "specification": "Спецификация", "required_skill": "Компетенция",
    "required_skill_level": "Требуемый уровень", "minimum_role": "Минимальная роль",
    "approval_required": "Требуется согласование", "approval_minimum_role": "Роль согласующего",
    "operation": "Операция", "depends_on": "Зависит от", "evidence_type": "Тип доказательства",
    "required": "Обязательно", "minimum_count": "Минимальное количество", "unit": "Единица измерения",
    "minimum_value": "Минимум", "maximum_value": "Максимум", "source_type": "Источник",
    "provider": "Провайдер", "source_url": "Ссылка", "file": "Файл", "vehicle": "Автомобиль",
    "procedure_version": "Версия процедуры", "complaint": "Жалоба", "result": "Результат",
    "verification_status": "Статус проверки", "opened_at": "Открыто", "started_at": "Начато",
    "completed_at": "Завершено", "repair_case": "Ремонтный кейс", "assigned_to": "Исполнитель",
    "case_operation": "Выполнение операции", "requirement": "Требование", "text": "Текст",
    "numeric_value": "Значение", "submitted_by": "Добавил", "submitted_at": "Добавлено",
    "decision": "Решение", "rationale": "Обоснование", "reviewer": "Эксперт", "decided_at": "Решено",
    "details": "Подробности", "performed_by": "Проверил", "performed_at": "Проверено",
    "snapshot": "Снимок ремонта", "actor": "Пользователь", "action": "Действие",
    "before_status": "Статус до", "after_status": "Статус после", "occurred_at": "Время события",
}
CHOICE_LABELS = {
    "draft": "Черновик", "published": "Опубликована", "retired": "Архивная", "instruction": "Инструкция",
    "measurement": "Измерение", "diagnostic_scan": "Диагностический скан", "decision_gate": "Точка решения",
    "calibration": "Калибровка", "road_test": "Дорожный тест", "qc": "Контроль качества", "photo": "Фото",
    "video": "Видео", "text": "Текст", "document": "Документ", "confirmation": "Подтверждение",
    "in_progress": "В работе", "blocked": "Заблокирован", "completed": "Завершён", "cancelled": "Отменён",
    "verified": "Подтверждён", "failed": "Не пройден", "incomplete": "Не завершён",
    "requires_review": "Требует проверки", "locked": "Недоступна", "available": "Доступна",
    "approve": "Одобрить", "reject": "Отклонить", "rework": "На доработку", "escalate": "Эскалировать",
}

FIELD_LABELS.update({
    "id": "ID", "key": "Ключ", "max_level": "Максимальный уровень", "is_active": "Активно",
    "vehicle_scope": "Применимость к автомобилям", "content_sha256": "Контрольная сумма SHA-256",
    "escalation_allowed": "Разрешена эскалация", "metadata_schema": "Схема метаданных",
    "provider_asset_id": "ID материала у провайдера", "start_seconds": "Начало, сек.",
    "end_seconds": "Окончание, сек.", "metadata": "Метаданные", "initial_state": "Исходное состояние",
    "assigned_by": "Назначил", "assigned_at": "Назначено", "completed_by": "Завершил",
    "supersedes": "Заменяет доказательство", "authorized_operation_keys": "Разрешённые следующие операции",
    "evidence": "Доказательство", "payload": "Данные события", "file": "Файл",
})
CHOICE_LABELS.update({
    "none": "Не требуется", "own": "Собственный", "service_capture": "Материал автосервиса",
    "youtube_embed": "Встраиваемое видео YouTube", "licensed": "Лицензированный", "oem": "OEM",
    "external": "Внешний", "verification": "На проверке", "not_run": "Не запускалась",
    "skipped": "Пропущена",
})

FIELD_LABELS = {key: _(value) for key, value in FIELD_LABELS.items()}
CHOICE_LABELS = {key: _(value) for key, value in CHOICE_LABELS.items()}


class RussianAdminMixin:
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if formfield:
            formfield.label = FIELD_LABELS.get(db_field.name, formfield.label)
            if getattr(formfield, "choices", None):
                formfield.choices = [(value, CHOICE_LABELS.get(value, label)) for value, label in formfield.choices]
        return formfield




class EvidenceRequirementInline(RussianAdminMixin, admin.TabularInline):
    model = EvidenceRequirement
    extra = 0


class ReferenceMediaInline(RussianAdminMixin, admin.TabularInline):
    model = ReferenceMedia
    extra = 0




@admin.register(Operation)
class OperationAdmin(RussianAdminMixin, admin.ModelAdmin):
    list_display = ("version", "sequence", "title", "operation_type", "blocking", "approval_required")
    list_filter = ("operation_type", "blocking", "qc_operation", "approval_required")
    inlines = (EvidenceRequirementInline, ReferenceMediaInline)


@admin.register(ProcedureVersion)
class ProcedureVersionAdmin(RussianAdminMixin, admin.ModelAdmin):
    list_display = ("procedure", "version", "status", "published_at")
    list_filter = ("status",)
    readonly_fields = ("status", "content_sha256", "published_at")
    actions = ("publish_selected_versions",)

    @admin.action(description="Опубликовать выбранные черновые версии")
    def publish_selected_versions(self, request, queryset):
        published = 0
        for version in queryset:
            try:
                publish_procedure_version(version, request.user)
            except Exception as exc:
                self.message_user(request, f"{version}: {exc}", level=messages.ERROR)
            else:
                published += 1
        if published:
            self.message_user(request, f"Опубликовано версий: {published}", level=messages.SUCCESS)


@admin.register(RepairCase)
class RepairCaseAdmin(RussianAdminMixin, admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    list_display = ("id", "vehicle", "title", "procedure_version", "status", "verification_status")
    list_filter = ("status", "verification_status", "organization", "workshop")


MODEL_NAMES = {
    Skill: ("компетенция", "компетенции"),
    TechnicianSkill: ("компетенция специалиста", "компетенции специалистов"),
    RepairProcedure: ("ремонтная процедура", "ремонтные процедуры"),
    ProcedureVersion: ("версия процедуры", "версии процедур"),
    Operation: ("операция", "операции"),
    OperationDependency: ("зависимость операции", "зависимости операций"),
    EvidenceRequirement: ("требование к доказательству", "требования к доказательствам"),
    ReferenceMedia: ("справочный материал", "справочные материалы"),
    RepairCase: ("ремонтный кейс", "ремонтные кейсы"),
    CaseOperation: ("выполнение операции", "выполнение операций"),
    Evidence: ("доказательство", "доказательства"),
    ExpertDecision: ("решение эксперта", "решения экспертов"),
    Verification: ("проверка ремонта", "проверки ремонта"),
    RepairRecord: ("подтверждённая запись ремонта", "подтверждённые записи ремонта"),
    RepairAuditEvent: ("событие аудита", "события аудита"),
}
for model, (singular, plural) in MODEL_NAMES.items():
    model._meta.verbose_name = singular
    model._meta.verbose_name_plural = plural
    for field in model._meta.fields:
        if field.name in FIELD_LABELS:
            field.verbose_name = FIELD_LABELS[field.name]


class RussianDefaultAdmin(RussianAdminMixin, admin.ModelAdmin):
    pass


for model in (RepairProcedure, OperationDependency, Skill, TechnicianSkill, CaseOperation,
              Evidence, ExpertDecision, Verification, RepairRecord, RepairAuditEvent):
    admin.site.register(model, RussianDefaultAdmin)
