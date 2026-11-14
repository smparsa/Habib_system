from django.urls import path

from . import views

app_name = "slideshow"

urlpatterns = [
    path("", views.home, name="home"),
    path("create/", views.create, name="create"),
    path("build/", views.build_preview, name="build"),
    path("delete/<int:pk>/", views.delete_slide, name="delete"),
]
