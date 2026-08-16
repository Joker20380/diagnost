from django.urls import path

from . import views

app_name = "assurance"

urlpatterns = [
    path("cases/", views.case_list, name="case_list"),
    path("cases/new/", views.case_create, name="case_create"),
    path("cases/<int:case_id>/", views.case_detail, name="case_detail"),
    path("operations/<int:execution_id>/evidence/", views.submit_operation_evidence, name="submit_evidence"),
    path("operations/<int:execution_id>/complete/", views.complete_case_operation, name="complete_operation"),
    path("operations/<int:execution_id>/review/", views.review_case_operation, name="review_operation"),
    path("cases/<int:case_id>/verify/", views.verify_case, name="verify_case"),
]
