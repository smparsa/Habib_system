"""تست گردش «تأیید مدیر + بازگشت وجه» برای تبلیغ و اسلایدشو و صفحهٔ ماژول تبلیغات."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from adminpanel.models import (
    AD_STATUS_APPROVED,
    AD_STATUS_PENDING,
    AD_STATUS_REJECTED,
    AdHeaderPlacement,
    Advertisement,
    StatSlide,
    StatSlideBox,
)
from ads.approvals import approve_item, open_approval_request, reject_item
from tickets.models import Ticket
from wallet.models import CoinLedger, FeatureCost, Wallet

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fcffff3f030005fe02fefa4ec50000000049454e44ae426082"
)


class ApprovalRefundTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(mobile_number="09120000111")
        self.admin = User.objects.create_user(mobile_number="09120000222")
        self.admin.is_staff = True
        self.admin.save()
        Wallet.objects.update_or_create(user=self.user, defaults={"balance": Decimal("500")})
        now = timezone.now()
        self.start, self.end = now + timedelta(days=1), now + timedelta(days=3)

    def _ad(self, paid="100", status=AD_STATUS_PENDING):
        ad = Advertisement(advertiser=self.user, title="تبلیغ تست", status=status,
                           coins_paid=Decimal(paid), show_from=self.start, show_until=self.end)
        ad.logo.save("l.png", ContentFile(PNG), save=False)
        ad.save()
        h = AdHeaderPlacement.objects.first()
        if h:
            ad.header_modules.add(h)
        return ad

    def _slide(self, paid="200", status=AD_STATUS_PENDING):
        s = StatSlide(advertiser=self.user, title="اسلاید تست", status=status,
                      coins_paid=Decimal(paid), show_from=self.start, show_until=self.end)
        s.image.save("s.png", ContentFile(PNG), save=False)
        s.save()
        b = StatSlideBox.the_box()
        if b:
            s.boxes.add(b)
        return s

    def balance(self):
        return Wallet.objects.get(user=self.user).balance

    # --- تیکت درخواست تأیید ---
    def test_open_request_creates_ticket_and_links_it(self):
        ad = self._ad()
        ticket = open_approval_request(ad)
        self.assertIsNotNone(ticket)
        ad.refresh_from_db()
        self.assertEqual(ad.approval_ticket_id, ticket.pk)
        self.assertIn("درخواست تأیید تبلیغ", ticket.subject)
        self.assertIn(f"AD-{ad.pk}", ticket.subject)

    # --- رد: ۱۰٪ کارمزد، ۹۰٪ بازگشت، فقط یک‌بار ---
    def test_reject_pending_refunds_90_percent_once(self):
        ad = self._ad(paid="100")
        open_approval_request(ad)
        before = self.balance()
        res = reject_item(ad, self.admin)
        self.assertTrue(res["refunded"])
        self.assertEqual(res["refund"], Decimal("90.00"))
        self.assertEqual(res["fee"], Decimal("10.00"))
        self.assertEqual(self.balance(), before + Decimal("90"))
        ad.refresh_from_db()
        self.assertEqual(ad.status, AD_STATUS_REJECTED)
        self.assertEqual(ad.refunded_coins, Decimal("90.00"))
        self.assertIsNotNone(ad.refunded_at)
        ledger = CoinLedger.objects.filter(user=self.user, kind=CoinLedger.KIND_REFUND)
        self.assertEqual(ledger.count(), 1)
        # رد دوباره = بدون بازگشت مضاعف
        res2 = reject_item(ad, self.admin)
        self.assertEqual(res2["code"], "already")
        self.assertEqual(self.balance(), before + Decimal("90"))
        self.assertEqual(ledger.count(), 1)

    def test_reject_slide_refunds_and_notifies_both_sides(self):
        s = self._slide(paid="200")
        open_approval_request(s)
        before = self.balance()
        n_tickets = Ticket.objects.count()
        res = reject_item(s, self.admin, reason="تصویر نامناسب")
        self.assertEqual(res["refund"], Decimal("180.00"))
        self.assertEqual(self.balance(), before + Decimal("180"))
        # تیکت رد/بازگشت وجه ساخته شده و به کاربر و مدیر می‌رسد
        self.assertGreater(Ticket.objects.count(), n_tickets)
        t = Ticket.objects.filter(subject__contains=f"SL-{s.pk}", subject__startswith="رد").first()
        self.assertIsNotNone(t)
        s.refresh_from_db()
        self.assertEqual(s.refund_fee_coins, Decimal("20.00"))

    def test_reject_non_pending_does_not_refund(self):
        ad = self._ad(status=AD_STATUS_APPROVED)
        before = self.balance()
        res = reject_item(ad, self.admin)
        self.assertTrue(res["ok"])
        self.assertFalse(res["refunded"])
        self.assertEqual(self.balance(), before)

    # --- تأیید ---
    def test_approve_moves_to_queue_and_blocks_after_refund(self):
        ad = self._ad()
        open_approval_request(ad)
        ok, code = approve_item(ad, self.admin)
        self.assertTrue(ok)
        ad.refresh_from_db()
        self.assertEqual(ad.status, AD_STATUS_APPROVED)
        self.assertEqual(approve_item(ad, self.admin), (False, "already"))
        # آگهی رد و بازگردانده‌شده دیگر قابل تأیید نیست
        ad2 = self._ad()
        reject_item(ad2, self.admin)
        self.assertEqual(approve_item(ad2, self.admin), (False, "refunded"))

    # --- صفحه‌ها ---
    def test_ads_home_renders_both_sections_and_history(self):
        FeatureCost.objects.update_or_create(code="ad_submission", defaults={
            "title": "تبلیغ", "coins": Decimal("50"), "is_active": True})
        self._ad(status=AD_STATUS_APPROVED)           # زمان‌بندی‌شده
        gone = self._slide()
        reject_item(gone, self.admin)                 # → تاریخچه
        self._slide()                                 # در انتظار
        self.client.force_login(self.user)
        r = self.client.get(reverse("ads:home"))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn("ثبت تبلیغ جدید", html)
        self.assertIn("ثبت اسلایدشوی آمار داشبورد", html)
        self.assertIn("اسلایدهای من", html)
        self.assertIn("تاریخچهٔ اسلایدها (1)", html)
        self.assertIn("بازگشت 180", html.replace("۱۸۰", "180"))

    def test_slideshow_home_redirects_to_ads(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("slideshow:home"))
        self.assertRedirects(r, reverse("ads:home"), fetch_redirect_response=False)

    # --- ویوهای ادمین (رد/تأیید) و صفحات ثبت ---
    def test_admin_views_reject_and_approve(self):
        self.client.force_login(self.admin)
        ad = self._ad(paid="100")
        before = self.balance()
        r = self.client.post(reverse("adminpanel:ads_reject", args=[ad.pk]))
        self.assertEqual(r.status_code, 302)
        ad.refresh_from_db()
        self.assertEqual(ad.status, AD_STATUS_REJECTED)
        self.assertEqual(self.balance(), before + Decimal("90"))
        self.client.post(reverse("adminpanel:ads_reject", args=[ad.pk]))   # دوباره: بدون بازگشت مضاعف
        self.assertEqual(self.balance(), before + Decimal("90"))

        s = self._slide(paid="50")
        r = self.client.post(reverse("adminpanel:stat_slide_approve", args=[s.pk]))
        self.assertEqual(r.status_code, 302)
        s.refresh_from_db()
        self.assertEqual(s.status, AD_STATUS_APPROVED)

    def test_create_pages_render_for_logged_in_user(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("ads:create")).status_code, 200)
        self.assertEqual(self.client.get(reverse("slideshow:create")).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("slideshow:create")).status_code, 302)

    # --- تأیید/رد مستقیم از داخل تیکت ---
    def test_ticket_page_shows_buttons_and_actions_work(self):
        s = self._slide(paid="100")
        ticket = open_approval_request(s)
        url = reverse("tickets:detail", args=[ticket.number])
        # کاربر عادی دکمه‌ها را نمی‌بیند و نمی‌تواند اقدام کند
        self.client.force_login(self.user)
        self.assertNotContains(self.client.get(url), "approval_approve")
        self.client.post(url, {"action": "approval_approve"})
        s.refresh_from_db()
        self.assertEqual(s.status, AD_STATUS_PENDING)
        # مدیر: دکمه‌ها هست؛ رد → بازگشت ۹۰٪؛ تکرار → بدون بازگشت مضاعف
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(url), "approval_approve")
        before = self.balance()
        self.client.post(url, {"action": "approval_reject", "reason": "نامناسب"})
        s.refresh_from_db()
        self.assertEqual(s.status, AD_STATUS_REJECTED)
        self.assertEqual(self.balance(), before + Decimal("90"))
        self.client.post(url, {"action": "approval_reject"})
        self.assertEqual(self.balance(), before + Decimal("90"))
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "resolved")

    def test_ticket_approve_action(self):
        ad = self._ad()
        ticket = open_approval_request(ad)
        self.client.force_login(self.admin)
        self.client.post(reverse("tickets:detail", args=[ticket.number]), {"action": "approval_approve"})
        ad.refresh_from_db()
        self.assertEqual(ad.status, AD_STATUS_APPROVED)


class SingleSlideshowTests(TestCase):
    """اسلایدشو فقط یک باکس دارد: «اسلایدشو A» (کد stat_tasks)."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(mobile_number="09120000333")
        Wallet.objects.update_or_create(user=self.user, defaults={"balance": Decimal("1000")})

    def test_only_box_a_exists_after_migrations(self):
        codes = list(StatSlideBox.objects.values_list("code", flat=True))
        self.assertEqual(codes, ["stat_tasks"])
        self.assertEqual(StatSlideBox.the_box().title, "اسلایدشو A")

    def test_dashboard_shows_one_slideshow(self):
        self.client.force_login(self.user)
        html = self.client.get(reverse("core:dashboard")).content.decode()
        self.assertEqual(html.count("hb-slideshow-card'"), 1)         # یک کارت اسلایدشو
        self.assertIn("stat-slide-default-banner.jpg", html)          # پیش‌فرضِ بنری ۴:۱
        self.assertEqual(html.count("alt='اسلایدشو A'"), 1)           # تصویر پیش‌فرضِ A
        for gone in ("اسلایدشو B", "اسلایدشو C", "اسلایدشو D"):
            self.assertNotIn(gone, html)

    def test_user_form_has_no_box_choice_and_cost_is_days_times_rate(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("slideshow:create"))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertNotIn('name="stat_boxes"', html)
        self.assertNotIn("data-slide-boxes", html)
        for gone in ("اسلایدشو B", "اسلایدشو C", "اسلایدشو D", "باکس(های)"):
            self.assertNotIn(gone, html)

    def test_ads_page_and_admin_pages_have_no_multi_box_text(self):
        FeatureCost.objects.update_or_create(code="stat_slide_submission", defaults={
            "title": "اسلایدشو", "coins": Decimal("30"), "is_active": True})
        self.client.force_login(self.user)
        html = self.client.get(reverse("ads:home")).content.decode()
        self.assertIn("30 سکه به ازای هر ۲۴ ساعت", html.replace("۳۰", "30"))
        for gone in ("A تا D", "اسلایدشو B", "اسلایدشو C", "اسلایدشو D", "× هر باکس"):
            self.assertNotIn(gone, html)
        staff = get_user_model().objects.create_user(mobile_number="09120000444")
        staff.is_staff = True
        staff.save()
        self.client.force_login(staff)
        for name in ("adminpanel:stat_slides_list", "adminpanel:stat_slide_add"):
            h = self.client.get(reverse(name)).content.decode()
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
            for gone in ("اسلایدشو B", "اسلایدشو C", "اسلایدشو D", "۴ باکس", "۴ گانه"):
                self.assertNotIn(gone, h)


class SlideImageSpecTests(TestCase):
    """مشخصات تصویر اسلایدشو: بنر ۴:۱ (توصیه‌شده ۲۴۰۰×۶۰۰)."""

    @staticmethod
    def _img(w, h, name="s.png", fmt="PNG"):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        buf = io.BytesIO()
        Image.new("RGB", (w, h), (10, 20, 40)).save(buf, fmt)
        return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")

    def test_default_banner_asset_is_4_to_1(self):
        from django.contrib.staticfiles import finders
        from PIL import Image
        path = finders.find("core/assets/stat-slide-default-banner.jpg")
        self.assertIsNotNone(path)
        w, h = Image.open(path).size
        self.assertEqual((w, h), (2400, 600))

    def test_validation_accepts_banner_and_rejects_old_ratio(self):
        from django import forms
        from adminpanel.forms import validate_stat_slide_image
        validate_stat_slide_image(self._img(2400, 600))      # توصیه‌شده
        validate_stat_slide_image(self._img(1200, 300))      # حداقل
        validate_stat_slide_image(self._img(1600, 400))
        for bad in ((800, 500), (2400, 1200), (1000, 250), (2400, 400)):
            with self.assertRaises(forms.ValidationError, msg=str(bad)):
                validate_stat_slide_image(self._img(*bad))

    def test_create_page_states_new_spec(self):
        user = get_user_model().objects.create_user(mobile_number="09120000555")
        self.client.force_login(user)
        html = self.client.get(reverse("slideshow:create")).content.decode()
        self.assertIn("۲۴۰۰×۶۰۰", html)
        self.assertIn("ناحیهٔ امن", html)
        self.assertNotIn("۸۰۰×۵۰۰", html)


class CreateSlideshowTests(TestCase):
    """«ساخت اسلایدشو (Create Slideshow)»: تبدیل تصویر ناسازگار به بنر ۲۴۰۰×۶۰۰ با کسر هزینه."""

    def setUp(self):
        from datetime import date
        User = get_user_model()
        self.user = User.objects.create_user(mobile_number="09120000777")
        self.other = User.objects.create_user(mobile_number="09120000888")
        Wallet.objects.update_or_create(user=self.user, defaults={"balance": Decimal("500")})
        FeatureCost.objects.update_or_create(code="stat_slide_create", defaults={
            "title": "ساخت اسلایدشو", "coins": Decimal("20"), "is_active": True})
        FeatureCost.objects.update_or_create(code="stat_slide_submission", defaults={
            "title": "اسلایدشو", "coins": Decimal("30"), "is_active": True})
        self.client.force_login(self.user)
        self.url = reverse("slideshow:build")
        d0 = date.today() + timedelta(days=2)
        self.dates = {"start_date": d0.isoformat(), "end_date": (d0 + timedelta(days=3)).isoformat(),
                      "ad_time": "10:00"}

    def balance(self):
        return Wallet.objects.get(user=self.user).balance

    @staticmethod
    def img(w, h, fmt="PNG", mode="RGB", name="x.png"):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        buf = io.BytesIO()
        Image.new(mode, (w, h), (200, 60, 60, 255) if mode == "RGBA" else (200, 60, 60)).save(buf, fmt)
        ctype = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}[fmt]
        return SimpleUploadedFile(name, buf.getvalue(), content_type=ctype)

    # --- موتور ساخت ---
    def test_builder_outputs_valid_banner_for_any_ratio(self):
        import io
        from PIL import Image
        from adminpanel.forms import validate_stat_slide_image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from slideshow import builder
        for w, h, fmt, mode in ((800, 500, "PNG", "RGB"), (500, 1000, "JPEG", "RGB"),
                                (414, 379, "PNG", "RGB"), (5000, 400, "PNG", "RGB"),
                                (600, 600, "PNG", "RGBA"), (1200, 800, "WEBP", "RGB")):
            src = builder.inspect_image(self.img(w, h, fmt, mode))
            data = builder.build_banner(src)
            out = Image.open(io.BytesIO(data))
            self.assertEqual(out.size, (2400, 600), (w, h))
            self.assertLessEqual(len(data), 1_900_000)
            validate_stat_slide_image(SimpleUploadedFile("o.jpg", data, content_type="image/jpeg"))

    def test_builder_keeps_whole_image_inside_safe_area(self):
        import io
        from PIL import Image
        from slideshow import builder
        # عکسِ ۳:۲ با رنگِ یکدست و قرمز؛ پیش‌زمینه باید وسط و فقط در x=۶۰۰..۱۸۰۰ باشد
        out = Image.open(io.BytesIO(builder.build_banner(builder.inspect_image(self.img(900, 600)))))
        red = lambda p: p[0] > 150 and p[1] < 110 and p[2] < 110
        self.assertTrue(red(out.getpixel((1200, 300))))              # مرکز: خودِ تصویر
        self.assertFalse(red(out.getpixel((300, 300))))              # بیرون ناحیهٔ امن: پس‌زمینهٔ محو/تیره
        self.assertFalse(red(out.getpixel((2100, 300))))

    def test_builder_rejects_bad_input(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from slideshow import builder
        for bad in (self.img(100, 100), SimpleUploadedFile("a.png", b"not an image", content_type="image/png"),
                    self.img(300, 300, "PNG").__class__("g.gif", self._gif(), content_type="image/gif")):
            with self.assertRaises(builder.BuildError):
                builder.inspect_image(bad)

    @staticmethod
    def _gif():
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (400, 400)).save(buf, "GIF")
        return buf.getvalue()

    # --- اندپوینت ساخت: کسر هزینه ---
    def test_build_charges_creates_temp_file_and_returns_token(self):
        from slideshow import builder
        before = self.balance()
        r = self.client.post(self.url, {"image": self.img(800, 500)})
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertTrue(j["ok"])
        self.assertEqual(self.balance(), before - Decimal("20"))
        self.assertEqual(Decimal(j["cost"]), Decimal("20"))
        self.assertIsNotNone(builder.load_temp(self.user, j["token"]))
        self.assertIsNone(builder.load_temp(self.other, j["token"]))     # فقط صاحبش
        ledger = CoinLedger.objects.filter(user=self.user, ref_code="stat_slide_create")
        self.assertEqual(ledger.count(), 1)
        # تیکت مالی کسر هزینه برای کاربر/مدیران
        self.assertTrue(Ticket.objects.filter(subject__contains="ساخت اسلایدشو").exists())

    def test_build_blocked_when_cost_inactive_or_zero(self):
        for kwargs in ({"is_active": False}, {"coins": Decimal("0")}):
            FeatureCost.objects.filter(code="stat_slide_create").update(**kwargs)
            before = self.balance()
            r = self.client.post(self.url, {"image": self.img(800, 500)})
            self.assertEqual(r.status_code, 400)
            self.assertEqual(self.balance(), before)
            FeatureCost.objects.filter(code="stat_slide_create").update(is_active=True, coins=Decimal("20"))

    def test_build_invalid_image_is_not_charged(self):
        before = self.balance()
        r = self.client.post(self.url, {"image": self.img(100, 100)})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.balance(), before)
        self.assertEqual(self.client.post(self.url, {}).status_code, 400)
        self.assertEqual(self.balance(), before)

    def test_build_insufficient_balance_returns_402_and_no_file(self):
        Wallet.objects.filter(user=self.user).update(balance=Decimal("5"))
        r = self.client.post(self.url, {"image": self.img(800, 500)})
        self.assertEqual(r.status_code, 402)
        self.assertTrue(r.json()["wallet"])
        self.assertEqual(self.balance(), Decimal("5"))

    def test_build_failure_after_charge_refunds_in_full(self):
        from unittest import mock
        before = self.balance()
        with mock.patch("slideshow.builder.build_banner", side_effect=RuntimeError("boom")):
            r = self.client.post(self.url, {"image": self.img(800, 500)})
        self.assertEqual(r.status_code, 500)
        self.assertEqual(self.balance(), before)
        self.assertTrue(CoinLedger.objects.filter(user=self.user, kind=CoinLedger.KIND_REFUND).exists())

    def test_build_requires_login_and_post(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url, {"image": self.img(800, 500)}).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    # --- ثبت نهایی با بنرِ ساخته‌شده ---
    def test_create_with_built_token_uses_built_image_and_cleans_up(self):
        from slideshow import builder
        tok = self.client.post(self.url, {"image": self.img(800, 500)}).json()["token"]
        before = self.balance()
        r = self.client.post(reverse("slideshow:create"), {
            "title": "با بنر ساخته‌شده", "built_token": tok, **self.dates})
        self.assertRedirects(r, reverse("ads:home"), fetch_redirect_response=False)
        s = StatSlide.objects.get(title="با بنر ساخته‌شده")
        from PIL import Image
        with s.image.open("rb") as fh:
            self.assertEqual(Image.open(fh).size, (2400, 600))
        self.assertEqual(s.coins_paid, Decimal("90"))                    # ۳ روز × ۳۰
        self.assertEqual(self.balance(), before - Decimal("90"))
        self.assertIsNone(builder.load_temp(self.user, tok))             # فایل موقت پاک شد
        self.assertEqual(s.status, AD_STATUS_PENDING)                    # هنوز نیازمند تأیید مدیر
        self.assertIsNotNone(s.approval_ticket_id)

    def test_create_ignores_someone_elses_or_bogus_token(self):
        tok = self.client.post(self.url, {"image": self.img(800, 500)}).json()["token"]
        self.client.force_login(self.other)
        for t in (tok, "x" * 24, "../../etc/passwd"):
            r = self.client.post(reverse("slideshow:create"), {"title": "نامعتبر", "built_token": t, **self.dates})
            self.assertEqual(r.status_code, 200)                          # فرم خطا می‌دهد: تصویر لازم است
            self.assertFalse(StatSlide.objects.filter(title="نامعتبر").exists())

    def test_create_page_offers_button_only_when_cost_active(self):
        html = self.client.get(reverse("slideshow:create")).content.decode()
        self.assertIn("data-build-open", html)
        self.assertIn("Create Slideshow", html)
        self.assertIn("enabled: true", html)
        # ثبتِ «تصویر ناسازگار» روی دکمهٔ پرداخت؛ اسکریپت هزینه آن را دوباره فعال نمی‌کند
        self.assertIn("dataset.imageBlocked = '1'", html)
        self.assertIn("btn.dataset.imageBlocked === '1'", html)
        FeatureCost.objects.filter(code="stat_slide_create").update(is_active=False)
        html = self.client.get(reverse("slideshow:create")).content.decode()
        self.assertIn("enabled: false", html)
        # دکمه با تعرفهٔ غیرفعال هم ساخته می‌شود ولی غیرفعال و با توضیح
        self.assertIn("هزینهٔ ساخت هنوز توسط مدیر تعریف/فعال نشده است", html)
        self.assertNotIn("ساخت اسلایدشو</b>» (", html)

    def test_ads_page_mentions_create_cost(self):
        html = self.client.get(reverse("ads:home")).content.decode()
        self.assertIn("ساخت اسلایدشو", html)
        self.assertIn("20 سکه، یک‌بار", html.replace("۲۰", "20"))


class DeleteSlideTests(TestCase):
    """حذف کاملِ اسلایدِ خودِ کاربر (فقط تمام‌شده/ردشده)."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(mobile_number="09120000901")
        self.other = User.objects.create_user(mobile_number="09120000902")
        self.client.force_login(self.user)

    def _slide(self, owner=None, status=AD_STATUS_APPROVED, past=True, title="اسلاید", image_name="s.png"):
        now = timezone.now()
        a, b = (now - timedelta(days=3), now - timedelta(days=1)) if past else (now - timedelta(days=1), now + timedelta(days=3))
        s = StatSlide(advertiser=owner or self.user, title=title, status=status, coins_paid=Decimal("50"),
                      show_from=a, show_until=b)
        s.image.save(image_name, ContentFile(PNG), save=False)
        s.save()
        s.boxes.add(StatSlideBox.the_box())
        return s

    def _del(self, s):
        return self.client.post(reverse("slideshow:delete", args=[s.pk]))

    def test_rule_matches_status(self):
        self.assertTrue(self._slide(past=True).user_can_delete)                               # منقضی
        self.assertTrue(self._slide(status=AD_STATUS_REJECTED, past=False).user_can_delete)   # ردشده
        self.assertFalse(self._slide(status=AD_STATUS_PENDING, past=False).user_can_delete)   # در انتظار
        self.assertFalse(self._slide(past=False).user_can_delete)                             # در حال پخش/زمان‌بندی‌شده
        self.assertFalse(self._slide(status=AD_STATUS_PENDING, past=True).user_can_delete)    # در انتظارِ گذشته از پایان

    def test_owner_deletes_expired_slide_and_unique_file_is_removed(self):
        import os
        s = self._slide(title="قدیمی")
        path = s.image.path
        self.assertTrue(os.path.exists(path))
        r = self._del(s)
        self.assertRedirects(r, reverse("ads:home"), fetch_redirect_response=False)
        self.assertFalse(StatSlide.objects.filter(pk=s.pk).exists())
        self.assertFalse(os.path.exists(path))                       # فایلِ بی‌مصرف پاک شد
        self.assertEqual(StatSlide.boxes.through.objects.filter(statslide_id=s.pk).count(), 0)   # اتصال به اسلایدشو پاک شد

    def test_shared_image_with_renewed_copy_is_kept(self):
        import os
        old = self._slide(title="قدیمی")
        renewed = StatSlide(advertiser=self.user, title="تمدیدشده", status=AD_STATUS_PENDING,
                            coins_paid=Decimal("50"), show_from=timezone.now() + timedelta(days=1),
                            show_until=timezone.now() + timedelta(days=3))
        renewed.image = old.image.name                                # همان فایل (مثل تمدید)
        renewed.save()
        path = old.image.path
        self._del(old)
        self.assertFalse(StatSlide.objects.filter(pk=old.pk).exists())
        self.assertTrue(StatSlide.objects.filter(pk=renewed.pk).exists())
        self.assertTrue(os.path.exists(path))                         # فایل برای اسلاید تمدیدشده می‌ماند

    def test_rejected_slide_can_be_deleted(self):
        s = self._slide(status=AD_STATUS_REJECTED, past=False)
        self._del(s)
        self.assertFalse(StatSlide.objects.filter(pk=s.pk).exists())

    def test_pending_and_live_slides_cannot_be_deleted(self):
        for st, past in ((AD_STATUS_PENDING, False), (AD_STATUS_APPROVED, False)):
            s = self._slide(status=st, past=past, title=f"{st}")
            r = self._del(s)
            self.assertRedirects(r, reverse("ads:home"), fetch_redirect_response=False)
            self.assertTrue(StatSlide.objects.filter(pk=s.pk).exists(), st)

    def test_other_users_slide_is_404_and_untouched(self):
        s = self._slide(owner=self.other)
        self.assertEqual(self._del(s).status_code, 404)
        self.assertTrue(StatSlide.objects.filter(pk=s.pk).exists())

    def test_only_post_and_login_required(self):
        s = self._slide()
        self.assertEqual(self.client.get(reverse("slideshow:delete", args=[s.pk])).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post(reverse("slideshow:delete", args=[s.pk])).status_code, 302)
        self.assertTrue(StatSlide.objects.filter(pk=s.pk).exists())

    def test_deletion_is_audited_and_no_coins_move(self):
        Wallet.objects.update_or_create(user=self.user, defaults={"balance": Decimal("100")})
        s = self._slide(title="حسابرسی")
        self._del(s)
        self.assertEqual(Wallet.objects.get(user=self.user).balance, Decimal("100"))
        from tickets.models import TicketAuditLog
        log = TicketAuditLog.objects.get(action="slideshow.slide.deleted", object_id=s.pk)
        self.assertEqual(log.actor, self.user)
        self.assertEqual(log.meta["title"], "حسابرسی")

    def test_page_shows_delete_only_for_deletable_slides(self):
        done = self._slide(title="تمام‌شده")
        live = self._slide(past=False, title="در حال پخش")
        pend = self._slide(status=AD_STATUS_PENDING, past=False, title="در انتظار")
        html = self.client.get(reverse("ads:home")).content.decode()
        self.assertEqual(html.count(reverse("slideshow:delete", args=[done.pk])), 1)
        self.assertNotIn(reverse("slideshow:delete", args=[live.pk]), html)
        self.assertNotIn(reverse("slideshow:delete", args=[pend.pk]), html)
        self.assertIn("برای همیشه حذف شود", html)
        self.assertIn("تمدید", html)                                  # دکمهٔ تمدید کنار آن هنوز هست


class DeleteAdvertisementTests(TestCase):
    """حذف کاملِ تبلیغِ خودِ کاربر (فقط تمام‌شده/ردشده) — هم‌قاعدهٔ اسلایدشو."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(mobile_number="09120000911")
        self.other = User.objects.create_user(mobile_number="09120000912")
        self.client.force_login(self.user)

    def _ad(self, owner=None, status=AD_STATUS_APPROVED, past=True, title="تبلیغ", logo="l.png"):
        now = timezone.now()
        a, b = (now - timedelta(days=3), now - timedelta(days=1)) if past else (now - timedelta(days=1), now + timedelta(days=3))
        ad = Advertisement(advertiser=owner or self.user, title=title, status=status, coins_paid=Decimal("40"),
                           show_from=a, show_until=b)
        ad.logo.save(logo, ContentFile(PNG), save=False)
        ad.save()
        return ad

    def _del(self, ad):
        return self.client.post(reverse("ads:delete", args=[ad.pk]))

    def test_rule_matches_status(self):
        self.assertTrue(self._ad(past=True).user_can_delete)
        self.assertTrue(self._ad(status=AD_STATUS_REJECTED, past=False).user_can_delete)
        self.assertFalse(self._ad(status=AD_STATUS_PENDING, past=False).user_can_delete)
        self.assertFalse(self._ad(past=False).user_can_delete)

    def test_owner_deletes_expired_ad_and_unique_logo_is_removed(self):
        import os
        ad = self._ad(title="قدیمی")
        path = ad.logo.path
        r = self._del(ad)
        self.assertRedirects(r, reverse("ads:home"), fetch_redirect_response=False)
        self.assertFalse(Advertisement.objects.filter(pk=ad.pk).exists())
        self.assertFalse(os.path.exists(path))

    def test_shared_logo_with_renewed_copy_is_kept(self):
        import os
        old = self._ad(title="قدیمی")
        renewed = Advertisement(advertiser=self.user, title="تمدیدشده", status=AD_STATUS_PENDING, coins_paid=Decimal("40"),
                                show_from=timezone.now() + timedelta(days=1), show_until=timezone.now() + timedelta(days=3))
        renewed.logo = old.logo.name
        renewed.save()
        path = old.logo.path
        self._del(old)
        self.assertTrue(Advertisement.objects.filter(pk=renewed.pk).exists())
        self.assertTrue(os.path.exists(path))

    def test_pending_and_live_cannot_be_deleted_and_others_get_404(self):
        for st, past in ((AD_STATUS_PENDING, False), (AD_STATUS_APPROVED, False)):
            ad = self._ad(status=st, past=past, title=st)
            self._del(ad)
            self.assertTrue(Advertisement.objects.filter(pk=ad.pk).exists(), st)
        foreign = self._ad(owner=self.other)
        self.assertEqual(self._del(foreign).status_code, 404)
        self.assertTrue(Advertisement.objects.filter(pk=foreign.pk).exists())

    def test_only_post_login_and_audit(self):
        ad = self._ad(title="حسابرسی")
        self.assertEqual(self.client.get(reverse("ads:delete", args=[ad.pk])).status_code, 405)
        self._del(ad)
        from tickets.models import TicketAuditLog
        log = TicketAuditLog.objects.get(action="ads.advertisement.deleted", object_id=ad.pk)
        self.assertEqual((log.actor, log.meta["title"]), (self.user, "حسابرسی"))
        self.client.logout()
        other = self._ad(owner=self.user)
        self.assertEqual(self.client.post(reverse("ads:delete", args=[other.pk])).status_code, 302)
        self.assertTrue(Advertisement.objects.filter(pk=other.pk).exists())

    def test_page_shows_delete_for_both_tables_only_when_allowed(self):
        done = self._ad(title="تمام‌شده")
        live = self._ad(past=False, title="جاری")
        html = self.client.get(reverse("ads:home")).content.decode()
        self.assertEqual(html.count(reverse("ads:delete", args=[done.pk])), 1)
        self.assertNotIn(reverse("ads:delete", args=[live.pk]), html)
        self.assertIn("تبلیغ «تمام‌شده» برای همیشه حذف شود", html.replace("\\", ""))
