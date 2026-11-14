"""تست‌های ماژول «تقویم و ساعت جاری» (calendar_converter)."""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .utils import convert_date, get_days_in_month, get_first_weekday_index


class ConvertLogicTests(TestCase):
    def test_shamsi_to_miladi_nowruz(self):
        r = convert_date('shamsi', 1403, 1, 1)
        self.assertEqual(r['miladi']['numeric'], '2024/3/20')
        self.assertEqual(r['weekday'], 'چهارشنبه')

    def test_miladi_to_shamsi(self):
        r = convert_date('miladi', 2026, 10, 24)
        self.assertEqual(r['shamsi']['numeric'], '1405/8/2')

    def test_ghamari_roundtrip(self):
        r = convert_date('miladi', 2025, 3, 1)
        g = r['ghamari']
        back = convert_date('ghamari', g['year'], g['month'], g['day'])
        self.assertEqual(back['miladi']['numeric'], '2025/3/1')

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            convert_date('shamsi', 1403, 13, 1)
        with self.assertRaises(ValueError):
            convert_date('nope', 1403, 1, 1)

    def test_grid_helpers(self):
        self.assertEqual(get_days_in_month('shamsi', 1403, 12), 30)  # کبیسه
        self.assertEqual(get_days_in_month('shamsi', 1404, 12), 29)
        self.assertEqual(get_days_in_month('miladi', 2024, 2), 29)
        # ۱ فروردین ۱۴۰۳ چهارشنبه است → اندیس ۴ در هفتهٔ شنبه‌محور
        self.assertEqual(get_first_weekday_index('shamsi', 1403, 1), 4)


class CalendarViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(mobile_number='09120000001', password='pass12345')

    def setUp(self):
        cache.clear()  # شمارندهٔ rate limit بین تست‌ها نشت نکند

    def login(self):
        self.client.force_login(self.user)

    # --- دسترسی ---
    def test_page_requires_login(self):
        r = self.client.get(reverse('calendar_converter:converter'))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('core:index'), r['Location'])

    def test_ajax_endpoints_require_login(self):
        for name in ('ajax_convert', 'calendar_grid', 'api_server_time'):
            r = self.client.get(reverse('calendar_converter:' + name))
            self.assertEqual(r.status_code, 302, name)

    # --- صفحه ---
    def test_page_renders_with_title_and_shell(self):
        self.login()
        r = self.client.get(reverse('calendar_converter:converter'))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn('تقویم و ساعت جاری', html)
        self.assertIn('hb-sidebar', html)          # قالب اصلی سایت
        self.assertIn('id="todayDatesData"', html)
        self.assertIn('Asia/Tehran', html)

    def test_dashboard_has_module_card_and_sidebar_link(self):
        self.login()
        r = self.client.get(reverse('core:dashboard'))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        url = reverse('calendar_converter:converter')
        self.assertIn("data-href=\"%s\"" % url, html)
        self.assertIn('تقویم و ساعت جاری', html)

    # --- AJAX ---
    def test_ajax_convert_ok(self):
        self.login()
        r = self.client.post(reverse('calendar_converter:ajax_convert'),
                             {'calendar_type': 'shamsi', 'year': '۱۴۰۳', 'month': '1', 'day': '1'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['data']['miladi']['numeric'], '2024/3/20')

    def test_ajax_convert_invalid(self):
        self.login()
        r = self.client.post(reverse('calendar_converter:ajax_convert'),
                             {'calendar_type': 'shamsi', 'year': 'abc', 'month': '1', 'day': '1'})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json()['success'])

    def test_ajax_convert_rejects_get(self):
        self.login()
        r = self.client.get(reverse('calendar_converter:ajax_convert'))
        self.assertEqual(r.status_code, 405)

    def test_grid(self):
        self.login()
        r = self.client.get(reverse('calendar_converter:calendar_grid'),
                            {'calendar_type': 'shamsi', 'year': '1403', 'month': '12'})
        self.assertEqual(r.status_code, 200)
        d = r.json()['data']
        self.assertEqual(d['days_in_month'], 30)
        self.assertEqual(d['month_name'], 'اسفند')

    def test_grid_bad_params(self):
        self.login()
        for params in ({'calendar_type': 'x', 'year': '1403', 'month': '1'},
                       {'calendar_type': 'shamsi', 'year': '1403', 'month': '13'},
                       {'calendar_type': 'shamsi', 'year': 'zz', 'month': '1'}):
            r = self.client.get(reverse('calendar_converter:calendar_grid'), params)
            self.assertEqual(r.status_code, 400, params)

    def test_server_time(self):
        self.login()
        r = self.client.get(reverse('calendar_converter:api_server_time'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('timestamp_ms', r.json())

    # --- API عمومی ---
    def test_public_api_get_and_post_json(self):
        url = reverse('calendar_converter:api_convert')
        r = self.client.get(url, {'calendar_type': 'miladi', 'year': 2024, 'month': 3, 'day': 20})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['data']['shamsi']['numeric'], '1403/1/1')
        r = self.client.post(url, data='{"calendar_type":"shamsi","year":1403,"month":1,"day":1}',
                             content_type='application/json')
        self.assertEqual(r.status_code, 200)
        r = self.client.get(url, {'calendar_type': 'shamsi'})
        self.assertEqual(r.status_code, 400)

    # --- Rate limit ---
    def test_rate_limit_returns_429(self):
        url = reverse('calendar_converter:api_convert')
        params = {'calendar_type': 'miladi', 'year': 2024, 'month': 3, 'day': 20}
        codes = [self.client.get(url, params).status_code for _ in range(32)]
        self.assertEqual(codes[:30], [200] * 30)
        self.assertEqual(codes[30:], [429, 429])
        r = self.client.get(url, params)
        self.assertEqual(r['Retry-After'], '60')
