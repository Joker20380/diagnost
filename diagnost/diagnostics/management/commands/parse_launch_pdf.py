from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from diagnostics.launch_pdf_parser import parse_launch_pdf


class Command(BaseCommand):
    help = "Parse Launch AllSystemDTC PDF and print extracted vehicle info and DTC faults."

    def add_arguments(self, parser):
        parser.add_argument("pdf_path")

    def handle(self, *args, **options):
        path = Path(options["pdf_path"])

        if not path.exists():
            raise CommandError(f"PDF not found: {path}")

        parsed = parse_launch_pdf(path)

        vehicle = parsed["vehicle"]
        faults = parsed["faults"]

        self.stdout.write("=== VEHICLE ===")
        for key, value in vehicle.items():
            self.stdout.write(f"{key}: {value}")

        self.stdout.write("")
        self.stdout.write(f"=== FAULTS: {len(faults)} ===")

        for fault in faults:
            self.stdout.write(
                f"{fault['code']} | {fault.get('status') or '-'} | "
                f"{fault.get('module_code') or '-'} ({fault.get('module_name') or '-'}) | "
                f"{fault.get('description') or '-'}"
            )
