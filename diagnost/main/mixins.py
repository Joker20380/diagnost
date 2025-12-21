from django.contrib import messages

class CookieConsentMixin:
    cookie_name = 'cookies_accepted'
    cookie_message = 'Мы используем cookies для улучшения сайта. Подробнее в политике конфиденциальности.'

    def dispatch(self, request, *args, **kwargs):
        if not request.COOKIES.get(self.cookie_name):
            messages.info(request, self.cookie_message)
        return super().dispatch(request, *args, **kwargs)


class OccupancyMixin:
    @property
    def occupied_places(self):
        return self.registration.count()

    @property
    def total_places_display(self):
        return self.total_places or 0

    @property
    def occupied_percent(self):
        if self.total_places:
            percent = (self.registration.count() / self.total_places) * 100
            return round(percent)
        return 0