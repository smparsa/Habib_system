from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "api"

router = DefaultRouter()
router.register("tickets", views.TicketViewSet, basename="ticket")

urlpatterns = router.urls + [
    path("tickets/attachments/<int:pk>/", views.AttachmentViewSet.as_view(
        {"get": "retrieve"}), name="ticket-attachment"),
]
