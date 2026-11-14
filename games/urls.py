from django.urls import path
from . import views

app_name = "games"

urlpatterns = [
    path("", views.home, name="home"),
    path("snake/", views.snake, name="snake"),
    path("magnet/", views.magnet, name="magnet"),
    path("tetris/", views.tetris, name="tetris"),
    path("hok/", views.hok, name="hok"),
]
