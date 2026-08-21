from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from users.models import UserProfile


class Skill(models.Model):
    organization = models.ForeignKey("users.Organization", on_delete=models.PROTECT, related_name="assurance_skills")
    code = models.SlugField(max_length=80)
    name = models.CharField(max_length=160)
    max_level = models.PositiveSmallIntegerField(default=3)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "code"], name="unique_assurance_skill_code")]

    def __str__(self):
        return self.name


class TechnicianSkill(models.Model):
    technician = models.ForeignKey("users.TechnicianProfile", on_delete=models.PROTECT, related_name="assurance_skills")
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT, related_name="technicians")
    level = models.PositiveSmallIntegerField(default=1)
    verified_by = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="verified_assurance_skills")
    verified_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["technician", "skill"], name="unique_assurance_technician_skill")]

    def clean(self):
        if self.technician.organization_id != self.skill.organization_id:
            raise ValidationError("Technician and skill must belong to one organization.")
        if self.level > self.skill.max_level:
            raise ValidationError({"level": "Level exceeds the skill maximum."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class RepairProcedure(models.Model):
    organization = models.ForeignKey("users.Organization", on_delete=models.PROTECT, related_name="repair_procedures")
    code = models.SlugField(max_length=120)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    vehicle_scope = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="created_repair_procedures")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "code"], name="unique_repair_procedure_code")]

    def __str__(self):
        return self.name


class ProcedureVersion(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        RETIRED = "retired", "Retired"

    procedure = models.ForeignKey(RepairProcedure, on_delete=models.PROTECT, related_name="versions")
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    change_summary = models.TextField(blank=True)
    content_sha256 = models.CharField(max_length=64, blank=True, editable=False)
    created_by = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="created_procedure_versions")
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["procedure", "version"], name="unique_repair_procedure_version")]

    @property
    def is_locked(self):
        return self.status in {self.Status.PUBLISHED, self.Status.RETIRED}

    def save(self, *args, **kwargs):
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).values_list("status", flat=True).first()
            if old in {self.Status.PUBLISHED, self.Status.RETIRED}:
                raise ValidationError("Published procedure versions are immutable.")
            if old == self.Status.DRAFT and self.status != self.Status.DRAFT:
                raise ValidationError("Publish procedure versions through the publication service.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_locked:
            raise ValidationError("Published procedure versions cannot be deleted.")
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.procedure} v{self.version}"


class DraftSpecification(models.Model):
    class Meta:
        abstract = True

    def procedure_version(self):
        raise NotImplementedError

    def _assert_draft(self):
        if self.procedure_version().status != ProcedureVersion.Status.DRAFT:
            raise ValidationError("Published procedure specifications are immutable.")

    def save(self, *args, **kwargs):
        self._assert_draft()
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self._assert_draft()
        return super().delete(*args, **kwargs)


class Operation(DraftSpecification):
    class Type(models.TextChoices):
        INSTRUCTION = "instruction", "Instruction"
        MEASUREMENT = "measurement", "Measurement"
        DIAGNOSTIC_SCAN = "diagnostic_scan", "Diagnostic scan"
        DECISION_GATE = "decision_gate", "Decision gate"
        CALIBRATION = "calibration", "Calibration"
        ROAD_TEST = "road_test", "Road test"
        QC = "qc", "Quality control"

    version = models.ForeignKey(ProcedureVersion, on_delete=models.PROTECT, related_name="operations")
    key = models.SlugField(max_length=100)
    sequence = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    description = models.TextField()
    operation_type = models.CharField(max_length=24, choices=Type.choices, default=Type.INSTRUCTION)
    mandatory = models.BooleanField(default=True)
    blocking = models.BooleanField(default=True)
    qc_operation = models.BooleanField(default=False)
    expected_result = models.TextField(blank=True)
    technical_requirements = models.JSONField(default=dict, blank=True)
    required_tools = models.JSONField(default=list, blank=True)
    specification = models.JSONField(default=dict, blank=True)
    required_skill = models.ForeignKey(Skill, on_delete=models.PROTECT, null=True, blank=True, related_name="operations")
    required_skill_level = models.PositiveSmallIntegerField(default=0)
    minimum_role = models.CharField(max_length=32, blank=True)
    approval_required = models.BooleanField(default=False)
    approval_minimum_role = models.CharField(max_length=32, blank=True)
    escalation_allowed = models.BooleanField(default=True)

    class Meta:
        ordering = ["version_id", "sequence"]
        constraints = [
            models.UniqueConstraint(fields=["version", "key"], name="unique_operation_key_per_version"),
            models.UniqueConstraint(fields=["version", "sequence"], name="unique_operation_sequence_per_version"),
        ]

    def procedure_version(self):
        return self.version

    def clean(self):
        if self.required_skill_id and self.required_skill.organization_id != self.version.procedure.organization_id:
            raise ValidationError("Required skill belongs to another organization.")
        if self.required_skill_id and self.required_skill_level < 1:
            raise ValidationError({"required_skill_level": "Required skill needs a level."})

    def __str__(self):
        return f"{self.sequence}. {self.title}"


class OperationDependency(DraftSpecification):
    operation = models.ForeignKey(Operation, on_delete=models.PROTECT, related_name="dependencies")
    depends_on = models.ForeignKey(Operation, on_delete=models.PROTECT, related_name="unlocks")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["operation", "depends_on"], name="unique_operation_dependency"),
            models.CheckConstraint(condition=~models.Q(operation=models.F("depends_on")), name="operation_not_self_dependent"),
        ]

    def procedure_version(self):
        return self.operation.version

    def clean(self):
        if self.operation.version_id != self.depends_on.version_id:
            raise ValidationError(
                {"depends_on": "Dependency must use the same procedure version."}
            )
        if self.depends_on.sequence >= self.operation.sequence:
            raise ValidationError(
                {"depends_on": "Dependency must point to an earlier operation."}
            )


class EvidenceRequirement(DraftSpecification):
    class Type(models.TextChoices):
        NONE = "none", "None"
        PHOTO = "photo", "Photo"
        VIDEO = "video", "Video"
        TEXT = "text", "Text"
        MEASUREMENT = "measurement", "Measurement"
        DIAGNOSTIC_SCAN = "diagnostic_scan", "Diagnostic scan"
        DOCUMENT = "document", "Document"
        CONFIRMATION = "confirmation", "Confirmation"

    operation = models.ForeignKey(Operation, on_delete=models.PROTECT, related_name="evidence_requirements")
    evidence_type = models.CharField(max_length=24, choices=Type.choices)
    description = models.TextField(blank=True)
    required = models.BooleanField(default=True)
    minimum_count = models.PositiveSmallIntegerField(default=1)
    unit = models.CharField(max_length=32, blank=True)
    minimum_value = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    maximum_value = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    metadata_schema = models.JSONField(default=dict, blank=True)

    def procedure_version(self):
        return self.operation.version

    def clean(self):
        if self.evidence_type == self.Type.NONE and self.required:
            raise ValidationError("NONE cannot be required evidence.")


class ReferenceMedia(DraftSpecification):
    class Source(models.TextChoices):
        OWN = "own", "Own"
        SERVICE_CAPTURE = "service_capture", "Service capture"
        YOUTUBE_EMBED = "youtube_embed", "YouTube embed"
        LICENSED = "licensed", "Licensed"
        OEM = "oem", "OEM"
        EXTERNAL = "external", "External"

    operation = models.ForeignKey(Operation, on_delete=models.PROTECT, related_name="reference_media")
    source_type = models.CharField(max_length=24, choices=Source.choices)
    title = models.CharField(max_length=255, blank=True)
    provider = models.CharField(max_length=64, blank=True)
    provider_asset_id = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(max_length=1000, blank=True)
    start_seconds = models.PositiveIntegerField(null=True, blank=True)
    end_seconds = models.PositiveIntegerField(null=True, blank=True)
    file = models.FileField(upload_to="assurance/reference/", null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    def procedure_version(self):
        return self.operation.version

    def clean(self):
        if self.source_type == self.Source.YOUTUBE_EMBED:
            if self.provider != "youtube" or not self.provider_asset_id:
                raise ValidationError("YouTube embed needs provider and video id.")
            if self.file:
                raise ValidationError("YouTube media must remain external.")
        if self.start_seconds is not None and self.end_seconds is not None and self.end_seconds <= self.start_seconds:
            raise ValidationError("Media end must be after start.")


class RepairCase(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_PROGRESS = "in_progress", "In progress"
        BLOCKED = "blocked", "Blocked"
        VERIFICATION = "verification", "Verification"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class VerificationStatus(models.TextChoices):
        NOT_RUN = "not_run", "Not run"
        VERIFIED = "verified", "Verified"
        FAILED = "failed", "Failed"
        INCOMPLETE = "incomplete", "Incomplete"
        REQUIRES_REVIEW = "requires_review", "Requires review"

    organization = models.ForeignKey("users.Organization", on_delete=models.PROTECT, related_name="assurance_repair_cases")
    workshop = models.ForeignKey("users.Workshop", on_delete=models.PROTECT, null=True, blank=True, related_name="assurance_repair_cases")
    vehicle = models.ForeignKey("diagnostics.Vehicle", on_delete=models.PROTECT, related_name="assurance_repair_cases")
    procedure_version = models.ForeignKey(ProcedureVersion, on_delete=models.PROTECT, related_name="repair_cases")
    title = models.CharField(max_length=255)
    complaint = models.TextField(blank=True)
    initial_state = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    verification_status = models.CharField(max_length=24, choices=VerificationStatus.choices, default=VerificationStatus.NOT_RUN)
    created_by = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="created_assurance_repair_cases")
    opened_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if self.vehicle.organization_id != self.organization_id:
            raise ValidationError("Vehicle belongs to another organization.")
        if self.procedure_version.procedure.organization_id != self.organization_id:
            raise ValidationError("Procedure belongs to another organization.")
        if self.workshop_id and self.workshop.organization_id != self.organization_id:
            raise ValidationError("Workshop belongs to another organization.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class RepairCaseTechnician(models.Model):
    repair_case = models.ForeignKey(RepairCase, on_delete=models.PROTECT, related_name="technician_assignments")
    technician = models.ForeignKey("users.TechnicianProfile", on_delete=models.PROTECT, related_name="assurance_case_assignments")
    assigned_by = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="assurance_assignments_made")
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["repair_case", "technician"], name="unique_assurance_case_technician")]

    def clean(self):
        if self.technician.organization_id != self.repair_case.organization_id:
            raise ValidationError("Technician belongs to another organization.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class CaseOperation(models.Model):
    class Status(models.TextChoices):
        LOCKED = "locked", "Locked"
        AVAILABLE = "available", "Available"
        IN_PROGRESS = "in_progress", "In progress"
        REQUIRES_REVIEW = "requires_review", "Requires review"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    repair_case = models.ForeignKey(RepairCase, on_delete=models.PROTECT, related_name="case_operations")
    operation = models.ForeignKey(Operation, on_delete=models.PROTECT, related_name="case_executions")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.LOCKED)
    assigned_to = models.ForeignKey(UserProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="assigned_assurance_operations")
    result = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(UserProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="completed_assurance_operations")

    class Meta:
        ordering = ["operation__sequence"]
        constraints = [models.UniqueConstraint(fields=["repair_case", "operation"], name="unique_assurance_case_operation")]

    def clean(self):
        if self.operation.version_id != self.repair_case.procedure_version_id:
            raise ValidationError("Operation is outside the pinned procedure version.")


class CaseOperationException(models.Model):
    case_operation = models.OneToOneField(
        CaseOperation,
        on_delete=models.PROTECT,
        related_name="approved_exception",
    )
    rationale = models.TextField()
    authorized_by = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        related_name="authorized_assurance_exceptions",
    )
    authorized_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Operation exceptions are append-only.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Operation exceptions are append-only.")


class Evidence(models.Model):
    repair_case = models.ForeignKey(RepairCase, on_delete=models.PROTECT, related_name="evidence")
    case_operation = models.ForeignKey(CaseOperation, on_delete=models.PROTECT, related_name="evidence")
    operation = models.ForeignKey(Operation, on_delete=models.PROTECT, related_name="evidence")
    requirement = models.ForeignKey(EvidenceRequirement, on_delete=models.PROTECT, null=True, blank=True, related_name="evidence")
    evidence_type = models.CharField(max_length=24, choices=EvidenceRequirement.Type.choices)
    file = models.FileField(upload_to="assurance/evidence/", null=True, blank=True)
    text = models.TextField(blank=True)
    numeric_value = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    unit = models.CharField(max_length=32, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    content_sha256 = models.CharField(max_length=64, blank=True, editable=False)
    submitted_by = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="assurance_evidence")
    submitted_at = models.DateTimeField(auto_now_add=True)
    supersedes = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="superseded_by")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["supersedes"],
                condition=models.Q(supersedes__isnull=False),
                name="unique_assurance_evidence_supersession",
            )
        ]

    @property
    def is_superseded(self):
        return self.superseded_by.exists()

    def clean(self):
        if not self.supersedes_id:
            return
        previous = self.supersedes
        if previous.repair_case_id != self.repair_case_id:
            raise ValidationError("Superseded evidence belongs to another repair case.")
        if previous.case_operation_id != self.case_operation_id:
            raise ValidationError("Superseded evidence belongs to another operation.")
        if previous.requirement_id != self.requirement_id:
            raise ValidationError("Replacement must use the same evidence requirement.")
        if previous.evidence_type != self.evidence_type:
            raise ValidationError("Replacement must use the same evidence type.")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Evidence is append-only.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Evidence is append-only.")


class ExpertDecision(models.Model):
    class Decision(models.TextChoices):
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"
        REWORK = "rework", "Rework"
        ESCALATE = "escalate", "Escalate"

    repair_case = models.ForeignKey(RepairCase, on_delete=models.PROTECT, related_name="expert_decisions")
    case_operation = models.ForeignKey(CaseOperation, on_delete=models.PROTECT, related_name="expert_decisions")
    decision = models.CharField(max_length=16, choices=Decision.choices)
    rationale = models.TextField()
    authorized_operation_keys = models.JSONField(default=list, blank=True)
    reviewer = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="assurance_expert_decisions")
    decided_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Expert decisions are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Expert decisions are append-only.")


class ExpertDecisionEvidence(models.Model):
    decision = models.ForeignKey(ExpertDecision, on_delete=models.PROTECT, related_name="evidence_links")
    evidence = models.ForeignKey(Evidence, on_delete=models.PROTECT, related_name="decision_links")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["decision", "evidence"], name="unique_assurance_decision_evidence")]


class ExpertReviewNotification(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    repair_case = models.ForeignKey(
        RepairCase, on_delete=models.PROTECT, related_name="expert_review_notifications"
    )
    case_operation = models.ForeignKey(
        CaseOperation, on_delete=models.PROTECT, related_name="expert_review_notifications"
    )
    recipient = models.ForeignKey(
        UserProfile, on_delete=models.PROTECT, related_name="assurance_review_notifications"
    )
    recipient_email = models.EmailField()
    review_requested_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["case_operation", "recipient", "review_requested_at"],
                name="unique_assurance_review_notification",
            )
        ]


class Verification(models.Model):
    repair_case = models.ForeignKey(RepairCase, on_delete=models.PROTECT, related_name="verifications")
    status = models.CharField(max_length=24, choices=RepairCase.VerificationStatus.choices)
    details = models.JSONField(default=dict)
    performed_by = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="assurance_verifications")
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["performed_at", "id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Verification results are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Verification results are append-only.")


class RepairRecord(models.Model):
    repair_case = models.OneToOneField(RepairCase, on_delete=models.PROTECT, related_name="repair_record")
    snapshot = models.JSONField()
    content_sha256 = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Repair records are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Repair records are immutable.")


class RepairAuditEvent(models.Model):
    repair_case = models.ForeignKey(RepairCase, on_delete=models.PROTECT, related_name="audit_events")
    case_operation = models.ForeignKey(CaseOperation, on_delete=models.PROTECT, null=True, blank=True, related_name="audit_events")
    actor = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="assurance_audit_events")
    action = models.CharField(max_length=80, db_index=True)
    before_status = models.CharField(max_length=32, blank=True)
    after_status = models.CharField(max_length=32, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["occurred_at", "id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Audit events are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit events are append-only.")
