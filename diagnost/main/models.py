import os
import uuid
from django.db import models
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.contrib.auth.models import User
from phonenumber_field.modelfields import PhoneNumberField
from .fields import WEBPField
from django_ckeditor_5.fields import CKEditor5Field
from model_utils import FieldTracker
from django.utils import timezone
from .mixins import OccupancyMixin
from users.models import Location


def image_folder(instance, filename):
    return "photos/{}.webp".format(uuid.uuid4().hex)

class Section(models.Model):
    name = models.CharField(max_length=100, verbose_name="Раздел сайта", db_index=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name='URL')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('section', kwargs={'section_slug': self.slug})

    class Meta:
        verbose_name = 'Раздел сайта'
        verbose_name_plural = 'Разделы сайта'
        ordering = ['id']


class CategoryProg(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название категории", db_index=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name='URL')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category', kwargs={'cat_slug': self.slug})

    class Meta:
        verbose_name = 'Категория проектов'
        verbose_name_plural = 'Категории проектов'
        ordering = ['id']


class Prog(OccupancyMixin, models.Model):
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name='URL')
    photo = WEBPField(upload_to=image_folder, verbose_name="Фото", null=True, blank=True)
    content = CKEditor5Field(blank=True, verbose_name="Текст", config_name="extends")
    photo2 = WEBPField(upload_to=image_folder, verbose_name="Фото2", null=True, blank=True)
    photo3 = WEBPField(upload_to=image_folder, verbose_name="Фото3", null=True, blank=True)
    photo4 = WEBPField(upload_to=image_folder, verbose_name="Фото4", null=True, blank=True)
    prog_statement = CKEditor5Field(blank=True, verbose_name="Положение о проекте", config_name="extends")
    photo5 = WEBPField(upload_to=image_folder, verbose_name="Фото5", null=True, blank=True)
    prog_statement2 = CKEditor5Field(blank=True, verbose_name="Положение о проекте 2 абзац", config_name="extends")
    name_pdffile = models.CharField(max_length=255, verbose_name="Имя PDF файла", null=True, blank=True)
    pdffile = models.FileField(upload_to="pdf/%Y/%m/%d/", verbose_name="PDF", null=True, blank=True)
    time_create = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время создания")
    time_update = models.DateTimeField(auto_now=True, verbose_name="Дата и время обновления")
    time_start = models.DateTimeField(verbose_name="Дата и время начала проекта", null=True, blank=True)
    time_ending = models.DateTimeField(verbose_name="Дата и время окончания проекта", null=True, blank=True)
    is_published = models.BooleanField(verbose_name="Публикация")
    supervisor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='supervisor', verbose_name="Руководитель",
                                   null=True, blank=True)
    registration = models.ManyToManyField(User, related_name="progs", verbose_name="Участники проекта", blank=True)
    cat = models.ForeignKey(CategoryProg, on_delete=models.PROTECT, verbose_name="Категория", null=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('project', kwargs={'project_slug': self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекты'
        ordering = ['time_create', 'title']


class CategoryLecture(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название категории", db_index=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name='URL')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category_lecture', kwargs={'cat_slug': self.slug})

    class Meta:
        verbose_name = 'Категория лекции'
        verbose_name_plural = 'Категории лекций'
        ordering = ['id']


class Lecture(models.Model):
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name='URL')
    content = models.CharField(max_length=255, blank=True, null=True, verbose_name="Текст")
    URL = models.URLField(blank=True, verbose_name="Ссылка на видео")
    prog = models.ForeignKey("Prog", on_delete=models.PROTECT, verbose_name="Программа", blank=True, null=True)
    time_create = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время создания")
    time_update = models.DateTimeField(auto_now=True, verbose_name="Дата и время обновления")
    is_published = models.BooleanField(default=True, verbose_name="Публикация")
    cat = models.ForeignKey(CategoryLecture, on_delete=models.PROTECT, verbose_name="Категория", null=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('lecture', kwargs={'lecture_slug': self.slug})

    def save(self, *args, **kwargs):  # new
        if not self.slug:
            self.slug = slugify(self.title)
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Лекции'
        verbose_name_plural = 'Лекции'
        ordering = ['time_create', 'title']


class Documents(models.Model):
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name='URL')
    content = CKEditor5Field(blank=True, verbose_name="Текст", config_name="extends")
    name_pdffile = models.CharField(max_length=255, verbose_name="Имя PDF файла", null=True, blank=True)
    pdf_file = models.FileField(upload_to="pdf/%Y/%m/%d/", verbose_name="Файл", null=True, blank=True)
    executor = models.ForeignKey(User, on_delete=models.PROTECT, null=True, verbose_name="Исполнитель")
    time_create = models.DateTimeField(auto_now_add=True, verbose_name="Время создания")
    time_update = models.DateTimeField(auto_now=True, verbose_name="Время обновления")
    is_published = models.BooleanField(default=True, verbose_name="Публикация")
    section = models.ManyToManyField(Section, related_name="Документы", verbose_name="Раздел сайта", blank=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('doc', kwargs={'doc_slug': self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'
        ordering = ['time_create']


class CategoryNews(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название категории", db_index=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name='URL')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category', kwargs={'cat_slug': self.slug})

    class Meta:
        verbose_name = 'Категория новости'
        verbose_name_plural = 'Категории новостей'
        ordering = ['id']


class News(models.Model):
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name='URL')
    content = CKEditor5Field(blank=True, verbose_name="Текст", config_name="extends")
    photo = WEBPField(verbose_name='фото 633x550px', upload_to=image_folder, blank=True, null=True)
    content2 = CKEditor5Field(blank=True, null=True, verbose_name="Текст2", config_name="extends")
    photo2 = WEBPField(verbose_name='фото2', upload_to=image_folder,  blank=True, null=True)
    photo3 = WEBPField(verbose_name="Фото№3", upload_to=image_folder, blank=True, null=True)
    content3 = CKEditor5Field(blank=True, null=True, verbose_name="Текст3", config_name="extends")
    photo4 = WEBPField(verbose_name="Фото№4", upload_to=image_folder, blank=True, null=True)
    photo5 = WEBPField(verbose_name="Фото№5", upload_to=image_folder, blank=True, null=True)
    content4 = CKEditor5Field(blank=True, null=True, verbose_name="Текст4", config_name="extends")
    time_create = models.DateTimeField(verbose_name="Дата и время создания")
    time_update = models.DateTimeField(auto_now=True, verbose_name="Дата и время обновления")
    is_published = models.BooleanField(default=True, verbose_name="Публикация")
    tracker = FieldTracker(fields=['is_published'])
    cat = models.ForeignKey(CategoryNews, on_delete=models.PROTECT, verbose_name="Категория")
    prog = models.ForeignKey('Prog', on_delete=models.PROTECT, verbose_name="Программа", blank=True, null=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('news', kwargs={'news_slug': self.slug})

    def save(self, *args, **kwargs):  # new
        if not self.slug:
            self.slug = slugify(self.title)
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'
        ordering = ['time_create', 'title']


class Service(models.Model):
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name='URL')
    content = CKEditor5Field(blank=True, verbose_name="Текст")
    price = models.DecimalField(decimal_places=2, max_digits=20, default=0.00, verbose_name="Цена")
    photo = models.ImageField(upload_to="photos/%Y/%m/%d/", verbose_name="Фото", blank=True, null=True)
    photo2 = models.ImageField(upload_to="photos/%Y/%m/%d/", verbose_name="Фото2", blank=True, null=True)
    photo3 = models.ImageField(upload_to="photos/%Y/%m/%d/", verbose_name="Фото3", blank=True, null=True)
    photo4 = models.ImageField(upload_to="photos/%Y/%m/%d/", verbose_name="Фото4", blank=True, null=True)
    photo5 = models.ImageField(upload_to="photos/%Y/%m/%d/", verbose_name="Фото5", blank=True, null=True)
    photo6 = models.ImageField(upload_to="photos/%Y/%m/%d/", verbose_name="Фото6", blank=True, null=True)
    time_create = models.DateTimeField(verbose_name="Дата и время создания")
    time_update = models.DateTimeField(verbose_name="Дата и время обновления")
    is_published = models.BooleanField(default=True, verbose_name="Публикация")
    number_of_employees = models.IntegerField(verbose_name="Количество сотрудников", default=0)
    executor = models.ManyToManyField(User, related_name='products', verbose_name='Исполнитель', blank=True)

	
    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('services', kwargs={'services_slug': self.slug})
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        return super().save(*args, **kwargs)


    class Meta:
        unique_together = [['title', 'slug']]
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'  


class Subscriber(models.Model):
    email = models.EmailField(unique=True, verbose_name="Email")
    is_active = models.BooleanField(default=True)  # Активна ли подписка
    unsubscribe_token = models.CharField(max_length=50, unique=True, blank=True, null=True)  # Токен для отписки
    subscribed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Подписчика'
        verbose_name_plural = 'Подписчики'
        ordering = ['email']

    def __str__(self):
        return self.email


class ContactGroup(models.Model):
    """Группа контактов (например, Администрация, Филиал)"""
    name = models.CharField(max_length=100, verbose_name="Название группы")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок сортировки")
    
    class Meta:
        verbose_name = "Группа контактов"
        verbose_name_plural = "Группы контактов"
        ordering = ['order']
    
    def __str__(self):
        return self.name


class Contact(models.Model):
    """Конкретный контакт"""
    group = models.ForeignKey(ContactGroup, on_delete=models.CASCADE, 
                            verbose_name="Группа", related_name='contacts')
    name = models.CharField(max_length=100, verbose_name="Название")
    phone = models.CharField(max_length=20, verbose_name="Телефон", blank=True)
    email = models.EmailField(verbose_name="Email", blank=True)
    address = models.CharField(max_length=255, verbose_name="Адрес", blank=True)
    description = models.TextField(verbose_name="Описание", blank=True)
    is_main = models.BooleanField(default=False, verbose_name="Основной контакт")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок сортировки")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="Contact", verbose_name="Местоположение", blank=True, null=True)
    
    class Meta:
        verbose_name = "Контакт"
        verbose_name_plural = "Контакты"
        ordering = ['order']
    
    def __str__(self):
        return f"{self.group}: {self.name}"


class ContactRequest(models.Model):
    name = models.CharField(max_length=100, verbose_name="Имя")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, verbose_name="Телефон", blank=True, null=True)
    message = models.TextField(verbose_name="Сообщение")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    contact = models.ForeignKey(
        'Contact',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Контактное лицо"
    )
    
    class Meta:
        verbose_name = "Запрос на контакт"
        verbose_name_plural = "Запросы на контакт"
        ordering = ['-created_at']
    
    def __str__(self):
        contact_name = self.contact.name if self.contact else "Общий запрос"
        return f"{self.name} → {contact_name} ({self.created_at:%d.%m.%Y})"
        


class Review(models.Model):
    project = models.ForeignKey(Prog, on_delete=models.PROTECT, related_name='review', verbose_name='Название проекта', blank=True, null=True)
    name = models.CharField(max_length=80, verbose_name='Имя')
    photo = models.ImageField(upload_to="photos/%Y/%m/%d/", verbose_name="Фото", blank=True, null=True)
    email = models.EmailField(verbose_name="Email", blank=True, null=True)
    body = models.TextField(verbose_name='Отзыв')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=False, verbose_name='Опубликовать')

    class Meta:
        ordering = ('created',)
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'

    def __str__(self):
        return 'Отзыв от {} на {}'.format(self.name, self.project)
                