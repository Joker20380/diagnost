# main/views.py

# Стандартные библиотеки
import csv
import logging
import os
import random
import uuid

from django.views.generic import ListView, DetailView, TemplateView
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db import transaction  # ✅ добавили

# Если используешь send_mail/settings в Unsubscribe — они должны быть импортированы
from django.core.mail import send_mail
from django.conf import settings

from users.models import UserProfile

# ✅ analyzer оставляем
from diagnostics.analyzer import analyze_dtc

# ✅ формы только формы (без моделей!)
from diagnostics.forms import DiagnosticUploadForm, SuspensionForm, SuspensionPartFormSet

# ✅ модели только из diagnostics.models
from diagnostics.models import (
    DiagnosticSession,
    DiagnosticCode,
    SensorReading,
    SuspensionInspection,
)

# Локальные импорты main (оставляю как у тебя)
from .models import *
from .utils import *
from .forms import *

logger = logging.getLogger(__name__)



# ============================
#  SUSPENSION: RECOMMENDATIONS (backend single source of truth)
# ============================

def _calc_replacement_hint(wear):
    """
    Возвращает (text, css_class) для отображения рекомендации.
    Пороги меняются централизованно здесь.
    """
    try:
        w = int(wear or 0)
    except (TypeError, ValueError):
        w = 0

    if w >= 70:
        return "Рекомендация: заменить", "badge bg-danger"
    if w >= 40:
        return "Рекомендация: наблюдать / перепроверить", "badge bg-warning text-dark"
    return "Рекомендация: замена не требуется", "badge bg-success"


def _annotate_formset_recommendations(formset):
    """
    Проставляет каждому сабформу:
      - repl_hint_text
      - repl_hint_class

    Работает и на GET, и на POST, включая невалидные формы.
    """
    for frm in formset.forms:
        raw = frm["wear_percent"].value()
        # На POST raw будет из request.POST; на GET может быть None/''.
        wear = raw
        if wear in (None, "", []):
            wear = getattr(frm.instance, "wear_percent", 0) or 0

        text, cls = _calc_replacement_hint(wear)
        frm.repl_hint_text = text
        frm.repl_hint_class = cls


class YandexView(TemplateView):
    template_name = 'yandex_d263e56262d9ffc1.html'


class RobotsTxtView(TemplateView):
    template_name = 'robots.txt'
    content_type = 'text/plain'


class SitemapXmlView(View):
    def get(self, request, *args, **kwargs):
        context = {
            'news': News.objects.all(),
            'programs': Prog.objects.all(),
            'docs': Documents.objects.all(),
            'lectures': Lecture.objects.all(),
            'request': request
        }
        xml_content = render_to_string('sitemap.xml', context)
        return HttpResponse(xml_content, content_type='application/xml')


class Index(DataMixin, ListView):
    queryset = News.objects.order_by('-time_update')
    model = News
    template_name = 'diagnost/index.html'
    context_object_name = 'news'
    paginate_by = 6

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="Домой")
        return dict(list(context.items()) + list(c_def.items()))

    @staticmethod
    def all_projects():
        return Prog.objects.order_by('-time_update')

    @staticmethod
    def all_reviews():
        return Review.objects.order_by('-created')

    @staticmethod
    def all_news():
        return News.objects.order_by('-time_create')

    @staticmethod
    def second_news():
        return News.objects.order_by('-time_create')[:3]

    @staticmethod
    def first_news():
        return News.objects.order_by('time_create')[:3]

    @staticmethod
    def one_news():
        return News.objects.order_by('-time_create')[:1]

    @staticmethod
    def one_second_news():
        return News.objects.order_by('time_create')[:1]


class About(DataMixin, ListView):
    queryset = News.objects.order_by('-time_update')
    model = News
    template_name = 'diagnost/about.html'
    context_object_name = 'news'
    paginate_by = 6

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="О нас")
        return dict(list(context.items()) + list(c_def.items()))


class ShowNews(DataMixin, DetailView):
    paginate_by = 1
    model = News
    template_name = 'diagnost/news-view.html'
    slug_url_kwarg = 'news_slug'
    context_object_name = 'news'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title=context['news'])
        return dict(list(context.items()) + list(c_def.items()))

    @staticmethod
    def post_last3():
        return News.objects.reverse()[:3]

    @staticmethod
    def post_last6():
        return News.objects.reverse()[:6]


class ShowDoc(DataMixin, DetailView):
    paginate_by = 1
    model = Documents
    template_name = 'diagnost/doc-view.html'
    slug_url_kwarg = 'doc_slug'
    context_object_name = 'doc'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title=context['doc'])
        return dict(list(context.items()) + list(c_def.items()))

    @staticmethod
    def post_last3():
        return News.objects.reverse()[:3]

    @staticmethod
    def post_last6():
        return News.objects.reverse()[:6]


class ShowProject(DataMixin, DetailView):
    paginate_by = 1
    model = Prog
    template_name = 'diagnost/project-view.html'
    slug_url_kwarg = 'project_slug'
    context_object_name = 'program'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title=context['program'])
        return dict(list(context.items()) + list(c_def.items()))

    @staticmethod
    def post_last3():
        return News.objects.reverse()[:3]

    @staticmethod
    def post_last6():
        return News.objects.reverse()[:6]


class ShowLecture(DataMixin, DetailView):
    paginate_by = 1
    model = Lecture
    template_name = 'diagnost/lecture-view.html'
    slug_url_kwarg = 'lecture_slug'
    context_object_name = 'lecture'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title=context['lecture'])
        return dict(list(context.items()) + list(c_def.items()))

    @staticmethod
    def post_last3():
        return News.objects.reverse()[:3]

    @staticmethod
    def post_last6():
        return News.objects.reverse()[:6]


class Projects(DataMixin, ListView):
    queryset = Prog.objects.order_by('-time_update')
    model = Prog
    template_name = 'diagnost/projects.html'
    context_object_name = 'program'
    paginate_by = 9

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="Проекты")
        return dict(list(context.items()) + list(c_def.items()))

    @staticmethod
    def all_projects():
        return Prog.objects.order_by('-time_update')

    @staticmethod
    def all_reviews():
        return Review.objects.order_by('-created')


class Blog(DataMixin, ListView):
    queryset = News.objects.all().reverse()
    template_name = "diagnost/blog.html"
    model = News
    context_object_name = 'news'
    paginate_by = 9

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title="Новости")
        return dict(list(context.items()) + list(c_def.items()))

    @staticmethod
    def news_all_news():
        return News.objects.all().reverse()


def Subscribe(request):
    if request.method == 'POST':
        form = SubscriberForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Вы успешно подписались на рассылку!')
            return redirect('index')
    else:
        form = SubscriberForm()
    return render(request, 'diagnost/index.html', {'form': form})


def Unsubscribe(request):
    if request.method == 'POST':
        form = UnsubscriberForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                subscriber = Subscriber.objects.get(email=email, is_active=True)
                subscriber.unsubscribe_token = uuid.uuid4().hex
                subscriber.save()

                unsubscribe_url = request.build_absolute_uri(
                    f"/unsubscribe/confirm/{subscriber.unsubscribe_token}/"
                )
                send_mail(
                    'Подтверждение отписки',
                    f'Для подтверждения отписки перейдите по ссылке: {unsubscribe_url}',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                messages.success(request, 'На ваш email отправлено письмо с подтверждением отписки.')
            except Subscriber.DoesNotExist:
                messages.error(request, 'Подписка с таким email не найдена.')
            return redirect('unsubscribe_request')
    else:
        form = UnsubscriberForm()
    return render(request, 'diagnost/unsubscribe_form.html', {'form': form})


def Unsubscribe_confirm(request, token):
    subscriber = get_object_or_404(Subscriber, unsubscribe_token=token, is_active=True)
    subscriber.is_active = False
    subscriber.unsubscribe_token = None
    subscriber.save()
    messages.success(request, 'Вы успешно отписались от рассылки.')
    return render(request, 'diagnost/unsubscribe_success.html')


class ContactsView(TemplateView):
    template_name = 'diagnost/contacts.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        main_contact = Contact.objects.filter(is_main=True).select_related('location').first()
        context.update({
            'main_contact': main_contact,
            'contact_groups': ContactGroup.objects.prefetch_related('contacts').all(),
        })

        if main_contact and main_contact.location:
            lat = main_contact.location.lat
            lon = main_contact.location.lon
            context['location_lat'] = f'{lat:.6f}'
            context['location_lon'] = f'{lon:.6f}'
            context['location_name'] = main_contact.name

        return context

    def post(self, request, *args, **kwargs):
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        message = request.POST.get('message')
        contact_id = request.POST.get('contact')

        if not all([name, email, message]):
            messages.error(request, 'Пожалуйста, заполните все обязательные поля')
            return self.get(request, *args, **kwargs)

        try:
            contact = Contact.objects.get(id=contact_id) if contact_id else None
        except Contact.DoesNotExist:
            contact = None

        ContactRequest.objects.create(
            name=name,
            email=email,
            phone=phone,
            message=message,
            contact=contact
        )

        messages.success(request, 'Ваше сообщение успешно отправлено!')
        return redirect('contacts')


# ============================
#  DIAGNOSTICS: UPDATED FLOWS
# ============================

@login_required
def upload_diagnostic(request):
    profile = getattr(request.user, 'userprofile', None)

    if request.method == 'POST':
        form = DiagnosticUploadForm(request.POST, request.FILES)
        if form.is_valid():
            session = form.save(commit=False)
            session.user_profile = profile
            session.status = 'suspension_pending'
            session.handover_time = timezone.now()
            session.save()

            # временно: фейковый анализ, пока нет парсера
            codes = ['P0171', 'P0420']
            for code in codes:
                DiagnosticCode.objects.create(session=session, code=code, description="Заглушка")

            session.recommendation = analyze_dtc(codes)
            # ✅ фиксируем время генерации подсказок
            session.ai_generated_at = timezone.now()
            session.save(update_fields=['recommendation', 'ai_generated_at'])

            return redirect('diagnostic_detail', session_id=session.id)
    else:
        form = DiagnosticUploadForm()

    return render(request, 'diagnost/upload.html', {'form': form})


@login_required
def diagnostic_detail(request, session_id):
    session = get_object_or_404(DiagnosticSession, id=session_id)
    codes = session.codes.all()
    readings = session.readings.all()
    inspection = getattr(session, 'suspension_inspection', None)

    return render(request, 'diagnost/detail.html', {
        'session': session,
        'codes': codes,
        'readings': readings,
        'inspection': inspection,
    })


@login_required
def suspension_inspection(request, session_id):
    session = get_object_or_404(DiagnosticSession, id=session_id)
    profile = getattr(request.user, 'userprofile', None)

    inspection, _ = SuspensionInspection.objects.get_or_create(
        session=session,
        defaults={'inspector': profile}
    )

    if request.method == 'POST':
        action = request.POST.get('action', 'save')

        # ✅ после подписи — только просмотр
        if inspection.status == 'signed':
            messages.error(request, "Осмотр уже подписан и доступен только для просмотра.")
            return redirect('diagnostic_detail', session_id=session.id)

        form = SuspensionForm(request.POST, instance=inspection)
        formset = SuspensionPartFormSet(request.POST, instance=inspection, prefix='parts')

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                insp = form.save()

                parts = formset.save(commit=False)
                for p in parts:
                    wear = p.wear_percent or 0

                    # ✅ авто-правила (НЕ ИИ) — только подсказка для severity
                    # не перетираем ручной выбор мастера: если выставлено — оставляем
                    if not p.severity:
                        if wear >= 70:
                            p.severity = 'crit'
                        elif wear >= 40:
                            p.severity = 'warn'
                        else:
                            p.severity = 'ok'

                    # ✅ QA FLAG: конфликт "рекомендация заменить" vs решение мастера
                    # Ничего не блокируем, только фиксируем в лог.
                    try:
                        if int(wear) >= 70 and not bool(p.needs_replacement):
                            logger.warning(
                                "QA_FLAG: replacement mismatch | session_id=%s inspection_id=%s part_type=%s wear=%s severity=%s user_id=%s",
                                getattr(session, "id", None),
                                getattr(insp, "id", None),
                                getattr(p, "part_type", None),
                                wear,
                                getattr(p, "severity", None),
                                getattr(getattr(request, "user", None), "id", None),
                            )
                    except Exception:
                        logger.exception("QA_FLAG: failed to log mismatch")

                    # ✅ КЛЮЧЕВОЕ: needs_replacement не ставим автоматически
                    p.save()

                # удалённые строки
                for obj in formset.deleted_objects:
                    obj.delete()

                # статус сессии
                session.status = 'suspension_done'
                session.suspension_comment = form.cleaned_data.get('comment', '')
                session.save(update_fields=['status', 'suspension_comment'])

                # ✅ подпись
                if action == 'sign':
                    if not insp.inspector:
                        insp.inspector = profile
                    insp.status = 'signed'
                    insp.signed_at = timezone.now()
                    insp.save(update_fields=['inspector', 'status', 'signed_at'])
                    messages.success(request, "Осмотр подписан. Редактирование заблокировано.")
                else:
                    messages.success(request, "Осмотр подвески сохранён (черновик).")

            return redirect('diagnostic_detail', session_id=session.id)

        # ❗️важно: даже при ошибках хотим показать рекомендации с сервера
        _annotate_formset_recommendations(formset)
        messages.error(request, "Ошибка при сохранении. Проверьте данные.")
    else:
        form = SuspensionForm(instance=inspection)
        formset = SuspensionPartFormSet(instance=inspection, prefix='parts')
        _annotate_formset_recommendations(formset)

    # ✅ блокировка UI, если подписан
    if inspection.status == 'signed':
        for f in form.fields.values():
            f.disabled = True
        for frm in formset.forms:
            for f in frm.fields.values():
                f.disabled = True

    return render(request, 'diagnost/suspension.html', {
        'form': form,
        'formset': formset,
        'session': session,
        'inspection': inspection,
    })



class Conf(ListView):
    queryset = News.objects.all()
    template_name = "diagnost/conf.html"
    model = News

    @staticmethod
    def news_all_conf():
        return News.objects.filter(title='Политика конфиденциальности')
