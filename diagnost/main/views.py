# main/views.py

# Стандартные библиотеки
import csv
import hashlib
import ipaddress
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
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required
from django.db import transaction  # ✅ добавили

# Если используешь send_mail/settings в Unsubscribe — они должны быть импортированы
from django.core.mail import send_mail
from django.core.cache import cache
from django.conf import settings

from users.models import UserProfile

# ✅ analyzer оставляем
from diagnostics.analyzer import analyze_dtc

# ✅ формы только формы (без моделей!)
from diagnostics.forms import (
    DiagnosticUploadForm,
    SuspensionForm,
    SuspensionPartFormSet,
    VehicleIdentityConfirmationForm,
)
from diagnostics.vehicle_identity import confirm_vehicle_identity

# ✅ модели только из diagnostics.models
from diagnostics.models import (
    DiagnosticSession,
    DiagnosticCode,
    SensorReading,
    SuspensionInspection,
    QAEvent,
    VehicleIdentityObservation,
)

# Локальные импорты main (оставляю как у тебя)
from .models import *
from .utils import *
from .forms import *

logger = logging.getLogger(__name__)


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    candidate = forwarded.split(',', 1)[0].strip() if forwarded else request.META.get('REMOTE_ADDR', '')
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return 'unknown'


def _is_rate_limited(request, scope, timeout=60):
    fingerprint = hashlib.sha256(f"{scope}:{_client_ip(request)}".encode()).hexdigest()
    return not cache.add(f"public-form:{fingerprint}", True, timeout=timeout)


def _diagnostic_sessions_for_user(user):
    return DiagnosticSession.objects.visible_to(user)



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
        return _("Рекомендация: заменить"), "badge bg-danger"
    if w >= 40:
        return _("Рекомендация: наблюдать / перепроверить"), "badge bg-warning text-dark"
    return _("Рекомендация: замена не требуется"), "badge bg-success"


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
            "base": "https://www.autozvuk15.ru",

            # ВАЖНО: именно services/projects — так будет читабельно и не путаться
            "services": Service.objects.all(),   # можешь добавить фильтр published
            "projects": Prog.objects.all(),      # твои "проекты" — это Prog

            # Если хочешь пока убрать docs/lectures из sitemap — не передавай
            # "docs": Documents.objects.all(),
            # "lectures": Lecture.objects.all(),
        }
        xml_content = render_to_string("sitemap.xml", context=context)
        return HttpResponse(xml_content, content_type="application/xml; charset=utf-8")



class Index(DataMixin, ListView):
    queryset = News.objects.filter(is_published=True).order_by('-time_update')
    model = News
    template_name = 'diagnost/index.html'
    context_object_name = 'news'
    paginate_by = 6

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title=_("Домой"))
        return dict(list(context.items()) + list(c_def.items()))

    @staticmethod
    def all_projects():
        return Prog.objects.order_by('-time_update')

    @staticmethod
    def all_reviews():
        return Review.objects.order_by('-created')

    @staticmethod
    def all_news():
        return News.objects.filter(is_published=True).order_by('-time_create')

    @staticmethod
    def second_news():
        return News.objects.filter(is_published=True).order_by('-time_create')[:3]

    @staticmethod
    def first_news():
        return News.objects.filter(is_published=True).order_by('time_create')[:3]

    @staticmethod
    def one_news():
        return News.objects.filter(is_published=True).order_by('-time_create')[:1]

    @staticmethod
    def one_second_news():
        return News.objects.filter(is_published=True).order_by('time_create')[:1]


class About(DataMixin, ListView):
    queryset = News.objects.filter(is_published=True).order_by('-time_update')
    model = News
    template_name = 'diagnost/about.html'
    context_object_name = 'news'
    paginate_by = 6

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title=_("О нас"))
        return dict(list(context.items()) + list(c_def.items()))


class ShowNews(DataMixin, DetailView):
    paginate_by = 1
    model = News
    template_name = 'diagnost/news-view.html'
    slug_url_kwarg = 'news_slug'
    context_object_name = 'news'

    def get_queryset(self):
        return News.objects.filter(
            is_published=True,
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title=context['news'])
        return dict(list(context.items()) + list(c_def.items()))

    @staticmethod
    def post_last3():
        return News.objects.filter(is_published=True).reverse()[:3]

    @staticmethod
    def post_last6():
        return News.objects.filter(is_published=True).reverse()[:6]


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
        return News.objects.filter(is_published=True).reverse()[:3]

    @staticmethod
    def post_last6():
        return News.objects.filter(is_published=True).reverse()[:6]


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
        return News.objects.filter(is_published=True).reverse()[:3]

    @staticmethod
    def post_last6():
        return News.objects.filter(is_published=True).reverse()[:6]


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
        return News.objects.filter(is_published=True).reverse()[:3]

    @staticmethod
    def post_last6():
        return News.objects.filter(is_published=True).reverse()[:6]


class ShowService(DataMixin, DetailView):
    paginate_by = 1
    model = Service
    template_name = 'diagnost/service-view.html'
    slug_url_kwarg = 'service_slug'
    context_object_name = 'service'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title=context['service'])
        return dict(list(context.items()) + list(c_def.items()))

    @staticmethod
    def post_last3():
        return News.objects.filter(is_published=True).reverse()[:3]

    @staticmethod
    def post_last6():
        return News.objects.filter(is_published=True).reverse()[:6]


class Projects(DataMixin, ListView):
    queryset = Prog.objects.order_by('-time_update')
    model = Prog
    template_name = 'diagnost/projects.html'
    context_object_name = 'program'
    paginate_by = 9

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title=_("Проекты"))
        return dict(list(context.items()) + list(c_def.items()))

    @staticmethod
    def all_projects():
        return Prog.objects.order_by('-time_update')

    @staticmethod
    def all_reviews():
        return Review.objects.order_by('-created')


class Blog(DataMixin, ListView):
    queryset = News.objects.filter(is_published=True).reverse()
    template_name = "diagnost/blog.html"
    model = News
    context_object_name = 'news'
    paginate_by = 9

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        c_def = self.get_user_context(title=_("Новости"))
        return dict(list(context.items()) + list(c_def.items()))

    @staticmethod
    def news_all_news():
        return News.objects.filter(is_published=True).reverse()


def Subscribe(request):
    if request.method == 'POST':
        form = SubscriberForm(request.POST)
        if form.is_valid():
            if form.cleaned_data.get('website'):
                return redirect('index')
            if _is_rate_limited(request, 'subscribe'):
                messages.error(request, _('Слишком много попыток. Повторите через минуту.'))
                return redirect('index')
            form.save()
            messages.success(request, _('Вы успешно подписались на рассылку!'))
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
                    _('Подтверждение отписки'),
                    _('Для подтверждения отписки перейдите по ссылке: %(url)s') % {"url": unsubscribe_url},
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                messages.success(request, _('На ваш email отправлено письмо с подтверждением отписки.'))
            except Subscriber.DoesNotExist:
                messages.error(request, _('Подписка с таким email не найдена.'))
            return redirect('unsubscribe_request')
    else:
        form = UnsubscriberForm()
    return render(request, 'diagnost/unsubscribe_form.html', {'form': form})


def Unsubscribe_confirm(request, token):
    subscriber = get_object_or_404(Subscriber, unsubscribe_token=token, is_active=True)
    subscriber.is_active = False
    subscriber.unsubscribe_token = None
    subscriber.save()
    messages.success(request, _('Вы успешно отписались от рассылки.'))
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
        form = ContactRequestForm(request.POST)
        if not form.is_valid():
            messages.error(request, _('Проверьте правильность заполнения формы.'))
            return self.get(request, *args, **kwargs)

        if form.cleaned_data.get('website'):
            return redirect('contacts')

        if _is_rate_limited(request, 'contact'):
            messages.error(request, _('Сообщение уже отправлено. Повторите через минуту.'))
            return redirect('contacts')

        form.save()
        messages.success(request, _('Ваше сообщение успешно отправлено!'))
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
            if profile is None:
                logger.error("Diagnostic upload rejected: user %s has no profile", request.user.pk)
                messages.error(request, _('Профиль пользователя не найден. Обратитесь к администратору.'))
                return render(request, 'diagnost/upload.html', {'form': form})

            session = form.save(commit=False)
            technician = getattr(profile, "technician_profile", None)
            if technician is not None and technician.is_active:
                session.organization = technician.organization
                session.workshop = technician.workshop
            session.user_profile = profile
            session.status = 'suspension_pending'
            session.handover_time = timezone.now()
            session.save()

            try:
                from diagnostics.launch_pdf_parser import parse_and_apply_launch_pdf
                parse_and_apply_launch_pdf(session)
            except Exception as exc:
                logger.exception(
                    "Launch PDF parsing failed for session_id=%s user_id=%s",
                    session.pk,
                    request.user.pk,
                )
                session.status = "parse_failed"
                session.save(update_fields=["status"])
                if not session.qa_events.filter(
                    code="LAUNCH_PDF_PARSE_FAILED"
                ).exists():
                    QAEvent.objects.create(
                        session=session,
                        code="LAUNCH_PDF_PARSE_FAILED",
                        severity=QAEvent.Severity.ERROR,
                        message="Launch PDF parsing failed.",
                        details={
                            "error_class": type(exc).__name__,
                            "error_message": str(exc)[:2000],
                            "user_id": request.user.pk,
                        },
                    )
                form.add_error(
                    'raw_file',
                    _('Не удалось прочитать отчёт Launch. Проверьте файл и попробуйте снова.'),
                )
                return render(request, 'diagnost/upload.html', {'form': form})

            return redirect('diagnostic_detail', session_id=session.id)
    else:
        form = DiagnosticUploadForm()

    return render(request, 'diagnost/upload.html', {'form': form})


@login_required
def diagnostic_detail(request, session_id):
    session = get_object_or_404(
        _diagnostic_sessions_for_user(request.user),
        id=session_id,
    )
    current_parse_run = session.parse_runs.filter(
        status="succeeded",
        is_current=True,
    ).first()
    if current_parse_run:
        codes = session.codes.filter(parse_run=current_parse_run)
    else:
        codes = session.codes.filter(parse_run__isnull=True)
    readings = session.readings.all()
    inspection = getattr(session, 'suspension_inspection', None)

    return render(request, 'diagnost/detail.html', {
        'session': session,
        'codes': codes,
        'readings': readings,
        'inspection': inspection,
    })


@login_required
def vehicle_identity_confirm(request, session_id):
    session = get_object_or_404(
        _diagnostic_sessions_for_user(request.user).select_related(
            "organization", "vehicle", "vehicle_configuration"
        ),
        id=session_id,
    )
    observation = get_object_or_404(
        VehicleIdentityObservation,
        session=session,
    )
    if request.method == "POST":
        form = VehicleIdentityConfirmationForm(
            request.POST, observation=observation
        )
        if form.is_valid():
            confirm_vehicle_identity(
                session=session,
                user=request.user,
                submitted_data=form.cleaned_data,
            )
            messages.success(request, _("Данные автомобиля подтверждены."))
            return redirect("diagnostic_detail", session_id=session.pk)
    else:
        form = VehicleIdentityConfirmationForm(observation=observation)
    return render(
        request,
        "diagnost/vehicle_identity_confirm.html",
        {"session": session, "observation": observation, "form": form},
    )


@login_required
def suspension_inspection(request, session_id):
    session = get_object_or_404(
        _diagnostic_sessions_for_user(request.user),
        id=session_id,
    )
    profile = getattr(request.user, 'userprofile', None)

    inspection, _inspection_created = SuspensionInspection.objects.get_or_create(
        session=session,
        defaults={'inspector': profile}
    )

    if request.method == 'POST':
        action = request.POST.get('action', 'save')

        # ✅ после подписи — только просмотр
        if inspection.status == 'signed':
            messages.error(request, _("Осмотр уже подписан и доступен только для просмотра."))
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

                    if int(wear) >= 70 and not bool(p.needs_replacement):
                        QAEvent.objects.create(
                            session=session,
                            code="SUSPENSION_REPLACEMENT_MISMATCH",
                            severity=QAEvent.Severity.WARNING,
                            message=(
                                "High wear was recorded without a replacement decision."
                            ),
                            details={
                                "inspection_id": insp.pk,
                                "part_type_id": p.part_type_id,
                                "wear_percent": int(wear),
                                "severity": p.severity,
                                "user_id": request.user.pk,
                            },
                        )

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
                    messages.success(request, _("Осмотр подписан. Редактирование заблокировано."))
                else:
                    messages.success(request, _("Осмотр подвески сохранён (черновик)."))

            return redirect('diagnostic_detail', session_id=session.id)

        # ❗️важно: даже при ошибках хотим показать рекомендации с сервера
        _annotate_formset_recommendations(formset)
        messages.error(request, _("Ошибка при сохранении. Проверьте данные."))
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
    queryset = News.objects.filter(is_published=True)
    template_name = "diagnost/conf.html"
    model = News

    @staticmethod
    def news_all_conf():
        return News.objects.filter(is_published=True, title='Политика конфиденциальности')
