from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from diagnostics.models import Vehicle
from users.models import Organization, TechnicianProfile, UserProfile, Workshop

from .models import (
    CaseOperation,
    EvidenceRequirement,
    ExpertDecision,
    Operation,
    OperationDependency,
    ProcedureVersion,
    RepairProcedure,
    Skill,
    TechnicianSkill,
)
from .services import (
    complete_operation,
    create_repair_case,
    decide_operation,
    publish_procedure_version,
    submit_evidence,
    verify_repair_case,
)


class RepairAssuranceExecutionTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Assurance Garage", slug="assurance-garage"
        )
        self.workshop = Workshop.objects.create(
            organization=self.organization, name="Main", code="main"
        )
        self.senior_user = User.objects.create_user("assurance-senior")
        self.junior_user = User.objects.create_user("assurance-junior")
        self.outsider_user = User.objects.create_user("assurance-outsider")
        self.senior_profile, _ = UserProfile.objects.get_or_create(user=self.senior_user)
        self.junior_profile, _ = UserProfile.objects.get_or_create(user=self.junior_user)
        self.outsider_profile, _ = UserProfile.objects.get_or_create(user=self.outsider_user)
        self.senior = TechnicianProfile.objects.create(
            user_profile=self.senior_profile,
            organization=self.organization,
            workshop=self.workshop,
            role=TechnicianProfile.Role.SENIOR_EXPERT,
        )
        self.junior = TechnicianProfile.objects.create(
            user_profile=self.junior_profile,
            organization=self.organization,
            workshop=self.workshop,
            role=TechnicianProfile.Role.JUNIOR_TECHNICIAN,
        )
        self.outsider = TechnicianProfile.objects.create(
            user_profile=self.outsider_profile,
            organization=self.organization,
            workshop=self.workshop,
            role=TechnicianProfile.Role.JUNIOR_TECHNICIAN,
        )
        self.vehicle = Vehicle.objects.create(
            organization=self.organization,
            vin="WBAJR71010B123456",
            make="BMW",
            model="5 Series",
            generation="G30",
            year=2020,
        )
        self.skill = Skill.objects.create(
            organization=self.organization,
            code="critical-fasteners",
            name="Critical fasteners",
        )
        TechnicianSkill.objects.create(
            technician=self.junior,
            skill=self.skill,
            level=2,
            verified_by=self.senior_profile,
        )
        self.procedure = RepairProcedure.objects.create(
            organization=self.organization,
            code="steering-rack-replacement",
            name="Steering rack replacement",
            created_by=self.senior_profile,
        )
        self.version = ProcedureVersion.objects.create(
            procedure=self.procedure,
            version=1,
            created_by=self.senior_profile,
        )
        self.scan = Operation.objects.create(
            version=self.version,
            key="pre-scan",
            sequence=1,
            title="Pre-repair diagnostic scan",
            description="Capture diagnostic scan.",
            operation_type=Operation.Type.DIAGNOSTIC_SCAN,
            minimum_role=TechnicianProfile.Role.JUNIOR_TECHNICIAN,
        )
        self.scan_requirement = EvidenceRequirement.objects.create(
            operation=self.scan,
            evidence_type=EvidenceRequirement.Type.DIAGNOSTIC_SCAN,
            description="Diagnostic result",
        )
        self.torque = Operation.objects.create(
            version=self.version,
            key="critical-torque",
            sequence=2,
            title="Critical fastener torque",
            description="Tighten the critical fastener.",
            operation_type=Operation.Type.MEASUREMENT,
            required_skill=self.skill,
            required_skill_level=2,
            minimum_role=TechnicianProfile.Role.JUNIOR_TECHNICIAN,
            approval_required=True,
            approval_minimum_role=TechnicianProfile.Role.SENIOR_EXPERT,
            specification={"target": "105", "unit": "Nm"},
        )
        OperationDependency.objects.create(
            operation=self.torque, depends_on=self.scan
        )
        self.torque_requirement = EvidenceRequirement.objects.create(
            operation=self.torque,
            evidence_type=EvidenceRequirement.Type.MEASUREMENT,
            description="Recorded torque",
            unit="Nm",
            minimum_value=Decimal("105"),
            maximum_value=Decimal("105"),
        )
        self.qc = Operation.objects.create(
            version=self.version,
            key="road-test",
            sequence=3,
            title="Road test",
            description="Perform final road test.",
            operation_type=Operation.Type.QC,
            qc_operation=True,
            minimum_role=TechnicianProfile.Role.JUNIOR_TECHNICIAN,
        )
        OperationDependency.objects.create(operation=self.qc, depends_on=self.torque)
        self.qc_requirement = EvidenceRequirement.objects.create(
            operation=self.qc,
            evidence_type=EvidenceRequirement.Type.CONFIRMATION,
            description="Road test passed",
        )
        publish_procedure_version(self.version, self.senior_user)
        self.version.refresh_from_db()
        self.case = create_repair_case(
            vehicle=self.vehicle,
            procedure_version=self.version,
            title="BMW G30 steering rack",
            complaint="Steering play",
            user=self.senior_user,
            workshop=self.workshop,
            technicians=[self.junior, self.senior],
        )

    def execution(self, operation):
        return self.case.case_operations.get(operation=operation)

    def test_assigned_mechanic_sees_simple_case_screen(self):
        self.client.force_login(self.junior_user)
        response = self.client.get(
            reverse("assurance:case_detail", args=[self.case.pk]),
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pre-repair diagnostic scan")
        self.assertContains(response, "BLOCKED")

    def test_unassigned_mechanic_cannot_open_case_screen(self):
        self.client.force_login(self.outsider_user)
        response = self.client.get(
            reverse("assurance:case_detail", args=[self.case.pk]),
            secure=True,
        )
        self.assertEqual(response.status_code, 404)

    def test_published_specification_is_immutable(self):
        self.scan.title = "Changed after publication"
        with self.assertRaises(ValidationError):
            self.scan.save()

    def test_case_creation_screen_is_manager_only(self):
        self.client.force_login(self.senior_user)
        response = self.client.get(reverse("assurance:case_create"), secure=True)
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.junior_user)
        response = self.client.get(reverse("assurance:case_create"), secure=True)
        self.assertEqual(response.status_code, 403)

    def test_direct_status_change_cannot_bypass_publication_service(self):
        draft = ProcedureVersion.objects.create(
            procedure=self.procedure,
            version=2,
            created_by=self.senior_profile,
        )
        draft.status = ProcedureVersion.Status.PUBLISHED
        with self.assertRaises(ValidationError):
            draft.save()

    def test_unassigned_technician_is_rejected_server_side(self):
        with self.assertRaises(PermissionDenied):
            submit_evidence(
                case_operation=self.execution(self.scan),
                user=self.outsider_user,
                requirement=self.scan_requirement,
                evidence_type=EvidenceRequirement.Type.DIAGNOSTIC_SCAN,
                text="scan",
            )

    def test_complete_repair_with_gates_approval_verification_and_record(self):
        scan_execution = self.execution(self.scan)
        torque_execution = self.execution(self.torque)
        qc_execution = self.execution(self.qc)
        self.assertEqual(scan_execution.status, CaseOperation.Status.AVAILABLE)
        self.assertEqual(torque_execution.status, CaseOperation.Status.LOCKED)
        self.assertEqual(qc_execution.status, CaseOperation.Status.LOCKED)

        with self.assertRaises(ValidationError):
            complete_operation(scan_execution, self.junior_user)

        scan_evidence = submit_evidence(
            case_operation=scan_execution,
            user=self.junior_user,
            requirement=self.scan_requirement,
            evidence_type=EvidenceRequirement.Type.DIAGNOSTIC_SCAN,
            text="No active steering faults",
        )
        complete_operation(scan_execution, self.junior_user)
        torque_execution.refresh_from_db()
        self.assertEqual(torque_execution.status, CaseOperation.Status.AVAILABLE)

        measurement = submit_evidence(
            case_operation=torque_execution,
            user=self.junior_user,
            requirement=self.torque_requirement,
            evidence_type=EvidenceRequirement.Type.MEASUREMENT,
            numeric_value=Decimal("105"),
            unit="Nm",
        )
        complete_operation(torque_execution, self.junior_user)
        torque_execution.refresh_from_db()
        qc_execution.refresh_from_db()
        self.assertEqual(torque_execution.status, CaseOperation.Status.REQUIRES_REVIEW)
        self.assertEqual(qc_execution.status, CaseOperation.Status.LOCKED)

        decision = decide_operation(
            case_operation=torque_execution,
            user=self.senior_user,
            decision=ExpertDecision.Decision.APPROVE,
            rationale="Torque evidence is within specification.",
            evidence=[measurement],
        )
        self.assertEqual(decision.authorized_operation_keys, ["road-test"])
        qc_execution.refresh_from_db()
        self.assertEqual(qc_execution.status, CaseOperation.Status.AVAILABLE)

        confirmation = submit_evidence(
            case_operation=qc_execution,
            user=self.junior_user,
            requirement=self.qc_requirement,
            evidence_type=EvidenceRequirement.Type.CONFIRMATION,
            text="Road test passed; steering centered.",
        )
        complete_operation(qc_execution, self.junior_user)
        verification = verify_repair_case(self.case, self.senior_user)
        self.case.refresh_from_db()

        self.assertEqual(
            verification.status, self.case.VerificationStatus.VERIFIED
        )
        self.assertEqual(self.case.status, self.case.Status.COMPLETED)
        self.assertTrue(hasattr(self.case, "repair_record"))
        self.assertEqual(
            self.case.repair_record.snapshot["procedure"]["version"], 1
        )
        self.assertGreaterEqual(self.case.audit_events.count(), 10)

        scan_evidence.text = "mutated"
        with self.assertRaises(ValidationError):
            scan_evidence.save()
        with self.assertRaises(ValidationError):
            confirmation.delete()
