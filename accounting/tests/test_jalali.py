"""تست‌های تقویم شمسی (بدون دیتابیس)."""

from datetime import date

from django.test import SimpleTestCase

from accounting.jalali import (
    JalaliDate,
    days_in_jalali_month,
    en_to_fa,
    fa_to_en,
    format_jalali,
    gregorian_to_jalali,
    is_jalali_leap,
    jalali_to_gregorian,
    parse_jalali_str,
)


class JalaliConversionTests(SimpleTestCase):
    def test_known_dates(self):
        self.assertEqual(gregorian_to_jalali(2026, 3, 21), (1405, 1, 1))
        self.assertEqual(gregorian_to_jalali(2026, 9, 24), (1405, 7, 2))
        self.assertEqual(jalali_to_gregorian(1405, 1, 1), (2026, 3, 21))
        self.assertEqual(jalali_to_gregorian(1403, 12, 30), (2025, 3, 20))

    def test_roundtrip_random_range(self):
        from datetime import timedelta
        start = date(1900, 3, 20).toordinal()
        end = date(2200, 3, 20).toordinal()
        d = start
        step = 97  # نمونه‌گیری سریع
        while d <= end:
            g = date.fromordinal(d)
            jy, jm, jd = gregorian_to_jalali(g.year, g.month, g.day)
            self.assertEqual(jalali_to_gregorian(jy, jm, jd), (g.year, g.month, g.day))
            d += step

    def test_leap_and_month_lengths(self):
        self.assertTrue(is_jalali_leap(1403))
        self.assertFalse(is_jalali_leap(1405))
        self.assertEqual(days_in_jalali_month(1403, 12), 30)
        self.assertEqual(days_in_jalali_month(1405, 12), 29)
        self.assertEqual(days_in_jalali_month(1405, 6), 31)
        with self.assertRaises(ValueError):
            JalaliDate(1405, 12, 30)

    def test_class_api(self):
        j = JalaliDate.fromgregorian(date=date(2026, 9, 24))
        self.assertEqual((j.year, j.month, j.day), (1405, 7, 2))
        self.assertEqual(str(j), "1405/07/02")
        self.assertEqual(j.strftime_fa(), "۱۴۰۵/۰۷/۰۲")
        self.assertEqual(j.togregorian(), date(2026, 9, 24))
        self.assertEqual(j.month_name, "مهر")

    def test_digits_and_parsing(self):
        self.assertEqual(en_to_fa("1405"), "۱۴۰۵")
        self.assertEqual(fa_to_en("۱۴۰۵/۰۷/۰۲"), "1405/07/02")
        self.assertEqual(parse_jalali_str("۱۴۰۵/۰۷/۰۲"), date(2026, 9, 24))
        self.assertEqual(parse_jalali_str("1405-7-2"), date(2026, 9, 24))
        self.assertEqual(parse_jalali_str("02/07/1405"), date(2026, 9, 24))
        self.assertIsNone(parse_jalali_str("1405/13/01"))
        self.assertIsNone(parse_jalali_str("garbage"))
        self.assertEqual(format_jalali(date(2026, 9, 24)), "1405/07/02")
        self.assertEqual(format_jalali(None), "")
