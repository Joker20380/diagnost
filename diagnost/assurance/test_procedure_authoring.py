from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase, override_settings

from users.models import Organization, TechnicianProfile, UserProfile

from .admin import OperationDependencyInline
from .models import (
    Operation,
    OperationDependency,
    ProcedureVersion,
    RepairProcedure,
)
from .services import publish_procedure_version


@override_settings(LANGUAGE_CODE="en")
class ProcedureAuthoringTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            "procedure-author", "author@example.com", "test-password"
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.organization = Organization.objects.create(
            name="Procedure Lab", slug="procedure-lab"
        )
        TechnicianProfile.objects.create(
            user_profile=self.profile,
            organization=self.organization,
            role=TechnicianProfile.Role.SENIOR_EXPERT,
        )
        self.procedure = RepairProcedure.objects.create(
            organization=self.organization,
            code="authoring-test",
            name="Authoring test",
            created_by=self.profile,
        )
        self.version = ProcedureVersion.objects.create(
            procedure=self.procedure, version=1, created_by=self.profile
        )
        self.first = self.create_operation("first", 10)
        self.second = self.create_operation("second", 20)
        self.third = self.create_operation("third", 30)

    def create_operation(self, key, sequence, version=None):
        return Operation.objects.create(
            version=version or self.version,
            key=key,
            sequence=sequence,
            title=key.title(),
            description=f"{key.title()} operation.",
        )

    def test_dependency_model_rejects_forward_operation(self):
        dependency = OperationDependency(
            operation=self.second, depends_on=self.third
        )

        with self.assertRaisesMessage(
            ValidationError, "Dependency must point to an earlier operation."
        ):
            dependency.full_clean()

    def test_publication_rechecks_dependencies_inserted_outside_model_save(self):
        OperationDependency.objects.bulk_create(
            [OperationDependency(operation=self.second, depends_on=self.third)]
        )

        with self.assertRaisesMessage(
            ValidationError, "Dependencies must point to an earlier operation."
        ):
            publish_procedure_version(self.version, self.user)

    def test_dependency_inline_only_offers_earlier_operations_in_same_version(self):
        other_version = ProcedureVersion.objects.create(
            procedure=self.procedure, version=2, created_by=self.profile
        )
        self.create_operation("other", 1, other_version)
        request = RequestFactory().get("/")
        request.user = self.user
        inline = OperationDependencyInline(Operation, admin.site)

        formset = inline.get_formset(request, self.third)

        self.assertQuerySetEqual(
            formset.form.base_fields["depends_on"].queryset,
            [self.first, self.second],
        )
