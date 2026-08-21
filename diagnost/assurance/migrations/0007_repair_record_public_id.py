import uuid

from django.db import migrations, models


def populate_public_ids(apps, schema_editor):
    RepairRecord = apps.get_model("assurance", "RepairRecord")
    for record in RepairRecord.objects.filter(public_id__isnull=True).iterator():
        record.public_id = uuid.uuid4()
        record.save(update_fields=["public_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("assurance", "0006_expert_review_notifications"),
    ]

    operations = [
        migrations.AddField(
            model_name="repairrecord",
            name="public_id",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(
            populate_public_ids,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="repairrecord",
            name="public_id",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
            ),
        ),
    ]
