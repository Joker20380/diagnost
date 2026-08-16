from django.contrib import admin
from django.contrib import messages
from .services import publish_procedure_version

from .models import (
    CaseOperation,
    Evidence,
    EvidenceRequirement,
    ExpertDecision,
    Operation,
    OperationDependency,
    ProcedureVersion,
    ReferenceMedia,
    RepairAuditEvent,
    RepairCase,
    RepairProcedure,
    RepairRecord,
    Skill,
    TechnicianSkill,
    Verification,
)


class EvidenceRequirementInline(admin.TabularInline):
    model = EvidenceRequirement
    extra = 0


class ReferenceMediaInline(admin.TabularInline):
    model = ReferenceMedia
    extra = 0


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = ("version", "sequence", "title", "operation_type", "blocking", "approval_required")
    list_filter = ("operation_type", "blocking", "qc_operation", "approval_required")
    inlines = (EvidenceRequirementInline, ReferenceMediaInline)


@admin.register(ProcedureVersion)
class ProcedureVersionAdmin(admin.ModelAdmin):
    list_display = ("procedure", "version", "status", "published_at")
    list_filter = ("status",)
    readonly_fields = ("status", "content_sha256", "published_at")
    actions = ("publish_selected_versions",)

    @admin.action(description="Publish selected draft versions")
    def publish_selected_versions(self, request, queryset):
        published = 0
        for version in queryset:
            try:
                publish_procedure_version(version, request.user)
            except Exception as exc:
                self.message_user(request, f"{version}: {exc}", level=messages.ERROR)
            else:
                published += 1
        if published:
            self.message_user(request, f"Published: {published}", level=messages.SUCCESS)


@admin.register(RepairCase)
class RepairCaseAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    list_display = ("id", "vehicle", "title", "procedure_version", "status", "verification_status")
    list_filter = ("status", "verification_status", "organization", "workshop")


admin.site.register(RepairProcedure)
admin.site.register(OperationDependency)
admin.site.register(Skill)
admin.site.register(TechnicianSkill)
admin.site.register(CaseOperation)
admin.site.register(Evidence)
admin.site.register(ExpertDecision)
admin.site.register(Verification)
admin.site.register(RepairRecord)
admin.site.register(RepairAuditEvent)
