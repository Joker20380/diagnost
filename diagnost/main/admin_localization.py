from django.apps import apps
from django.utils.translation import gettext_lazy as _


COMMON_LABELS = {
    "address": "Адрес", "created_at": "Создано", "description": "Описание", "details": "Подробности",
    "message": "Сообщение", "opened_at": "Открыто", "phone": "Телефон", "slug": "URL-идентификатор",
    "started_at": "Начато", "unit": "Единица измерения", "value": "Значение", "vin": "VIN",
}


LABELS = {

    "action": "Действие", "actor": "Пользователь", "after_status": "Статус после",
    "ai_disclaimer_version": "Версия предупреждения AI", "ai_generated_at": "Сформировано AI",
    "ambient_temperature_c": "Температура воздуха, °C", "analysis_engine": "Механизм анализа",
    "analysis_generated_at": "Анализ сформирован", "analysis_method": "Метод анализа",
    "analysis_version": "Версия анализа", "approved_at": "Согласовано",
    "assigned_to": "Назначено исполнителю", "before_status": "Статус до", "brand": "Марка",
    "case": "Случай", "case_operation": "Выполнение операции", "closed_at": "Закрыто",
    "code": "Код", "comment": "Комментарий", "completed_at": "Завершено",
    "completed_by": "Завершил", "completeness_status": "Полнота данных",
    "confirmed_at": "Подтверждено", "confirmed_by": "Подтвердил",
    "confirmed_cause": "Подтверждённая причина", "content_sha256": "Контрольная сумма SHA-256",
    "corrections": "Исправления", "created": "Создано", "created_by": "Создал",
    "customer_words": "Слова клиента", "description_en": "Описание на английском",
    "description_ru": "Описание на русском", "diagnostic_notes": "Диагностические заметки",
    "diagnostic_value": "Диагностическое значение", "ecu_hardware": "Аппаратная версия ЭБУ",
    "ecu_software": "Программная версия ЭБУ", "employee_id": "Табельный номер",
    "engine_code": "Код двигателя", "engine_load": "Нагрузка двигателя",
    "engine_temperature": "Температура двигателя", "evidence": "Доказательство",
    "expert_conclusion": "Заключение эксперта", "expert_name": "Имя эксперта",
    "expert_signed_at": "Подписано экспертом", "file": "Файл", "file_name": "Имя файла",
    "frequency": "Частота", "fuel_type": "Тип топлива", "generation": "Поколение",
    "handover_time": "Время передачи", "import_batch": "Пакет импорта", "inspection": "Осмотр",
    "inspector": "Проверяющий", "intermittent": "Периодическая неисправность",
    "is_active": "Активно", "is_current": "Текущая", "is_known": "Известно",
    "job_title": "Должность", "key": "Ключ", "lat": "Широта", "legal_name": "Юридическое название",
    "level": "Уровень", "lift_used": "Использован подъёмник", "lon": "Долгота",
    "make": "Марка", "manufacturer": "Производитель", "market": "Рынок",
    "max_level": "Максимальный уровень", "metadata": "Метаданные", "mileage_km": "Пробег, км",
    "missing_fields": "Недостающие поля", "model": "Модель", "module_code": "Код модуля",
    "module_name": "Название модуля", "name": "Название", "name_en": "Название на английском",
    "name_ru": "Название на русском", "needs_replacement": "Требуется замена", "notes": "Заметки",
    "observed_at": "Зафиксировано", "onset": "Начало проявления", "organization": "Организация",
    "original_data": "Исходные данные", "overall_risk": "Общий риск",
    "parse_run": "Запуск распознавания", "part_number": "Номер детали", "part_type": "Тип детали",
    "payload": "Данные события", "pid": "PID", "possible_causes": "Возможные причины",
    "previous_revision": "Предыдущая редакция", "raw_file": "Исходный файл",
    "raw_text": "Исходный текст", "reason": "Причина", "recommendation": "Рекомендация",
    "recommended_checks": "Рекомендуемые проверки", "recommended_work": "Рекомендуемые работы",
    "record": "Запись", "recorded_at": "Записано", "recorded_by": "Записал",
    "reference": "Справочное значение", "resolved_at": "Устранено", "resolved_by": "Устранил",
    "review_reasons": "Причины проверки", "revision": "Редакция", "role": "Роль",
    "rows_created": "Создано строк", "rows_skipped": "Пропущено строк", "rows_total": "Всего строк",
    "rows_updated": "Обновлено строк", "safety_notes": "Примечания по безопасности",
    "scope": "Область применения", "session": "Диагностическая сессия", "severity": "Критичность",
    "signed_at": "Подписано", "source_name": "Название источника", "source_url": "Ссылка на источник",
    "status": "Статус", "status_text": "Описание статуса", "submitted_at": "Добавлено",
    "submitted_by": "Добавил", "subscribed_at": "Дата подписки", "summary": "Резюме",
    "supersedes": "Заменяет", "suspension_comment": "Комментарий по подвеске", "symptoms": "Симптомы",
    "system": "Система", "system_report": "Системный отчёт", "tax_id": "Налоговый номер",
    "technician": "Специалист", "test_drive": "Тестовая поездка", "timestamp": "Время",
    "title_en": "Название на английском", "title_ru": "Название на русском",
    "transmission": "Трансмиссия", "unsubscribe_token": "Токен отписки",
    "updated": "Обновлено", "updated_at": "Обновлено", "user_profile": "Профиль пользователя",
    "variant": "Модификация", "vehicle": "Автомобиль", "vehicle_configuration": "Конфигурация автомобиля",
    "vehicle_model": "Модель автомобиля", "vehicle_speed": "Скорость автомобиля",
    "verified_at": "Подтверждено", "verified_by": "Подтвердил", "vin_normalized": "Нормализованный VIN",
    "wear_percent": "Износ, %", "workshop": "Автосервис", "year": "Год",
}

LABELS.update(COMMON_LABELS)

CHOICES = {
    "draft": "Черновик", "published": "Опубликовано", "retired": "Архив",
    "pending": "Ожидает", "in_progress": "В работе", "blocked": "Заблокировано",
    "completed": "Завершено", "cancelled": "Отменено", "failed": "Не пройдено",
    "verified": "Подтверждено", "incomplete": "Не завершено", "requires_review": "Требует проверки",
    "locked": "Недоступно", "available": "Доступно", "skipped": "Пропущено",
    "approve": "Одобрить", "reject": "Отклонить", "rework": "Вернуть на доработку",
    "escalate": "Передать эксперту", "open": "Открыто", "closed": "Закрыто",
    "low": "Низкая", "medium": "Средняя", "high": "Высокая", "critical": "Критическая",
    "unknown": "Неизвестно", "confirmed": "Подтверждено", "rejected": "Отклонено",
    "manual": "Вручную", "automatic": "Автоматически",
}


def apply_admin_localization():
    for app_label in ("main", "users", "diagnostics", "assurance"):
        for model in apps.get_app_config(app_label).get_models():
            model._meta.verbose_name = _(str(model._meta.verbose_name))
            model._meta.verbose_name_plural = _(str(model._meta.verbose_name_plural))
            for field in model._meta.fields:
                if field.name in LABELS:
                    field.verbose_name = _(LABELS[field.name])
                field.verbose_name = _(str(field.verbose_name))
                if field.choices:
                    field.choices = [(value, _(CHOICES.get(str(value), label))) for value, label in field.choices]
