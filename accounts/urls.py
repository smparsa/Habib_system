from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("jobs/add/", views.job_add, name="job_add"),
    path("jobs/<int:job_id>/edit/", views.job_edit, name="job_edit"),
    path("jobs/<int:job_id>/delete/", views.job_delete, name="job_delete"),
    path("jobs/<int:job_id>/photo/delete/", views.job_photo_delete, name="job_photo_delete"),
    path("jobs/<int:job_id>/photo/add/", views.job_photo_add, name="job_photo_add"),
    path("jobs/<int:job_id>/status/add/", views.job_status_add, name="job_status_add"),
    path("jobs/<int:job_id>/status/<int:status_id>/delete/", views.job_status_delete, name="job_status_delete"),
    path("jobs/<int:job_id>/toggle-current/", views.job_toggle_current, name="job_toggle_current"),
    path("location/update/", views.location_update, name="location_update"),
    path("location/lookup/", views.location_lookup, name="location_lookup"),
    path("location/search-place/", views.location_place_search, name="location_place_search"),
    path("names/search/", views.name_search, name="name_search"),
    path("family/nid-lookup/", views.family_nid_lookup, name="family_nid_lookup"),
    path("locations/search/", views.location_search, name="location_search"),
    path("education/fields/", views.study_fields, name="study_fields"),
    path("documents/<int:doc_id>/download/", views.document_download, name="document_download"),
    path("documents/add/", views.document_add, name="document_add"),
    path("documents/<int:doc_id>/delete/", views.document_delete, name="document_delete"),
    path("jobs/documents/add/", views.job_document_add, name="job_document_add"),
    path("documents/<int:doc_id>/job-delete/", views.job_document_delete, name="job_document_delete"),
    path("jobs/<int:job_id>/status/photo/add/", views.job_photo_status_add, name="job_photo_status_add"),
    path("education/specializations/", views.study_specializations, name="study_specializations"),
]
