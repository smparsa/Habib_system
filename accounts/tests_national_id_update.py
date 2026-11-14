"""تست‌های ماژول «تغییر کد ملی» — جایگزینی سراسری کد جدید در برنامه و دیتابیس.

سناریو: کاربر در پروفایل کد ملی خود را تغییر می‌دهد → کد جدید باید در ایمیل
خودکار، «کد ملی معرف» کاربرانِ معرفی‌شده، متن دفتر کل کیف پول، پوشهٔ مدارک و
مسیرهای رسانه جایگزین کد قدیم شود و رویداد حسابرسی هم ثبت گردد.
"""

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from wallet.models import CoinLedger


@override_settings(MEDIA_ROOT="/tmp/habib_test_media")
class NationalIdUpdateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09120000930")
        profile = self.user.profile
        profile.national_id = "0011223344"
        # ایمیل خودکار بر اساس کد ملی (مثل ذخیرهٔ اطلاعات شخصی) روی پروفایل است
        profile.email = "0011223344@HabibHub.com"
        profile.save(update_fields=["national_id", "email"])
        # کاربری که با کد قدیمی این کاربر ثبت‌نام کرده (معرفی‌شده)
        self.referred = User.objects.create_user(
            mobile_number="09120000931", referrer_national_id="0011223344"
        )
        # یک رکورد دفتر کل حاوی کد قدیم در توضیحات
        CoinLedger.objects.create(
            user=self.user, kind=CoinLedger.KIND_REWARD, amount=0,
            balance_after=0, ref_code="REW", note="پاداش کاربر 0011223344",
        )

    def _change_nid_via_profile(self, new_nid="0099887766"):
        self.client.force_login(self.user)
        fn = __import__(
            "accounts.models", fromlist=["FirstnameTbl"]
        ).FirstnameTbl.objects.create(first_name_fa="علی")
        ln = __import__(
            "accounts.models", fromlist=["FamilynameTbl"]
        ).FamilynameTbl.objects.create(familyname_fa="احمدی")
        return self.client.post(
            reverse("core:profile"),
            {
                "first_name": str(fn.pk),
                "last_name": str(ln.pk),
                "father_name": str(fn.pk),
                "mother_name": str(ln.pk),
                "national_id": new_nid,
                "date_of_birth": "1991-05-05",
                "gender": "male",
                "marital_status": "single",
                "citizenship": "ایران",
                "nationality": "ایران",
                "permanent_residence": "ایران",
                "religion": "islam",
                "sect": "shia",
            },
            follow=True,
        )

    def test_change_via_profile_updates_email_referrer_and_ledger(self):
        resp = self._change_nid_via_profile()
        self.assertContains(resp, "کد ملی شما به‌روز شد")
        self.user.profile.refresh_from_db()
        self.referred.refresh_from_db()
        self.assertEqual(self.user.profile.national_id, "0099887766")
        # ایمیل خودکار پروفایل با کد جدید همگام شد
        self.assertEqual(self.user.profile.email, "0099887766@HabibHub.com")
        # کد ملی معرفِ کاربرِ معرفی‌شده به کد جدید تغییر کرد
        self.assertEqual(self.referred.referrer_national_id, "0099887766")
        # متن دفتر کل هم به‌روز شد
        row = CoinLedger.objects.get(ref_code="REW")
        self.assertIn("0099887766", row.note)
        self.assertNotIn("0011223344", row.note)
        # رویداد حسابرسی ثبت شد
        from tickets.models import TicketAuditLog

        self.assertTrue(
            TicketAuditLog.objects.filter(
                action="profile.national_id_changed", object_id=str(self.user.profile.pk)
            ).exists()
        )

    def test_same_nid_is_noop(self):
        from accounts.national_id_update import propagate_national_id_change

        self.assertFalse(
            propagate_national_id_change(self.user.profile, "0011223344", "0011223344")
        )

    def test_function_replaces_everywhere(self):
        from accounts.national_id_update import propagate_national_id_change

        self.assertTrue(
            propagate_national_id_change(
                self.user.profile, "0011223344", "0099887766"
            )
        )
        self.user.profile.refresh_from_db()
        self.referred.refresh_from_db()
        self.assertEqual(self.user.profile.email, "0099887766@HabibHub.com")
        self.assertEqual(self.referred.referrer_national_id, "0099887766")
        self.assertIn("0099887766", CoinLedger.objects.get(ref_code="REW").note)
