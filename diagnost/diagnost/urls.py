"""
URL configuration for diagnost project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import set_language


urlpatterns = [
    # Tech endpoints (keep without language prefix)
    path("ckeditor5/", include("django_ckeditor_5.urls")),

    # Language switch endpoint (POST)
    path("i18n/setlang/", set_language, name="set_language"),
]

# Public + admin + auth under language prefix
urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("", include("main.urls")),
    path("accounts/", include("allauth.urls")),
    prefix_default_language=False,  # default language at "/" (no /en/)
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
