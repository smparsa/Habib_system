from django.urls import path

from . import views

app_name = "ads"

urlpatterns = [
    path("", views.home, name="home"),
    path("create/", views.create, name="create"),
    path("delete/<int:pk>/", views.delete_ad, name="delete"),
]
