"""بررسی سرتاسری ماژول «کاربران و پروفایل‌ها» — همهٔ نوشته‌ها rollback می‌شوند."""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "habib_system.settings")
django.setup()

from django.db import transaction
from django.forms import model_to_dict
from django.test import Client
from django.urls import reverse

from accounts.models import FamilynameTbl, FirstnameTbl, Job, Profile, User
from adminpanel.forms import ADMIN_PROFILE_SECTIONS

PASSED = []


def ok(name):
    PASSED.append(name)
    print("OK  ", name)


with transaction.atomic():
    transaction.set_rollback(True)

    # ---- دادهٔ آزمایشی (ایزوله) ----
    fn, _ = FirstnameTbl.objects.get_or_create(
        first_name_fa="علی", defaults={"first_name_en": "Ali"}
    )
    ln, _ = FamilynameTbl.objects.get_or_create(
        familyname_fa="محمدی", defaults={"familyname_en": "Mohammadi"}
    )

    admin = User.objects.create_user("09120000088")
    admin.is_staff = True
    admin.is_active = True
    admin.save(update_fields=["is_staff", "is_active"])
    admin.profile.first_name = fn
    admin.profile.last_name = ln
    admin.profile.save()

    bob = User.objects.create_user("09120000099")
    bob.profile.first_name = fn
    bob.profile.last_name = ln
    bob.profile.city = "قم"
    bob.profile.save()
    Job.objects.create(profile=bob.profile, title="کارشناس فنی", organization="شرکت نمونه")

    # ---- دسترسی ----
    anon = Client()
    r = anon.get(reverse("adminpanel:users_list"))
    assert r.status_code in (301, 302), r.status_code
    ok("دسترسی ناشناس به فهرست کاربران مسدود است")

    c = Client()
    c.force_login(admin)

    # ---- فهرست / جستجو / فیلتر ----
    r = c.get(reverse("adminpanel:users_list"))
    assert r.status_code == 200 and "فهرست کاربران" in r.content.decode("utf-8")
    ok("فهرست کاربران برای ادمین 200")

    r = c.get(reverse("adminpanel:users_list"), {"q": "محمدی"})
    body = r.content.decode("utf-8")
    assert "09120000099" in body and "فهرست کاربران (1 نفر)" in body
    ok("جستجو با نام خانوادگی")

    r = c.get(reverse("adminpanel:users_list"), {"q": "00099"})
    assert "09120000099" in r.content.decode("utf-8")
    ok("جستجو با بخشی از موبایل")

    r = c.get(reverse("adminpanel:users_list"), {"role": "admin"})
    body = r.content.decode("utf-8")
    assert "09120000088" in body and "09120000099" not in body
    ok("فیلتر نقش=ادمین")

    r = c.get(reverse("adminpanel:users_list"), {"state": "inactive"})
    assert "کاربری یافت نشد" in r.content.decode("utf-8")
    ok("فیلتر وضعیت=غیرفعال")

    # ---- ویرایش پروفایل ----
    edit_url = reverse("adminpanel:user_edit", args=[bob.pk])
    r = c.get(edit_url)
    assert r.status_code == 200
    body = r.content.decode("utf-8")
    for s in ("اطلاعات فردی", "تماس و موقعیت مکانی", "تحصیلات", "ذخیرهٔ پروفایل"):
        assert s in body, s
    assert "کارشناس فنی" in body and "شرکت نمونه" in body  # کارت مشاغل ثبت‌شده
    ok("صفحهٔ ویرایش: فرم پروفایل بخش‌بندی‌شده + مشاغل ثبت‌شده")

    fields = [f for sec in ADMIN_PROFILE_SECTIONS for f in sec["fields"]]
    data = model_to_dict(bob.profile, fields=fields)
    data.update(
        {
            "submit": "profile",
            "next": reverse("adminpanel:users_list") + "?q=x",
            "city": "تهران",
            "bio": "توضیح ویرایش‌شده توسط ادمین",
        }
    )
    r = c.post(edit_url, data)
    assert r.status_code in (301, 302), r.status_code
    assert r.url.startswith(reverse("adminpanel:users_list")), r.url
    bob.refresh_from_db()
    assert bob.profile.city == "تهران" and bob.profile.bio == "توضیح ویرایش‌شده توسط ادمین"
    ok("ذخیرهٔ پروفایل و بازگشت به فهرست با حفظ فیلتر")

    # ---- ویرایش حساب کاربری ----
    data = {
        "submit": "account",
        "next": reverse("adminpanel:users_list"),
        "mobile_number": bob.mobile_number,
        "is_active": "on",
        "is_staff": "on",
        "is_superuser": "on",
    }
    r = c.post(edit_url, data)
    assert r.status_code in (301, 302), r.status_code
    bob.refresh_from_db()
    assert bob.is_staff and bob.is_superuser and bob.is_active
    ok("ارتقای نقش کاربر به ادمین/سوپریوزر")

    # موبایل تکراری رد شود
    data["mobile_number"] = admin.mobile_number
    r = c.post(edit_url, data)
    assert r.status_code == 200
    assert "این شماره موبایل قبلاً برای کاربر دیگری ثبت شده است" in r.content.decode("utf-8")
    ok("موبایل تکراری با پیام فارسی رد می‌شود")

    # موبایل معتبر جدید
    data["mobile_number"] = "09120000077"
    r = c.post(edit_url, data)
    bob.refresh_from_db()
    assert bob.mobile_number == "09120000077"
    ok("تغییر شماره موبایل کاربر")

    # ---- محافظت از حساب خودِ ادمین ----
    self_url = reverse("adminpanel:user_edit", args=[admin.pk])
    r = c.get(self_url)
    body = r.content.decode("utf-8")
    assert "تغییر وضعیت فعال/ادمین/سوپریوزر حسابِ خودتان" in body
    r = c.post(
        self_url,
        {
            "submit": "account",
            "next": reverse("adminpanel:users_list"),
            "mobile_number": admin.mobile_number,
            "is_active": "",  # تلاش برای غیرفعال‌کردن خودش
            "is_staff": "",
        },
    )
    admin.refresh_from_db()
    assert admin.is_active and admin.is_staff
    ok("تغییر دسترسی حسابِ خودِ ادمین ممکن نیست")

    # ---- فعال/غیرفعال‌کردن ----
    toggle_url = reverse("adminpanel:user_toggle", args=[bob.pk])
    r = c.post(toggle_url, {"next": reverse("adminpanel:users_list") + "?q=77"})
    assert r.status_code in (301, 302)
    assert r.url == reverse("adminpanel:users_list") + "?q=77"
    bob.refresh_from_db()
    assert not bob.is_active
    ok("غیرفعال‌کردن حساب و بازگشت با حفظ فیلتر")

    r = c.post(toggle_url)
    bob.refresh_from_db()
    assert bob.is_active
    ok("فعال‌کردن دوبارهٔ حساب")

    # خودِ ادمین قابل تغییر نیست
    r = c.post(reverse("adminpanel:user_toggle", args=[admin.pk]))
    admin.refresh_from_db()
    assert admin.is_active
    ok("غیرفعال‌کردن خودِ ادمین مسدود است")

    # ---- صفحه‌بندی و صفحه‌های نامعتبر ----
    for extra in ({"page": "1"}, {"page": "999"}, {"state": "active", "role": "member"}):
        r = c.get(reverse("adminpanel:users_list"), extra)
        assert r.status_code == 200
    ok("صفحه‌بندی/فیلترهای ترکیبی بدون خطا")

    r = c.get(reverse("adminpanel:user_edit", args=[999999]))
    assert r.status_code == 404
    ok("کاربر ناموجود → 404")

    # ---- داشبورد: کارت ماژول و آمار ----
    r = c.get(reverse("adminpanel:dashboard"))
    body = r.content.decode("utf-8")
    assert 'data-href="' + reverse("adminpanel:users_list") + '"' in body
    assert "کاربران" in body
    ok("داشبورد: کارت ماژول کاربران فعال + آمار")

print(f"\n{len(PASSED)}/{len(PASSED)} checks passed — همهٔ تغییرات دیتابیس rollback شد.")
