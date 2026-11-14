# -*- coding: utf-8 -*-
"""تست زندهٔ جریان هشدار انقضا (۲ روز پایانی) تبلیغ و اسلاید + نشان‌های داشبورد."""
import os
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "habib_system.settings")
django.setup()

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from adminpanel.models import AD_STATUS_APPROVED, AdHeaderPlacement, Advertisement, StatSlide, StatSlideBox
from ads import tasks as ads_tasks
from slideshow import tasks as slide_tasks
from tickets.models import Ticket
from wallet import services as wservices
from wallet.models import CoinLedger

User = get_user_model()

# ---- پاک‌سازی بقایای اجرای قبلی تست (کاربر آزمایشی ۰۹۹۹...) ----
old_users = User.objects.filter(mobile_number__startswith="0999")
Ticket.objects.filter(author__in=old_users).delete()
Advertisement.objects.filter(advertiser__in=old_users).delete()
StatSlide.objects.filter(advertiser__in=old_users).delete()
CoinLedger.objects.filter(user__in=old_users).delete()
old_users.delete()

suffix = f"{timezone.now().timestamp():.0f}"[-6:]
u = User.objects.create_user(mobile_number=f"0999{suffix}", password="x")
with transaction.atomic():
    wservices._apply(u, Decimal(1000), CoinLedger.KIND_ADJUST, note="تست هشدار")

hdr = AdHeaderPlacement.objects.first()
box = StatSlideBox.objects.first()

now = timezone.now()
ad_exp = Advertisement.objects.create(
    advertiser=u, logo="ads/test.png", title="تب منقضی", show_from=now - timedelta(days=3),
    show_until=now - timedelta(hours=2), status=AD_STATUS_APPROVED,
)
ad_exp.header_modules.add(hdr)
ad_near = Advertisement.objects.create(
    advertiser=u, logo="ads/test.png", title="تب نزدیک", show_from=now - timedelta(days=3),
    show_until=now + timedelta(hours=20), status=AD_STATUS_APPROVED,
)
ad_near.header_modules.add(hdr)
sl_exp = StatSlide.objects.create(
    advertiser=u, image="slides/test.png", title="اسلاید منقضی", show_from=now - timedelta(days=3),
    show_until=now - timedelta(hours=2), status=AD_STATUS_APPROVED,
)
sl_exp.boxes.add(box)
sl_near = StatSlide.objects.create(
    advertiser=u, image="slides/test.png", title="اسلاید نزدیک", show_from=now - timedelta(days=3),
    show_until=now + timedelta(hours=20), status=AD_STATUS_APPROVED,
)
sl_near.boxes.add(box)

before = Ticket.objects.filter(author=u).count()
r1 = ads_tasks.ads_expiry_warning_task()
r2 = ads_tasks.ads_expiry_sweep_task()
r3 = slide_tasks.slideshow_expiry_warning_task()
r4 = slide_tasks.slideshow_expired_sweep_task()
print("task results:", r1, r2, r3, r4)

ad_exp.refresh_from_db(); ad_near.refresh_from_db()
sl_exp.refresh_from_db(); sl_near.refresh_from_db()
assert r1["warned"] >= 1 and r2["notified"] >= 1 and r3["warned"] >= 1 and r4["notified"] >= 1
assert ad_near.expiry_warning_notified_at is not None
assert ad_near.expiry_notified_at is None, "نزدیک‌انقضا نباید پایان‌دوره بگیرد"
assert ad_exp.expiry_notified_at is not None and ad_exp.expiry_warning_notified_at is None, "منقضی فقط تیکت پایان"
assert sl_near.expiry_warning_notified_at is not None and sl_near.expiry_notified_at is None
assert sl_exp.expiry_notified_at is not None

new_tickets = list(Ticket.objects.filter(author=u))
print("tickets sent:", [t.subject for t in new_tickets])
assert len(new_tickets) == 4, new_tickets
assert sum(1 for t in new_tickets if "۲ روز پایانی" in t.subject) == 2
assert sum(1 for t in new_tickets if "پایان دورهٔ" in t.subject) == 2

# idempotency: اجرای مجدد باید صفر باشد
r1b = ads_tasks.ads_expiry_warning_task(); r3b = slide_tasks.slideshow_expiry_warning_task()
assert r1b["warned"] == 0 and r3b["warned"] == 0, (r1b, r3b)

# اطمینان: اسلاید بدون صاحب (ادمین) تیکت نمی‌گیرد
sl_admin = StatSlide.objects.create(image="slides/x.png", title="ادمین‌ساخته", show_from=now,
                                    show_until=now - timedelta(hours=1), status=AD_STATUS_APPROVED)
r4b = slide_tasks.slideshow_expired_sweep_task()
assert r4b["notified"] == 0, r4b

# ویژگی‌های مدل
assert ad_near.is_near_expiry and not ad_near.is_expired
assert ad_exp.is_expired and not ad_exp.is_near_expiry
assert sl_near.is_near_expiry and sl_exp.is_expired

# رندر داشبورد: دکمهٔ تمدید برای منقضی + نشان نزدیک‌انقضا
from django.test import Client
c = Client(); c.force_login(User.objects.get(mobile_number=f"0999{suffix}"))
resp = c.get("/dashboard/")
html = resp.content.decode()
assert resp.status_code == 200
assert "تمدید تبلیغ" in html and "تمدید اسلاید" in html
import re
m = re.findall(r"\?renew=(\d+)", html)
# منقضی‌ها: «تمدید تبلیغ/اسلاید» + نزدیک‌انقضاها: «تمدید دوره» — هر ۴ دکمه
assert set(m) == {str(ad_exp.id), str(ad_near.id), str(sl_exp.id), str(sl_near.id)}, set(m)
assert html.count("نزدیک انقضا") >= 2  # نشان ۲ روز پایانی برای دو آیتم نزدیک
print("dashboard badges + renew buttons OK")

# ---- پاک‌سازی داده‌های تست ----
Ticket.objects.filter(author=u).delete()
sl_admin.delete()
for obj in (ad_exp, ad_near, sl_exp, sl_near):
    obj.delete()
CoinLedger.objects.filter(user=u).delete()
u.delete()
print("CLOVER-CLEANED")
print("ALLOK")
