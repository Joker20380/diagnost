from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe

from .models import UserProfile

from django.contrib import admin
from django.utils.safestring import mark_safe
from import_export.admin import ImportExportModelAdmin
from django_admin_geomap import ModelAdmin

from .resources import *
from .models import *


class Admin(ImportExportModelAdmin, ModelAdmin):
	resource_class = LocationResource
	geomap_default_longitude = "44.6835"
	geomap_default_latitude = "43.0167"
	geomap_default_zoom = "13"
	geomap_field_longitude = 'id_lon'
	geomap_field_latitude = 'id_lat'
	geomap_item_zoom = "18"
	geomap_height = "500px"
#	geomap_new_feature_icon = "https://workhub-rso.ru/static/pillow/img/svg7.svg"


class UserInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Доп. информация'


# Определяем новый класс настроек для модели User
class UserAdmin(ImportExportModelAdmin, UserAdmin, admin.ModelAdmin):
    inlines = (UserInline,)
    resource_classes = [UserResource, UserResource2]
    list_display = ('id', 'username', 'last_name', 'first_name', 'get_patronymic', 'get_image', 'email',)
    search_fields = ('id', 'username', 'last_name', 'first_name', 'get_patronymic', 'school_class', 'school', 'get_image',
                     'email', 'phone_number', 'address')
    list_editable = ('email',)
    list_filter = ('username', 'email')

    def get_patronymic(self, obj):
        return obj.userprofile.patronymic

    def get_image(self, obj):
        if obj.userprofile.image:
            return mark_safe(f"<img src='{obj.userprofile.image.url}' width=50>")

    get_image.short_description = 'Фото'
    get_patronymic.short_description = 'Отчество'


# Перерегистрируем модель User
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Location, Admin)
