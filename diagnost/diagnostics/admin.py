from django.contrib import admin

# --- DTC / OBD reference admin ---

from .models import (
    DTCImportBatch,
    DTCReference,
    CustomerComplaint,
    DiagnosticCase,
    DiagnosticApproval,
    DiagnosticMeasurement,
    DiagnosticRecord,
    OBDLiveDataPIDReference,
    QAEvent,
    OperatingConditions,
    RecentRepair,
    Symptom,
    VehicleBrand,
    Vehicle,
    VehicleConfiguration,
    VehicleIdentityObservation,
)


class SymptomInline(admin.TabularInline):
    model = Symptom
    extra = 0


class RecentRepairInline(admin.TabularInline):
    model = RecentRepair
    extra = 0


@admin.register(DiagnosticCase)
class DiagnosticCaseAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "organization", "workshop", "status", "assigned_to")
    list_filter = ("status", "organization", "workshop")
    search_fields = ("session__vin", "customer_complaint__description")
    inlines = (SymptomInline, RecentRepairInline)


admin.site.register(CustomerComplaint)
admin.site.register(OperatingConditions)


@admin.register(VehicleBrand)
class VehicleBrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("vin_normalized", "make", "model", "year", "organization")
    search_fields = ("vin_normalized", "make", "model")
    list_filter = ("organization", "make")


@admin.register(VehicleConfiguration)
class VehicleConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "vehicle",
        "engine_code",
        "completeness_status",
        "mileage_km",
        "is_current",
        "confirmed_at",
    )
    list_filter = ("completeness_status", "is_current", "fuel_type")
    readonly_fields = ("missing_fields", "review_reasons")


@admin.register(VehicleIdentityObservation)
class VehicleIdentityObservationAdmin(admin.ModelAdmin):
    list_display = ("session", "status", "confirmed_by", "confirmed_at")
    list_filter = ("status",)
    readonly_fields = ("original_data", "observed_at")


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

class DiagnosticMeasurementInline(admin.TabularInline):
    model = DiagnosticMeasurement
    extra = 0


class DiagnosticApprovalInline(admin.TabularInline):
    model = DiagnosticApproval
    extra = 0
    can_delete = False
    readonly_fields = ("reviewer", "decision", "comment", "snapshot_sha256", "decided_at")


@admin.register(DiagnosticRecord)
class DiagnosticRecordAdmin(admin.ModelAdmin):
    list_display = ("session", "revision", "status", "created_by", "submitted_at", "approved_at")
    list_filter = ("status", "created_at", "approved_at")
    search_fields = ("session__vin", "summary", "confirmed_cause")
    readonly_fields = ("content_sha256", "created_at", "updated_at", "submitted_at", "approved_at")
    inlines = (DiagnosticMeasurementInline, DiagnosticApprovalInline)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_locked:
            return False
        return super().has_delete_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj and obj.is_locked:
            return False
        return super().has_change_permission(request, obj)


@admin.register(QAEvent)
class QAEventAdmin(admin.ModelAdmin):
    list_display = ("code", "severity", "session", "record", "created_at", "resolved_at")
    list_filter = ("severity", "code", "created_at", "resolved_at")
    search_fields = ("session__vin", "code", "message")
    readonly_fields = ("created_at",)
