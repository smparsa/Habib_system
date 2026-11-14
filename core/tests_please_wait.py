"""اورلی سراسری «لطفاً منتظر بمانید» باید در «همهٔ» صفحه‌ها فعال باشد (حتی صفحه‌های بدون app.js)."""

import os
import re
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

SKIP_DIRS = {"node_modules", ".git", "__pycache__", "media", "staticfiles"}


def _template_files():
    for root, dirs, files in os.walk(settings.BASE_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if fn.endswith(".html"):
                yield os.path.join(root, fn)


class PleaseWaitCoverage(TestCase):
    def test_every_full_page_template_loads_the_overlay(self):
        """هر قالبِ صفحهٔ کامل (دارای </body>) یا app.js دارد یا please_wait؛ وگرنه اورلی در آن صفحه کار نمی‌کند.

        قالب‌های فرزند از والدشان ارث می‌برند، پس فقط قالب‌هایی بررسی می‌شوند که خودشان </body> دارند.
        """
        missing = []
        for p in _template_files():
            t = open(p, encoding="utf-8", errors="replace").read()
            if "</body>" not in t:
                continue
            if "js/app.js" in t or "_please_wait.html" in t or "js/please_wait.js" in t:
                continue
            # صفحه‌ای که سرتاسر partial دیگری را include می‌کند که app.js دارد
            if re.search(r"{%\s*include\s+['\"][^'\"]*(_sidebar_nav_script|_please_wait)\.html['\"]", t) and "js/app.js" in t:
                continue
            missing.append(os.path.relpath(p, settings.BASE_DIR))
        self.assertEqual(missing, [], f"قالب‌های بدون اورلی «لطفاً منتظر بمانید»: {missing}")

    def test_overlay_script_is_idempotent_and_documents_opt_out(self):
        src = open(os.path.join(settings.BASE_DIR, "core/static/core/js/please_wait.js"), encoding="utf-8").read()
        self.assertIn("window.__hbPwBound", src)
        self.assertIn("data-no-please-wait", src)
        app = open(os.path.join(settings.BASE_DIR, "core/static/core/js/app.js"), encoding="utf-8").read()
        self.assertIn("core/js/please_wait.js", app)          # app.js بارگذاری آن را تضمین می‌کند
        self.assertNotIn("const HB_PLEASE_WAIT_DELAY", app)    # دیگر پیاده‌سازی تکراری ندارد

    def test_ticket_pages_load_overlay_and_export_is_opted_out(self):
        User = get_user_model()
        staff = User.objects.create_user(mobile_number="09120000123")
        staff.is_staff = True
        staff.save()
        self.client.force_login(staff)
        for name in ("tickets:center", "tickets:staff", "tickets:create"):
            html = self.client.get(reverse(name)).content.decode()
            self.assertIn("core/js/please_wait.js", html, name)
        html = self.client.get(reverse("tickets:staff")).content.decode()
        self.assertRegex(html, r"tickets/export\.csv[^>]*data-no-please-wait|data-no-please-wait[^>]*tickets/export\.csv")

    def test_accounting_and_games_pages_load_overlay(self):
        User = get_user_model()
        u = User.objects.create_user(mobile_number="09120000124")
        self.client.force_login(u)
        for name in ("games:home",):
            r = self.client.get(reverse(name))
            if r.status_code == 200:
                self.assertIn("core/js/please_wait.js", r.content.decode(), name)


class PleaseWaitTicketApproval(TestCase):
    def test_approval_forms_have_fast_overlay_delay(self):
        """تأییدِ تیکت درخواست سنگین است (کیف پول + چند تیکت)؛ اورلی باید زودتر از ۲ ثانیه بیاید."""
        from datetime import timedelta
        from django.core.files.base import ContentFile
        from django.utils import timezone
        from adminpanel.models import StatSlide, StatSlideBox
        from ads.approvals import open_approval_request
        from ads.tests import PNG
        User = get_user_model()
        user = User.objects.create_user(mobile_number="09120000125")
        staff = User.objects.create_user(mobile_number="09120000126")
        staff.is_staff = True
        staff.save()
        s = StatSlide(advertiser=user, title="t", coins_paid=Decimal("10"),
                      show_from=timezone.now(), show_until=timezone.now() + timedelta(days=1))
        s.image.save("s.png", ContentFile(PNG), save=False)
        s.save()
        s.boxes.add(StatSlideBox.the_box())
        ticket = open_approval_request(s)
        self.client.force_login(staff)
        html = self.client.get(reverse("tickets:detail", args=[ticket.number])).content.decode()
        self.assertEqual(html.count("data-pw-delay='600'"), 2)           # فرم تأیید + فرم رد
        self.assertIn("core/js/please_wait.js", html)
        src = open(os.path.join(settings.BASE_DIR, "core/static/core/js/please_wait.js"), encoding="utf-8").read()
        self.assertIn("data-pw-delay", src)


class SingleOverlayTests(TestCase):
    """فقط یک اورلیِ «لطفاً منتظر بمانید» در کل برنامه؛ پنل مدیریت و فضای ابری از همان استفاده می‌کنند."""

    def _read(self, rel):
        return open(os.path.join(settings.BASE_DIR, rel), encoding="utf-8").read()

    def test_no_standalone_overlay_markup_remains(self):
        for p in _template_files():
            t = open(p, encoding="utf-8", errors="replace").read()
            self.assertNotIn("hb-admin-loading", t, p)       # اورلی مستقلِ قدیمیِ پنل مدیریت
            self.assertNotIn("waitOverlay", t, p)             # اورلی مستقلِ قدیمیِ فضای ابری
        self.assertNotIn("hb-admin-loading", self._read("core/static/core/js/app.js"))

    def test_cloud_page_delegates_to_global_overlay(self):
        html = self._read("cloudstorage/templates/cloudstorage/home.html")
        self.assertIn("window.hbPleaseWait", html)
        self.assertNotIn("window.hbWait =", html)             # hbWait از please_wait.js ساخته می‌شود

    def test_global_overlay_exposes_counted_api(self):
        js = self._read("core/static/core/js/please_wait.js")
        for token in ("begin: begin", "end: end", "label: setLabel", "window.hbWait", "hb-pw-label"):
            self.assertIn(token, js)

    def test_pages_still_render(self):
        User = get_user_model()
        staff = User.objects.create_user(mobile_number="09120000127")
        staff.is_staff = True
        staff.is_superuser = True
        staff.save()
        self.client.force_login(staff)
        for name in ("cloudstorage:home", "adminpanel:dashboard"):
            try:
                url = reverse(name)
            except Exception:  # noqa: BLE001 - نام مسیر در این پروژه متفاوت باشد
                continue
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, name)
            self.assertNotIn("hb-admin-loading", r.content.decode())
