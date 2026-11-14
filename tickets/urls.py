from django.urls import path

from . import views

app_name = "tickets"

urlpatterns = [
    path("", views.center_view, name="center"),
    path("create/", views.create_view, name="create"),
    path("estimate/", views.audience_estimate, name="audience_estimate"),
    path("ticket/<str:number>/", views.detail_view, name="detail"),
    path("admin/", views.staff_dashboard, name="staff"),
    path("export.csv", views.export_csv, name="export"),
]
