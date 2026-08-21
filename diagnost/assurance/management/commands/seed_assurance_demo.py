from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from assurance.models import (
    EvidenceRequirement,
    Operation,
    OperationDependency,
    ProcedureVersion,
    RepairProcedure,
    Skill,
    TechnicianSkill,
)
from assurance.services import create_repair_case, publish_procedure_version
from diagnostics.models import Vehicle
from users.models import Organization, TechnicianProfile, UserProfile, Workshop


DISCLAIMER = (
    "DEMONSTRATION ONLY — NOT OEM REPAIR INFORMATION. "
    "The values and sequence are fictional training data. Do not use them to "
    "repair a real vehicle. Always use current OEM instructions."
)


class Command(BaseCommand):
    help = "Create an idempotent, explicitly non-OEM steering-rack demo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-slug",
            default="assurance-demo",
            help="Organization slug for isolated demonstration data.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        slug = options["organization_slug"]
        organization, _ = Organization.objects.get_or_create(
            slug=slug, defaults={"name": "Repair Assurance Demo"}
        )
        workshop, _ = Workshop.objects.get_or_create(
            organization=organization,
            code="demo-workshop",
            defaults={"name": "Demonstration Workshop"},
        )
        senior = self._technician(
            organization,
            workshop,
            f"{slug}-senior",
            TechnicianProfile.Role.SENIOR_EXPERT,
        )
        junior = self._technician(
            organization,
            workshop,
            f"{slug}-junior",
            TechnicianProfile.Role.JUNIOR_TECHNICIAN,
        )
        skill, _ = Skill.objects.get_or_create(
            organization=organization,
            code="demo-critical-fasteners",
            defaults={"name": "Demo critical-fastener evidence", "max_level": 3},
        )
        TechnicianSkill.objects.update_or_create(
            technician=junior,
            skill=skill,
            defaults={"level": 2, "verified_by": senior.user_profile},
        )
        vehicle, _ = Vehicle.objects.get_or_create(
            organization=organization,
            vin="DEMOASSURANC00001",
            defaults={
                "make": "DEMO",
                "model": "Training Vehicle",
                "generation": "Non-OEM",
                "year": 2026,
            },
        )
        procedure, _ = RepairProcedure.objects.get_or_create(
            organization=organization,
            code="demo-steering-rack-replacement",
            defaults={
                "name": "Demo steering rack replacement",
                "description": DISCLAIMER,
                "vehicle_scope": {"demo_only": True, "oem_validated": False},
                "created_by": senior.user_profile,
            },
        )
        version, created = ProcedureVersion.objects.get_or_create(
            procedure=procedure,
            version=1,
            defaults={
                "change_summary": DISCLAIMER,
                "created_by": senior.user_profile,
            },
        )
        if created:
            self._build_version(version, skill)
            publish_procedure_version(version, senior.user_profile.user)
            version.refresh_from_db()
        elif version.status != ProcedureVersion.Status.PUBLISHED:
            raise RuntimeError(
                "The demo version exists but is not published; review it manually."
            )

        repair_case = version.repair_cases.filter(
            initial_state__seed_key="assurance-steering-rack-demo-v1"
        ).first()
        if repair_case is None:
            repair_case = create_repair_case(
                vehicle=vehicle,
                procedure_version=version,
                title="DEMO ONLY — steering rack controlled execution",
                complaint="Fictional steering-play complaint for workflow training.",
                user=senior.user_profile.user,
                workshop=workshop,
                technicians=[junior, senior],
            )
            repair_case.initial_state = {
                "seed_key": "assurance-steering-rack-demo-v1",
                "demo_only": True,
                "oem_validated": False,
                "disclaimer": DISCLAIMER,
            }
            repair_case.save(update_fields=["initial_state"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo ready: procedure={procedure.pk}, version={version.pk}, "
                f"case={repair_case.pk}. {DISCLAIMER}"
            )
        )

    def _technician(self, organization, workshop, username, role):
        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        user_profile, _ = UserProfile.objects.get_or_create(user=user)
        technician, _ = TechnicianProfile.objects.update_or_create(
            user_profile=user_profile,
            defaults={
                "organization": organization,
                "workshop": workshop,
                "role": role,
            },
        )
        return technician

    def _build_version(self, version, skill):
        common = {
            "demo_only": True,
            "oem_validated": False,
            "warning": DISCLAIMER,
        }
        scan = Operation.objects.create(
            version=version,
            key="pre-scan",
            sequence=1,
            title="Capture pre-repair diagnostic scan",
            description=f"Record the fictional vehicle state. {DISCLAIMER}",
            operation_type=Operation.Type.DIAGNOSTIC_SCAN,
            minimum_role=TechnicianProfile.Role.JUNIOR_TECHNICIAN,
            technical_requirements=common,
        )
        EvidenceRequirement.objects.create(
            operation=scan,
            evidence_type=EvidenceRequirement.Type.DIAGNOSTIC_SCAN,
            description="Demo diagnostic scan output",
        )
        torque = Operation.objects.create(
            version=version,
            key="demo-critical-torque",
            sequence=2,
            title="Record fictional critical-fastener torque",
            description=f"Training gate using a fictional value. {DISCLAIMER}",
            operation_type=Operation.Type.MEASUREMENT,
            required_skill=skill,
            required_skill_level=2,
            minimum_role=TechnicianProfile.Role.JUNIOR_TECHNICIAN,
            approval_required=True,
            approval_minimum_role=TechnicianProfile.Role.SENIOR_EXPERT,
            specification={**common, "target": "105", "unit": "Nm"},
            technical_requirements=common,
        )
        OperationDependency.objects.create(operation=torque, depends_on=scan)
        EvidenceRequirement.objects.create(
            operation=torque,
            evidence_type=EvidenceRequirement.Type.MEASUREMENT,
            description="Fictional demo torque measurement",
            unit="Nm",
            minimum_value="105",
            maximum_value="105",
            metadata_schema=common,
        )
        qc = Operation.objects.create(
            version=version,
            key="demo-road-test",
            sequence=3,
            title="Confirm fictional QC road-test outcome",
            description=f"Record a simulation; do not drive. {DISCLAIMER}",
            operation_type=Operation.Type.QC,
            qc_operation=True,
            minimum_role=TechnicianProfile.Role.JUNIOR_TECHNICIAN,
            technical_requirements=common,
        )
        OperationDependency.objects.create(operation=qc, depends_on=torque)
        EvidenceRequirement.objects.create(
            operation=qc,
            evidence_type=EvidenceRequirement.Type.CONFIRMATION,
            description="Simulated road-test confirmation",
            metadata_schema=common,
        )
