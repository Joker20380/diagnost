from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from assurance.management.commands.seed_assurance_demo import DISCLAIMER
from assurance.models import ProcedureVersion, RepairProcedure


class AssuranceDemoSeedTests(TestCase):
    def test_seed_is_idempotent_published_and_explicitly_non_oem(self):
        output = StringIO()
        call_command("seed_assurance_demo", stdout=output)
        call_command("seed_assurance_demo", stdout=output)

        procedure = RepairProcedure.objects.get(
            code="demo-steering-rack-replacement"
        )
        version = procedure.versions.get(version=1)
        repair_case = version.repair_cases.get(
            initial_state__seed_key="assurance-steering-rack-demo-v1"
        )

        self.assertEqual(version.status, ProcedureVersion.Status.PUBLISHED)
        self.assertEqual(procedure.versions.count(), 1)
        self.assertEqual(version.repair_cases.count(), 1)
        self.assertEqual(version.operations.count(), 3)
        self.assertEqual(repair_case.case_operations.count(), 3)
        self.assertTrue(procedure.vehicle_scope["demo_only"])
        self.assertFalse(procedure.vehicle_scope["oem_validated"])
        self.assertIn(DISCLAIMER, procedure.description)
        self.assertIn(DISCLAIMER, version.change_summary)
        self.assertIn(DISCLAIMER, repair_case.initial_state["disclaimer"])
        for operation in version.operations.all():
            self.assertTrue(operation.technical_requirements["demo_only"])
            self.assertFalse(operation.technical_requirements["oem_validated"])
