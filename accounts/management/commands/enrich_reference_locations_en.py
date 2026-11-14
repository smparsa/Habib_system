# -*- coding: utf-8 -*-
"""تکمیل ستون‌های لاتین (*_en) جدول‌های مرجع مکان از روی نام فارسی.

برای کشور/استان/شهرستانِ فاقد مقدار لاتین، یک نام لاتینِ پیشنهادی (نام رسمیِ
شناخته‌شدهٔ استان‌ها/شهرستان‌های مهم یا نویسه‌گردانی برای بقیه) می‌نویسد تا
جستجوی «تایپ به انگلیسی» و تطبیقِ نتایجِ GPS/geo که گاهی انگلیسی برمی‌گردانند
ممکن شود. این فرمان امن و قابل تکرار است: مقدار لاتینی که از قبل ثبت شده (یا\nادمین دستی وارد کرده) را بازنویسی نمی‌کند.

اجرا:
    python manage.py enrich_reference_locations_en
"""

from django.core.management.base import BaseCommand

from accounts.location_ref import suggested_en
from accounts.models import CityTbl, ProvinceTbl


class Command(BaseCommand):
    help = "تکمیل نام لاتین (en) استان‌ها و شهرستان‌های جدول مرجع اطلاعات مکانی"

    def handle(self, *args, **options):
        updated_province = 0
        updated_city = 0

        for prov in ProvinceTbl.objects.all():
            if prov.province_en:
                continue
            en = suggested_en(prov.province_fa, kind="province")
            if en:
                prov.province_en = en
                prov.save(update_fields=["province_en"])
                updated_province += 1

        for city in CityTbl.objects.all():
            if city.city_en:
                continue
            en = suggested_en(city.city_fa, kind="city")
            if en:
                city.city_en = en
                city.save(update_fields=["city_en"])
                updated_city += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"تکمیل شد: نام لاتین {updated_province} استان و "
                f"{updated_city} شهرستان نوشته شد. (مقادیر دستی بازنویسی نشد)"
            )
        )
