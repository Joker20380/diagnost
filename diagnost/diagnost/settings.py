"""
Django settings for diagnost project.
Docker-ready config: Postgres + Redis, sane defaults, no host-specific paths.
"""

from pathlib import Path
from decouple import Csv, config
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------------------
# Core
# ------------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

USE_X_FORWARDED_HOST = config("USE_X_FORWARDED_HOST", default=False, cast=bool)

_secure_hdr = config("SECURE_PROXY_SSL_HEADER", default="", cast=str).strip()
if _secure_hdr and "," in _secure_hdr:
    k, v = [x.strip() for x in _secure_hdr.split(",", 1)]
    SECURE_PROXY_SSL_HEADER = (k, v)

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in config("CSRF_TRUSTED_ORIGINS", default="", cast=str).split(",")
    if o.strip()
]

# ------------------------------------------------------------------------------
# Applications
# ------------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    "django_ckeditor_5",
    "import_export",
    "phonenumber_field",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.vk",
    "allauth.socialaccount.providers.telegram",
    "allauth.socialaccount.providers.yandex",
    "allauth.socialaccount.providers.google",
    "django_admin_geomap",
    "dal",
    "dal_select2",
    "django_select2",

    "main",
    "users",
    "diagnostics",
]

# ------------------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "diagnost.urls"

# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "main" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "diagnost.wsgi.application"

# ------------------------------------------------------------------------------
# Database
# ------------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DATABASE_NAME"),
        "USER": config("DATABASE_USER"),
        "PASSWORD": config("DATABASE_PASSWORD"),
        "HOST": config("DATABASE_HOST", default="postgres"),
        "PORT": config("DATABASE_PORT", default="5432"),
    }
}

# ------------------------------------------------------------------------------
# Auth / allauth
# ------------------------------------------------------------------------------
SITE_ID = config("SITE_ID", default=1, cast=int)

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

_login_methods = config("ACCOUNT_LOGIN_METHODS", default="username,email")
ACCOUNT_LOGIN_METHODS = {m.strip() for m in _login_methods.split(",") if m.strip()}

_signup_fields = config(
    "ACCOUNT_SIGNUP_FIELDS",
    default="email*,username*,password1*,password2*",
)
ACCOUNT_SIGNUP_FIELDS = [f.strip() for f in _signup_fields.split(",") if f.strip()]

ACCOUNT_EMAIL_VERIFICATION = config("ACCOUNT_EMAIL_VERIFICATION", default="none")

LOGIN_REDIRECT_URL = config("LOGIN_REDIRECT_URL", default="/")
LOGOUT_REDIRECT_URL = config("LOGOUT_REDIRECT_URL", default="/")

# ------------------------------------------------------------------------------
# I18N / TZ
# ------------------------------------------------------------------------------
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Default language for BE-prod (override via env if needed)
LANGUAGE_CODE = config("LANGUAGE_CODE", default="en")

TIME_ZONE = config("TIME_ZONE", default="Europe/Brussels")

LANGUAGES = [
    ("en", _("English")),
    ("nl", _("Nederlands")),
    ("fr", _("Français")),
    ('de', _('Deutsch')),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# ------------------------------------------------------------------------------
# Static / Media
# ------------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ------------------------------------------------------------------------------
# Email
# ------------------------------------------------------------------------------
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=False, cast=bool)

DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="no-reply@localhost")
SERVER_EMAIL = config("SERVER_EMAIL", default="no-reply@localhost")

# ------------------------------------------------------------------------------
# Redis / Celery
# ------------------------------------------------------------------------------
REDIS_URL = config("REDIS_URL", default="redis://redis:6379/0")
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=REDIS_URL)

# ------------------------------------------------------------------------------
# Security toggles
# ------------------------------------------------------------------------------
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=False, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=False, cast=bool)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
