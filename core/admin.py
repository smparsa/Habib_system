from django.contrib import admin

from .models import InfoPage, SiteFeedback


@admin.register(InfoPage)
class InfoPageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_active", "show_in_sidebar", "show_in_footer", "sort_order", "updated_at")
    list_editable = ("is_active", "show_in_sidebar", "show_in_footer", "sort_order")
    list_filter = ("is_active", "show_in_sidebar", "show_in_footer")
    prepopulated_fields = {}
    fieldsets = (
        ("صفحه", {"fields": ("slug", "title", "subtitle", "icon")}),
        ("محتوا", {"fields": ("content",)}),
        ("نمایش", {"fields": ("is_active", "show_in_sidebar", "show_in_footer", "sort_order")}),
        (
            "اطلاعات تماس (فقط صفحهٔ تماس با ما)",
            {"fields": ("contact_phone", "contact_email", "contact_hours", "contact_address")},
        ),
    )


@admin.register(SiteFeedback)
class SiteFeedbackAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "satisfaction", "quality", "support_speed", "recommend")
    list_filter = ("satisfaction", "quality", "support_speed", "recommend")
    readonly_fields = ("created_at", "user")
    search_fields = ("improvements", "user__mobile_number")
