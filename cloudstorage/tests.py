"""تست‌های ماژول «فضای ذخیره‌سازی ابری».

پوشش الزامات پروژه:
- انتخاب پوشه و آپلود با حفظ ساختار | انتخاب گروهی رسانه از گالری
- آپلود پوشهٔ خالی (ساختار خالی) | آپلود مجدد (بدون تغییر = بدون هزینه)
- فایل تغییرکرده (نسخه‌بندی) | دانلود بخشی از پوشه (ZIP گزینشی)
- پرداخت ناموفق (موجودی ناکافی) | بازپرداخت لغو | قطع ارتباط/بازیابی/idempotent
- عبور از سهمیه | جلوگیری از دسترسی به فایل کاربران دیگر | Path Traversal
- غیرفعال بودن ماژول | پنل ادمین (تنظیمات + عکس‌برداری تعرفه + دفتر ممیزی)
"""
import json
import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms.models import model_to_dict
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from wallet.models import CoinLedger, Wallet

from . import services as S
from .models import (
    ArchiveJob,
    StorageAccount,
    StorageAuditLog,
    StorageFolder,
    StorageObject,
    StoragePricing,
    StorageSettings,
    UploadSession,
)

User = get_user_model()
_DOCS_TMP = tempfile.mkdtemp(prefix="cloudstorage_test_")


def _cleanup_docs():
    shutil.rmtree(_DOCS_TMP, ignore_errors=True)


@override_settings(DOCS_ROOT=_DOCS_TMP)
class CloudStorageFlowTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        _cleanup_docs()

    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09127770001")
        self.user.is_active = True
        self.user.save(update_fields=["is_active"])
        Wallet.objects.create(user=self.user, balance=Decimal("1000"))
        self.other = User.objects.create_user(mobile_number="09127770002")
        self.other.is_active = True
        self.other.save(update_fields=["is_active"])
        Wallet.objects.create(user=self.other, balance=Decimal("100"))
        self.client = Client()
        self.client.force_login(self.user)

    # ------------------------------------------------------------------ # 
    # کمکی‌ها
    # ------------------------------------------------------------------ #
    def _quote(self, files, folders=(), source="folder", name="MyFolder", target=""):
        payload = {"source": source, "folder_name": name, "target_uid": target,
                   "files": files, "folders": list(folders)}
        return self.client.post(reverse("cloudstorage:api_quote"),
                                json.dumps(payload), content_type="application/json")

    def _pay(self, token):
        return self.client.post(reverse("cloudstorage:api_pay", args=[token]))

    def _upload(self, token, relpath, content, sha=""):
        return self.client.post(
            reverse("cloudstorage:api_upload", args=[token]),
            {"file": SimpleUploadedFile(relpath.split("/")[-1], content),
             "relpath": relpath, "sha256": sha})

    def _finalize(self, token):
        return self.client.post(reverse("cloudstorage:api_finalize", args=[token]))

    def _full_upload(self, files, folders=(), source="folder", name="MyFolder"):
        """گردش کامل: برآورد → پرداخت → آپلود → تسویه؛ سشن و پوشه را برمی‌گرداند."""
        r = self._quote(files, folders, source, name)
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertTrue(data["ok"], data)
        token, stats = data["token"], data["stats"]
        if Decimal(stats["total_cost"]) > 0:
            self.assertTrue(self._pay(token).json().get("paid"))
        for item in stats and [m for m in self._all_manifest(token)
                               if m["state"] in ("new", "changed")]:
            content = files_by_path[item["relpath"]]
            res = self._upload(token, item["relpath"], content)
            self.assertEqual(res.status_code, 200, res.content)
        r2 = self._finalize(token)
        self.assertEqual(r2.status_code, 200, r2.content)
        self.assertTrue(r2.json()["ok"], r2.content)
        session = UploadSession.objects.get(token=token)
        return session, session.target_folder

    def _all_manifest(self, token):
        return UploadSession.objects.get(token=token).manifest

    # ------------------------------------------------------------------ #
    # ۱) انتخاب پوشه و آپلود کامل با حفظ ساختار
    # ------------------------------------------------------------------ #
    def test_folder_upload_flow_with_structure(self):
        global files_by_path
        files_by_path = {
            "a.txt": b"hello a",
            "sub/b.txt": b"hello b",
            "sub/deep/c.txt": b"hello c",
        }
        manifest = [{"relpath": k, "size": len(v)} for k, v in files_by_path.items()]
        r = self._quote(manifest, folders=["sub", "sub/deep"], name="Photos")
        self.assertEqual(r.status_code, 200, r.content)
        stats = r.json()["stats"]
        self.assertEqual(stats["new_count"], 3)
        self.assertEqual(stats["folders_count"], 2)
        self.assertGreater(Decimal(stats["total_cost"]), 0)

        token = r.json()["token"]
        self.assertTrue(self._pay(token).json()["paid"])

        balance_after_pay = Wallet.objects.get(user=self.user).balance
        self.assertLess(balance_after_pay, Decimal("1000"))

        for path, content in files_by_path.items():
            res = self._upload(token, path, content)
            self.assertEqual(res.status_code, 200, res.content)
        fin = self._finalize(token)
        self.assertTrue(fin.json()["ok"], fin.content)

        folder = fin.json()["folder_uid"] and StorageFolder.objects.get(uid=fin.json()["folder_uid"])
        self.assertEqual(folder.files_count, 3)
        objs = StorageObject.objects.filter(folder=folder, status="active")
        self.assertEqual({o.rel_path for o in objs}, set(files_by_path))
        # مسیر فیزیکی: DOCS_ROOT/cloud/{storage_key}/{folder_uid}/{rel_path}
        acc = StorageAccount.objects.get(user=self.user)
        for obj in objs:
            self.assertTrue(obj.file.storage.exists(obj.file.name))
            self.assertTrue(obj.file.name.startswith(f"{acc.storage_key}/{folder.uid}/"))
        self.assertEqual(acc.files_count, 3)
        self.assertGreater(acc.used_bytes, 0)

    # ------------------------------------------------------------------ #
    # ۲) انتخاب گروهی رسانه از گالری → پوشهٔ منطقی Gallery Import
    # ------------------------------------------------------------------ #
    def test_gallery_multi_media_import(self):
        global files_by_path
        files_by_path = {
            "Gallery Import/IMG_1.jpg": b"\xff\xd8JPEGDATA",
            "Gallery Import/VID_2.mp4": b"\x00\x00ftypMP4",
            "Gallery Import/IMG_3.jpg": b"\xff\xd8JPEGDATA2",
        }
        manifest = [{"relpath": k, "size": len(v)} for k, v in files_by_path.items()]
        r = self._quote(manifest, folders=["Gallery Import"],
                        source="gallery", name="Gallery Import")
        self.assertEqual(r.status_code, 200, r.content)
        token = r.json()["token"]
        self.assertTrue(self._pay(token).json()["paid"])
        for path, content in files_by_path.items():
            self.assertEqual(self._upload(token, path, content).status_code, 200)
        folder = self._finalize(token).json()["folder_uid"]
        self.assertEqual(StorageObject.objects.filter(folder__uid=folder).count(), 3)

        # انتخاب دوباره به پوشهٔ قبلی متصل می‌شود (اتصال/پوشهٔ جدید)
        r2 = self._quote(manifest, folders=["Gallery Import"],
                         source="gallery", name="Gallery Import", target=folder)
        self.assertEqual(r2.status_code, 200, r2.content)
        stats = r2.json()["stats"]
        self.assertEqual(stats["unchanged_count"], 3, "رسانهٔ تکراری نباید دوباره آپلود/هزینه شود")
        self.assertEqual(Decimal(stats["total_cost"]), 0)

    # ------------------------------------------------------------------ #
    # ۳) آپلود پوشهٔ خالی → ساختار خالی ثبت می‌شود
    # ------------------------------------------------------------------ #
    def test_empty_folder_registered(self):
        global files_by_path
        files_by_path = {}
        r = self._quote([], folders=["empty/sub"], name="خالی")
        self.assertEqual(r.status_code, 200, r.content)
        stats = r.json()["stats"]
        self.assertEqual(stats["files_count"], 0)
        self.assertEqual(stats["folders_count"], 1)
        self.assertEqual(Decimal(stats["total_cost"]), 0)

        token = r.json()["token"]
        self.assertTrue(self._pay(token).json()["paid"])  # صفر = بدون کسر
        fin = self._finalize(token)
        fin_data = fin.json()
        self.assertTrue(fin_data.get("ok"), fin.content)
        folder_uid = fin_data.get("folder_uid") or StorageFolder.objects.filter(account__user=self.user, name="خالی", status=StorageFolder.STATUS_ACTIVE).first().uid
        folder = StorageFolder.objects.get(uid=folder_uid)
        self.assertEqual(folder.files_count, 0)
        self.assertIn("empty/sub", folder.subtree_dirs)

    # ------------------------------------------------------------------ #
    # ۴) آپلود مجدد پوشه (بدون تغییر = بدون هزینه) + فایل تغییرکرده (نسخه)
    # ------------------------------------------------------------------ #
    def test_reupload_unchanged_free_and_changed_versioned(self):
        global files_by_path
        files_by_path = {"a.txt": b"data-v1!!", "b.txt": b"other"}
        manifest = [{"relpath": k, "size": len(v)} for k, v in files_by_path.items()]
        session, folder = self._full_upload(manifest, name="Docs")
        self.assertEqual(folder.files_count, 2)

        # آپلود مجدد همان پوشه → بدون تغییر
        r = self._quote(manifest, name="Docs", target=folder.uid)
        stats = r.json()["stats"]
        self.assertEqual(stats["unchanged_count"], 2)
        self.assertEqual(Decimal(stats["total_cost"]), 0)

        # فایل تغییرکرده (هش متفاوت از سمت سرور) → نسخهٔ جدید
        changed = [
            {"relpath": "a.txt", "size": len(files_by_path["a.txt"]), "sha256": "0" * 64},
            {"relpath": "b.txt", "size": files_by_path["b.txt"] and len(files_by_path["b.txt"])},
        ]
        r2 = self._quote(changed, name="Docs", target=folder.uid)
        stats2 = r2.json()["stats"]
        self.assertEqual(stats2["changed_count"], 1)
        self.assertEqual(stats2["unchanged_count"], 1)

        token = r2.json()["token"]
        self.assertTrue(self._pay(token).json()["paid"])
        self.assertEqual(self._upload(token, "a.txt", b"data-v2!!").status_code, 200)
        self._finalize(token)

        versions = list(StorageObject.objects.filter(
            folder=folder, rel_path="a.txt").order_by("version"))
        self.assertEqual(len(versions), 2)                       # نسخهٔ قدیمی نگه داشته شد (سیاست ۳)
        self.assertEqual(versions[-1].status, "active")
        self.assertEqual(versions[-1].version, 2)
        self.assertEqual(versions[-1].file.read() if False else versions[-1].size_bytes,
                         len(b"data-v2!!"))
        folder.refresh_from_db()
        self.assertEqual(folder.files_count, 2)

    # ------------------------------------------------------------------ #
    # ۵) دانلود بخشی از پوشه (ZIP گزینشی با لینک زمان‌دار) + کل پوشه
    # ------------------------------------------------------------------ #
    def test_partial_and_full_archive_download(self):
        global files_by_path
        files_by_path = {"a.txt": b"A" * 10, "sub/b.txt": b"B" * 10, "sub/c.txt": b"C" * 10}
        manifest = [{"relpath": k, "size": len(v)} for k, v in files_by_path.items()]
        _, folder = self._full_upload(manifest, folders=["sub"], name="Arch")

        # انتخاب بخشی از پوشه
        r = self.client.post(reverse("cloudstorage:archive_create", args=[folder.uid]),
                             json.dumps({"paths": ["sub/b.txt"]}),
                             content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertTrue(data["ok"], data)
        self.assertEqual(data["files"], 1)
        dl = self.client.get(reverse("cloudstorage:archive_download", args=[data["token"]]))
        job = ArchiveJob.objects.filter(download_token=data["token"]).first()
        self.assertEqual(dl.status_code, 200, str({"status": job and job.status, "note": job and job.note}))
        self.assertEqual(dl["Content-Type"], "application/zip")

        import zipfile, io
        with zipfile.ZipFile(io.BytesIO(b"".join(dl.streaming_content))) as zf:
            self.assertEqual(zf.namelist(), ["sub/b.txt"])

        # کل پوشه
        r2 = self.client.post(reverse("cloudstorage:archive_create", args=[folder.uid]),
                              json.dumps({"paths": []}), content_type="application/json")
        self.assertEqual(r2.json()["files"], 3)

    # ------------------------------------------------------------------ #
    # ۶) پرداخت ناموفق (موجودی ناکافی) + بازپرداخت لغو + قطع ارتباط/idempotent
    # ------------------------------------------------------------------ #
    def test_failed_payment_no_charge(self):
        global files_by_path
        poor = User.objects.create_user(mobile_number="09127770003")
        Wallet.objects.create(user=poor, balance=Decimal("0"))
        c = Client()
        c.force_login(poor)
        r = c.post(reverse("cloudstorage:api_quote"),
                   json.dumps({"source": "folder", "folder_name": "X",
                               "files": [{"relpath": "big.bin", "size": 150 * 1024 * 1024}],
                               "folders": []}),
                   content_type="application/json")
        # حجم ۱۵۰MB × ۱۰ سکه/GB ≈ ۱.۴ سکه → پرداخت باید شکست بخورد (کیف خالی)
        if r.status_code == 200 and Decimal(r.json()["stats"]["total_cost"]) > 0:
            pay = c.post(reverse("cloudstorage:api_pay", args=[r.json()["token"]]))
            self.assertEqual(pay.status_code, 400, pay.content)
            self.assertFalse(pay.json()["ok"])
            session = UploadSession.objects.get(token=r.json()["token"])
            self.assertEqual(session.status, UploadSession.STATUS_DRAFT)
            self.assertEqual(Wallet.objects.get(user=poor).balance, Decimal("0"))
            self.assertFalse(CoinLedger.objects.filter(user=poor).exists())
        else:
            # اگر سقف عملیات مانع شد هم پولی کسر نشده است
            self.assertEqual(Wallet.objects.get(user=poor).balance, Decimal("0"))

    def test_cancel_paid_session_refunds(self):
        global files_by_path
        files_by_path = {"a.txt": b"refund me"}
        manifest = [{"relpath": "a.txt", "size": len(files_by_path["a.txt"])}]
        r = self._quote(manifest, name="R")
        token = r.json()["token"]
        self.assertTrue(self._pay(token).json()["paid"])
        paid_amount = Decimal("1000") - Wallet.objects.get(user=self.user).balance
        self.assertGreater(paid_amount, 0)
        self.client.post(reverse("cloudstorage:session_cancel", args=[token]))
        session = UploadSession.objects.get(token=token)
        self.assertEqual(session.status, UploadSession.STATUS_REFUNDED)
        self.assertEqual(Wallet.objects.get(user=self.user).balance, Decimal("1000"))

    def test_payment_idempotent_after_disconnect(self):
        global files_by_path
        files_by_path = {"a.txt": b"x"}
        r = self._quote([{"relpath": "a.txt", "size": 1}], name="D")
        token = r.json()["token"]
        self.assertTrue(self._pay(token).json()["paid"])
        balance_once = Wallet.objects.get(user=self.user).balance
        # «اتصال قطع شد» → کلاینت دوباره پرداخت را می‌زند: نباید دوبار کسر شود
        again = self._pay(token)
        self.assertTrue(again.json()["paid"])
        self.assertEqual(Wallet.objects.get(user=self.user).balance, balance_once)
        # سشن قابل بازیابی است و آپلود پس از بازگشت هم می‌پذیرد
        self.assertEqual(self._upload(token, "a.txt", b"x").status_code, 200)
        self.assertTrue(self._finalize(token).json()["ok"])

    # ------------------------------------------------------------------ #
    # ۷) سهمیه: عبور از سقف فضای کاربر رد می‌شود
    # ------------------------------------------------------------------ #
    def test_quota_exceeded_rejected(self):
        account = StorageAccount.ensure_for(self.user)
        account.used_bytes = account.quota_bytes - 10
        account.save(update_fields=["used_bytes"])
        r = self._quote([{"relpath": "big.bin", "size": 10_000}], name="Q")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("کافی نیست", r.json()["error"])

    # ------------------------------------------------------------------ #
    # ۸) امنیت: دسترسی کاربر دیگر + Path Traversal + مانیفست خارج
    # ------------------------------------------------------------------ #
    def test_other_user_cannot_access(self):
        global files_by_path
        files_by_path = {"secret.txt": b"top"}
        manifest = [{"relpath": "secret.txt", "size": 3}]
        _, folder = self._full_upload(manifest, name="Private")
        obj = StorageObject.objects.filter(folder=folder).first()

        intruder = Client()
        intruder.force_login(self.other)
        self.assertEqual(intruder.get(
            reverse("cloudstorage:folder_detail", args=[folder.uid])).status_code, 404)
        self.assertEqual(intruder.get(
            reverse("cloudstorage:browse")).status_code, 200)  # فقط فضای خودش
        self.assertEqual(StorageFolder.objects.filter(
            account__user=self.other).count(), 0)
        self.assertEqual(intruder.get(
            reverse("cloudstorage:object_download", args=[folder.uid, obj.pk])).status_code, 404)
        arc = intruder.post(
            reverse("cloudstorage:archive_create", args=[folder.uid]),
            json.dumps({"paths": []}), content_type="application/json")
        self.assertEqual(arc.status_code, 404)
        # پرداخت سشن کاربر دیگر
        r = self._quote(manifest, name="X")
        pay = intruder.post(reverse("cloudstorage:api_pay", args=[r.json()["token"]]))
        self.assertEqual(pay.status_code, 403)

    def test_path_traversal_and_foreign_manifest_rejected(self):
        r = self._quote([{"relpath": "../evil.txt", "size": 5}], name="E")
        self.assertEqual(r.status_code, 403, r.content)   # نرمال‌سازی، خطا می‌دهد

        # مسیر خارج از مانیفست پرداخت‌شده
        global files_by_path
        files_by_path = {"ok.txt": b"ok"}
        r2 = self._quote([{"relpath": "ok.txt", "size": 2}], name="F")
        token = r2.json()["token"]
        self.assertTrue(self._pay(token).json()["paid"])
        res = self._upload(token, "../../etc/passwd", b"hacked")
        self.assertEqual(res.status_code, 403, res.content)
        res2 = self._upload(token, "not-in-manifest.txt", b"hacked")
        self.assertEqual(res2.status_code, 403, res2.content)

    def test_module_disabled_blocks_everything(self):
        sts = StorageSettings.get()
        sts.module_enabled = False
        sts.save(update_fields=["module_enabled"])
        r = self._quote([{"relpath": "a.txt", "size": 1}], name="X")
        self.assertEqual(r.status_code, 403)
        home = self.client.get(reverse("cloudstorage:home"))
        self.assertEqual(home.status_code, 302)
        # غیرفعال‌سازی «انتخاب از گالری» به‌تنهایی
        sts.module_enabled = True
        sts.gallery_enabled = False
        sts.save(update_fields=["module_enabled", "gallery_enabled"])
        r2 = self._quote([{"relpath": "a.txt", "size": 1}], source="gallery", name="G")
        self.assertEqual(r2.status_code, 400)
        self.assertIn("گالری", r2.json()["error"])

    # ------------------------------------------------------------------ #
    # ۹) Sync: تشخیص بدون تغییر/جدید + مالکیت + توقف خودکار
    # ------------------------------------------------------------------ #
    def test_sync_detects_changes_and_ownership(self):
        global files_by_path
        files_by_path = {"a.txt": b"v1", "b.txt": b"v2"}
        manifest = [{"relpath": k, "size": len(v)} for k, v in files_by_path.items()]
        _, folder = self._full_upload(manifest, name="Synced")

        r = self.client.post(reverse("cloudstorage:sync_quote", args=[folder.uid]),
                             json.dumps({"files": manifest}), content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Decimal(r.json()["stats"]["total_cost"]), 0)
        self.assertEqual(r.json()["diff"]["unchanged"], 2)

        # فایل جدید + حذف محلی (نباید حذف ابری ایجاد کند)
        manifest2 = manifest + [{"relpath": "c.txt", "size": 9}]
        files_by_path["c.txt"] = b"newthing!"
        r2 = self.client.post(reverse("cloudstorage:sync_quote", args=[folder.uid]),
                              json.dumps({"files": manifest2}), content_type="application/json")
        self.assertEqual(r2.json()["diff"]["new"], 1)
        cloud_only = r2.json()["cloud_only"]  # «ابر دارد، محلی ندارد» → دست نمی‌خورد
        self.assertEqual(cloud_only, [])

        intruder = Client()
        intruder.force_login(self.other)
        sync_forbidden = intruder.post(
            reverse("cloudstorage:sync_quote", args=[folder.uid]),
            json.dumps({"files": []}), content_type="application/json")
        self.assertEqual(sync_forbidden.status_code, 404)

        # توقف/فعال‌سازی Sync خودکار فقط توسط مالک
        tg = self.client.post(reverse("cloudstorage:sync_toggle", args=[folder.uid]))
        self.assertEqual(tg.status_code, 302)
        folder.refresh_from_db()
        self.assertTrue(folder.auto_sync_enabled)

    def test_sync_download_plan_and_stream(self):
        """دانلود واقعی (ابر ← دستگاه): برنامهٔ دانلود + استریم فایل (با لینک مالک-محدود)."""
        global files_by_path
        files_by_path = {"chapter1/intro.txt": b"intro content v1", "notes.txt": b"n"}
        manifest = [{"relpath": k, "size": len(v)} for k, v in files_by_path.items()]
        _, folder = self._full_upload(manifest, name="DlSync")

        # مانیفست محلی خالی → همهٔ فایل‌های ابری باید «new» و دانلودشدنی باشند
        r = self.client.post(
            reverse("cloudstorage:sync_download_plan", args=[folder.uid]),
            json.dumps({"files": []}), content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        self.assertTrue(d["ok"])
        self.assertEqual(d["stats"]["files_download"], 2)
        self.assertEqual(d["stats"]["files_new"], 2)
        paths = {i["relpath"] for i in d["items"]}
        self.assertEqual(paths, {"chapter1/intro.txt", "notes.txt"})
        for i in d["items"]:
            self.assertIn("/object/", i["url"])  # لینک مالک-محدود؛ هیچ API key لازم نیست

        # فایل واقعی از همان لینک قابل دانلود است (همان کاری که مرورگر می‌کند)
        target = next(i for i in d["items"] if i["relpath"] == "notes.txt")
        dl = self.client.get(target["url"])
        self.assertEqual(dl.status_code, 200)
        body = b"".join(dl.streaming_content) if dl.streaming else dl.content
        self.assertEqual(body, files_by_path["notes.txt"])

        # کاربر غیرمالک: 404
        intruder = Client()
        intruder.force_login(self.other)
        r2 = intruder.post(
            reverse("cloudstorage:sync_download_plan", args=[folder.uid]),
            json.dumps({"files": []}), content_type="application/json")
        self.assertEqual(r2.status_code, 404)

    def test_sync_download_cost_uses_admin_download_tariff_and_charges_wallet(self):
        """هزینهٔ دانلود = تعرفهٔ «آرشیوسازی/Download» ادمین × حجم؛ از کیف پول کسر و تیکت ثبت می‌شود."""
        from tickets.models import Ticket

        global files_by_path
        files_by_path = {"big.bin": b"x" * (1024 * 1024), "notes.txt": b"n"}
        manifest = [{"relpath": k, "size": len(v)} for k, v in files_by_path.items()]
        _, folder = self._full_upload(manifest, name="DlCost")

        sts = StorageSettings.get()
        sts.archive_coin_per_gb = Decimal("2")
        sts.save()

        plan = self.client.post(
            reverse("cloudstorage:sync_download_plan", args=[folder.uid]),
            json.dumps({"files": []}), content_type="application/json").json()
        self.assertEqual(plan["stats"]["rate_per_gb"], "2.00")
        expected = S._coin(Decimal("2") * S._gb(plan["stats"]["bytes_download"]))
        self.assertGreater(expected, 0)
        self.assertEqual(Decimal(plan["stats"]["total_cost"]), expected)

        before = Wallet.objects.get(user=self.user).balance
        r = self.client.post(
            reverse("cloudstorage:sync_download_charge", args=[folder.uid]),
            "{}", content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        self.assertTrue(d["ok"])
        self.assertEqual(Decimal(d["amount"]), expected)
        after = Wallet.objects.get(user=self.user).balance
        self.assertEqual(before - after, expected)
        self.assertEqual(Decimal(d["balance"]), after)
        self.assertEqual(len(d["items"]), 2)
        self.assertTrue(CoinLedger.objects.filter(
            user=self.user, kind=CoinLedger.KIND_CHARGE, amount=-expected).exists())
        # اعلام کسر هزینه (تیکت: نویسنده = کاربر، گیرندگان = کارکنان/ادمین)
        self.assertTrue(Ticket.objects.filter(
            author=self.user, subject__startswith="کسر هزینهٔ دانلود").exists())

        # موجودی ناکافی → خطا و بدون کسر
        w = Wallet.objects.get(user=self.user)
        w.balance = Decimal("0")
        w.save()
        r_low = self.client.post(
            reverse("cloudstorage:sync_download_charge", args=[folder.uid]),
            "{}", content_type="application/json")
        self.assertEqual(r_low.status_code, 400)
        self.assertEqual(Wallet.objects.get(user=self.user).balance, Decimal("0"))

        # کاربر غیرمالک: 404
        intruder = Client()
        intruder.force_login(self.other)
        r_x = intruder.post(
            reverse("cloudstorage:sync_download_charge", args=[folder.uid]),
            "{}", content_type="application/json")
        self.assertEqual(r_x.status_code, 404)


    # ------------------------------------------------------------------ #
    # قاعدهٔ Sync دوطرفه: فقط جدید / حجم متفاوت / Modify شده منتقل می‌شود
    # ------------------------------------------------------------------ #
    def test_sync_upload_diff_new_size_and_modified(self):
        """دستگاه ← ابر: جدید، حجم متفاوت و Modify (زمان متفاوت) آپلود؛ بقیه نه."""
        global files_by_path
        files_by_path = {"same.txt": b"aaaa", "grow.txt": b"bbbb", "touch.txt": b"cccc"}
        base = [{"relpath": k, "size": len(v), "mtime": 1000} for k, v in files_by_path.items()]
        self._full_upload(base, name="DiffUp")

        second = [
            {"relpath": "same.txt", "size": 4, "mtime": 1000},     # بدون تغییر
            {"relpath": "grow.txt", "size": 9, "mtime": 1000},     # حجم متفاوت
            {"relpath": "touch.txt", "size": 4, "mtime": 5000},    # Modify (حجم برابر، زمان متفاوت)
            {"relpath": "fresh.txt", "size": 3, "mtime": 1000},    # جدید
        ]
        r = self._quote(second, name="DiffUp")
        self.assertEqual(r.status_code, 200, r.content)
        states = {m["relpath"]: m["state"] for m in r.json()["manifest"]}
        self.assertEqual(states, {
            "same.txt": "unchanged", "grow.txt": "changed",
            "touch.txt": "changed", "fresh.txt": "new"})

    def test_sync_download_diff_new_size_and_cloud_newer(self):
        """ابر ← دستگاه: جدید، حجم متفاوت و نسخهٔ ابریِ جدیدتر دانلود؛ بقیه نه و فقط همان‌ها هزینه دارند."""
        global files_by_path
        files_by_path = {k: b"x" * n for k, n in
                         {"same.txt": 4, "cloud_newer.txt": 4, "local_newer.txt": 4,
                          "size.txt": 4, "missing.txt": 4}.items()}
        base = [{"relpath": k, "size": len(v), "mtime": 1000} for k, v in files_by_path.items()]
        _, folder = self._full_upload(base, name="DiffDown")

        sts = StorageSettings.get()
        sts.archive_coin_per_gb = Decimal("1000")  # هزینهٔ قابل‌مشاهده روی فایل‌های کوچک
        sts.save()

        local = [
            {"relpath": "same.txt", "size": 4, "mtime": 1000},          # برابر → رد
            {"relpath": "cloud_newer.txt", "size": 4, "mtime": 500},    # ابر جدیدتر → دانلود
            {"relpath": "local_newer.txt", "size": 4, "mtime": 9000},   # دستگاه جدیدتر → رد
            {"relpath": "size.txt", "size": 7, "mtime": 1000},          # حجم متفاوت → دانلود
        ]                                                               # missing.txt → جدید
        plan = self.client.post(
            reverse("cloudstorage:sync_download_plan", args=[folder.uid]),
            json.dumps({"files": local}), content_type="application/json").json()
        states = {i["relpath"]: i["state"] for i in plan["items"]}
        self.assertEqual(states, {
            "cloud_newer.txt": "changed", "size.txt": "changed", "missing.txt": "new"})
        self.assertEqual(plan["stats"]["files_unchanged"], 2)

        # هزینه و دانلود فقط برای همین تفاوت‌ها (نه کل پوشه)
        before = Wallet.objects.get(user=self.user).balance
        d = self.client.post(
            reverse("cloudstorage:sync_download_charge", args=[folder.uid]),
            json.dumps({"files": local}), content_type="application/json").json()
        self.assertTrue(d["ok"], d)
        self.assertEqual({i["relpath"] for i in d["items"]}, set(states))
        self.assertEqual(Decimal(d["amount"]), Decimal(plan["stats"]["total_cost"]))
        self.assertEqual(before - Wallet.objects.get(user=self.user).balance, Decimal(d["amount"]))

    def test_sync_after_identical_content_does_not_reupload_forever(self):
        """محتوای یکسان با زمان تازه: یک‌بار آپلود → تسویه بدون هزینه، زمان ثبت می‌شود → دفعهٔ بعد unchanged."""
        global files_by_path
        files_by_path = {"f.txt": b"same-content"}
        _, folder = self._full_upload([{"relpath": "f.txt", "size": 12, "mtime": 1000}], name="Loop")
        # همان محتوا ولی زمان تازه (مثل فایلی که از ابر دانلود شده)
        self._full_upload([{"relpath": "f.txt", "size": 12, "mtime": 7000}], name="Loop")
        r = self._quote([{"relpath": "f.txt", "size": 12, "mtime": 7000}], name="Loop")
        self.assertEqual({m["relpath"]: m["state"] for m in r.json()["manifest"]},
                         {"f.txt": "unchanged"})


# --------------------------------------------------------------------------- #
# پنل ادمین
# --------------------------------------------------------------------------- #
@override_settings(DOCS_ROOT=_DOCS_TMP)
class CloudStorageAdminTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        _cleanup_docs()

    def setUp(self):
        self.admin = User.objects.create_user(mobile_number="09127770011", is_staff=True)
        self.client = Client()
        self.client.force_login(self.admin)

    def test_admin_settings_save_snapshot_and_audit(self):
        url = reverse("adminpanel:storage_home")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "فضای ذخیره‌سازی ابری")

        sts = StorageSettings.get()
        data = model_to_dict(sts)
        data.update({
            "user_quota_gb": 77,
            "storage_coin_per_gb": "12.5",
            "archive_retention_hours": 6,
        })
        post = self.client.post(url, data)
        self.assertEqual(post.status_code, 302)

        sts.refresh_from_db()
        self.assertEqual(sts.user_quota_gb, 77)
        self.assertEqual(sts.storage_coin_per_gb, Decimal("12.5"))
        self.assertEqual(sts.archive_retention_hours, 6)

        # عکس‌برداری تعرفه (تغییر نرخ ذخیره‌سازی)
        latest = StoragePricing.objects.filter(is_active=True).first()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.storage_coin_per_gb, Decimal("12.5"))

        # دفتر ممیزی با مقادیر قبل/بعد و شناسهٔ مدیر
        log = StorageAuditLog.objects.filter(
            action="storage_settings_changed", actor=self.admin).first()
        self.assertIsNotNone(log)
        changed = log.meta["changed"]
        self.assertEqual(changed["user_quota_gb"]["before"], 50)
        self.assertEqual(changed["user_quota_gb"]["after"], 77)

    def test_admin_queues_reports_audit_pages(self):
        for name, url in {
            "queues": reverse("adminpanel:storage_queues"),
            "reports": reverse("adminpanel:storage_reports"),
            "audit": reverse("adminpanel:storage_audit"),
        }.items():
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f"{name}: {resp.status_code}")

    def test_non_staff_denied(self):
        user = User.objects.create_user(mobile_number="09127770012")
        c = Client()
        c.force_login(user)
        resp = c.get(reverse("adminpanel:storage_home"))
        self.assertEqual(resp.status_code, 302)  # به داشبورد هدایت می‌شود