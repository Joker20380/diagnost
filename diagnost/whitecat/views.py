from django.views.generic import TemplateView


class WhiteCatHomeView(TemplateView):
    template_name = 'whitecat/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['services'] = [
            {
                'title': 'Сложные web-системы',
                'text': 'Проектируем backend, frontend, базы данных, роли пользователей, административные панели и бизнес-логику под реальные процессы.',
            },
            {
                'title': 'CRM и личные кабинеты',
                'text': 'Создаём внутренние панели, кабинеты клиентов, системы заявок, записи, статусов, документов и уведомлений.',
            },
            {
                'title': 'Интеграции и автоматизация',
                'text': 'Подключаем внешние API, импорт данных, XML/JSON-обмен, фоновые задачи, парсинг и автоматические workflows.',
            },
            {
                'title': 'AI-assisted инструменты',
                'text': 'Встраиваем LLM, генерацию контента, анализ данных и интеллектуальные помощники в рабочие продукты.',
            },
        ]

        context['stack'] = [
            'Python', 'Django', 'C#', '.NET', 'ASP.NET',
            'PostgreSQL', 'MySQL', 'MSSQL',
            'Docker', 'Linux', 'Nginx', 'Caddy',
            'Redis', 'Celery', 'REST API',
            'DevExpress', 'DevExtreme', 'AI / LLM',
        ]

        context['directions'] = [
            'Медицинские лаборатории и каталоги анализов',
            'Автомобильная диагностика и сервисные платформы',
            'Образовательные системы и личные кабинеты',
            'CRM, заявки, dashboards и корпоративные панели',
            'SEO-системы, новости, генерация и обработка контента',
        ]

        return context
