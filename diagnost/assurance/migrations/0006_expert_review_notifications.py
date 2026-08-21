import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assurance", "0005_case_exceptions"),
        ("users", "0002_organization_workshop_technicianprofile_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExpertReviewNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("recipient_email", models.EmailField(max_length=254)),
                ("review_requested_at", models.DateTimeField()),
                ("status", models.CharField(choices=[("queued", "Queued"), ("sent", "Sent"), ("failed", "Failed")], db_index=True, default="queued", max_length=16)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("next_attempt_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("last_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("case_operation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="expert_review_notifications", to="assurance.caseoperation")),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assurance_review_notifications", to="users.userprofile")),
                ("repair_case", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="expert_review_notifications", to="assurance.repaircase")),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
        migrations.AddConstraint(
            model_name="expertreviewnotification",
            constraint=models.UniqueConstraint(
                fields=("case_operation", "recipient", "review_requested_at"),
                name="unique_assurance_review_notification",
            ),
        ),
    ]
