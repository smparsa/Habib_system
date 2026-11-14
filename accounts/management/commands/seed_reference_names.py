# -*- coding: utf-8 -*-
"""بارگذاری نام‌ها و نام‌های خانوادگی ایرانی در جدول‌های مرجع پروفایل.

منبع داده‌های اولیه مجموعه‌های عمومیِ اینترنتی است (جزئیات و مجوزها در
accounts/seed_data/ATTRIBUTION.md). این فرمان امن و قابل تکرار است:
رکوردهایی که از قبل وجود دارند رد می‌شوند و فقط رکوردهای جدید اضافه می‌شوند.

اجرا:
    python manage.py seed_reference_names
"""

import csv
from pathlib import Path

from django.db import transaction
from django.core.management.base import BaseCommand

from accounts.models import FamilynameTbl, FirstnameTbl

DATA_DIR = Path(__file__).resolve().parents[2] / "seed_data"
FIRST_NAMES_FILE = DATA_DIR / "first_names.csv"
FAMILY_NAMES_FILE = DATA_DIR / "family_names.csv"

# جنسیت نام از دادهٔ منبع (male/female/نامشخص)
_GENDER_MAP = {"male": "male", "female": "female", "m": "male", "f": "female"}


class Command(BaseCommand):
    help = "بارگذاری نام‌ها و نام‌های خانوادگی ایرانی (مرجع پروفایل) از seed_data"

    def handle(self, *args, **options):
        first_file, family_file = FIRST_NAMES_FILE, FAMILY_NAMES_FILE
        if not first_file.exists() or not family_file.exists():
            self.stderr.write(
                self.style.ERROR(
                    f"فایل‌های داده یافت نشد: {FIRST_NAMES_FILE} / {FAMILY_NAMES_FILE}"
                )
            )
            return

        added_first = 0
        added_family = 0
        updated_gender = 0
        updated_en = 0

        with transaction.atomic():
            # نام‌های کوچک (فهرست «نام/نام پدر/نام مادر» پروفایل)
            with open(first_file, encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    name = (row.get("first_name_fa") or "").strip()
                    if not name:
                        continue
                    gender = _GENDER_MAP.get(
                        (row.get("gender") or "").strip().lower(), ""
                    )
                    en = (row.get("first_name_en") or "").strip()
                    # get_or_create: حساسیت هم‌ارزی را به دیتابیس می‌سپارد تا
                    # نگارش‌های هم‌ارز در collation دیتابیس تکراری ساخته نشوند.
                    obj, created = FirstnameTbl.objects.get_or_create(
                        first_name_fa=name,
                        defaults={"gender": gender, "first_name_en": en},
                    )
                    if created:
                        added_first += 1
                        continue
                    updates = {}
                    if gender and not obj.gender:
                        updates["gender"] = gender
                        updated_gender += 1
                    if en and not obj.first_name_en:
                        updates["first_name_en"] = en
                        updated_en += 1
                    if updates:
                        for field, value in updates.items():
                            setattr(obj, field, value)
                        obj.save(update_fields=list(updates))

            # نام‌های خانوادگی (همراه با معادل انگلیسی اختیاری)
            with open(family_file, encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    fa = (row.get("familyname_fa") or "").strip()
                    if not fa:
                        continue
                    en = (row.get("familyname_en") or "").strip()
                    _, created = FamilynameTbl.objects.get_or_create(
                        familyname_fa=fa,
                        defaults={"familyname_en": en},
                    )
                    if created:
                        added_family += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"تکمیل شد: {added_first} نام و {added_family} نام خانوادگی اضافه شد "
                f"(جنسیت {updated_gender} نام و لاتین {updated_en} نامِ موجود تکمیل شد). "
                f"فعلی: {FirstnameTbl.objects.count()} نام، "
                f"{FamilynameTbl.objects.count()} نام خانوادگی"
            )
        )