from django.urls import path
from . import views

app_name = 'calendar_converter'

urlpatterns = [
    path('', views.calendar_converter_view, name='converter'),
    path('ajax/convert/', views.ajax_convert_date, name='ajax_convert'),
    path('grid/', views.calendar_grid_view, name='calendar_grid'),
    path('api/convert/', views.api_convert_date, name='api_convert'),
    path('api/server-time/', views.api_server_time, name='api_server_time'),
]