from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'
    verbose_name = _('Сайт и контент')
    
    def ready(self):
        from main.admin_localization import apply_admin_localization
        import main.signals
        apply_admin_localization()


class CookieConsentConfig(AppConfig):
    name = 'cookie_consent'