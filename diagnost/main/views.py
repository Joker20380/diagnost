# Стандартные библиотеки
import csv
import logging
import os
import random
import uuid
from django.views.generic import ListView, CreateView, DetailView, TemplateView
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import HttpResponse
from django.template.loader import render_to_string

from users.models import UserProfile

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from diagnostics.analyzer import analyze_dtc
from diagnostics.forms import DiagnosticUploadForm, SuspensionForm, SuspensionPartFormSet, SuspensionInspection
from diagnostics.models import DiagnosticSession, DiagnosticCode, SensorReading, SuspensionPartType





# Локальные импорты
from .models import *
from .utils import *
from .forms import *


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
            'request': request  # чтобы {{ request.get_host }} и {{ request.scheme }} работали
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
    	all_projects = Prog.objects.order_by('-time_update')
    	return all_projects
    	
    @staticmethod
    def all_reviews():
    	all_reviews = Review.objects.order_by('-created')
    	return all_reviews
    	
    @staticmethod
    def all_news():
    	all_news = News.objects.order_by('-time_create')
    	return all_news
    	
    @staticmethod
    def second_news():
    	second_news = News.objects.order_by('-time_create')[:3]
    	return second_news
    	
    @staticmethod
    def first_news():
    	first_news = News.objects.order_by('time_create')[:3]
    	return first_news
    	
    @staticmethod
    def one_news():
    	one_news = News.objects.order_by('-time_create')[:1]
    	return one_news
    	
    @staticmethod
    def one_second_news():
    	one_second_news = News.objects.order_by('time_create')[:1]
    	return one_second_news
    	

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
        post_last3 = News.objects.reverse()[:3]
        return post_last3

    @staticmethod
    def post_last6():
        post_last6 = News.objects.reverse()[:6]
        return post_last6


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
        post_last3 = News.objects.reverse()[:3]
        return post_last3

    @staticmethod
    def post_last6():
        post_last6 = News.objects.reverse()[:6]
        return post_last6


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
        post_last3 = News.objects.reverse()[:3]
        return post_last3

    @staticmethod
    def post_last6():
        post_last6 = News.objects.reverse()[:6]
        return post_last6


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
        post_last3 = News.objects.reverse()[:3]
        return post_last3

    @staticmethod
    def post_last6():
        post_last6 = News.objects.reverse()[:6]
        return post_last6  
        
        
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
		all_projects = Prog.objects.order_by('-time_update')
		return all_projects
		
	@staticmethod
	def all_reviews():
		all_reviews = Review.objects.order_by('-created')
		return all_reviews
		

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
		news_all = News.objects.all().reverse()
		return news_all


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
                # Генерация уникального токена для отписки
                subscriber.unsubscribe_token = uuid.uuid4().hex
                subscriber.save()
                # Отправка письма с подтверждением
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
    subscriber.unsubscribe_token = None  # Очищаем токен
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

        # Добавим координаты, если они есть
        if main_contact and main_contact.location:
            lat = main_contact.location.lat
            lon = main_contact.location.lon
            context['location_lat'] = f'{lat:.6f}'  # строка с точкой
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


@login_required
def upload_diagnostic(request):
    profile = getattr(request.user, 'userprofile', None)

    if request.method == 'POST':
        form = DiagnosticUploadForm(request.POST, request.FILES)
        if form.is_valid():
            session = form.save(commit=False)
            session.user_profile = profile
            session.status = 'suspension_pending'  # <- передаём на ходовую диагностику
            session.handover_time = timezone.now()
            session.save()

            # временно: фейковый анализ, пока нет парсера
            codes = ['P0171', 'P0420']
            for code in codes:
                DiagnosticCode.objects.create(session=session, code=code, description="Заглушка")

            session.recommendation = analyze_dtc(codes)
            session.save()

            return redirect('diagnostic_detail', session_id=session.id)
    else:
        form = DiagnosticUploadForm()
    return render(request, 'diagnost/upload.html', {'form': form})


@login_required
def diagnostic_detail(request, session_id):
    session = get_object_or_404(DiagnosticSession, id=session_id)
    codes = session.codes.all()
    readings = session.readings.all()

    return render(request, 'diagnost/detail.html', {
        'session': session,
        'codes': codes,
        'readings': readings,
    })


@login_required
def suspension_inspection(request, session_id):
    session = get_object_or_404(DiagnosticSession, id=session_id)

    # получаем или создаём запись осмотра
    try:
        inspection = session.suspension_inspection
    except SuspensionInspection.DoesNotExist:
        inspection = SuspensionInspection.objects.create(session=session)

    if request.method == 'POST':
        form = SuspensionForm(request.POST, instance=inspection)
        formset = SuspensionPartFormSet(request.POST, instance=inspection, prefix='parts')

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()

            # обновляем статус сессии
            session.status = 'suspension_done'
            session.suspension_comment = form.cleaned_data.get('comment', '')
            session.save()

            messages.success(request, "Осмотр подвески успешно сохранён.")
            return redirect('diagnostic_detail', session_id=session.id)
        else:
            # полезно при отладке
            print("Ошибки формы:", form.errors)
            print("Ошибки формсета:", formset.errors)
            messages.error(request, "Ошибка при сохранении. Проверьте данные.")
    else:
        form = SuspensionForm(instance=inspection)
        formset = SuspensionPartFormSet(instance=inspection, prefix='parts')

    return render(request, 'diagnost/suspension.html', {
        'form': form,
        'formset': formset,
        'session': session,
    })




class Conf(ListView):
    queryset = News.objects.all()
    template_name = "diagnost/conf.html"
    model = News
    
    
    @staticmethod
    def news_all_conf():
        news_all_conf = News.objects.filter(title= 'Политика конфиденциальности')
        return news_all_conf
        
        