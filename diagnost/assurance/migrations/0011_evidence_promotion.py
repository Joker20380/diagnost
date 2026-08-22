import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assurance", "0010_certification_vehicle_scope"),
        ("users", "0002_organization_workshop_technicianprofile_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="referencemedia",
            name="promoted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="referencemedia",
            name="promoted_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="promoted_reference_media", to="users.userprofile"),
        ),
        migrations.AddField(
            model_name="referencemedia",
            name="source_evidence",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="promoted_reference_media", to="assurance.evidence"),
        ),
        migrations.CreateModel(
            name="EvidencePromotionRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("proposed_title", models.CharField(max_length=255)),
                ("license_basis", models.TextField()),
                ("rationale", models.TextField()),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("status", models.CharField(choices=[("pending", "Ожидает"), ("approved", "Approved"), ("rejected", "Отклонено")], default="pending", max_length=12)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_rationale", models.TextField(blank=True)),
                ("evidence", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="promotion_requests", to="assurance.evidence")),
                ("reference_media", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="promotion_request", to="assurance.referencemedia")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="evidence_promotion_requests", to="users.userprofile")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="evidence_promotions_reviewed", to="users.userprofile")),
                ("target_operation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="evidence_promotion_requests", to="assurance.operation")),
            ],
        ),
        migrations.AddConstraint(
            model_name="evidencepromotionrequest",
            constraint=models.UniqueConstraint(fields=("evidence", "target_operation"), name="unique_evidence_promotion_target"),
        ),
    ]
