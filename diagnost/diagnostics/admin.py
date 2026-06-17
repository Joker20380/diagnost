from django.contrib import admin

# --- DTC / OBD reference admin ---

from .models import DTCImportBatch, DTCReference, OBDLiveDataPIDReference, VehicleBrand


@admin.register(VehicleBrand)
class VehicleBrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


@admin.register(DTCImportBatch)
class DTCImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "source_name",
        "file_name",
        "rows_total",
        "rows_created",
        "rows_updated",
        "rows_skipped",
        "created_at",
    )
    search_fields = ("source_name", "file_name", "source_url", "notes")
    readonly_fields = ("created_at",)


@admin.register(DTCReference)
class DTCReferenceAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "system",
        "scope",
        "manufacturer",
        "title_ru",
        "severity",
        "is_active",
        "updated_at",
    )
    list_filter = ("system", "scope", "severity", "is_active", "manufacturer")
    search_fields = (
        "code",
        "manufacturer",
        "title_ru",
        "title_en",
        "description_ru",
        "description_en",
        "symptoms",
        "possible_causes",
        "diagnostic_notes",
        "recommended_checks",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(OBDLiveDataPIDReference)
class OBDLiveDataPIDReferenceAdmin(admin.ModelAdmin):
    list_display = ("pid", "name_ru", "name_en", "unit", "is_active")
    list_filter = ("is_active",)
    search_fields = ("pid", "name_ru", "name_en", "description_ru", "description_en", "diagnostic_value")
