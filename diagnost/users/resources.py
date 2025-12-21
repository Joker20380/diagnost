from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget
from .models import *


class UserResource(resources.ModelResource):

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'first_name', 'last_name', 'userprofile__image', 'userprofile__address', 
        			'userprofile__phone_number', 'userprofile__patronymic', 'userprofile__birth', 'userprofile__merit',
        			)


class UserResource2(resources.ModelResource):
    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'first_name', 'last_name',)
        

class LocationResource(resources.ModelResource):
    class Meta:
        model = Location
        fields = ('id', 'name', 'lon', 'lat')
        import_id_fields = ('id',)  # Используем id для обновления существующих записей
