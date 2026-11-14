"""تست فیلترهای مشترک تاریخ/ساعت شمسی (core.templatetags.core_extras)."""

from datetime import datetime

from django.test import TestCase
from django.template import Context, Template
from django.utils import timezone

from accounting.jalali import gregorian_to_jalali


def _tehran(y, m, d, hh=0, mm=0):
    """datetime آگاه در منطقهٔ زمانی تهران (برای مقایسهٔ نمایش محلی)."""
    import zoneinfo

    return datetime(y, m, d, hh, mm, tzinfo=zoneinfo.ZoneInfo("Asia/Tehran"))


class JDateFiltersTest(TestCase):
    """تبدیل نمایشی تاریخ‌ها به تقویم جلالی در کل سیستم."""

    def test_jdatetime_gregorian_to_jalali(self):
        """میلادی → شمسی با ارقام فارسی و ساعت محلی تهران."""
        dt = _tehran(2026, 9, 28, 14, 30)  # 1405/07/06
        out = Template("{% load core_extras %}{{ dt|jdatetime }}").render(Context({"dt": dt}))
        self.assertEqual(out, "۱۴۰۵/۰۷/۰۶ ۱۴:۳۰")

    def test_jdate_only_date(self):
        out = Template("{% load core_extras %}{{ dt|jdate }}").render(Context({"dt": _tehran(2026, 3, 21)}))
        self.assertEqual(out, "۱۴۰۵/۰۱/۰۱")  # نوروز ۱۴۰۵

    def test_jtime_local_hour(self):
        """ساعت به وقت تهران (UTC ورودی، ۲۰:۰۰ UTC = ۲۳:۳۰ تهران)."""
        from datetime import timezone as dt_timezone

        dt = timezone.make_aware(datetime(2026, 9, 28, 20, 0), dt_timezone.utc)
        out = Template("{% load core_extras %}{{ dt|jtime }}").render(Context({"dt": dt}))
        self.assertEqual(out, "۲۳:۳۰")

    def test_naive_datetime_no_crash(self):
        out = Template("{% load core_extras %}{{ dt|jdatetime }}").render(
            Context({"dt": datetime(2026, 9, 28, 8, 5)})
        )
        self.assertEqual(out, "۱۴۰۵/۰۷/۰۶ ۰۸:۰۵")

    def test_none_and_garbage(self):
        t = Template("{% load core_extras %}[{{ v|jdatetime }}][{{ v|jdate }}][{{ v|jtime }}]")
        self.assertEqual(t.render(Context({"v": None})), "[][][]")
        self.assertEqual(t.render(Context({"v": "not-a-date"})), "[not-a-date][not-a-date][not-a-date]")

    def test_date_object(self):
        from datetime import date

        out = Template("{% load core_extras %}{{ d|jdate }}{{ d|jdatetime }}").render(
            Context({"d": date(2026, 9, 28)})
        )
        self.assertEqual(out, "۱۴۰۵/۰۷/۰۶۱۴۰۵/۰۷/۰۶")

    def test_consistency_with_accounting_jalali(self):
        """نتایج با ماژول مرجع accounting.jalali یکسان است."""
        dt = _tehran(2026, 9, 28, 9, 15)
        jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
        self.assertEqual((jy, jm, jd), (1405, 7, 6))
