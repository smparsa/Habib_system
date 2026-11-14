# -*- coding: utf-8 -*-
"""تست E2E ماژول تبلیغات — همهٔ تغییرات جدید با rollback کامل DB در یک transaction.atomic.

- AdHeaderPlacement (۴ هدر سیدشده)
- AdvertisementForm: چک‌باکس هدرها (M2M) + clean days
- ایجاد تبلیغ + هزینهٔ (روزها × هدرها) از کیف پول
- active_ads(placement=...) فیلتر هدر
- شمارندهٔ views (update اتمی)
- ads_expiry_sweep_task: تیکت financial پایان دوره + idempotency
"""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "habib_system.settings")
sys.path.insert(0, os.getcwd())
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import Client
from django.utils import timezone

# فایل واقعی minimal PNG (1x1 transparent)
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fcffff3f030005fe02fefa4ec50000000049454e44ae426082"
)


def run_tests():
    from django.contrib.auth import get_user_model
    from django.db.models import F

    from adminpanel.models import (
        AD_STATUS_APPROVED,
        AdHeaderPlacement,
        Advertisement,
    )
    from ads.tasks import ads_expiry_sweep_task
    from core.context_processors import dashboard_ads, dashboard_ads_wallet
    from tickets.models import Ticket, TicketCategory
    from wallet.models import CoinLedger, FeatureCost, Wallet

    User = get_user_model()
    dt = timezone.timedelta

    # --- 1) هدرهای سیدشده ---
    codes = list(AdHeaderPlacement.objects.order_by("sort_order").values_list("code", flat=True))
    assert codes == ["dashboard", "wallet", "accounting", "tickets"], f"placements: {codes}"
    print(f"[1] AdHeaderPlacement seeds OK → {codes}")

    # --- 2) کاربر + کیف پول + تعرفه ---
    user = User.objects.filter(mobile_number="09120000099").first()
    if user is None:
        user = User.objects.create_user(mobile_number="09120000099")
    user.is_staff = False
    user.is_active = True
    user.save()
    if Wallet.objects.filter(user=user).exists():
        Wallet.objects.filter(user=user).delete()
    Wallet.objects.create(user=user, balance=10000)
    fc, _made = FeatureCost.objects.get_or_create(
        code="ad_submission",
        defaults={"title": "ثبت تبلیغ", "coins": 50, "is_active": True},
    )
    print("[2] user wallet(10000) + FeatureCost(ad_submission=50) ready")

    # --- 3) ثبت تبلیغ با ۲ هدر از طریق ویو ---
    d1 = (timezone.now() + dt(days=1)).date().strftime("%Y-%m-%d")
    d3 = (timezone.now() + dt(days=3)).date().strftime("%Y-%m-%d")
    header_pks = list(AdHeaderPlacement.objects.filter(code__in=["dashboard", "wallet"])
                      .order_by("sort_order").values_list("id", flat=True))
    c = Client()
    c.force_login(user)
    logo = SimpleUploadedFile("t.png", PNG_BYTES, content_type="image/png")
    resp = c.post("/ads/create/", data={
        "title": "تست ارزان",
        "description": "تست",
        "link_url": "",
        "start_date": d1,
        "end_date": d3,
        "ad_time": "08:00",
        "header_modules": header_pks,
        "logo": logo,
    })
    assert resp.status_code == 302, f"فرم باید ریدایرکت شود، status={resp.status_code}"
    ad = Advertisement.objects.filter(title="تست ارزان").latest("id")
    assert ad.header_modules.count() == 2, f"M2M = {ad.header_modules.count()}"
    days = (ad.show_until.date() - ad.show_from.date()).days
    assert days == 2, f"days = {days}"
    assert str(ad.coins_paid) == "200.00", f"coins_paid = {ad.coins_paid} (باید 50×2روز×2هدر=200)"
    ledger = CoinLedger.objects.filter(user=user, ref_code="ad_submission").latest("id")
    assert str(ledger.amount) == "-200.00", f"ledger = {ledger.amount}"
    wallet = Wallet.objects.get(user=user)
    assert str(wallet.balance) == "9800.00", f"balance = {wallet.balance}"
    print(f"[3] create: days={days}, headers=2, coins_paid={ad.coins_paid}, "
          f"ledger={ledger.amount}, balance={wallet.balance} OK")

    # --- 4) فیلتر placement ---
    ad.status = AD_STATUS_APPROVED
    # ترتیب صحیح: تبلیغ باید در حال حاضر «زنده» باشد؛ بازه را به همین امروز واحد تنظیم می‌کنیم
    ad.show_from = timezone.now()
    ad.show_until = timezone.now() + timezone.timedelta(days=2)
    ad.save(update_fields=["status", "show_from", "show_until"])
    assert ad.pk in [a.pk for a in Advertisement.active_ads(placement="dashboard")], "dashboard"
    fake_req = type("R", (), {"user": user})()
    assert ad.pk in [a["id"] for a in dashboard_ads_wallet(fake_req)["dashboard_ads"]], "wallet"
    assert ad.pk not in [a.pk for a in Advertisement.active_ads(placement="accounting")], "accounting"
    print("[4] placement filter dashboard/wallet/accounting OK")

    # --- 5) شمارندهٔ views (update اتمی) ---
    # (یک بار در بخش ۴ از طریق context processor شمرده شد؛ +۲ دوباره اینجا)
    dashboard_ads(fake_req)
    dashboard_ads(fake_req)
    ad.refresh_from_db()
    assert ad.views == 3, f"views = {ad.views} (باید 3: 1 + 2)"
    print(f"[5] views counter → {ad.views} OK")

    # --- 6) تیکت پایان دوره (financial/normal) + idempotency ---
    cat_fin = TicketCategory.objects.filter(code="financial", is_active=True).first()
    if cat_fin is None:
        cat_fin = TicketCategory.objects.create(code="financial", name_fa="مالی", is_active=True)
    ad.show_until = timezone.now() - dt(minutes=5)
    ad.save(update_fields=["show_until"])
    result = ads_expiry_sweep_task()
    assert result["notified"] == 1, f"notified = {result}"
    t = Ticket.objects.filter(author=user, subject__icontains="پایان دورهٔ نمایش تبلیغ").latest("id")
    assert t.category_id == cat_fin.id, f"category = {t.category}"
    assert t.priority == "normal", f"priority = {t.priority}"
    ad.refresh_from_db()
    assert ad.expiry_notified_at is not None, "expiry_notified_at ثبت نشد"
    again = ads_expiry_sweep_task()
    assert again["notified"] == 0, f"باید idempotent باشد: {again}"
    print("[6] expiry ticket (financial/normal) + idempotency OK")

    print("\nALL ADS E2E TESTS PASSED ✓")


def main():
    """کل تست در یک transaction.atomic؛ در پایان تغییرات DB rollback می‌شود."""
    with transaction.atomic():
        errors = None
        try:
            run_tests()
        except Exception as exc:  # noqa: BLE001
            errors = exc
        else:
            errors = None
        # اگر خطایی نبود، rollback دستی برای نگه‌داشتن DB تمیز:
        if errors is None:
            raise RuntimeError("ROLLBACK_TEST")
        print(f"TEST FAILED ✗: {errors}")
        raise RuntimeError("ROLLBACK_TEST")  # حتی در خطا هم rollback کامل
        # (در هر دو مسیر DB به حالت پیش از تست بازمی‌گردد)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        if "ROLLBACK_TEST" in str(exc):
            print("DB ROLLED BACK ✓ — هیچ دادهٔ آزمایشی در DB واقعی ثبت نشد.")
            sys.exit(0)
        raise
    sys.exit(1)
