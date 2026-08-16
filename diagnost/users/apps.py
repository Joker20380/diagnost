from django.apps import AppConfig


MODEL_NAMES = {
    "Location": ("местоположение", "местоположения"),
    "Organization": ("организация", "организации"),
    "Workshop": ("автосервис", "автосервисы"),
    "TechnicianProfile": ("профиль специалиста", "профили специалистов"),
}


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'Организации и сотрудники'

    def ready(self):
        for model_name, (singular, plural) in MODEL_NAMES.items():
            model = self.get_model(model_name)
            model._meta.verbose_name = singular
            model._meta.verbose_name_plural = plural
