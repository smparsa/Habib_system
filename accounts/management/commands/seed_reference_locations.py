# -*- coding: utf-8 -*-
"""بارگذاری کشور/استان/شهرستان در جدول‌های مرجع اطلاعات مکانی پروفایل.

پیش‌فرض: تقسیمات کشوری ایران (منبع رسمیِ منتشرشده — جزئیات در
accounts/seed_data/ATTRIBUTION.md). فرمان امن و قابل تکرار است: رکوردهایی که از
قبل وجود دارند رد می‌شوند و فقط رکوردهای جدید اضافه می‌شوند؛ دادهٔ موجودِ پروفایل
کاربران را لمس نمی‌کند (پروفایل‌ها نام را متن نگه می‌دارند).

گسترش به کشورهای دیگر (بدون شکستن دادهٔ موجود):
    python manage.py seed_reference_locations --country-fa قطر --country-en Qatar \
        --file مسیر/fایل.csv
ستون‌های فایل CSV (با سطر عنوان): country_fa[,country_en],province_fa[,province_en],city_fa[,city_en]
— اگر ستون country_fa در فایل نبود، کشورِ --country-fa برای همهٔ سطرها استفاده می‌شود.

اجرا (ایران):
    python manage.py seed_reference_locations
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.location_ref import suggested_en
from accounts.models import CityTbl, CountryTbl, ProvinceTbl

DATA_DIR = Path(__file__).resolve().parents[2] / "seed_data"
LOCATIONS_FILE = DATA_DIR / "locations_iran.csv"


class Command(BaseCommand):
    help = "بارگذاری کشور/استان/شهرستان مرجع اطلاعات مکانی پروفایل (پیش‌فرض: ایران)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", dest="file", default=None,
            help="مسیر CSV دلخواه برای بارگذاری یک کشور دیگر (به‌جای فایل پیش‌فرض ایران)",
        )
        parser.add_argument(
            "--country-fa", dest="country_fa", default="",
            help="نام فارسی کشور برای سطرهایی که ستون country_fa ندارند",
        )
        parser.add_argument(
            "--country-en", dest="country_en", default="",
            help="نام انگلیسی کشور (برای سطرهای بدون ستون country_en)",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        country_fa_fallback = (options["country_fa"] or "").strip()
        country_en_fallback = (options["country_en"] or "").strip()

        if file_path:
            source = Path(file_path)
            if not source.exists():
                raise CommandError(f"فایل داده یافت نشد: {source}")
        else:
            source = LOCATIONS_FILE
            if not source.exists():
                raise CommandError(f"فایل داده یافت نشد: {source}")

        added_country = added_province = added_city = 0
        updated_en = 0

        with transaction.atomic():
            with open(source, encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    country_fa = (
                        row.get("country_fa") or country_fa_fallback or ""
                    ).strip()
                    province_fa = (row.get("province_fa") or "").strip()
                    city_fa = (row.get("city_fa") or "").strip()
                    if not country_fa or not province_fa or not city_fa:
                        continue
                    country_en = (
                        row.get("country_en") or country_en_fallback or ""
                    ).strip()
                    province_en = (row.get("province_en") or "").strip()
                    city_en = (row.get("city_en") or "").strip()

                    # get_or_create: تشخیص هم‌ارزی را به دیتابیس می‌سپارد تا نگارش‌های
                    # هم‌ارز در collation دیتابیس تکراری ساخته نشوند.
                    country, created = CountryTbl.objects.get_or_create(
                        country_fa=country_fa,
                        defaults={"country_en": country_en},
                    )
                    if created:
                        added_country += 1
                    elif country_en and not country.country_en:
                        country.country_en = country_en
                        country.save(update_fields=["country_en"])
                        updated_en += 1

                    province, created = ProvinceTbl.objects.get_or_create(
                        country=country,
                        province_fa=province_fa,
                        defaults={
                            "province_en": province_en
                            or suggested_en(province_fa, kind="province"),
                        },
                    )
                    if created:
                        added_province += 1
                    elif province_en and not province.province_en:
                        province.province_en = province_en
                        province.save(update_fields=["province_en"])
                        updated_en += 1

                    _, created = CityTbl.objects.get_or_create(
                        province=province,
                        city_fa=city_fa,
                        defaults={
                            "city_en": city_en or suggested_en(city_fa, kind="city"),
                        },
                    )
                    if created:
                        added_city += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"تکمیل شد: {added_country} کشور، {added_province} استان و "
                f"{added_city} شهرستان اضافه شد "
                f"(نام لاتین {updated_en} رکورد موجود تکمیل شد). فعلی: "
                f"{CountryTbl.objects.count()} کشور، "
                f"{ProvinceTbl.objects.count()} استان، "
                f"{CityTbl.objects.count()} شهرستان"
            )
        )
