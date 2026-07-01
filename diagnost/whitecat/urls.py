from django.urls import path

from .views import WhiteCatHomeView

app_name = 'whitecat'

urlpatterns = [
    path('', WhiteCatHomeView.as_view(), name='home'),
]
