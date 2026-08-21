from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("assurance", "0007_repair_record_public_id")]

    operations = [
        migrations.CreateModel(
            name="WorkshopWalkthroughObservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(choices=[("usability", "Usability"), ("workflow", "Workflow"), ("content", "Procedure content"), ("performance", "Performance"), ("safety", "Safety"), ("other", "Other")], max_length=20)),
                ("severity", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("blocker", "Blocker")], max_length=12)),
                ("description", models.TextField()),
                ("expected_behavior", models.TextField(blank=True)),
                ("recorded_at", models.DateTimeField(auto_now_add=True)),
                ("case_operation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="walkthrough_observations", to="assurance.caseoperation")),
                ("recorded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="walkthrough_observations", to="users.userprofile")),
                ("repair_case", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="walkthrough_observations", to="assurance.repaircase")),
            ],
            options={"ordering": ["recorded_at", "id"]},
        ),
    ]
