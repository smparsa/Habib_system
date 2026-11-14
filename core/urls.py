from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.index, name="index"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("profile/preview/", views.profile_preview, name="profile_preview"),
    path("pages/<slug:slug>/", views.info_page, name="info_page"),
    path("feedback/", views.feedback, name="feedback"),
]
