from django.urls import path

from . import views

app_name = "magazine"

urlpatterns = [
    path("", views.magazine_list, name="list"),
    path("react/", views.react, name="react"),
    path("watch/start/", views.watch_start, name="watch_start"),
    path("watch/award/", views.watch_award, name="watch_award"),
    path("forward/", views.forward, name="forward"),
    path("inbox/", views.inbox, name="inbox"),
    path("tickets/read-all/", views.tickets_read_all, name="tickets_read_all"),
    path("ticket/<int:ticket_id>/open/", views.ticket_open, name="ticket_open"),
]
