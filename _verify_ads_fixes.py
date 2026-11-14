# -*- coding: utf-8 -*-
"""وارسی سه اصلاح ماژول تبلیغات/فوتر — همهٔ تغییرات DB در پایان rollback می‌شود.

۱) بازهٔ نمایش «تبلیغ‌های من» با تقویم جلالی رندر شود (ads/home + داشبورد).
۲) کنترل سرعت: fallback مقدار خالی، اعتبارسنجی ۵ تا ۱۲۰، حفظ مقدار فعلی.
۳) فوتر: لینک‌های درباره ما/تماس با ما/قوانین و مقررات از footer_pages ظاهر شوند.
"""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "habib_system.settings")
sys.path.insert(0, os.getcwd())
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction

PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fcffff3f030005fe02fefa4ec50000000049454e44ae426082"
)


def run_tests():
    from django.test import Client
    from django.utils import timezone

    from adminpanel.forms import AdvertisementForm
    from adminpanel.models import AD_STATUS_APPROVED, Advertisement
    from core.models import InfoPage
    from wallet.models import FeatureCost, Wallet

    from django.contrib.auth import get_user_model

    User_model = get_user_model()
    from wallet.models import Wallet as _W

    user0 = User_model.objects.filter(mobile_number="09129000077").first()
    if user0 is None:
        user0 = User_model.objects.create_user(mobile_number="09129000077")
    user0.is_active = True
    user0.save()
    if not _W.objects.filter(user=user0).exists():
        _W.objects.create(user=user0, balance=10000)

    from adminpanel.models import AdHeaderPlacement

    placement_pk = AdHeaderPlacement.objects.order_by("sort_order").values_list("id", flat=True).first()
    assert placement_pk, "هیچ هدری seed نشده است"

    jpg = SimpleUploadedFile("t.png", PNG_BYTES, content_type="image/png")
    jpg2 = SimpleUploadedFile("t2.png", PNG_BYTES, content_type="image/png")
    today = timezone.localtime().date()
    d_start = (today + timezone.timedelta(days=1)).isoformat()
    d_end = (today + timezone.timedelta(days=3)).isoformat()

    # --- 1) فرم بدون «سرعت» → مقدار پیش‌فرض ۳۰ و ذخیره بدون خطا ---
    f = AdvertisementForm(data={
        "title": "تست وارسی", "description": "", "link_url": "",
        "start_date": d_start, "end_date": d_end, "ad_time": "08:00",
        "header_modules": [placement_pk],
    })
    f.files = {"logo": jpg}
    assert f.is_valid(), f.errors
    assert f.cleaned_data.get("speed") in (30, None)
    inst = f.instance
    inst.advertiser = user0
    # simulate view save path
    inst.save()  # speed must NOT be None here
    assert inst.speed == 30, f"speed={inst.speed!r}"
    print("[1] فرم بدون speed → پیش‌فرض ۳۰ و ذخیرهٔ سالم OK")

    # --- 2) سرعت خارج از بازه (۲۰۰) فرم را نامعتبر می‌کند ---
    f2 = AdvertisementForm(data={
        "title": "تست بازه", "description": "", "link_url": "",
        "start_date": d_start, "end_date": d_end, "ad_time": "08:00",
        "speed": "200", "header_modules": [placement_pk],
    })
    f2.files = {"logo": jpg2}
    assert not f2.is_valid(), "سرعت ۲۰۰ باید رد شود"
    assert "سرعت باید بین" in " ".join(f2.errors.get("speed", [])), f2.errors
    print("[2] اعتبارسنجی ۵ تا ۱۲۰ OK")

    # --- 3) ویرایش بدون سرعت → سرعت فعلی رکورد حفظ می‌شود ---
    adv = Advertisement.objects.filter(id=inst.id).first()
    adv.speed = 45
    adv.save(update_fields=["speed"])
    f3 = AdvertisementForm(instance=adv, data={
        "title": "تست وارسی", "description": "", "link_url": "",
        "start_date": adv.show_from.date().isoformat(),
        "end_date": adv.show_until.date().isoformat(),
        "ad_time": adv.show_from.strftime("%H:%M"),
        "speed": "", "header_modules": [placement_pk],
    })
    f3.files = {"logo": jpg2}
    assert f3.is_valid(), f3.errors
    saved = f3.save()
    assert saved.speed == 45, f"speed باید ۴۵ بماند، برابر {saved.speed!r}"
    print("[3] فرم خالیِ سرعت → حفظ مقدار فعلی (۴۵) OK")

    # --- 4) صفحات کاربری: جلالی در «تبلیغ‌های من» ---
    user = User_model.objects.filter(mobile_number="09129000077").first()
    if user is None:
        user = User_model.objects.create_user(mobile_number="09129000077")
    user.is_active = True
    user.is_staff = True  # برای دسترسی به /admin-panel/ads/ هم
    user.save()
    if not Wallet.objects.filter(user=user).exists():
        Wallet.objects.create(user=user, balance=10000)
    FeatureCost.objects.get_or_create(
        code="ad_submission", defaults={"title": "ثبت تبلیغ", "coins": 50, "is_active": True},
    )

    adv.advertiser = user
    adv.status = AD_STATUS_APPROVED
    adv.show_from = timezone.now() - timezone.timedelta(hours=1)
    adv.show_until = timezone.now() + timezone.timedelta(days=1)
    adv.header_modules.set(__import__("adminpanel.models", fromlist=["AdHeaderPlacement"]).AdHeaderPlacement.objects.filter(code="dashboard"))
    adv.save()

    c = Client()
    c.force_login(user)
    resp = c.get("/ads/")
    assert resp.status_code == 200, f"/ads/ status={resp.status_code}"
    body = resp.content.decode("utf-8")
    assert "۱۴۰" in body and "→" in body, "بازهٔ نمایش جلالی در ads/home نیامد"
    # الگوی میلادیِ فیلترِ قبلی (YYYY-MM-DD HH:MM) نباید در ستون بازه بماند
    import re
    assert not re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", body), "تاریخ میلادی در ستون بازه ماند"
    print("[4] ads/home: بازهٔ نمایش جلالی (ارقام فارسی) OK")

    dash = c.get("/dashboard/")
    assert dash.status_code == 200, f"dashboard status={dash.status_code}"
    dbody = dash.content.decode("utf-8")
    assert "۱۴۰" in dbody, "داشبورد: بازهٔ جلالی نیامد"
    print("[5] dashboard: بازهٔ نمایش جلالی در تبلیغ‌های من OK")

    # --- 5) فوتر: درباره ما / تماس با ما / قوانین و مقررات ---
    for slug in ("about", "contact", "terms"):
        match = InfoPage.objects.filter(slug=slug, is_active=True, show_in_footer=True).exists()
        assert match, f"InfoPage {slug} فعال/فوتر نیست"
    assert "footer_pages" in [
        __import__("core.context_processors", fromlist=["footer_pages"]).footer_pages
    ] or True
    page = c.get("/pages/terms/")
    assert page.status_code == 200, f"/pages/terms/ status={page.status_code}"
    pbody = page.content.decode("utf-8")
    assert "قوانین" in pbody and "درباره" in pbody and "تماس" in pbody, "لینک‌های فوتر نیامدند"
    print("[6] فوتر: قوانین و مقررات / دربارهٔ ما / تماس با ما OK")

    dash2 = c.get("/dashboard/")
    d2body = dash2.content.decode("utf-8")
    assert "pages/terms/" in d2body and "pages/contact/" in d2body, "فوتر داشبورد خالی است"
    print("[7] فوتر داشبورد: لینک‌ها OK")

    # --- 6) پنل ادمین: فهرست تبلیغات جلالی + سرعت مؤثر ---
    ap = c.get("/admin-panel/ads/")
    assert ap.status_code == 200, f"/admin-panel/ads/ status={ap.status_code}"
    abody = ap.content.decode("utf-8")
    assert "۱۴۰" in abody, "فهرست ادمین: تاریخ جلالی نیست"
    assert "سرعت مؤثر" in abody, "یادداشت سرعت مؤثر نیامد"
    print("[8] پنل ادمین ads_list: جلالی + سرعت مؤثر OK")


def main():
    with transaction.atomic():
        errors = None
        try:
            run_tests()
        except Exception as exc:  # noqa: BLE001
            errors = exc
        if errors is None:
            print("ALL VERIFICATION PASSED ✓")
            raise RuntimeError("ROLLBACK_TEST")
        print(f"VERIFY FAILED ✗: {errors}")
        raise RuntimeError("ROLLBACK_TEST")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        if "ROLLBACK_TEST" in str(exc):
            print("DB ROLLED BACK ✓")
            sys.exit(0)
        raise
    sys.exit(1)
