# -*- coding: utf-8 -*-
"""ساخت ۴ اسلاید نمایشی (یک اسلاید برای هر باکس آمار) + تصاویر بنر.

تصاویر با PIL ساخته می‌شوند (سمت داشبورد: بنر تیره/طلایی در ابعاد کارت آمار).
بازهٔ نمایش: از دیروز تا ۳۰ روز بعد → اسلایدشو بلافاصله در داشبورد پخش می‌شود.
"""

import io
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "habib_system.settings")
sys.path.insert(0, os.getcwd())
django.setup()

from PIL import Image, ImageDraw

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from adminpanel.models import StatSlide, StatSlideBox

COLORS = {
    "stat_users": ((201, 162, 39), (24, 30, 48)),
    "stat_projects": ((65, 120, 220), (18, 24, 40)),
    "stat_revenue": ((46, 160, 67), (16, 28, 24)),
    "stat_tasks": ((200, 70, 60), (30, 18, 18)),
}

IMAGES = {}
for code, (accent, base) in COLORS.items():
    w, h = 800, 340
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1)
        c0 = base
        c1 = tuple(int(base[i] * 0.55) for i in range(3))
        d.line([(0, y), (w, y)], fill=tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3)))
    d.polygon(
        [(w - 240, h), (w, 0), (w, h)],
        fill=tuple(int((accent[i] * 0.34 + base[i] * 0.66)) for i in range(3)),
    )
    for x, tw in ((0, 10), (w - 10, 10)):
        d.rectangle([0 if x == 0 else w - 10, 0, w if x == 0 else w, h], fill=accent)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    IMAGES[code] = buf.getvalue()

BOXES = {b.code: b for b in StatSlideBox.objects.all()}
assert set(BOXES) == set(COLORS), f"باکس‌های موجود: {sorted(BOXES)}"

DEMO = {
    "stat_users": (f"© {timezone.localtime().year}", "HabibHub — همه ابزارها، یک هاب"),
    "stat_projects": ("مشتریان و پروژه‌های شما", "معرفی مجموعه‌های تولیدی بازار"),
    "stat_revenue": ("کیف پول و سکه", "خرید، فروش و انتقال سکه‌ها"),
    "stat_tasks": ("مرکز تیکت", "ارتباطات و تیکت هوشمند"),
}

now = timezone.now()
created = 0
for code, (title, desc) in DEMO.items():
    box = BOXES[code]
    if StatSlide.objects.filter(title=title, boxes=box).exists():
        continue
    StatSlide.objects.filter(title=title).delete()
    img = SimpleUploadedFile(f"demo_{code}.png", IMAGES[code], content_type="image/png")
    slide = StatSlide(title=title, description=desc, link_url="",
                      coins_paid=0, is_active=True, views=0,
                      show_from=now - timezone.timedelta(days=1),
                      show_until=now + timezone.timedelta(days=30))
    slide.image.save(f"demo_{code}.png", img, save=True)
    slide.save()
    slide.boxes.set([box])
    created += 1

print(f"اسلایدهای نمایشی ساخته/به‌روزرسانی شد: {created}")
for s in StatSlide.objects.all():
    print(" -", s.pk, s.title, list(s.boxes.values_list('code', flat=True)))
