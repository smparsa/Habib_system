from django.contrib import admin

from .models import (
    CoinLedger,
    CoinOrder,
    CoinPriceHistory,
    CoinTransfer,
    FeatureCost,
    Wallet,
    WalletSetting,
)


@admin.register(WalletSetting)
class WalletSettingAdmin(admin.ModelAdmin):
    list_display = ("coin_value_rial", "buy_enabled", "sell_enabled",
                    "transfer_enabled", "bank_name", "updated_at")


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "updated_at")
    search_fields = ("user__mobile_number",)


@admin.register(CoinLedger)
class CoinLedgerAdmin(admin.ModelAdmin):
    # دفتر کل فقط-خواندنی است تا یکپارچگی مالی حفظ شود
    list_display = ("user", "kind", "amount", "balance_after", "ref_code", "created_at")
    list_filter = ("kind",)
    search_fields = ("user__mobile_number", "ref_code")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CoinOrder)
class CoinOrderAdmin(admin.ModelAdmin):
    list_display = ("code", "user", "kind", "coins", "total_rial", "status", "created_at")
    list_filter = ("kind", "status")
    search_fields = ("code", "user__mobile_number")


@admin.register(CoinTransfer)
class CoinTransferAdmin(admin.ModelAdmin):
    list_display = ("code", "sender", "receiver", "coins", "created_at")
    search_fields = ("code", "sender__mobile_number", "receiver__mobile_number")


@admin.register(FeatureCost)
class FeatureCostAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "coins", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("code", "title")


@admin.register(CoinPriceHistory)
class CoinPriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("value_rial", "changed_by", "note", "created_at")