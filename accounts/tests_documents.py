"""تست‌های بخش «مدارک و فایل‌ها»ی پروفایل.

پوشش:
- قفل بودن بخش برای کاربر بدون کد ملی و فعال‌بودن پس از ثبت آن
- ساخت پوشهٔ اختصاصی «Docs/<کد ملی>» هنگام نخستین ذخیره و مسیر ثبت‌شده در دیتابیس
- کنترل فرمت هر نوع مدرک (عکس / Word-PDF / هر فرمتی)
- جایگزینی نسخهٔ قبلی هر مدرک با بارگذاری مجدد
- دسترسی دانلود: فقط صاحب مدرک یا ادمین
"""

import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User, UserDocument

_DOCS_TMP = tempfile.mkdtemp(prefix="habib_docs_test_")


@override_settings(DOCS_ROOT=_DOCS_TMP)
class DocumentsSectionTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_DOCS_TMP, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09129990001")
        self.client.force_login(self.user)
        self.profile = self.user.profile
        self.profile.national_id = "0123456789"
        self.profile.save(update_fields=["national_id"])
        self.url = reverse("core:profile")

    def png(self, name="photo.png"):
        # یک PNG واقعی ۱×۱ (امضای فایل برای کنترل فرمت کافی است)
        payload = bytes.fromhex(
            "89504e470d0a1a0a0000000d494844520000000100000001080600000"
            "01f15c4890000000d4944415478da63fcffff3f030005020100b9a1db"
            "690d0000000049454e44ae426082"
        )
        return SimpleUploadedFile(name, payload, content_type="image/png")

    def pdf(self, name="resume.pdf"):
        return SimpleUploadedFile(
            name, b"%PDF-1.4 test", content_type="application/pdf"
        )

    # --- قفل بخش بدون کد ملی -------------------------------------------- #
    def test_locked_without_national_id(self):
        self.profile.national_id = None
        self.profile.save(update_fields=["national_id"])

        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "کد ملی</b> در بخش «اطلاعات شخصی» ثبت کرده‌اند")
        self.assertNotContains(resp, "ذخیره مدارک و فایل‌ها")

        # تلاش برای بارگذاری هم رد می‌شود
        resp = self.client.post(
            self.url,
            {"action": "docs", "attachment": self.pdf("x.pdf")},
        )
        self.assertRedirects(resp, f"{self.url}#documents")
        self.assertEqual(UserDocument.objects.count(), 0)

    # --- آپلود سالم: پوشهٔ کد ملی + مسیر در دیتابیس ---------------------- #
    def test_upload_creates_national_id_folder_and_db_paths(self):
        resp = self.client.post(
            self.url,
            {
                "action": "docs",
                "personal_photo": self.png(),
                "resume": self.pdf(),
            },
        )
        self.assertRedirects(resp, f"{self.url}#documents")

        docs = list(UserDocument.objects.order_by("doc_type"))
        self.assertEqual(len(docs), 2)

        import os
        from django.conf import settings

        for doc in docs:
            # مسیر ذخیره‌شده در دیتابیس: <کد ملی>/<فایل>
            self.assertTrue(doc.file.name.startswith("0123456789/"))
            # فایل واقعاً زیر Docs/<کد ملی> قرار گرفته است
            self.assertTrue(doc.file.storage.exists(doc.file.name))
            expected_dir = os.path.join(str(settings.DOCS_ROOT), "0123456789")
            self.assertEqual(
                os.path.dirname(os.path.abspath(doc.file.path)), expected_dir
            )
        self.assertTrue(
            os.path.isdir(os.path.join(str(settings.DOCS_ROOT), "0123456789"))
        )

    # --- کنترل فرمت‌ها ---------------------------------------------------- #
    def test_image_only_types_reject_non_image(self):
        resp = self.client.post(
            self.url,
            {"action": "docs", "national_card": self.pdf("card.pdf")},
        )
        self.assertEqual(UserDocument.objects.count(), 0)
        resp = self.client.get(self.url)
        self.assertContains(resp, "برای این مدرک مجاز نیست")

    def test_resume_contract_require_word_or_pdf(self):
        resp = self.client.post(
            self.url,
            {"action": "docs", "resume": self.png("resume.png")},
        )
        self.assertEqual(UserDocument.objects.count(), 0)
        resp = self.client.get(self.url)
        self.assertContains(resp, "برای این مدرک مجاز نیست")

    def test_attachment_accepts_any_format(self):
        zipped = SimpleUploadedFile("arch.zip", b"PK\x03\x04", "application/zip")
        self.client.post(self.url, {"action": "docs", "attachment": zipped})
        self.assertEqual(
            UserDocument.objects.filter(doc_type="attachment").count(), 1
        )

    def test_empty_submit_rejected(self):
        self.client.post(self.url, {"action": "docs"})
        self.assertEqual(UserDocument.objects.count(), 0)

    # --- جایگزینی نسخهٔ قبلی ---------------------------------------------- #
    def test_reupload_replaces_previous_file_of_same_type(self):
        import os
        from django.conf import settings

        self.client.post(
            self.url, {"action": "docs", "passport": self.png("p1.png")}
        )
        first = UserDocument.objects.get(doc_type="passport")
        first_path = first.file.path
        self.assertTrue(os.path.exists(first_path))

        self.client.post(
            self.url, {"action": "docs", "passport": self.png("p2.png")}
        )
        self.assertEqual(
            UserDocument.objects.filter(doc_type="passport").count(), 1
        )
        second = UserDocument.objects.get(doc_type="passport")
        self.assertEqual(second.original_name, "p2.png")
        self.assertFalse(os.path.exists(first_path))
        self.assertTrue(second.file.storage.exists(second.file.name))

    # --- دانلود امن -------------------------------------------------------- #
    def test_download_owner_ok_others_forbidden(self):
        self.client.post(
            self.url, {"action": "docs", "personal_photo": self.png()}
        )
        doc = UserDocument.objects.get(doc_type="personal_photo")

        other = User.objects.create_user(mobile_number="09129990002")
        self.client.force_login(other)
        url = reverse("accounts:document_download", args=[doc.pk])
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 200)

        self.admin = User.objects.create_user(mobile_number="09129990003")
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)
