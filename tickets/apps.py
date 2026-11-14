from django.apps import AppConfig


class TicketsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tickets"
    verbose_name = "مرکز تیکت و ارتباطات"

    def ready(self):
        import tickets.signals  # noqa: F401
