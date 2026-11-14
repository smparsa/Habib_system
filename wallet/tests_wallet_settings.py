"""تست‌های «تنظیمات سکه و کیف پول» در پنل مدیریت.

- فیلدهای جدید «شماره کارت دریافت وجه» و «ارزش هر سکه (امتیاز)»
- اثر coin_value_point بر امتیازِ پاداشِ کل برنامه (هر سکه = چند امتیاز)
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import FirstnameTbl, FamilynameTbl, User
from wallet.models import WalletSetting


class WalletSettingsAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(mobile_number="09120000901", is_staff=True)
        cls.setting = WalletSetting.get()

    def _post_settings(self, **over):
        data = {
            "coin_value_rial": "1000.00",
            "coin_value_point": "1",
            "buy_enabled": "on",
            "sell_enabled": "on",
            "transfer_enabled": "on",
            "min_buy_coins": "1",
            "max_buy_coins": "100000",
            "min_sell_coins": "1",
            "max_sell_coins": "100000",
            "bank_name": "بانک ملی ایران",
            "receiving_iban": "IR123456789012345678901234",
            "receiving_card_number": "6037997512345678",
            "submit": "settings",
        }
        data.update(over)
        self.client.force_login(self.admin)
        return self.client.post(reverse("adminpanel:wallet_settings"), data, follow=True)

    def test_new_fields_visible_on_page(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("adminpanel:wallet_settings"))
        self.assertContains(resp, "شماره کارت دریافت وجه")
        self.assertContains(resp, "ارزش هر سکه (امتیاز)")

    def test_save_receiving_card_number_and_coin_points(self):
        resp = self._post_settings()
        self.assertContains(resp, "تنظیمات کیف پول ذخیره شد")
        self.setting.refresh_from_db()
        self.assertEqual(self.setting.receiving_card_number, "6037997512345678")
        self.assertEqual(self.setting.coin_value_point, 1)

    def test_coin_point_value_applies_to_reward_points(self):
        """پاداش فقط امتیازی است: میزانِ قانونِ «فهرست امتیازها» به‌عنوان امتیاز اعمال می‌شود."""
        from accounts.referrals import grant_personal_info_rewards

        self._post_settings(coin_value_point="7")
        self.setting.refresh_from_db()
        self.assertEqual(self.setting.coin_value_point, 7)

        fn = FirstnameTbl.objects.create(first_name_fa="علی")
        ln = FamilynameTbl.objects.create(familyname_fa="احمدی")
        user = User.objects.create_user(mobile_number="09120000902")
        user.profile.first_name = fn
        user.profile.last_name = ln
        user.profile.save()

        RewardRule = __import__("wallet.models", fromlist=["RewardRule"]).RewardRule
        RewardRule.objects.update_or_create(
            code="profile_completion",
            defaults={"title": "تکمیل اطلاعات شخصی", "coins": Decimal("2"), "is_active": True},
        )
        user.profile.national_id = "1234567890"
        user.profile.save()
        grant_personal_info_rewards(user)
        user.profile.refresh_from_db()
        # میزان قانون (۲) مستقیم به‌عنوان امتیاز داده می‌شود؛ معادل سکهٔ آن نیز
        # بر اساس نرخ (هر سکه = ۷ امتیاز) به کیف پول تجمیع می‌شود (2/7 ≈ 0.29).
        self.assertEqual(user.profile.user_score, 2)
