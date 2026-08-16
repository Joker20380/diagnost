from django.apps import AppConfig


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'
    verbose_name = 'Сайт и контент'
    
    def ready(self):
    	import main.signals


class CookieConsentConfig(AppConfig):
    name = 'cookie_consent'