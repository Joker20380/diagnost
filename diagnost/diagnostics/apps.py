from django.apps import AppConfig


MODEL_NAMES = {
    "SuspensionPartType": ("тип элемента подвески", "типы элементов подвески"),
    "SuspensionPart": ("элемент подвески", "элементы подвески"),
    "DiagnosticSession": ("диагностическая сессия", "диагностические сессии"),
    "DiagnosticCode": ("диагностический код", "диагностические коды"),
    "SensorReading": ("показание датчика", "показания датчиков"),
    "SuspensionInspection": ("осмотр подвески", "осмотры подвески"),
    "DiagnosticCase": ("диагностический случай", "диагностические случаи"),
    "CustomerComplaint": ("жалоба клиента", "жалобы клиентов"),
    "OperatingConditions": ("условия эксплуатации", "условия эксплуатации"),
    "Vehicle": ("автомобиль", "автомобили"),
    "VehicleConfiguration": ("конфигурация автомобиля", "конфигурации автомобилей"),
    "VehicleIdentityObservation": ("наблюдение идентификации", "наблюдения идентификации"),
    "DiagnosticRecord": ("диагностическая запись", "диагностические записи"),
    "QAEvent": ("событие контроля качества", "события контроля качества"),
}


class DiagnosticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'diagnostics'
    verbose_name = 'Диагностика и автомобили'

    def ready(self):
        for model_name, (singular, plural) in MODEL_NAMES.items():
            model = self.get_model(model_name)
            model._meta.verbose_name = singular
            model._meta.verbose_name_plural = plural
