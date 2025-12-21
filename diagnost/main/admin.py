from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.utils import timezone
from import_export.admin import ImportExportModelAdmin

from .models import (
    Section, CategoryNews, News,
    CategoryLecture, Lecture,
    CategoryProg, Prog,
    Documents, Service, Subscriber,
    ContactGroup, Contact, ContactRequest, Review
)

from diagnostics.models import (
    DiagnosticSession, DiagnosticCode, SensorReading,
    SuspensionInspection, SuspensionPart, SuspensionPartType
)


@admin.register(SuspensionPartType)
class SuspensionPartTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(SuspensionPart)
class SuspensionPartAdmin(admin.ModelAdmin):
    list_display = ('part_type', 'wear_percent', 'part_number', 'needs_replacement', 'inspection')
    list_filter = ('needs_replacement', 'part_type')
    search_fields = ('part_number',)


class SuspensionPartInline(admin.TabularInline):
    model = SuspensionPart
    extra = 1
    fields = ('part_type', 'wear_percent', 'part_number', 'needs_replacement')


class SuspensionInline(admin.StackedInline):
    model = SuspensionInspection
    extra = 0
    fields = ('inspector', 'comment')
    show_change_link = True


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(CategoryNews)
class CategoryNewsAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(News)
class NewsAdmin(ImportExportModelAdmin):
    list_display = ('id', 'title', 'get_photo', 'time_create', 'time_update', 'is_published')
    list_display_links = ('id', 'title')
    search_fields = ('title', 'content')
    list_editable = ('is_published',)
    list_filter = ('is_published', 'time_create')
    prepopulated_fields = {"slug": ("title",)}

    def get_photo(self, obj):
        if obj.photo:
            return mark_safe(f"<img src='{obj.photo.url}' width=50>")
        return None
    get_photo.short_description = 'Фото'


@admin.register(CategoryLecture)
class CategoryLectureAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'time_create', 'is_published')
    list_display_links = ('id', 'title')
    search_fields = ('title',)
    list_editable = ('is_published',)
    list_filter = ('is_published', 'time_create')
    prepopulated_fields = {"slug": ("title",)}


@admin.register(CategoryProg)
class CategoryProgAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Prog)
class ProgAdmin(ImportExportModelAdmin):
    list_display = ('id', 'title', 'get_photo', 'supervisor', 'time_create', 'is_published')
    list_display_links = ('id', 'title')
    search_fields = ('title',)
    list_editable = ('is_published',)
    list_filter = ('is_published', 'time_create')
    filter_horizontal = ('registration',)
    prepopulated_fields = {"slug": ("title",)}

    def get_photo(self, obj):
        if obj.photo:
            return mark_safe(f"<img src='{obj.photo.url}' width=50>")
        return None
    get_photo.short_description = 'Фото'


@admin.register(Documents)
class DocumentsAdmin(ImportExportModelAdmin):
    list_display = ('id', 'title', 'name_pdffile', 'is_published')
    list_display_links = ('id', 'title', 'is_published')
    search_fields = ('title',)
    list_filter = ('is_published', 'time_create')
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Service)
class ServiceAdmin(ImportExportModelAdmin):
    list_display = ('id', 'title', 'time_create', 'is_published')
    list_display_links = ('id', 'title')
    search_fields = ('title',)
    list_editable = ('is_published',)
    list_filter = ('is_published', 'time_create')
    prepopulated_fields = {"slug": ("title",)}

    def get_photo(self, obj):
        if obj.photo:
            return mark_safe(f"<img src='{obj.photo.url}' width=50>")
        return None
    get_photo.short_description = 'Фото'


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('id', 'email')
    list_display_links = ('id', 'email')
    search_fields = ('email',)


@admin.register(ContactGroup)
class ContactGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'contacts_count')
    list_editable = ('order',)
    ordering = ('order',)

    def contacts_count(self, obj):
        return obj.contacts.count()
    contacts_count.short_description = "Кол-во контактов"


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'group', 'phone', 'email', 'is_main', 'order')
    list_filter = ('group', 'is_main')
    list_editable = ('is_main', 'order')
    search_fields = ('name', 'phone', 'email')
    fieldsets = (
        (None, {
            'fields': ('group', 'name', 'is_main', 'order', 'location')
        }),
        ('Контактная информация', {
            'fields': ('phone', 'email', 'address', 'description')
        }),
    )


@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'contact_link', 'created_at', 'is_new')
    list_filter = ('created_at', 'contact__group')
    search_fields = ('name', 'email', 'phone', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    def contact_link(self, obj):
        if obj.contact:
            return format_html('<a href="/admin/contacts/contact/{}/change/">{}</a>', obj.contact.id, obj.contact.name)
        return "-"
    contact_link.short_description = "Контакт"

    def is_new(self, obj):
        return obj.created_at.date() == timezone.now().date()
    is_new.boolean = True
    is_new.short_description = "Новый?"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_photo', 'email', 'project')

    def get_photo(self, object):
        if object.photo:
            return mark_safe(f"<img src='{object.photo.url}' width=50>")
    get_photo.short_description = 'Фото'


@admin.register(DiagnosticSession)
class DiagnosticSessionAdmin(admin.ModelAdmin):
    list_display = ('vin', 'created_at', 'status')
    search_fields = ('vin',)
    inlines = [SuspensionInline]


@admin.register(DiagnosticCode)
class DiagnosticCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'description', 'session')
    search_fields = ('code',)


@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = ('value', 'timestamp', 'session')
    list_filter = ('value',)


@admin.register(SuspensionInspection)
class SuspensionInspectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'inspector', 'created_at')
    search_fields = ('session__vin', 'inspector__user__username')
    inlines = [SuspensionPartInline]



admin.site.site_title = 'Администрирование сайта'
admin.site.site_header = 'Администрирование сайта'
