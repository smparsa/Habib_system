"""تست‌های تبدیل خودکار امتیاز به سکه (اتصال «تعرفه امتیازها» به کیف پول).

- هر امتیازِ award() بلافاصله معادل سکه‌اش (نرخ: «ارزش هر سکه (امتیاز)») به
  کیف پول تجمیع می‌شود؛ هر امتیاز فقط یک‌بار تبدیل می‌شود (watermark در
  profile.extra_data["points_converted"]).
- امتیازهای قبلی کاربران نیز با فراخوانی سرویس تبدیل یک‌بار به سکه می‌رسند
  (همان منطقی که مهاجرت 0014 برای همهٔ کاربران اجرا می‌کند).
- امتیازِ سطح کاربری (user_score) دست‌نخورده می‌ماند.
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts import scoring
from accounts.models import User
from wallet.models import CoinLedger, WalletSetting
from wallet.services import convert_unconverted_points, get_wallet


class PointsToCoinsConversionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(mobile_number="09120000931")
        setting = WalletSetting.get()
        setting.coin_value_point = 1
        setting.save(update_fields=["coin_value_point"])

    def test_award_credits_coins_immediately(self):
        scoring.award(
            self.user.profile, 5, reason="تست", commit=False, rule_code="referral"
        )
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.user_score, 5)
        wallet = get_wallet(self.user)
        self.assertEqual(wallet.balance, Decimal("5.00"))
        row = CoinLedger.objects.get(user=self.user, ref_code="PTS")
        self.assertEqual(row.amount, Decimal("5.00"))
        self.assertEqual(row.kind, CoinLedger.KIND_REWARD)
        # watermark: امتیازها به‌عنوان تبدیل‌شده ثبت شده‌اند
        self.assertEqual(self.user.profile.extra_data.get("points_converted"), 5)

    def test_second_award_converts_only_delta(self):
        scoring.award(self.user.profile, 4, commit=False, rule_code="referral")
        scoring.award(self.user.profile, 3, commit=False, rule_code="magazine_watch")
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.user_score, 7)
        wallet = get_wallet(self.user)
        self.assertEqual(wallet.balance, Decimal("7.00"))
        self.assertEqual(
            CoinLedger.objects.filter(user=self.user, ref_code="PTS").count(), 2
        )

    def test_rate_seven_gives_fractional_coins(self):
        setting = WalletSetting.get()
        setting.coin_value_point = 7
        setting.save(update_fields=["coin_value_point"])
        scoring.award(self.user.profile, 2, commit=False, rule_code="referral")
        self.user.profile.refresh_from_db()
        wallet = get_wallet(self.user)
        self.assertEqual(wallet.balance, Decimal("0.29"))  # 2/7 = 0.2857 → 0.29
        # watermark پیش می‌رود تا همان امتیاز دوباره تبدیل نشود
        self.assertEqual(self.user.profile.extra_data.get("points_converted"), 2)

    def test_zero_rate_disables_conversion(self):
        setting = WalletSetting.get()
        setting.coin_value_point = 0
        setting.save(update_fields=["coin_value_point"])
        scoring.award(self.user.profile, 5, commit=False, rule_code="referral")
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.user_score, 5)
        self.assertEqual(get_wallet(self.user).balance, Decimal("0"))
        self.assertFalse(
            CoinLedger.objects.filter(user=self.user, ref_code="PTS").exists()
        )

    def test_legacy_points_converted_once_by_service(self):
        # امتیازهای قبلی (بدون watermark) با فراخوانی سرویس یک‌بار تبدیل می‌شوند
        profile = self.user.profile
        profile.user_score = 12
        profile.save(update_fields=["user_score"])
        wallet = convert_unconverted_points(profile)
        self.assertEqual(wallet.balance, Decimal("12.00"))
        profile.refresh_from_db()
        self.assertEqual(profile.extra_data.get("points_converted"), 12)
        # فراخوانی مجدد چیزی اضافه نمی‌کند
        self.assertIsNone(convert_unconverted_points(profile))
        self.assertEqual(get_wallet(self.user).balance, Decimal("12.00"))
        # امتیاز سطح کاربری حفظ شده است
        self.assertEqual(profile.user_score, 12)

    def test_dashboard_shows_points_card(self):
        """کارت «بانک مبادلات» جای خود را به «موجودی امتیازات» داده است."""
        scoring.award(self.user.profile, 9, commit=False, rule_code="referral")
        self.client.force_login(self.user)
        resp = self.client.get(reverse("wallet:dashboard"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        self.assertIn("موجودی امتیازات", html)
        self.assertNotIn("بانک مبادلات", html)
        self.assertIn("9", html)
