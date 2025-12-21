from django.db.models import Count

from .models import *

menu = [
    {'title': "Домой", 'url_name': 'index'},
    {'title': 'О нас', 'url_name': 'about'},
    {'title': "Проекты", 'url_name': 'projects'},
    {'title': 'Услуги', 'url_name': 'services',
     'submenu': [{'title': 'Авто диагностика', 'url_name': 'auto_diagnost'},
                 {'title': 'Ремонт ходовой', 'url_name': 'chassis_repair'},
                 {'title': 'Авто электрик', 'url_name': 'auto_electrician'},
        		]},
    {'title': 'Новости', 'url_name': 'blog'},
    {'title': 'Контакты', 'url_name': 'contacts'},]



class DataMixin:
    def get_user_context(self, **kwargs):
        context = kwargs
        cats = CategoryNews.objects.all()

        user_menu = menu.copy()
        if not self.request.user.is_authenticated:
            user_menu

        context['menu'] = user_menu

        context['cats'] = cats
        if 'cat_selected' not in context:
            context['cat_selected'] = 0
        return context