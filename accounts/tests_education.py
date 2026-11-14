from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.education import grant_education_completion_reward
from accounts.forms import EducationInfoForm, JobForm
from accounts.models import (
    EducationInstitution,
    Job,
    Profile,
    StudyField,
    StudyGroup,
    StudySpecialization,
    User,
)
from wallet.models import CoinLedger, RewardRule, Wallet


class EducationFeatureTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(mobile_number="09129990001")
        self.admin = User.objects.create_user(mobile_number="09129990002")
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])
        self.institution = EducationInstitution.objects.create(
            name="مرکز آزمایشی", code="TEST-INST", institution_type="government"
        )
        self.group = StudyGroup.objects.create(
            name="آزمایشی", code="EG-TEST", description=""
        )
        self.field = StudyField.objects.create(
            name="رشته آزمایشی", code="TEST-FIELD", study_group=self.group
        )
        self.specialization = StudySpecialization.objects.create(
            field=self.field, name="گرایش آزمایشی", code="TEST-SPEC"
        )
        RewardRule.objects.update_or_create(
            code="education_completion",
            defaults={"title": "تکمیل تحصیلات", "coins": Decimal("3"), "is_active": True},
        )

    def education_data(self, **extra):
        data = {
            "degree": "کارشناسی",
            "education_institution": str(self.institution.pk),
            "study_field": str(self.field.pk),
            "study_specialization": str(self.specialization.pk),
            "graduation_year": "1402",
            "gpa": "17.50",
            "courses": "دوره تست",
            "languages": "انگلیسی",
            "language_levels": "B2",
        }
        data.update(extra)
        return data

    def test_degree_required(self):
        """آخرین مدرک الزامی است."""
        data = self.education_data(degree="")
        form = EducationInfoForm(data, instance=self.user.profile)
        self.assertFalse(form.is_valid())
        self.assertIn("degree", form.errors)

    def test_diploma_disables_institution_and_field(self):
        """اگر دیپلم انتخاب شود، مرکز دانشگاهی و رشته تحصیلی باید خالی باشند
        و اعتبارسنجی آن‌ها انجام نشود."""
        data = self.education_data(degree="دیپلم")
        data.pop("education_institution", None)
        data.pop("study_field", None)
        data.pop("study_specialization", None)
        form = EducationInfoForm(data, instance=self.user.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.degree, "دیپلم")
        self.assertIsNone(self.user.profile.education_institution_id)
        self.assertIsNone(self.user.profile.study_field_id)
        self.assertEqual(self.user.profile.university, "")
        self.assertEqual(self.user.profile.field_of_study, "")

    def test_diploma_with_institution_ignored(self):
        """اگر دیپلم با مرکز دانشگاهی ارسال شود، نادیده گرفته بشود."""
        data = self.education_data(degree="دیپلم", education_institution=str(self.institution.pk))
        form = EducationInfoForm(data, instance=self.user.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.degree, "دیپلم")
        self.assertIsNone(self.user.profile.education_institution_id)
        self.assertEqual(self.user.profile.university, "")

    def test_diploma_with_field_ignored(self):
        """اگر دیپلم با رشته تحصiliesarbazeh anastomose شود، نادیده گرفته بشود."""
        data = self.education_data(degree="دیپلم", study_field=str(self.field.pk))
        form = EducationInfoForm(data, instance=self.user.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.degree, "دیپلم")
        self.assertIsNone(self.user.profile.study_field_id)
        self.assertEqual(self.user.profile.field_of_study, "")

    def test_education_form_saves_reference_and_legacy_values(self):
        form = EducationInfoForm(self.education_data(), instance=self.user.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.education_institution_id, self.institution.pk)
        self.assertEqual(self.user.profile.study_field_id, self.field.pk)
        self.assertEqual(self.user.profile.study_specialization_id, self.specialization.pk)
        self.assertEqual(self.user.profile.university, self.institution.name)
        self.assertEqual(self.user.profile.field_of_study, self.field.name)
        self.assertEqual(self.user.profile.extra_data["education"]["languages"], "انگلیسی")

    def test_specialization_must_belong_to_selected_field(self):
        other_group = StudyGroup.objects.create(name="آزمایشی", code="EG-OTHER", description="")
        other_field = StudyField.objects.create(name="رشته دیگر", code="OTHER-FIELD", study_group=other_group)
        other_spec = StudySpecialization.objects.create(
            field=other_field, name="گرایش دیگر", code="OTHER-SPEC"
        )
        form = EducationInfoForm(
            self.education_data(study_specialization=str(other_spec.pk)),
            instance=self.user.profile,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("study_specialization", form.errors)

    def test_group_field_mismatch_rejected(self):
        """اگر گروه امتحانی انتخاب شود، رشته باید به همان گروه تعلق داشته باشد."""
        other_group = StudyGroup.objects.create(name="گروه دیگر", code="EG-OTHER2")
        other_field = StudyField.objects.create(name="رشته گروه دیگر", code="OTHER2-FIELD", study_group=other_group)
        form = EducationInfoForm(
            self.education_data(study_group=str(other_group.pk)),
            instance=self.user.profile,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("study_field", form.errors)

    def test_group_matching_field_accepted_and_saved(self):
        """گروهِ هم‌خانوادهٔ رشته پذیرفته و در extra_data ذخیره می‌شود."""
        form = EducationInfoForm(
            self.education_data(study_group=str(self.group.pk)),
            instance=self.user.profile,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.study_field_id, self.field.pk)
        self.assertEqual(self.user.profile.extra_data["education"]["group_id"], self.group.pk)

    def test_study_fields_endpoint_filters_by_group(self):
        """اندپوینت آبشاری رشته‌ها فقط رشته‌های گروه خواسته‌شده را می‌دهد."""
        self.client.force_login(self.user)
        other_group = StudyGroup.objects.create(name="گروه دیگر", code="EG-ENDP")
        StudyField.objects.create(name="رشته اندپوینت", code="ENDP-FIELD", study_group=other_group)
        response = self.client.get(reverse("accounts:study_fields"), {"group_id": other_group.pk})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual([r["name"] for r in results], ["رشته اندپوینت"])
        # بدون گروه: همهٔ رشته‌های فعال
        response = self.client.get(reverse("accounts:study_fields"))
        names = [r["name"] for r in response.json()["results"]]
        self.assertIn("رشته اندپوینت", names)
        self.assertIn("رشته آزمایشی", names)

    def test_unemployed_job_skips_catalog_chain(self):
        """«بدون شغل / بیکار»: زنجیرهٔ کاتالوگ لازم نیست؛ عنوان ثابت ذخیره می‌شود."""
        form = JobForm({
            "is_unemployed": "on",
            "is_current": "on",
            "title": "",
            "sector_id": "",
            "industry_id": "",
            "category_id": "",
            "occupation_title_id": "",
            "specialization_id": "",
            "work_same_as_residence": "on",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["title"], "بدون شغل")

    def test_unemployed_without_chain_and_without_catalog_rejected(self):
        """بدون تیکِ بیکار و بدون انتخاب از فهرست، فرم رد می‌شود (رفتار قبلی)."""
        form = JobForm({
            "is_unemployed": "",
            "title": "",
            "sector_id": "",
            "industry_id": "",
            "category_id": "",
            "occupation_title_id": "",
            "specialization_id": "",
        })
        self.assertFalse(form.is_valid())

    def test_admin_can_list_and_create_catalog_records(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse("adminpanel:education_institutions_list")).status_code,
            200,
        )
        response = self.client.post(
            reverse("adminpanel:education_field_add"),
            {"name": "رشته جدید", "code": "NEW-FIELD", "study_group": str(self.group.pk), "is_active": "on"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StudyField.objects.filter(code="NEW-FIELD").exists())

    def test_non_staff_cannot_access_catalog(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("adminpanel:education_fields_list"))
        self.assertEqual(response.status_code, 302)

    def test_reward_is_granted_once(self):
        # پاداش تحصیلات طبق سرفصل «تعرفه امتیازها»: میزانِ سرفصل = امتیاز؛
        # معادل سکهٔ امتیاز (نرخ پیش‌فرض ۱) نیز به کیف پول تجمیع می‌شود.
        self.assertTrue(grant_education_completion_reward(self.user))
        self.assertFalse(grant_education_completion_reward(self.user))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.user_score, 3)
        # یک‌بار تبدیل و تجمیع شده است؛ تکرار دوباره اضافه نمی‌کند
        self.assertEqual(Wallet.objects.get(user=self.user).balance, Decimal("3.00"))
        self.assertEqual(
            CoinLedger.objects.filter(user=self.user, kind=CoinLedger.KIND_REWARD).count(),
            1,
        )
