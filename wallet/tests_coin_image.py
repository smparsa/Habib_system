"""تست تصویر/لوگوی سکه در تنظیمات کیف پول و صفحهٔ پرداخت خرید."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from wallet.models import CoinOrder, WalletSetting


def _png_bytes():
    """PNG یک‌بیکسلی معتبر."""
    import io
    import struct
    import zlib

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\xcc\x00")
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", idat)
        + chunk(b"IEND", b"")
    )


class CoinImageTest(TestCase):
    """نمایش عکس و لوگوی سکه مطابق آپلود ادمین."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(mobile_number="09121110000", password="test1234")
        self.client.force_login(self.user)
        self.setting = WalletSetting.get()

    def _make_buy_order(self):
        from wallet.services import create_buy_order

        return create_buy_order(user=self.user, coins=10, notify=False)

    def test_default_coin_image_fallback_in_template(self):
        """بدون آپلود ادمین، تصویر پیش‌فرض استاتیک نمایش داده می‌شود."""
        self.assertFalse(self.setting.coin_image)
        order = self._make_buy_order()
        resp = self.client.get(reverse("wallet:buy_payment", args=[order.code]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "core/assets/coin.jpg")

    def test_uploaded_coin_image_displayed(self):
        """تصویر آپلودشدهٔ ادمین به‌جای پیش‌فرض نمایش داده می‌شود."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            from django.test import override_settings

            with override_settings(MEDIA_ROOT=tmp):
                upload = SimpleUploadedFile("coin_custom.png", _png_bytes(), content_type="image/png")
                self.setting.coin_image = upload
                self.setting.save()
                self.setting.refresh_from_db()
                self.assertTrue(self.setting.coin_image.name)

                order = self._make_buy_order()
                resp = self.client.get(reverse("wallet:buy_payment", args=[order.code]))
                self.assertEqual(resp.status_code, 200)
                self.assertContains(resp, self.setting.coin_image.url)
                self.assertNotContains(resp, "core/assets/coin.jpg")

    def test_admin_panel_shows_coin_image_form(self):
        """فرم تنظیمات پنل، فیلد تصویر سکه + پیش‌نمایش دارد."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        admin = User.objects.create_user(mobile_number="09122220000", password="adm1234", is_staff=True)
        self.client.force_login(admin)
        resp = self.client.get(reverse("adminpanel:wallet_settings"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "coin_image")

    def test_admin_panel_can_upload_coin_image(self):
        """ادمین می‌تواند تصویر سکه را از پنل آپلود و ذخیره کند."""
        import tempfile

        from django.contrib.auth import get_user_model

        User = get_user_model()
        admin = User.objects.create_user(mobile_number="09123330000", password="adm1234", is_staff=True)
        self.client.force_login(admin)
        with tempfile.TemporaryDirectory() as tmp:
            from django.test import override_settings

            with override_settings(MEDIA_ROOT=tmp):
                upload = SimpleUploadedFile("coin_panel.png", _png_bytes(), content_type="image/png")
                resp = self.client.post(
                    reverse("adminpanel:wallet_settings"),
                    {
                        "submit": "settings",
                        "coin_image": upload,
                        "coin_value_rial": "1000",
                        "coin_value_point": "1",
                        "min_buy_coins": "1", "max_buy_coins": "100000",
                        "min_sell_coins": "1", "max_sell_coins": "100000",
                        "bank_name": "بانک ملی ایران",
                        "receiving_iban": "", "receiving_card_number": "",
                    },
                )
                self.assertEqual(resp.status_code, 302)
                self.setting.refresh_from_db()
                self.assertTrue(self.setting.coin_image.name)
