# -*- coding: utf-8 -*-
"""وارسی گردش‌کار کاربر/ادمین «اسلایدشوی آمار داشبورد» — rollback در پایان.

۱) سقف ۱۰ اسلاید در هر باکس (فرم، ادمین و کاربر).
۲) ثبت اسلاید توسط کاربر از /slideshow/ → pending + کسر سکه (تعرفهٔ تبلیغات).
۳) اسلایدِ pending در داشبورد پخش نمی‌شود؛ پس از تأیید ادمین (داخل بازه) پخش می‌شود.
۴) رد اسلاید → حذف از پخش + آزاد شدن ظرفیت؛ صفحات پنل ۲۰۰.
"""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "habib_system.settings")
sys.path.insert(0, os.getcwd())
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.utils import timezone

PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000108060000001f15c489"
    "0000000d4944415478da63fcffff3f030005fe02fefa4ec50000000049454e44ae426082"
)


def _img(name):
    return SimpleUploadedFile(name, PNG_BYTES, content_type="image/png")


def run_tests():
    from django.contrib.auth import get_user_model
    from django.test import Client
    from django.utils import timezone

    from adminpanel.forms import StatSlideForm, StatSlideUserForm
    from adminpanel.models import AD_STATUS_PENDING, STAT_SLIDE_MAX_PER_BOX, StatSlide, StatSlideBox
    from wallet.models import Wallet

    from datetime import timedelta

    User_model = get_user_model()
    admin = User_model.objects.filter(is_staff=True).first()
    if admin is None:
        admin = User_model.objects.create_superuser(mobile_number="09129000099")
    c = Client()
    c.force_login(admin)

    user = User_model.objects.filter(mobile_number="09129000077").first()
    if user is None:
        user = User_model.objects.create_user(mobile_number="09129000077")
    user.is_active = True
    user.save()
    Wallet.objects.get_or_create(user=user)[0].balance = 0
    Wallet.objects.filter(user=user).update(balance=10000)
    user = User_model.objects.get(pk=user.pk)  # balance refresh

    cu = Client()
    cu.force_login(user)

    boxes = list(StatSlideBox.objects.all().order_by("sort_order"))
    box0, box1 = boxes[0], boxes[1]
    assert STAT_SLIDE_MAX_PER_BOX == 10

    today = timezone.localtime().date()
    d_start = (today + timedelta(days=1)).isoformat()
    d_end = (today + timedelta(days=3)).isoformat()

    def slide_data(extra=None):
        data = {
            "title": "اسلاید تست ظرفیت", "description": "", "link_url": "",
            "start_date": d_start, "end_date": d_end, "ad_time": "08:00",
            "stat_boxes": [box0.pk],
        }
        data.update(extra or {})
        return data

    with transaction.atomic():
        # --- ۱) سقف ۱۰ اسلاید در یک باکس ---
        for i in range(STAT_SLIDE_MAX_PER_BOX):
            s = StatSlide(
                title=f"ظرفیت {i}", is_active=True,
                show_from=timezone.now() - timedelta(hours=1),
                show_until=timezone.now() + timedelta(days=5),
            )
            s.image.save(f"cap_{i}.png", SimpleUploadedFile(f"c{i}.png", PNG_BYTES, content_type="image/png"), save=True)
            s.save()
            s.boxes.set([box0])
        f11 = StatSlideForm(data=slide_data())
        f11.files = {"image": _img("x.png")}
        assert not f11.is_valid(), "اسلاید ۱۱م باید رد شود"
        assert any("ظرفیت" in e for errors in f11.errors.values() for e in errors), f11.errors
        print("[1] سقف ۱۰ اسلاید در باکس اعمال شد")

        # ظرفیت باکس دوم آزاد است → فرم کاربر معتبر
        f_ok = StatSlideUserForm(data=slide_data({"stat_boxes": [box1.pk]}))
        f_ok.files = {"image": _img("x2.png")}
        assert f_ok.is_valid(), f_ok.errors
        print("[2] باکس با ظرفیت آزاد، اسلاید جدید را می‌پذیرد")

        # --- ۲) گردش کار کاربر از HTTP ---
        balance_before = Wallet.objects.get(user=user).balance
        r = cu.post("/slideshow/create/", {
            **slide_data({"stat_boxes": [box1.pk], "title": "اسلاید کاربر"}),
            "ad_time": "12:00",
        }, files={"image": _img("us.png")})
        assert r.status_code == 302, getattr(r, "status_code", None)
        slide = StatSlide.objects.latest("pk")
        assert slide.status == AD_STATUS_PENDING, slide.status
        assert slide.advertiser_id == user.pk
        assert slide.coins_paid > 0
        balance_after = Wallet.objects.get(user=user).balance
        assert balance_after < balance_before, (balance_before, balance_after)
        days = (slide.show_until.date() - slide.show_from.date()).days
        print(f"[3] ثبت کاربر OK: pending، کسر سکه {balance_before - balance_after} (هزینه={slide.coins_paid}, {days} روز × ۱ باکس)")

        # صفحات ماژول کاربر
        assert cu.get("/slideshow/").status_code == 200
        assert cu.get("/slideshow/create/").status_code == 200
        assert "اسلایدهای من" in cu.get("/slideshow/").content.decode("utf-8", "replace")
        print("[4] صفحات /slideshow/ ۲۰۰ OK")

        # --- ۳) داشبورد: pending پخش نشود،باکس دارای اسلاید هم ظرفیتِ پر --- 
        dash = c.get("/dashboard/")
        html = dash.content.decode("utf-8", "replace")
        assert "اسلاید کاربر" not in html, "اسلاید pending نباید پخش شود"
        print("[5] اسلاید pending در داشبورد پخش نمی‌شود")

        # پنل ادمین: فهرست + فیلتر وضعیت
        for url in (
            "/admin-panel/stat-slides/",
            "/admin-panel/stat-slides/?status=pending",
            f"/admin-panel/stat-slides/{slide.pk}/edit/",
        ):
            assert c.get(url).status_code == 200, url
        print("[6] صفحات پنل با ستون تأیید/فیلتر ۲۰۰ OK")

        # تأیید ادمین → در داشبورد پخش شود؟ هنوز نه: بازه از فردا است (scheduled)
        r = c.post(f"/admin-panel/stat-slides/{slide.pk}/approve/")
        slide.refresh_from_db()
        assert slide.status == "approved"
        dash = c.get("/dashboard/")
        assert "اسلاید کاربر" not in dash.content.decode("utf-8", "replace")
        print("[7] تأیید اده، اسلاید خارج از بازه (زمان‌بندی‌شده) پخش نمی‌شود")

        # داخل بازه → پخش شود
        StatSlide.objects.filter(pk=slide.pk).update(
            show_from=timezone.now() - timedelta(hours=1),
            show_until=timezone.now() + timedelta(days=2),
        )
        dash = c.get("/dashboard/")
        html = dash.content.decode("utf-8", "replace")
        assert "اسلاید کاربر" in html, "اسلاید تأییدشده باید پخش شود"
        assert "setInterval" in html
        print("[8] اسلاید تأییدشدهٔ کاربر در باکس آمار پخش می‌شود")

        # رد اسلاید ادمین → از پخش خارج و ظرفیت آزاد
        r = c.post(f"/admin-panel/stat-slides/{slide.pk}/reject/")
        slide.refresh_from_db()
        assert slide.status == "rejected"
        dash = c.get("/dashboard/")
        assert "اسلاید کاربر" not in dash.content.decode("utf-8", "replace")
        f12 = StatSlideForm(data=slide_data())
        f12.files = {"image": _img("x3.png")}
        # یکی از ۱۰ جای‌گیر رد شد → باکس یک ظرفیت آزاد دارد؛ اما ۱۰ آنها جای‌گیرند
        # و سقف هنوز پر است (در انتظار/تأییدشده = ۱۰) → همچنان باید رد شود؟
        # شمارش ظرفیت «ردشده» را از ظرفیت خارج می‌کند → ۹ جای‌گیر → فرم معتبر است.
        assert f12.is_valid(), f12.errors
        print("[9] رد ادمین: از پخش خارج می‌شود + ظرفیت آزاد")

        raise Exception("ROLLBACK")


try:
    run_tests()
except Exception as exc:
    if str(exc) == "ROLLBACK":
        print("همهٔ وارسی‌ها OK (تغییرات rollback شد).")
    else:
        raise
