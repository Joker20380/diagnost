from django.urls import path

from . import views

app_name = "assurance"

urlpatterns = [
    path(
        "certificates/<uuid:public_id>/",
        views.repair_certificate,
        name="repair_certificate",
    ),
    path("cases/", views.case_list, name="case_list"),
    path("competency-reviews/new/", views.competency_review_create, name="competency_review_create"),
    path("cases/new/", views.case_create, name="case_create"),
    path("cases/<int:case_id>/", views.case_detail, name="case_detail"),
    path(
        "cases/<int:case_id>/walkthrough-observations/",
        views.record_walkthrough_observation,
        name="record_walkthrough_observation",
    ),
    path("cases/<int:case_id>/audit/", views.case_audit, name="case_audit"),
    path(
        "cases/<int:case_id>/audit.<str:export_format>",
        views.case_audit_export,
        name="case_audit_export",
    ),
    path("cases/<int:case_id>/cancel/", views.cancel_case, name="cancel_case"),
    path("operations/<int:execution_id>/evidence/", views.submit_operation_evidence, name="submit_evidence"),
    path("evidence/<int:evidence_id>/supersede/", views.supersede_operation_evidence, name="supersede_evidence"),
    path("operations/<int:execution_id>/complete/", views.complete_case_operation, name="complete_operation"),
    path("operations/<int:execution_id>/skip/", views.skip_operation, name="skip_operation"),
    path("operations/<int:execution_id>/review/", views.review_case_operation, name="review_operation"),
    path("cases/<int:case_id>/verify/", views.verify_case, name="verify_case"),
]
