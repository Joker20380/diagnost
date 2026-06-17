from django.urls import path

from . import views

app_name = "diagnostics"

urlpatterns = [
    path("dtc/", views.dtc_search, name="dtc_search"),
    path("dtc/api/<str:code>/", views.dtc_api_detail, name="dtc_api_detail"),
    path("dtc/<str:code>/", views.dtc_detail, name="dtc_detail"),
]
