# تبدیل یک‌بارهٔ امتیازهای قبلی همهٔ کاربران به سکه (طبق «تعرفه امتیازها»).
#
# نرخ تبدیل از «ارزش هر سکه (امتیاز)» (WalletSetting.coin_value_point) خوانده
# می‌شود: coins = امتیازهای تبدیل‌نشده ÷ نرخ. نقطهٔ آبخست تبدیل در
# profile.extra_data["points_converted"] ثبت می‌گردد تا هر امتیاز فقط یک‌بار
# تبدیل شود و از این پس امتیازهای جدید نیز هنگام award() به‌صورت خودکار
# (wallet.services.convert_unconverted_points) به کیف پول تجمیع شوند.
# امتیازِ سطح کاربری (user_score) دست‌نخورده می‌ماند.

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import migrations

CONVERT_NOTE = "تبدیل امتیاز به سکه (تعرفه)"


def convert_forwards(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    Wallet = apps.get_model("wallet", "Wallet")
    WalletSetting = apps.get_model("wallet", "WalletSetting")
    CoinLedger = apps.get_model("wallet", "CoinLedger")

    setting = WalletSetting.objects.order_by("pk").first()
    rate = int(getattr(setting, "coin_value_point", 0) or 0) if setting else 0
    if rate <= 0:
        return

    for profile in Profile.objects.select_related("user").iterator():
        score = int(profile.user_score or 0)
        data = dict(profile.extra_data or {})
        converted = int(data.get("points_converted") or 0)
        delta = score - converted
        if delta <= 0:
            continue
        try:
            coins = (Decimal(delta) / Decimal(rate)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        except (InvalidOperation, OverflowError):
            continue
        if coins <= 0:
            continue
        wallet, _created = Wallet.objects.get_or_create(user=profile.user)
        wallet.balance = (wallet.balance or Decimal("0")) + coins
        wallet.save(update_fields=["balance", "updated_at"])
        CoinLedger.objects.create(
            user=profile.user,
            kind="reward",
            amount=coins,
            balance_after=wallet.balance,
            ref_code="PTS",
            note=CONVERT_NOTE,
        )
        data["points_converted"] = score
        profile.extra_data = data
        profile.save(update_fields=["extra_data", "updated_at"])


def convert_backwards(apps, schema_editor):
    """بازگشت: رکوردهای «تبدیل امتیاز» حذف و همان مبلغ از کیف پول‌ها کم می‌شود."""
    Profile = apps.get_model("accounts", "Profile")
    Wallet = apps.get_model("wallet", "Wallet")
    CoinLedger = apps.get_model("wallet", "CoinLedger")

    rows = CoinLedger.objects.filter(ref_code="PTS", note=CONVERT_NOTE)
    totals = {}
    for row in rows:
        totals[row.user_id] = totals.get(row.user_id, Decimal("0")) + row.amount
    for user_id, total in totals.items():
        wallet = Wallet.objects.filter(user_id=user_id).first()
        if wallet is not None:
            wallet.balance = (wallet.balance or Decimal("0")) - total
            wallet.save(update_fields=["balance", "updated_at"])
    rows.delete()
    for profile in Profile.objects.iterator():
        data = dict(profile.extra_data or {})
        if "points_converted" in data:
            data.pop("points_converted")
            profile.extra_data = data
            profile.save(update_fields=["extra_data", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("wallet", "0013_alter_rewardrule_options_and_more"),
        ("accounts", "0050_job_catalog_keyword_labels"),
    ]

    operations = [
        migrations.RunPython(convert_forwards, convert_backwards),
    ]
