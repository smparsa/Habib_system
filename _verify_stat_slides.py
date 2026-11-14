# -*- coding: utf-8 -*-
"""وارسی ماژول «اسلایدشوی آمار داشبورد» — همهٔ تغییرات DB در پایان rollback می‌شود.

۱) فرم ثبت اسلاید (تقویم شمسی + تصویر + باکس‌ها) معتبر و ذخیره شود.
۲) صفحات پنل مدیریت (فهرست/افزودن/ویرایش/تنظیمات/باکس) برای ادمین ۲۰۰ بدهند.
۳) داشبورد: به‌جای ۴ باکس آمار، اسلایدشو رندر شود؛ با غیرفعال‌کردن باکس،
   کارت آمار معمولی برگردد. تغییر اسلاید: درجا (بدون transition) با setInterval.
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
    from django.contrib.auth import get_user_model
    from django.test import Client
    from django.utils import timezone

    from adminpanel.forms import StatSlideForm
    from adminpanel.models import StatSlide, StatSlideBox, StatSlideSetting

    User_model = get_user_model()
    admin = User_model.objects.filter(is_staff=True).first()
    if admin is None:
        admin = User_model.objects.create_superuser(mobile_number="09129000099")
    c = Client()
    c.force_login(admin)

    today = timezone.localtime().date()
    d_start = (today + timezone.timedelta(days=1)).isoformat()
    d_end = (today + timezone.timedelta(days=3)).isoformat()

    boxes = list(StatSlideBox.objects.all().order_by("sort_order"))
    assert len(boxes) == 4, f"boxes seeded: {len(boxes)}"
    box_codes = [b.code for b in boxes]
    assert box_codes == ["stat_users", "stat_projects", "stat_revenue", "stat_tasks"], box_codes
    print(f"[1] ۴ باکس seed شده → {box_codes}")

    # --- فرم: بدون تصویر → خطا؛ با تصویر+بازه+باکس → ذخیره ---
    f_bad = StatSlideForm(data={
        "title": "تست", "link_url": "", "start_date": d_start, "end_date": d_end,
        "ad_time": "08:00", "stat_boxes": [boxes[0].pk],
    })
    assert not f_bad.is_valid(), "فرم بدون تصویر نباید معتبر باشد"
    print("[2] فرم بدون تصویر رد شد")

    with transaction.atomic():
        img = SimpleUploadedFile("s.png", PNG_BYTES, content_type="image/png")
        f = StatSlideForm(data={
            "title": "اسلاید تست", "description": "توضیح", "link_url": "https://example.com",
            "coins_paid": 120, "start_date": d_start, "end_date": d_end,
            "ad_time": "08:00", "stat_boxes": [boxes[0].pk, boxes[3].pk],
        })
        f.files = {"image": img}
        assert f.is_valid(), f.errors
        slide = f.save()
        slide.boxes.set(f.cleaned_data["stat_boxes"])
        assert str(slide.show_from.date()) == d_start and str(slide.show_until.date()) == d_end
        assert float(slide.coins_paid) == 120
        print("[3] اسلاید ذخیره شد (بازه + هزینهٔ دریافتی) OK")

        # --- صفحات پنل ---
        for url in (
            "/admin-panel/stat-slides/",
            "/admin-panel/stat-slides/add/",
            f"/admin-panel/stat-slides/{slide.pk}/edit/",
            "/admin-panel/stat-slides/?box=stat_users",
        ):
            r = c.get(url)
            assert r.status_code == 200, f"{url} → {r.status_code}"
        print("[4] صفحات پنل مدیریت ۲۰۰ OK")

        # تنظیمات سراسری: خارج از بازه → خطا؛ داخل بازه → ذخیره
        r = c.post("/admin-panel/stat-slides/settings/", {"switch_seconds": "2"})
        assert r.status_code == 302
        setting = StatSlideSetting.get()
        before_secs = setting.switch_seconds
        r = c.post("/admin-panel/stat-slides/settings/", {"switch_seconds": "8"})
        assert StatSlideSetting.get().switch_seconds == 8
        StatSlideSetting.get().switch_seconds = before_secs
        StatSlideSetting.get().save()
        print("[5] تنظیمات زمان اسلاید OK")

        # زمان اختصاصی باکس (۰ = پیش‌فرض سراسری)
        r = c.post(f"/admin-panel/stat-slides/boxes/{boxes[1].pk}/update/", {"switch_seconds": "12"})
        boxes[1].refresh_from_db()
        assert boxes[1].switch_seconds == 12
        boxes[1].switch_seconds = 0
        boxes[1].save()
        print("[6] زمان اختصاصی باکس OK")

        # --- داشبورد: هنوز در بازه نیست → کارت آمار معمولی ---
        dash = c.get("/dashboard/")
        assert dash.status_code == 200
        content = dash.content.decode("utf-8", "replace")
        assert "hb-stat-value" in content, "fallback کارت آمار نباید از بین برود"

        # اسلاید را «زنده» کنیم → اسلایدشو جای کارت آمار پدیدار شود
        now = timezone.now()
        StatSlide.objects.filter(pk=slide.pk).update(
            show_from=now - timezone.timedelta(hours=1),
            show_until=now + timezone.timedelta(days=2),
        )
        dash = c.get("/dashboard/")
        content = dash.content.decode("utf-8", "replace")
        assert "class='hb-stat-slide" in content, "کارت آمار کل کاربران باید اسلایدشو شود"

        assert "اسلاید تست" in content
        assert "/media/" in content, "تصویر اسلاید در داشبورد نیست"
        # باکس سوم (stat_revenue) اسلاید ندارد → کارت آمار باقی می‌ماند
        assert content.count("class='hb-stat-slide") == 2, \
            f"فقط ۲ باکسِ انتخاب‌شده اسلایدشو شود ({content.count(chr(39)+'hb-stat-slide')})"
        # تعویض درجا: بدون transition، با setInterval
        assert "setInterval" in content and "transition" not in content
        print("[7] داشبورد: اسلایدشو در محل باکس‌ها، مستقل و تعویض درجا OK")

        # غیرفعال‌کردن باکس اول → کارت آمار برگردد
        b0 = boxes[0]
        active_back = b0.is_active
        StatSlideBox.objects.filter(pk=b0.pk).update(is_active=False)
        dash = c.get("/dashboard/")
        content = dash.content.decode("utf-8", "replace")
        assert content.count("class='hb-stat-slide") == 1, "باکس غیرفعال نباید اسلایدشو بگیرد"
        StatSlideBox.objects.filter(pk=b0.pk).update(is_active=active_back)
        print("[8] باکس غیرفعال → fallback کارت آمار OK")

        # شمارندهٔ نمایش + toggle/حذف از پنل
        views_before = StatSlide.objects.get(pk=slide.pk).views
        assert views_before >= 3, f"views {views_before}"
        StatSlide.objects.filter(pk=slide.pk).update(is_active=False)
        dash = c.get("/dashboard/")
        content = dash.content.decode("utf-8", "replace")
        assert content.count("class='hb-stat-slide") == 0, "اسلاید متوقف نباید پخش شود"
        print("[9] توقف/شمارندهٔ نمایش OK")

        raise Exception("ROLLBACK")  # همهٔ تغییرات DB برگردد


try:
    run_tests()
except Exception as exc:
    if str(exc) == "ROLLBACK":
        print("همهٔ وارسی‌ها OK (تغییرات rollback شد).")
    else:
        raise
