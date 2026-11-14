from django.contrib import admin

from .models import (
    Account,
    AccountingOrg,
    AccountingSession,
    AccountingUser,
    AuditLog,
    Cheque,
    FiscalYear,
    JournalEntry,
    LoginAttempt,
    TransactionLine,
)


class TransactionLineInline(admin.TabularInline):
    model = TransactionLine
    extra = 0


@admin.register(AccountingOrg)
class AccountingOrgAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name", "owner__mobile_number")


@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ("name", "org", "jalali_year", "start_date", "end_date", "is_closed", "is_default")
    list_filter = ("is_closed", "is_default", "jalali_year")
    search_fields = ("name", "org__name")


@admin.register(AccountingUser)
class AccountingUserAdmin(admin.ModelAdmin):
    list_display = ("username", "org", "full_name", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("username", "full_name")


@admin.register(AccountingSession)
class AccountingSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "fiscal_year", "created_at", "expires_at", "is_active")
    list_filter = ("is_active",)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "fiscal_year", "level", "group", "parent", "is_leaf", "is_active")
    list_filter = ("fiscal_year", "group", "level", "is_active")
    search_fields = ("code", "name")
    ordering = ("fiscal_year", "code")


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ("number", "fiscal_year", "date", "status", "total_debit", "total_credit", "created_at")
    list_filter = ("status", "fiscal_year")
    inlines = [TransactionLineInline]


@admin.register(Cheque)
class ChequeAdmin(admin.ModelAdmin):
    list_display = ("number", "fiscal_year", "direction", "amount", "due_date", "status", "party_name")
    list_filter = ("direction", "status", "fiscal_year")
    search_fields = ("number", "sayad_id", "party_name")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "org", "user", "action", "object_repr")
    list_filter = ("action",)
    readonly_fields = [f.name for f in AuditLog._meta.fields]


admin.site.register(LoginAttempt)
