from django.contrib import admin

from .models import (
    SensitiveTerm, Ticket, TicketAssignment, TicketAttachment, TicketAudience,
    TicketAuditLog, TicketCategory, TicketDepartment, TicketDepartmentMember,
    TicketMessage, TicketNotification, TicketPriorityHistory, TicketRating,
    TicketRecipient, TicketSLA, TicketStatusHistory, TicketTarget,
    TicketTargetRule, UserNotificationPreferences,
)


@admin.register(SensitiveTerm)
class SensitiveTermAdmin(admin.ModelAdmin):
    list_display = ("term", "mode", "category", "is_active", "note", "updated_at")
    list_filter = ("category", "mode", "is_active")
    search_fields = ("term", "note")


@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name_fa", "name_en", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(TicketAudience)
class TicketAudienceAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "is_active", "created_at", "updated_at")
    list_filter = ("kind", "is_active")
    search_fields = ("name", "description")


class TicketDepartmentMemberInline(admin.TabularInline):
    model = TicketDepartmentMember
    extra = 0


@admin.register(TicketDepartment)
class TicketDepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name_fa", "parent", "is_active")
    inlines = [TicketDepartmentMemberInline]


class TicketRecipientInline(admin.TabularInline):
    model = TicketRecipient
    extra = 0
    readonly_fields = ("user", "state", "is_author")


class TicketAssignmentInline(admin.TabularInline):
    model = TicketAssignment
    extra = 0
    readonly_fields = ("agent", "assigned_by", "kind", "assigned_at", "is_active")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("number", "subject", "author", "category", "priority",
                    "status", "department", "created_at")
    list_filter = ("status", "priority", "category", "department", "created_at")
    search_fields = ("number", "subject", "description", "author__mobile_number")
    date_hierarchy = "created_at"
    readonly_fields = ("number", "created_at", "updated_at")
    inlines = [TicketRecipientInline, TicketAssignmentInline]


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author", "kind", "created_at")
    list_filter = ("kind",)
    search_fields = ("ticket__number", "body")


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ("message", "name", "size", "mime", "created_at")


@admin.register(TicketAuditLog)
class TicketAuditLogAdmin(admin.ModelAdmin):
    """لاگ ضمیمه‌ناپذیر — فقط نمایش، بدون افزودن/حذف از UI."""

    list_display = ("created_at", "actor", "action", "object_type", "object_id", "ip")
    list_filter = ("action", "created_at")
    search_fields = ("actor__mobile_number", "object_type", "action")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(TicketRecipient)
admin.site.register(TicketStatusHistory)
admin.site.register(TicketPriorityHistory)
admin.site.register(TicketSLA)
admin.site.register(TicketRating)
admin.site.register(TicketTarget)
admin.site.register(TicketTargetRule)
admin.site.register(TicketNotification)
admin.site.register(UserNotificationPreferences)
admin.site.register(TicketDepartmentMember)
