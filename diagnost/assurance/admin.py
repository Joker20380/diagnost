import json

from django.contrib import admin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .services import (
    clone_procedure_version, compare_procedure_versions,
    moderate_evidence_promotion, publish_procedure_version,
)

from .models import (
    Certification,
    CaseOperation,
    Evidence,
    EvidenceRequirement,
    ExpertDecision,
    EvidencePromotionRequest,
    Operation,
    OperationCertificationRequirement,
    OperationDependency,
    ProcedureVersion,
    ReferenceMedia,
    RepairAuditEvent,
    RepairCase,
    RepairProcedure,
    RepairRecord,
    Skill,
    TechnicianCertification,
    TechnicianSkill,
    Verification,
)


FIELD_LABELS = {
    "organization": "Организация", "workshop": "Автосервис", "code": "Код", "name": "Название",
    "description": "Описание", "technician": "Специалист", "skill": "Компетенция", "level": "Уровень",
    "certification": "Сертификат", "required_certifications": "Требуемые сертификаты",
    "valid_from": "Действует с", "valid_until": "Действует до", "issued_by": "Выдал",
    "issued_at": "Выдано", "vehicle_brands": "Марки автомобилей", "vehicle_models": "Модели автомобилей",
    "verified_by": "Подтвердил", "verified_at": "Подтверждено", "created_by": "Создал", "created_at": "Создано",
    "procedure": "Процедура", "version": "Версия", "status": "Статус", "change_summary": "Описание изменений",
    "published_at": "Опубликовано", "sequence": "Порядок", "title": "Название", "operation_type": "Тип операции",
    "mandatory": "Обязательная", "blocking": "Блокирующая", "qc_operation": "Контроль качества",
    "expected_result": "Ожидаемый результат", "technical_requirements": "Технические требования",
    "target_operation": "Целевая операция", "proposed_title": "Предлагаемое название",
    "license_basis": "Основание прав на повторное использование", "rationale": "Обоснование",
    "requested_by": "Запросил", "requested_at": "Запрошено", "reviewed_by": "Проверил",
    "reviewed_at": "Проверено", "review_rationale": "Обоснование модерации",
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




class OperationDependencyInline(RussianAdminMixin, admin.TabularInline):
    model = OperationDependency
    fk_name = "operation"
    fields = ("depends_on",)
    extra = 0

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        queryset = Operation.objects.none()
        if obj and obj.version_id:
            queryset = Operation.objects.filter(
                version_id=obj.version_id, sequence__lt=obj.sequence
            )
        formset.form.base_fields["depends_on"].queryset = queryset
        return formset


class OperationCertificationRequirementInline(RussianAdminMixin, admin.TabularInline):
    model = OperationCertificationRequirement
    extra = 0


class EvidenceRequirementInline(RussianAdminMixin, admin.TabularInline):
    model = EvidenceRequirement
    extra = 0


class ReferenceMediaInline(RussianAdminMixin, admin.TabularInline):
    model = ReferenceMedia
    extra = 0




@admin.register(Operation)
class OperationAdmin(RussianAdminMixin, admin.ModelAdmin):
    list_display = ("version", "sequence", "title", "operation_type", "blocking", "approval_required")
    list_filter = (
        "version__procedure", "version", "operation_type", "blocking",
        "qc_operation", "approval_required",
    )
    list_select_related = ("version", "version__procedure", "required_skill")
    search_fields = ("key", "title", "description", "version__procedure__name")
    ordering = ("version", "sequence")
    inlines = (
        OperationDependencyInline,
        OperationCertificationRequirementInline,
        EvidenceRequirementInline,
        ReferenceMediaInline,
    )


@admin.register(ProcedureVersion)
class ProcedureVersionAdmin(RussianAdminMixin, admin.ModelAdmin):
    list_display = ("procedure", "version", "status", "operation_count", "comparison_summary", "published_at")
    list_filter = ("status",)
    search_fields = ("procedure__code", "procedure__name", "change_summary")
    list_select_related = ("procedure",)
    readonly_fields = ("status", "content_sha256", "published_at", "comparison_with_previous")
    actions = ("publish_selected_versions", "clone_selected_versions")

    @admin.display(description=_("операции"))
    def operation_count(self, obj):
        return obj.operations.count()
    def _comparison(self, obj):
        previous = obj.procedure.versions.filter(version__lt=obj.version).order_by("-version").first()
        return compare_procedure_versions(base=previous, candidate=obj) if previous else None

    @admin.display(description=_("изменения"))
    def comparison_summary(self, obj):
        comparison = self._comparison(obj)
        if not comparison:
            return _("первая версия")
        return f"+{len(comparison['added_operations'])} / -{len(comparison['removed_operations'])} / Δ{len(comparison['changed_operations'])}"

    @admin.display(description=_("Сравнение с предыдущей версией"))
    def comparison_with_previous(self, obj):
        comparison = self._comparison(obj)
        if not comparison:
            return _("Предыдущая версия отсутствует.")
        return format_html("<pre>{}</pre>", json.dumps(comparison, ensure_ascii=False, indent=2))

    @admin.action(description=_("Клонировать выбранные версии в новые черновики"))
    def clone_selected_versions(self, request, queryset):
        for version in queryset.order_by("procedure_id", "version"):
            try:
                clone = clone_procedure_version(source_version=version, user=request.user)
            except Exception as exc:
                self.message_user(request, f"{version}: {exc}", level=messages.ERROR)
            else:
                self.message_user(request, f"{version} → {clone}", level=messages.SUCCESS)



    @admin.action(description=_("Опубликовать выбранные черновые версии"))
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


@admin.register(EvidencePromotionRequest)
class EvidencePromotionRequestAdmin(RussianAdminMixin, admin.ModelAdmin):
    list_display = ("id", "evidence", "target_operation", "status", "requested_by", "requested_at")
    list_filter = ("status", "target_operation__version__procedure")
    search_fields = ("proposed_title", "license_basis", "rationale")
    readonly_fields = (
        "requested_by", "requested_at", "status", "reviewed_by",
        "reviewed_at", "review_rationale", "reference_media",
    )
    actions = ("approve_selected", "reject_selected")

    def save_model(self, request, obj, form, change):
        if change:
            return
        obj.requested_by = request.user.userprofile
        super().save_model(request, obj, form, change)

    def _moderate(self, request, queryset, decision, rationale):
        count = 0
        for item in queryset:
            try:
                moderate_evidence_promotion(
                    promotion_request=item, decision=decision,
                    review_rationale=rationale, user=request.user,
                )
            except Exception as exc:
                self.message_user(request, f"{item.pk}: {exc}", level=messages.ERROR)
            else:
                count += 1
        if count:
            self.message_user(request, f"Обработано заявок: {count}", level=messages.SUCCESS)

    @admin.action(description=_("Одобрить выбранные заявки на справочный материал"))
    def approve_selected(self, request, queryset):
        self._moderate(
            request, queryset, EvidencePromotionRequest.Status.APPROVED,
            "Права и техническая применимость подтверждены модератором.",
        )

    @admin.action(description=_("Отклонить выбранные заявки на справочный материал"))
    def reject_selected(self, request, queryset):
        self._moderate(
            request, queryset, EvidencePromotionRequest.Status.REJECTED,
            "Заявка отклонена модератором после проверки прав и применимости.",
        )


@admin.register(RepairCase)
class RepairCaseAdmin(RussianAdminMixin, admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    list_display = ("id", "vehicle", "title", "procedure_version", "status", "verification_status")
    list_filter = ("status", "verification_status", "organization", "workshop")


MODEL_NAMES = {
    Skill: ("компетенция", "компетенции"),
    TechnicianSkill: ("компетенция специалиста", "компетенции специалистов"),
    Certification: ("сертификат", "сертификаты"),
    TechnicianCertification: ("сертификат специалиста", "сертификаты специалистов"),
    RepairProcedure: ("ремонтная процедура", "ремонтные процедуры"),
    ProcedureVersion: ("версия процедуры", "версии процедур"),
    Operation: ("операция", "операции"),
    OperationCertificationRequirement: ("требование сертификата", "требования сертификатов"),
    OperationDependency: ("зависимость операции", "зависимости операций"),
    EvidencePromotionRequest: ("заявка на справочный материал", "заявки на справочные материалы"),
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
    # Keep model captions lazy so they follow the language selected for the
    # current admin request instead of being frozen in Russian at import time.
    model._meta.verbose_name = _(singular)
    model._meta.verbose_name_plural = _(plural)
    for field in model._meta.fields:
        if field.name in FIELD_LABELS:
            field.verbose_name = FIELD_LABELS[field.name]


class RussianDefaultAdmin(RussianAdminMixin, admin.ModelAdmin):
    pass


for model in (RepairProcedure, OperationDependency, Skill, TechnicianSkill, Certification,
              TechnicianCertification, CaseOperation,
              Evidence, ExpertDecision, Verification, RepairRecord, RepairAuditEvent):
    admin.site.register(model, RussianDefaultAdmin)
