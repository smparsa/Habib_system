from django.contrib import admin

from .models import BackupFile, BackupSetting


@admin.register(BackupSetting)
class BackupSettingAdmin(admin.ModelAdmin):
    list_display = ["auto_enabled", "interval_minutes", "keep_count", "sync_folder", "stale_after_days", "last_auto_at", "updated_at"]


@admin.register(BackupFile)
class BackupFileAdmin(admin.ModelAdmin):
    list_display = ["filename", "title", "kind", "status", "size_bytes", "created_by", "created_at"]
    list_filter = ["kind", "status"]
    search_fields = ["filename", "title", "note"]
    readonly_fields = ["filename", "kind", "status", "size_bytes", "created_by", "created_at", "error"]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False
