import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("assurance", "0009_evidence_based_competency_review"),
        ("diagnostics", "0013_link_vehicle_catalog"),
        ("users", "0002_organization_workshop_technicianprofile_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Certification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=80)),
                ("name", models.CharField(max_length=160)),
                ("is_active", models.BooleanField(default=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assurance_certifications", to="users.organization")),
            ],
        ),
        migrations.CreateModel(
            name="TechnicianCertification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("valid_from", models.DateField(default=django.utils.timezone.localdate)),
                ("valid_until", models.DateField(blank=True, null=True)),
                ("issued_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("certification", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="technician_grants", to="assurance.certification")),
                ("issued_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="issued_assurance_certifications", to="users.userprofile")),
                ("technician", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assurance_certifications", to="users.technicianprofile")),
                ("vehicle_brands", models.ManyToManyField(blank=True, related_name="technician_certifications", to="diagnostics.vehiclebrand")),
                ("vehicle_models", models.ManyToManyField(blank=True, related_name="technician_certifications", to="diagnostics.vehiclemodel")),
            ],
        ),
        migrations.CreateModel(
            name="OperationCertificationRequirement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("certification", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="operation_requirements", to="assurance.certification")),
                ("operation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="certification_requirements", to="assurance.operation")),
            ],
        ),
        migrations.AddField(
            model_name="operation",
            name="required_certifications",
            field=models.ManyToManyField(blank=True, related_name="operations", through="assurance.OperationCertificationRequirement", to="assurance.certification"),
        ),
        migrations.AddConstraint(
            model_name="operationcertificationrequirement",
            constraint=models.UniqueConstraint(fields=("operation", "certification"), name="unique_operation_certification_requirement"),
        ),
        migrations.AddConstraint(
            model_name="certification",
            constraint=models.UniqueConstraint(
                fields=("organization", "code"),
                name="unique_assurance_certification_code",
            ),
        ),
        migrations.AddConstraint(
            model_name="techniciancertification",
            constraint=models.UniqueConstraint(
                fields=("technician", "certification"),
                name="unique_assurance_technician_certification",
            ),
        ),
    ]
