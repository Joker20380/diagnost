class WhiteCatDomainRoutingMiddleware:
    """
    Routes white_cat domains to a separate URLConf without touching the main site.

    Django supports per-request URLConf switching through request.urlconf.
    This keeps white_cat isolated and ready for future urls/models/views.
    """

    WHITECAT_HOSTS = {
        'white--cat.ru',
        'www.white--cat.ru',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':', 1)[0].lower()

        if host in self.WHITECAT_HOSTS:
            request.urlconf = 'whitecat.urls'

        return self.get_response(request)
