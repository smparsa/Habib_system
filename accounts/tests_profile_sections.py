"""تست‌های بخش‌های آزاد/اختیاری پروفایل: اطلاعات سازمانی، مهارت‌ها، سوابق آموزشی، اطلاعات سلامت.

پوشش:
- همهٔ فیلدها اختیاری‌اند (ارسال فرم خالی هم موفق است)
- ذخیرهٔ فیلدهای ستون‌دار مدل (اطلاعات سازمانی) و extra_data سایر بخش‌ها
- جداسازی کلیدهای extra_data (ذخیرهٔ یک بخش، بقیه را پاک نمی‌کند)
- پاک‌شدن مقدارها با ارسال خالی و خطای اعتبارسنجی عددی
- اطلاعات سلامت: فقط گروه خونی اجباری است و بقیهٔ فیلدها اختیاری
"""

from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class ProfileSectionsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(mobile_number="09129990077")
        cls.url = reverse("core:profile")

    def setUp(self):
        self.client.force_login(self.user)
        self.profile = self.user.profile

    def msg(self, resp):
        from django.contrib.messages import get_messages

        return " | ".join(str(m) for m in get_messages(resp.wsgi_request))

    # --- همه اختیاری: فرم خالی موفق است ---------------------------------- #
    def test_all_sections_optional_empty_submit(self):
        for action in ("organization", "skills", "training"):
            resp = self.client.post(self.url, {"action": action})
            self.assertEqual(resp.status_code, 302, action)
            self.assertTrue(resp["Location"].endswith(f"#{action}"))
            self.assertIn("با موفقیت ذخیره شد", self.msg(resp))

    # --- اطلاعات سازمانی: ستون‌های مدل + extra_data ----------------------- #
    def test_organization_saves_model_fields_and_extra(self):
        resp = self.client.post(self.url, {
            "action": "organization",
            "personnel_id": "P-123",
            "org_code": "ORG-9",
            "manager_name": "مهندس رضایی",
            "workplace": "واحد فنی",
            "branch": "شعبهٔ مرکزی",
            "work_group": "توسعهٔ نرم‌افزار",
            "cooperation_status": "در حال همکاری",
            "hire_date": "1402-05-01",
        })
        self.assertEqual(resp.status_code, 302)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.personnel_id, "P-123")
        self.assertEqual(self.profile.org_code, "ORG-9")
        self.assertEqual(self.profile.employment_type, "در حال همکاری")
        self.assertEqual(str(self.profile.hire_date), "1402-05-01")
        org = self.profile.extra_data.get("organization") or {}
        self.assertEqual(org.get("manager_name"), "مهندس رضایی")
        self.assertEqual(org.get("workplace"), "واحد فنی")
        self.assertEqual(org.get("branch"), "شعبهٔ مرکزی")
        self.assertEqual(org.get("work_group"), "توسعهٔ نرم‌افزار")
        self.assertEqual(org.get("cooperation_status"), "در حال همکاری")

    def test_organization_partial_fill_only(self):
        self.client.post(self.url, {"action": "organization", "work_group": "پشتیبانی"})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.personnel_id, "")
        self.assertIsNone(self.profile.hire_date)
        self.assertEqual(self.profile.extra_data["organization"], {"work_group": "پشتیبانی"})

    def test_organization_empty_clears_saved_values(self):
        self.profile.personnel_id = "OLD-1"
        self.profile.extra_data = {"organization": {"branch": "قدیم"}}
        self.profile.save()
        self.client.post(self.url, {"action": "organization"})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.personnel_id, "")
        self.assertNotIn("organization", self.profile.extra_data)

    # --- مهارت‌ها ---------------------------------------------------------- #
    def test_skills_saved_in_extra_data(self):
        self.client.post(self.url, {
            "action": "skills",
            "technical_skills": "Python, Django",
            "soft_skills": "رهبری",
            "software": "Excel",
            "programming_languages": "Python",
            "skill_level": "پیشرفته",
            "career_interests": "هوش مصنوعی",
        })
        self.profile.refresh_from_db()
        skills = self.profile.extra_data["skills"]
        self.assertEqual(skills["technical_skills"], "Python, Django")
        self.assertEqual(skills["skill_level"], "پیشرفته")
        self.assertEqual(skills["career_interests"], "هوش مصنوعی")

    def test_skills_partial_then_clear(self):
        self.client.post(self.url, {"action": "skills", "software": "Word"})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.extra_data["skills"], {"software": "Word"})

        self.client.post(self.url, {"action": "skills"})
        self.profile.refresh_from_db()
        self.assertNotIn("skills", self.profile.extra_data)

    # --- سوابق آموزشی ------------------------------------------------------- #
    def test_training_saved_with_numeric_score(self):
        self.client.post(self.url, {
            "action": "training",
            "classes": "دورهٔ جنگو",
            "certificates": "ISC2",
            "training_score": "85",
        })
        self.profile.refresh_from_db()
        training = self.profile.extra_data["training"]
        self.assertEqual(training["classes"], "دورهٔ جنگو")
        self.assertEqual(training["training_score"], 85)
        self.assertNotIn("webinars", training)

    def test_training_invalid_score_rejected(self):
        resp = self.client.post(self.url, {"action": "training", "training_score": "abc"})
        self.profile.refresh_from_db()
        self.assertNotIn("training", self.profile.extra_data)
        self.assertIn("عدد", self.msg(resp))

    # --- جداسازی بخش‌ها ------------------------------------------------------ #
    def test_sections_do_not_wipe_each_other(self):
        self.client.post(self.url, {"action": "organization", "branch": "شعبهٔ ۲"})
        self.client.post(self.url, {"action": "skills", "software": "Figma"})
        self.client.post(self.url, {"action": "training", "exams": "آزمون جامع"})
        self.profile.refresh_from_db()
        extra = self.profile.extra_data
        self.assertEqual(extra["organization"], {"branch": "شعبهٔ ۲"})
        self.assertEqual(extra["skills"], {"software": "Figma"})
        self.assertEqual(extra["training"], {"exams": "آزمون جامع"})

        # ذخیرهٔ مجدد بخش مهارت‌ها، سازمانی و آموزشی را دست‌نخورده نگه می‌دارد
        self.client.post(self.url, {"action": "skills", "skill_level": "خبره"})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.extra_data["organization"], {"branch": "شعبهٔ ۲"})
        self.assertEqual(self.profile.extra_data["training"], {"exams": "آزمون جامع"})
        self.assertEqual(self.profile.extra_data["skills"], {"skill_level": "خبره"})

    # --- رندر مقادیر ذخیره‌شده در فرم ---------------------------------------- #
    def test_saved_values_render_back_into_forms(self):
        self.profile.personnel_id = "R-42"
        self.profile.extra_data = {
            "organization": {"branch": "شعبهٔ رندر"},
            "skills": {"software": "Blender"},
            "training": {"certificates": "CCNA"},
            "health": {"blood_group": "O-", "trusted_doctor": "دکتر رندر"},
        }
        self.profile.save()
        html = self.client.get(self.url).content.decode("utf-8")
        self.assertIn('value="R-42"', html)
        self.assertIn("شعبهٔ رندر", html)
        self.assertIn("Blender", html)
        self.assertIn("دکتر رندر", html)

    # --- اطلاعات سلامت: فقط گروه خونی اجباری، بقیه اختیاری ------------------ #
    def test_health_requires_blood_group(self):
        resp = self.client.post(self.url, {"action": "health"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].endswith("#health"))
        self.profile.refresh_from_db()
        self.assertNotIn("health", self.profile.extra_data)
        self.assertIn("الزامی", self.msg(resp))

    def test_health_blood_group_only_is_enough(self):
        self.client.post(self.url, {"action": "health", "blood_group": "AB+"})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.extra_data["health"], {"blood_group": "AB+"})

    def test_health_saves_all_fields(self):
        self.client.post(self.url, {
            "action": "health",
            "blood_group": "O-",
            "allergies": "گردهٔ گل",
            "insurance_status": "دارد",
            "trusted_doctor": "دکتر محمدی",
            "emergency_conditions": "بیماری قند",
        })
        self.profile.refresh_from_db()
        health = self.profile.extra_data["health"]
        self.assertEqual(health["blood_group"], "O-")
        self.assertEqual(health["allergies"], "گردهٔ گل")
        self.assertEqual(health["insurance_status"], "دارد")
        self.assertEqual(health["trusted_doctor"], "دکتر محمدی")
        self.assertEqual(health["emergency_conditions"], "بیماری قند")

    def test_health_partial_fill_then_clear_optional(self):
        self.client.post(self.url, {
            "action": "health", "blood_group": "B+", "allergies": "آسپرین",
        })
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.extra_data["health"], {
            "blood_group": "B+", "allergies": "آسپرین",
        })

        # ارسال دوباره بدون فیلدهای اختیاری → فقط اختیاری‌ها پاک می‌شوند
        self.client.post(self.url, {"action": "health", "blood_group": "B+"})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.extra_data["health"], {"blood_group": "B+"})

    def test_health_invalid_blood_group_rejected(self):
        self.client.post(self.url, {"action": "health", "blood_group": "XX"})
        self.profile.refresh_from_db()
        self.assertNotIn("health", self.profile.extra_data)

    def test_health_save_does_not_touch_other_sections(self):
        self.profile.extra_data = {"skills": {"software": "Figma"}}
        self.profile.save()
        self.client.post(self.url, {"action": "health", "blood_group": "A+"})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.extra_data["skills"], {"software": "Figma"})
        self.assertEqual(self.profile.extra_data["health"]["blood_group"], "A+")
