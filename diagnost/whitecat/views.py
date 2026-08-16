from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView


class WhiteCatHomeView(TemplateView):
    template_name = 'whitecat/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['services'] = [
            {
                'number': '01',
                'title': _('Наблюдения и контекст'),
                'text': _('Собираю сигналы, историю, условия эксплуатации и факторы риска в единую структурированную модель.'),
            },
            {
                'number': '02',
                'title': _('Гипотезы и зависимости'),
                'text': _('Связываю симптомы с возможными причинами, учитывая зависимости, ограничения и предметные знания.'),
            },
            {
                'number': '03',
                'title': _('Оценка свидетельств'),
                'text': _('Ранжирую гипотезы по силе подтверждений и показываю, почему система пришла к такому выводу.'),
            },
            {
                'number': '04',
                'title': _('Следующий лучший тест'),
                'text': _('Определяю проверку или вопрос, который сильнее всего снизит неопределённость на текущем шаге.'),
            },
        ]

        context['stack'] = [
            'Python', 'Django', 'C#', '.NET', 'ASP.NET',
            'PostgreSQL', 'MySQL', 'MSSQL', 'Redis', 'Celery',
            'REST API', 'Docker', 'Linux', 'Nginx', 'Caddy',
            'Rule Engine', 'Knowledge Graph', 'Evidence Scoring',
            'Probabilistic Models', 'Explainable AI', 'AI / LLM',
        ]

        context['cases'] = [
            {
                'type': _('Общее инженерное ядро'),
                'title': _('Diagnostic Engine'),
                'text': _('Observation, Context, Risk Factor, Hypothesis, Evidence, Test, Result и Recommendation — единая модель принятия решений для разных предметных областей.'),
                'tags': ['Rules', 'Knowledge Graph', 'Evidence', 'Next Best Test'],
            },
            {
                'type': _('Automotive diagnostics'),
                'title': _('От DTC к проверяемой причине'),
                'text': _('Код ошибки, телеметрия и условия эксплуатации превращаются в ранжированные гипотезы: что проверить следующим, ремонтировать или наблюдать.'),
                'tags': ['DTC', 'Telemetry', 'Causal Model', 'Testing'],
            },
            {
                'type': _('Health diagnostics'),
                'title': _('От факторов риска к осмысленной проверке'),
                'text': _('Профессия, воздействия, жалобы и результаты анализов дают контекст для следующего исследования — без подмены врача автоматическим диагнозом.'),
                'tags': ['Risk Factors', 'Biomarkers', 'Screening', 'Decision Support'],
            },
        ]

        context['steps'] = [
            (_('Сигнал + контекст'), _('Собираем наблюдения, историю, зависимости и условия, влияющие на интерпретацию сигнала.')),
            (_('Гипотезы'), _('Строим несколько возможных объяснений и оцениваем подтверждающие и опровергающие свидетельства.')),
            (_('Следующая проверка'), _('Выбираем наиболее информативный и рациональный следующий тест, вопрос или измерение.')),
            (_('Обновление модели'), _('Новый результат изменяет вероятности, объяснение и дальнейшую рекомендацию системы.')),
        ]

        return context
