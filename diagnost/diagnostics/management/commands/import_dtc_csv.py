import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from diagnostics.models import DTCImportBatch, DTCReference, VehicleBrand


ALLOWED_SEVERITY = {"info", "low", "medium", "high", "critical"}


def normalize_code(value):
    return (value or "").strip().upper()


def code_system(code):
    code = normalize_code(code)
    return code[0] if code and code[0] in ["P", "C", "B", "U"] else ""


def normalize_severity(value):
    value = (value or "").strip().lower()

    if value in ALLOWED_SEVERITY:
        return value

    return DTCReference.Severity.MEDIUM


class Command(BaseCommand):
    help = "Import DTCReference rows from CSV."

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True, help="Path to CSV file")
        parser.add_argument("--source-name", default="Manual DTC CSV")
        parser.add_argument("--source-url", default="")
        parser.add_argument("--delimiter", default=",")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--show-bad-rows", action="store_true")

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])
        source_name = options["source_name"]
        source_url = options["source_url"]
        delimiter = options["delimiter"]
        dry_run = options["dry_run"]
        show_bad_rows = options["show_bad_rows"]

        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f, delimiter=delimiter))

        bad_rows = []

        for index, row in enumerate(rows, start=2):
            code = normalize_code(row.get("code"))
            severity = (row.get("severity") or "").strip().lower()

            if not code_system(code):
                bad_rows.append((index, code, "bad code"))

            if severity and severity not in ALLOWED_SEVERITY:
                bad_rows.append((index, code, f"bad severity: {severity[:120]}"))

            # Если в CSV есть лишние колонки из-за незакрытых запятых, csv кладёт их в None.
            if None in row:
                bad_rows.append((index, code, f"extra columns: {row[None]}"))

        if dry_run:
            self.stdout.write(f"DRY RUN rows={len(rows)} bad_rows={len(bad_rows)}")
            for item in bad_rows[:30]:
                self.stdout.write(str(item))
            for row in rows[:5]:
                self.stdout.write(str(row))
            return

        if show_bad_rows and bad_rows:
            self.stdout.write(self.style.WARNING(f"Bad rows detected: {len(bad_rows)}"))
            for item in bad_rows[:50]:
                self.stdout.write(str(item))

        batch = DTCImportBatch.objects.create(
            source_name=source_name,
            source_url=source_url,
            file_name=csv_path.name,
        )

        created = 0
        updated = 0
        skipped = 0

        for row in rows:
            code = normalize_code(row.get("code"))
            system = code_system(code)

            if not code or not system:
                skipped += 1
                continue

            manufacturer = (row.get("manufacturer") or "").strip()
            brand = None

            if manufacturer:
                brand, _ = VehicleBrand.objects.get_or_create(
                    name=manufacturer,
                    defaults={
                        "slug": slugify(manufacturer) or manufacturer.lower().replace(" ", "-")
                    },
                )

            defaults = {
                "system": system,
                "scope": DTCReference.Scope.MANUFACTURER if manufacturer else DTCReference.Scope.GENERIC,
                "manufacturer": manufacturer,
                "brand": brand,
                "title_ru": (row.get("title_ru") or "").strip()[:500],
                "title_en": (row.get("title_en") or "").strip()[:500],
                "description_ru": (row.get("description_ru") or "").strip(),
                "description_en": (row.get("description_en") or "").strip(),
                "symptoms": (row.get("symptoms") or "").strip(),
                "possible_causes": (row.get("possible_causes") or "").strip(),
                "diagnostic_notes": (row.get("diagnostic_notes") or "").strip(),
                "recommended_checks": (row.get("recommended_checks") or "").strip(),
                "severity": normalize_severity(row.get("severity")),
                "source_name": (row.get("source_name") or "").strip() or source_name,
                "source_url": (row.get("source_url") or "").strip() or source_url,
                "is_active": True,
                "import_batch": batch,
            }

            _, was_created = DTCReference.objects.update_or_create(
                code=code,
                manufacturer=manufacturer,
                defaults=defaults,
            )

            if was_created:
                created += 1
            else:
                updated += 1

        batch.rows_total = len(rows)
        batch.rows_created = created
        batch.rows_updated = updated
        batch.rows_skipped = skipped
        batch.notes = f"bad_rows={len(bad_rows)}"
        batch.save()

        self.stdout.write(self.style.SUCCESS(
            f"DTC CSV imported: total={len(rows)} created={created} updated={updated} skipped={skipped} bad_rows={len(bad_rows)}"
        ))
