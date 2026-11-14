from django.urls import path

from . import views

app_name = "jobs"

urlpatterns = [
    path("api/options/", views.api_options, name="api_options"),
    path("api/search/", views.api_search, name="api_search"),
]
