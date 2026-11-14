import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.forms import (
    AvatarUploadForm,
    ContactInfoForm,
    DocsSectionForm,
    EducationInfoForm,
    FamilyInfoForm,
    FinancialInfoForm,
    HealthSectionForm,
    JobForm,
    LocationForm,
    OrganizationSectionForm,
    PersonalInfoForm,
    SkillsSectionForm,
    TrainingSectionForm,
    UiSettingsForm,
    profile_ui_appearance,
    _store_country_en,
)
from accounts.models import Job, Profile, UserDocument
from core.models import InfoPage, SiteFeedback
from jobs.models import Sector
from magazine.models import MagazineTicket
from magazine.views import _mag_next_url


def index(request):
    """صفحه ورود / ثبت‌نام"""
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    return render(request, "core/index.html")


@login_required(login_url="core:index")
def dashboard(request):
    """داشبورد اصلی — آپلود عکس پروفایل به بخش «اطلاعات شخصی» پروفایل منتقل شده است"""
    profile_obj = request.user.profile

    # رنگ رابط برای متای hb-appearance در داشبورد (تم داشبورد ثابت است)
    _, ui_accent = profile_ui_appearance(profile_obj)

    # ماژول «تبلیغات»: هزینهٔ ثبت تبلیغ طبق تعرفهٔ «هزینه‌های سکهٔ ماژول‌ها»
    from wallet.models import FeatureCost

    ad_cost = FeatureCost.objects.filter(code="ad_submission", is_active=True).first()

    # ماژول «اسلایدشوی آمار داشبورد»: هزینهٔ ثبت اسلاید (تعرفهٔ اختصاصی؛
    # اگر ادمین تعریفش نکرده باشد، از تعرفهٔ تبلیغات پیروی می‌شود)
    slide_cost = (
        FeatureCost.objects.filter(code="stat_slide_submission", is_active=True).first()
        or ad_cost
    )

    return render(request, "core/dashboard.html", {
        "profile": profile_obj,
        "ui_accent": ui_accent,
        "ad_cost": ad_cost,
        "slide_cost": slide_cost,
        # تبلیغ‌های تأییدشدهٔ این کاربر برای فهرست «تبلیغات من»
        "my_ads": profile_obj.user.advertisements.all()[:10],
        # اسلایدهای این کاربر برای فهرست «اسلایدهای من» (جدیدترین)
        "my_stat_slides": profile_obj.user.stat_slides.order_by("-created_at")[:6],
        # تیکت‌های فوروارد مجلهٔ خوانده‌نشده برای نشانِ زنگوله در هدر
        "ticket_unread": MagazineTicket.objects.filter(
            recipient=request.user, is_read=False
        ).count(),
    })


@login_required(login_url="core:index")
def profile(request):
    """صفحه پروفایل کاربر - اعتبارسنجی فیلدهای ضروری + تأیید موقعیت مکانی"""
    profile_obj = request.user.profile
    jobs = (
        profile_obj.jobs.select_related(
            "sector", "industry", "category", "occupation_title", "specialization"
        ).all()
    )

    info_form = PersonalInfoForm(instance=profile_obj)
    family_form = FamilyInfoForm(instance=profile_obj)
    location_form = LocationForm(instance=profile_obj)
    avatar_form = AvatarUploadForm(instance=profile_obj)
    financial_form = FinancialInfoForm(instance=profile_obj)
    education_form = EducationInfoForm(instance=profile_obj)
    contact_form = ContactInfoForm(instance=profile_obj, user=request.user)
    # بخش‌های آزاد/اختیاری پروفایل — هرکدام با دکمهٔ ذخیرهٔ مستقل خودشان
    organization_form = OrganizationSectionForm(profile=profile_obj)
    skills_form = SkillsSectionForm(profile=profile_obj)
    training_form = TrainingSectionForm(profile=profile_obj)
    ui_settings_form = UiSettingsForm(profile=profile_obj)
    # اعتبارنامهٔ مجزای حسابداری: نمایش وضعیت فعلی در بخش «اطلاعات امنیتی»
    from accounts.acc_credentials import AccCredentialsForm, AccPasswordResetForm
    # نام کاربری موجود همیشه در فیلد نمایش داده می‌شود (خواندنی) تا کاربر آن را
    # فراموش نکند؛ در حالت تعریف جدید خالی است.
    acc_credentials_form = AccCredentialsForm(
        user=request.user,
        initial={"username": (request.user.acc_username or "")}
        if request.user.has_acc_credentials() else None,
    )
    # فرم ریست کلمهٔ عبور (فقط برای کاربرِ دارای اعتبارنامه استفاده می‌شود)
    acc_reset_form = AccPasswordResetForm(user=request.user)
    health_form = HealthSectionForm(profile=profile_obj)
    # «مدارک و فایل‌ها»: تنها برای کاربرانی که کد ملی ثبت‌شده دارند فعال است
    has_national_id = bool((profile_obj.national_id or "").strip())
    docs_form = DocsSectionForm(profile=profile_obj) if has_national_id else None
    documents = (
        profile_obj.documents.all() if has_national_id else UserDocument.objects.none()
    )
    # فرم شغل: موقعیت مکانی شغلی به‌صورت پیش‌فرض «همان محل سکونت» است
    job_form = JobForm(initial={
        "work_same_as_residence": True,
        "work_country": profile_obj.country or "ایران",
        "work_province": profile_obj.province or "",
        "work_city": profile_obj.city or "",
        "work_address": profile_obj.address or "",
    })

    # حالت ویرایش شغل (?edit=<id>): فرم با مقادیر ذخیره‌شدهٔ همان شغل پر می‌شود و
    # دادهٔ کامل آن برای بازخوانیِ سمت کلاینت (جابجایی رادیو ب↔ج بدون بازنویسی از
    # محل سکونت) در JSON (hb-job-edit-data) در اختیار app.js قرار می‌گیرد.
    job_edit = None
    job_edit_values = None
    edit_param = (request.GET.get("edit") or "").strip()
    if edit_param.isdigit():
        candidate = profile_obj.jobs.filter(pk=int(edit_param)).first()
        if candidate is not None and not candidate.is_unemployed:
            job_edit = candidate
            job_form = JobForm(instance=candidate)
            job_edit_values = {
                "employment_mode": candidate.employment_mode or "free",
                "organization": candidate.organization,
                "department": candidate.department,
                "employment_type": candidate.employment_type,
                "hire_date": candidate.hire_date.isoformat() if candidate.hire_date else "",
                "field_of_activity": candidate.field_of_activity,
                "skills": candidate.skills,
                "is_current": candidate.is_current,
                "free_address": candidate.free_address,
                "free_country": candidate.free_country or "ایران",
                "free_province": candidate.free_province,
                "free_city": candidate.free_city,
                "work_same_as_residence": candidate.work_same_as_residence,
                "work_country": candidate.work_country,
                "work_province": candidate.work_province,
                "work_city": candidate.work_city,
                "work_address": candidate.work_address,
                "work_gps_latitude": candidate.work_gps_latitude,
                "work_gps_longitude": candidate.work_gps_longitude,
                "work_gps_accuracy": candidate.work_gps_accuracy,
                "free_gps_latitude": candidate.free_gps_latitude,
                "free_gps_longitude": candidate.free_gps_longitude,
                "free_gps_accuracy": candidate.free_gps_accuracy,
                # زنجیرهٔ کاتالوگ (حوزه ← صنعت ← دسته ← عنوان ← تخصص‌های مرتبط):
                # برای پیش‌پرکردن فهرست سلسله‌مراتبی در حالت ویرایش (JS)
                "sector_id": candidate.sector_id,
                "industry_id": candidate.industry_id,
                "category_id": candidate.category_id,
                "occupation_title_id": candidate.occupation_title_id,
                "specialization_id": candidate.specialization_id,
                # توضیحات (description) سطوحِ زنجیره برای نمایش در پیش‌نمایش پروفایل
                "sector_description": (candidate.sector.description or "") if candidate.sector else "",
                "industry_description": (candidate.industry.description or "") if candidate.industry else "",
                "category_description": (candidate.category.description or "") if candidate.category else "",
                "occupation_title_description": (candidate.occupation_title.description or "") if candidate.occupation_title else "",
                "specialization_description": (candidate.specialization.description or "") if candidate.specialization else "",
                "title": candidate.title,
                "is_current": candidate.is_current,
            }

    if request.method == "POST":
        action = request.POST.get("action", "info")

        if action == "avatar":
            avatar_form = AvatarUploadForm(
                request.POST, request.FILES, instance=profile_obj
            )
            if avatar_form.is_valid():
                avatar_form.save()
                messages.success(request, "عکس پروفایل با موفقیت به‌روزرسانی شد.")
            else:
                messages.error(request, "خطا در آپلود عکس پروفایل.")
            return redirect("core:profile")
        elif action == "location":
            # تأیید کاربر: مقادیر استخراج‌شده (یا دستی) همین‌جا ذخیره می‌شوند
            location_form = LocationForm(request.POST, instance=profile_obj)
            if location_form.is_valid():
                # هم‌ارزسازی با جدول مرجع: اگر کاربر یا جریان GPS مقدارِ غیررسمی
                # (مثلاً انگلیسیِ سرویس بیرونی) وارد کرده باشد و رکوردِ مرجعِ هم‌ارز
                # پیدا شود، نام رسمی فارسی ذخیره می‌شود تا با فهرست انتخابی و
                # هدف‌گیری تیکت‌ها یکی باشد؛ مقدارهای بدون رکورد دست‌نخورده می‌مانند.
                from accounts.location_ref import (
                    canonicalize_geo,
                    city_en_for,
                    country_en_for,
                    province_en_for,
                )

                cleaned = location_form.cleaned_data
                geo = canonicalize_geo({
                    "country": cleaned.get("country") or "",
                    "province": cleaned.get("province") or "",
                    "city": cleaned.get("city") or "",
                })
                saved = location_form.save(commit=False)
                canonicalized = []
                for field in ("country", "province", "city"):
                    canonical = (geo.get(field) or "").strip()
                    current = (cleaned.get(field) or "").strip()
                    if canonical and canonical != current:
                        setattr(saved, field, canonical)
                        canonicalized.append(canonical)
                extra = dict(saved.extra_data or {})
                # «محل کار» از بخش اطلاعات مکانی حذف شده؛ موقعیت شغلی برای هر شغل
                # به‌صورت مجزا در بخش «اطلاعات شغلی» ثبت می‌شود.
                extra.pop("workplace", None)
                # ذخیرهٔ دوزبانهٔ مکان: مقدارِ رسمی فارسی در Profile.country/province/city
                # می‌ماند و نام انگلیسیِ هم‌ارزِ هرکدام در extra_data («*_en») ذخیره می‌شود
                # تا انتخاب‌گرها و بج‌های خلاصه با زبانِ فعالِ رابط نمایش داده شوند.
                for _f, _resolver in (
                    ("country", country_en_for),
                    ("province", province_en_for),
                    ("city", city_en_for),
                ):
                    _fa = (geo.get(_f) or cleaned.get(_f) or "").strip()
                    _en = (geo.get(f"{_f}_en") or "").strip() or _resolver(_fa)
                    if _en:
                        extra[f"{_f}_en"] = _en
                    else:
                        extra.pop(f"{_f}_en", None)
                # «دقت GPS» (متر) ثبت‌شده هنگام دریافت موقعیت — بدون فیلد مدل، در extra_data
                _gps_acc = (request.POST.get("gps_accuracy") or "").strip()
                if _gps_acc:
                    try:
                        extra["gps_accuracy"] = round(float(_gps_acc), 1)
                    except (TypeError, ValueError):
                        extra.pop("gps_accuracy", None)
                else:
                    extra.pop("gps_accuracy", None)
                saved.extra_data = extra
                saved.save()
                # موقعیت پیشنهادیِ ثبت‌نامی پس از تأیید، دیگر لازم نیست
                request.session.pop("pending_location", None)
                if canonicalized:
                    messages.success(
                        request,
                        "موقعیت مکانی با موفقیت ذخیره شد. نام محل به شکل رسمیِ "
                        + "فهرست مرجع ثبت شد: " + "، ".join(canonicalized) + ".",
                    )
                else:
                    messages.success(request, "موقعیت مکانی با موفقیت ذخیره شد.")
                return redirect("core:profile")
            messages.error(request, "لطفاً اطلاعات مکانی را به‌درستی وارد کنید.")
        elif action == "financial":
            # اطلاعات مالی (بانکی): فقط اعلام شماره شبا کافی است؛ کیف پول همین
            # شبا را برای واریز وجه می‌خواند و نام بانک از کد داخل شبا تشخیص داده می‌شود
            financial_form = FinancialInfoForm(request.POST, instance=profile_obj)
            if financial_form.is_valid():
                saved_profile = financial_form.save(commit=False)
                from wallet.services import iban_bank_name

                saved_profile.bank_name = iban_bank_name(saved_profile.iban)
                # «شماره شبا با نام و نام‌خانوادگی کنترل بشود»: در صورت مغایرت،
                # شبا تأیید و ذخیره نمی‌شود. در نبودِ سرویس، شبا با هشدار ذخیره
                # می‌شود تا پس از فعال‌شدن سرویس استعلام دوباره کنترل شود.
                from accounts.iban_verify import verify as verify_iban

                _first = getattr(saved_profile, "first_name", None)
                _last = getattr(saved_profile, "last_name", None)
                full_name = (
                    f"{getattr(_first, 'first_name_fa', '') or ''} "
                    f"{getattr(_last, 'familyname_fa', '') or ''}"
                ).strip()
                if full_name:
                    iban_result = verify_iban(full_name, saved_profile.iban)
                else:
                    from django.utils import timezone as _tz

                    iban_result = {
                        "available": False, "match": None,
                        "message": "نام و نام‌خانوادگی پروفایل کامل نیست؛ کنترل نامی انجام نشد.",
                        "checked_at": _tz.now().isoformat(),
                    }
                extra = dict(saved_profile.extra_data or {})
                extra["iban_verify"] = {
                    "match": iban_result.get("match"),
                    "available": iban_result.get("available"),
                    "checked_at": iban_result.get("checked_at"),
                }
                if iban_result.get("available") and iban_result.get("match") is False:
                    # مغایرت: شبا ذخیره نمی‌شود؛ فقط نتیجهٔ کنترل ثبت می‌شود.
                    # (نمونهٔ درون‌حافظه‌ای فرم مقدار جدید را دارد ولی ذخیره نمی‌شود؛
                    #  extra_data روی نمونهٔ موجودِ دیتابیس به‌روز می‌شود.)
                    profile_obj.extra_data = extra
                    profile_obj.save(update_fields=["extra_data"])
                    messages.error(
                        request,
                        "شبا تأیید نمی‌باشد: "
                        + (iban_result.get("message") or
                           "نام دارندهٔ این شبا با نام و نام‌خانوادگی شما هم‌خوانی ندارد."),
                    )
                    return redirect(f"{request.path}#financial")
                saved_profile.extra_data = extra
                saved_profile.save()
                if iban_result.get("available") and iban_result.get("match"):
                    messages.success(
                        request,
                        "شماره شبا با موفقیت ذخیره شد و با نام شما تطبیق داده شد.",
                    )
                else:
                    messages.warning(
                        request,
                        "شماره شبا ذخیره شد؛ اما کنترل خودکار نام انجام نشد. "
                        "پس از فعال‌شدن سرویس استعلام، شبای شما کنترل و تأیید خواهد شد.",
                    )
                # بازگشت به همان بخش باز و نمایان برای پیام تأیید
                return redirect(f"{request.path}#financial")
            messages.error(request, "لطفاً شماره شبا را به‌درستی وارد کنید.")
            # خطای شبا فقط در بخش «اطلاعات مالی» نشان داده شود و همان بخش باز و فوکوس شود
            return redirect(f"{request.path}#financial")
        elif action == "education":
            education_form = EducationInfoForm(request.POST, instance=profile_obj)
            if education_form.is_valid():
                education_form.save()
                from accounts.education import grant_education_completion_reward

                granted = grant_education_completion_reward(request.user, request=request)
                if granted:
                    messages.success(
                        request,
                        "اطلاعات تحصیلی ذخیره شد؛ سکه و امتیاز پاداش تکمیل تحصیلات به شما اختصاص یافت.",
                    )
                else:
                    messages.success(request, "اطلاعات تحصیلی با موفقیت ذخیره شد.")
                return redirect(f"{request.path}#education")
            messages.error(
                request,
                "لطفاً اطلاعات تحصیلی را به‌درستی وارد کنید.",
            )
            return redirect(f"{request.path}#education")
        elif action == "docs":
            # «مدارک و فایل‌ها»: ذخیرهٔ مستقل با دکمهٔ خودش — مشابه سایر بخش‌ها.
            # نیازمندی‌ها: کد ملی ثبت‌شده (پوشهٔ Docs/<کد ملی> یک‌بار ساخته می‌شود)،
            # فرمت مجاز هر نوع مدرک، و دست‌کم یک فایل انتخاب‌شده.
            docs_form = DocsSectionForm(
                request.POST, request.FILES, profile=profile_obj
            )
            if docs_form.is_valid():
                saved_count = 0
                replaced_types = []
                for field_name, f in docs_form.iter_files():
                    # هر نوع مدرک «آخرین فایل» را نگه می‌دارد: فایل‌های قبلی همان
                    # نوع حذف می‌شوند تا پوشهٔ کاربر شلوغ و گمراه‌کننده نشود.
                    existing = profile_obj.documents.filter(doc_type=field_name)
                    if existing.exists():
                        replaced_types.append(docs_form.fields[field_name].label)
                        for old in existing:
                            # فایل قبلی از دیسک هم پاک می‌شود تا پوشهٔ کاربر شلوغ نشود
                            if old.file:
                                old.file.delete(save=False)
                            old.delete()
                    doc = UserDocument(profile=profile_obj, doc_type=field_name)
                    doc.file.save(os.path.basename(f.name), f, save=False)
                    doc.original_name = os.path.basename(f.name)[:255]
                    doc.save()
                    saved_count += 1
                msg = f"{saved_count} فایل با موفقیت ذخیره شد."
                if replaced_types:
                    msg += " نسخهٔ قبلی این مدرک‌ها حذف شد: " + "، ".join(replaced_types) + "."
                messages.success(request, msg)
                return redirect(f"{request.path}#documents")
            first_err = next(iter(docs_form.errors.values()), [""])[0]
            messages.error(request, first_err or "خطا در بارگذاری مدارک.")
            return redirect(f"{request.path}#documents")
        elif action == "doc_delete":
            # حذف یک مدرکِ ذخیره‌شده (فایل از پوشهٔ کاربر هم پاک می‌شود)
            doc = get_object_or_404(
                UserDocument, pk=request.POST.get("doc_id"), profile=profile_obj
            )
            if doc.file:
                doc.file.delete(save=False)
            doc.delete()
            messages.success(request, "مدرک حذف شد.")
            return redirect(f"{request.path}#documents")
        elif action in ("organization", "skills", "training"):
            # بخش‌های آزاد/اختیاری: همهٔ فیلدها اختیاری‌اند؛ هر بخش دکمهٔ ذخیرهٔ
            # مجزای خودش را دارد و فقط داده‌های همان بخش نوشته می‌شود.
            form_cls = {
                "organization": OrganizationSectionForm,
                "skills": SkillsSectionForm,
                "training": TrainingSectionForm,
            }[action]
            section_form = form_cls(request.POST, profile=profile_obj)
            if section_form.is_valid():
                section_form.apply()
                profile_obj.save()
                messages.success(request, "اطلاعات با موفقیت ذخیره شد.")
            else:
                first_err = next(iter(section_form.errors.values()), [""])[0]
                messages.error(request, first_err or "خطا در ذخیرهٔ اطلاعات.")
            if action == "organization":
                organization_form = section_form
            elif action == "skills":
                skills_form = section_form
            else:
                training_form = section_form
            return redirect(f"{request.path}#{action}")
        elif action == "health":
            # اطلاعات سلامت: فقط «گروه خونی» اجباری است و بقیهٔ فیلدها آزاد و
            # اختیاری؛ ذخیرهٔ مستقل با دکمهٔ خودش، مشابه سایر بخش‌ها.
            health_form = HealthSectionForm(request.POST, profile=profile_obj)
            if health_form.is_valid():
                health_form.apply()
                profile_obj.save()
                messages.success(request, "اطلاعات سلامت با موفقیت ذخیره شد.")
            else:
                first_err = next(iter(health_form.errors.values()), [""])[0]
                messages.error(request, first_err or "خطا در ذخیرهٔ اطلاعات سلامت.")
            return redirect(f"{request.path}#health")
        elif action == "family":
            # اطلاعات خانواده: نام پدر/مادر و وضعیت تأهل (الزامی؛ منتقل‌شده از
            # اطلاعات شخصی) + فرزند/تکفل/تماس اضطراری؛ ذخیرهٔ مستقل با دکمهٔ خودش.
            family_form = FamilyInfoForm(request.POST, instance=profile_obj)
            if family_form.is_valid():
                family_form.save()
                # redirect با لنگر #family و پرچم family_saved: اعلان موفقیت فقط
                # داخل کارت «اطلاعات خانواده» می‌آید، نه در سایر بخش‌ها.
                request.session['family_saved'] = True
                return redirect(f"{request.path}#family")
            # اعلان خطا فقط در همین بخش (خانواده) نشان داده می‌شود — به جای
            # messages.error (که در همهٔ بخش‌های صفحه تکرار می‌شود)، فرمِ خطادار
            # دوباره رندر می‌شود و اعلان/خطای فیلدها داخل کارت «اطلاعات خانواده»
            # می‌آید (قالب + فوکوس در app.js). کد ملی‌ها اختیاری‌اند؛ پس وقتی
            # فیلدهای الزامی (نام پدر/مادر/وضعیت تأهل) تکمیل باشند، اعلانی نیست.
        elif action == "ui_settings":
            # تنظیمات شخصی سیستم: فقط تم نرم‌افزار و رنگ رابط کاربری قابل تغییرند
            # (سایر موارد پیش‌فرض و ثابت‌اند). ذخیره در extra_data["ui_settings"].
            ui_settings_form = UiSettingsForm(request.POST, profile=profile_obj)
            if ui_settings_form.is_valid():
                ui_settings_form.apply()
                profile_obj.save(update_fields=["extra_data"])
                messages.success(request, "تنظیمات شخصی با موفقیت ذخیره شد.")
                return redirect(f"{request.path}#ui_settings")
            messages.error(
                request,
                next(iter(ui_settings_form.errors.values()), [""])[0]
                or "خطا در ذخیرهٔ تنظیمات شخصی.",
            )
            return redirect(f"{request.path}#ui_settings")
        elif action == "acc_credentials":
            # اعتبارنامهٔ مجزای ماژول حسابداری (پروفایل ← اطلاعات امنیتی):
            # نام کاربری + کلمه عبور + تکرار؛ فقط برای ورود به حسابداری کاربرد دارد.
            # اعلان موفقیت/خطا یک‌بارمصرف است و فقط داخل همان کارت در بخش
            # «اطلاعات امنیتی» نشان داده می‌شود (نه در همهٔ بخش‌های پروفایل).
            acc_credentials_form = AccCredentialsForm(request.POST, user=request.user)
            if acc_credentials_form.is_valid():
                acc_credentials_form.apply()
                request.session["acc_credentials_notice"] = {
                    "level": "success",
                    "text": "اعتبارنامهٔ حسابداری ذخیره شد. این نام کاربری/کلمه عبور فقط "
                    "برای ورود به ماژول حسابداری قابل استفاده است.",
                }
                return redirect(f"{request.path}#security")
            first_err = next(iter(acc_credentials_form.errors.values()), [""])[0]
            first_field = next(iter(acc_credentials_form.errors), "")
            request.session["acc_credentials_notice"] = {
                "level": "error",
                "text": first_err or "خطا در ذخیرهٔ اعتبارنامهٔ حسابداری.",
                "field": first_field or "",
            }
            return redirect(f"{request.path}#security")
        elif action == "acc_reset_password":
            # «ریست کلمهٔ عبور حسابداری» (پروفایل ← اطلاعات امنیتی):
            # برای کاربرِ دارای اعتبارنامه، کلمهٔ عبور فعلی (فراموش‌شده) دور ریخته
            # می‌شود و رمز جدیدِ انتخابیِ خودِ کاربر (بدون نیاز به رمز فعلی) ذخیره
            # می‌گردد. نام کاربری دست‌نخورده می‌ماند.
            from accounts.acc_credentials import AccPasswordResetForm

            reset_form = AccPasswordResetForm(request.POST, user=request.user)
            if reset_form.is_valid():
                reset_form.apply()
                request.session["acc_credentials_notice"] = {
                    "level": "success",
                    "text": "کلمهٔ عبور حسابداری شما بازنشانی شد؛ از همین لحظه با کلمهٔ عبور "
                    "جدید وارد ماژول حسابداری شوید.",
                }
                return redirect(f"{request.path}#security")
            first_err = next(iter(reset_form.errors.values()), [""])[0]
            request.session["acc_credentials_notice"] = {
                "level": "error",
                "text": first_err or "خطا در بازنشانی کلمهٔ عبور.",
            }
            return redirect(f"{request.path}#security")
        elif action == "contact":
            # اطلاعات ارتباطی: شماره‌های تماس، وب‌سایت، شبکه‌های اجتماعی و
            # «کد ملی معرف» (که اینجا قابل تغییر است)
            contact_form = ContactInfoForm(
                request.POST, instance=profile_obj, user=request.user
            )
            if contact_form.is_valid():
                contact_form.save()
                messages.success(request, "اطلاعات ارتباطی با موفقیت ذخیره شد.")
                return redirect(f"{request.path}#communication")
            messages.error(
                request,
                "لطفاً اطلاعات ارتباطی را به‌درستی وارد کنید.",
            )
        else:
            # کد ملی پیش از اعتبارسنجی ثبت می‌شود: پاک‌سازی فرم نمونه را به‌روز
            # می‌کند و مقدارِ قدیم دیگر در دسترس نخواهد بود.
            _prev_nid = (profile_obj.national_id or "").strip()
            info_form = PersonalInfoForm(request.POST, instance=profile_obj)
            if info_form.is_valid():
                saved_profile = info_form.save(commit=False)
                # ایمیل خودکار بر اساس کد ملی
                if saved_profile.national_id:
                    saved_profile.email = f"{saved_profile.national_id}@HabibHub.com"
                # ذخیرهٔ دوزبانهٔ کشور (تابعیت/ملیت/اقامت دائم): مقدار رسمی فارسی
                # در فیلد خودش می‌ماند و نام انگلیسیِ هم‌ارز در extra_data ذخیره می‌شود.
                saved_profile.extra_data = _store_country_en(saved_profile)
                saved_profile.save()
                info_form.save_m2m()
                # «پاداش تکمیل اطلاعات شخصی و معرفی»: به محض ثبت کد ملی، به خودِ
                # کاربر سکه + امتیاز تعلق می‌گیرد (حتی بدون معرف) و اگر کاربر معرفی
                # داشته باشد به معرف هم پاداش می‌رسد؛ برای کاربر، معرف و ادمین هرکدام
                # جداگانه تیکت ساخته می‌شود (هر رویداد فقط یک‌بار؛ میزان طبق قانونِ
                # پاداشِ تعریف‌شده توسط ادمین).
                if saved_profile.national_id:
                    from accounts.referrals import grant_personal_info_rewards

                    grant_personal_info_rewards(request.user, request=request)
                    # «تغییر کد ملی»: اگر کد ملی قبلاً ثبت بوده و اکنون تغییر کرده
                    # است، کد جدید باید در سراسر برنامه جایگزین کد قدیم شود (ایمیل
                    # خودکار، کد ملی معرفِ معرفی‌شدگان، متن دفتر کل، پوشهٔ مدارک و
                    # مسیرهای رسانه) و رویداد حسابرسی هم ثبت گردد.
                    if (
                        _prev_nid
                        and _prev_nid != saved_profile.national_id
                        and info_form.national_id_locked is False
                    ):
                        from accounts.national_id_update import (
                            propagate_national_id_change,
                        )

                        try:
                            propagate_national_id_change(
                                saved_profile, _prev_nid, saved_profile.national_id,
                                request=request,
                            )
                            messages.success(
                                request,
                                f"کد ملی شما به‌روز شد ({_prev_nid} ← {saved_profile.national_id}) "
                                "و در سراسر سامانه جایگزین گردید.",
                            )
                        except Exception:  # noqa: BLE001 - جایگزینی نباید ذخیره را بشکند
                            import logging

                            logging.getLogger(__name__).exception(
                                "national id propagation failed"
                            )
                messages.success(request, "اطلاعات شخصی با موفقیت ذخیره شد.")
                # کاربری که با لینکِ مجله آمده بود و حالا کد ملی ثبت کرده → به همان مطلب برگرد
                if saved_profile.national_id:
                    mag_next = _mag_next_url(request)
                    if mag_next:
                        request.session.pop("mag_next", None)
                        return redirect(mag_next)
                return redirect("core:profile")
            messages.error(
                request,
                "لطفاً فیلدهای ضروری را به درستی تکمیل کنید.",
            )

    # موقعیت پیشنهادی شناسایی‌شده هنگام ثبت‌نام: فقط داخل فرم می‌رود (بدون ذخیرهٔ نهایی).
    # کاربر صحت آن را بررسی و با «تأیید و ذخیره موقعیت» تثبیت می‌کند.
    pending_location = None
    if request.method != "POST":
        pending = request.session.get("pending_location")
        if pending:
            pending_location = pending
            for key in (
                "address", "city", "province", "country",
                "postal_code", "latitude", "longitude",
            ):
                if pending.get(key) is not None and not location_form.initial.get(key):
                    location_form.initial[key] = pending[key]

    # اعلان موفقیت/خطای اعتبارنامهٔ حسابداری یک‌بارمصرف است: از session خوانده و
    # پاک می‌شود و فقط داخل کارت «نام کاربری و کلمه عبور ماژول حسابداری» در بخش
    # «اطلاعات امنیتی» نمایش داده می‌شود (نه در سایر بخش‌های پروفایل).
    acc_credentials_notice = request.session.pop("acc_credentials_notice", None)

    # اعلان موفقیت خانواده یک‌بارمصرف است: از session خوانده و پاک می‌شود
    family_saved = request.session.pop('family_saved', False)

    # ظاهر رابط (تم/رنگ) برای متای hb-appearance در قالب
    ui_theme, ui_accent = profile_ui_appearance(profile_obj)

    return render(request, "core/profile.html", {
        "profile": profile_obj,
        "ui_theme": ui_theme,
        "ui_accent": ui_accent,
        "jobs": jobs,
        "info_form": info_form,
        "family_form": family_form,
        "family_saved": family_saved,
        "ui_settings_form": ui_settings_form,
        "acc_credentials_form": acc_credentials_form,
        "acc_reset_form": acc_reset_form,
        "acc_credentials_set": request.user.has_acc_credentials(),
        "acc_password_updated_at": request.user.acc_password_updated_at,
        "acc_credentials_notice": acc_credentials_notice,
        "location_form": location_form,
        "avatar_form": avatar_form,
        "financial_form": financial_form,
        "education_form": education_form,
        "contact_form": contact_form,
        "job_form": job_form,
        # حالت ویرایش شغل (فرم با مقادیر ذخیره‌شدهٔ همان شغل)
        "job_edit": job_edit,
        "job_edit_values": job_edit_values,
        # «مدارک و فایل‌ها»
        "has_national_id": has_national_id,
        "docs_form": docs_form,
        "documents": documents,
        # بخش‌های آزاد/اختیاری
        "organization_form": organization_form,
        "skills_form": skills_form,
        "training_form": training_form,
        # اطلاعات سلامت (فقط گروه خونی اجباری)
        "health_form": health_form,
        # مقدار «محل سکونت» برای دکمهٔ «همان محل سکونت» (Current Location) در فرم شغل
        "job_residence": {
            "country": profile_obj.country or "ایران",
            "country_en": profile_obj.country_en,
            "province": profile_obj.province or "",
            "province_en": profile_obj.province_en,
            "city": profile_obj.city or "",
            "city_en": profile_obj.city_en,
            "address": profile_obj.address or "",
        },
        "pending_location": pending_location,
        "ticket_unread": MagazineTicket.objects.filter(
            recipient=request.user, is_read=False
        ).count(),
        # کلید عمومی نقشه برای سمت مرورگر (در صورت ست شدن روی سرور): اولویت با «نشان»
        # (NESHAN_API_KEY) است و در نبودِ آن Google Maps (GOOGLE_MAPS_API_KEY).
        # بدون کلید، نقشه نمایش داده نمی‌شود و پیام راهنما داخل قاب نقشه نشان داده می‌شود.
        # دقت GPS ثبت‌شدهٔ آخرین دریافت موقعیت (برای نمایش اولیه در بخش اطلاعات مکانی)
        "gps_accuracy": (profile_obj.extra_data or {}).get("gps_accuracy", ""),
        "neshan_api_key": os.environ.get("NESHAN_API_KEY", "").strip(),
        "google_maps_api_key": os.environ.get("GOOGLE_MAPS_API_KEY", "").strip(),
        # «الف) بدون شغل» فقط برای کاربرِ بدون شغل مجاز است؛ این نشانه هم در
        # قالب (غیرفعال‌کردن رادیو) و هم در JS (قفل زنده پس از افزودن/حذف شغل) استفاده می‌شود.
        "has_jobs": jobs.count() > 0,
        "can_add_job": jobs.count() < Job.MAX_PER_PROFILE,
        "max_jobs": Job.MAX_PER_PROFILE,
        # حوزه‌های فعال برای سطح اول انتخاب سلسله‌مراتبی شغل
        "catalog_sectors": Sector.objects.filter(is_active=True),
        # لوگوی/مستنداتِ شغلِ در دستِ ویرایش (یا جدیدترین شغل) برای پیش‌نمایش
        # «همان‌جا» در فرم شغل + شناسهٔ هدفِ فرم پنهانِ آپلود لوگو
        "job_doc_logo": (
            job_edit.job_logo_doc if job_edit is not None
            else (jobs.first().job_logo_doc if jobs.exists() else None)
        ),
        "latest_job_id": jobs.first().id if jobs.exists() else None,
    })


@login_required(login_url="core:index")
def profile_preview(request):
    """پیش‌نمایش اطلاعات من — فهرست تفکیکی همهٔ بخش‌های تکمیل‌شدهٔ پروفایل.

    هر فیلد تکمیل‌شده یک ردیفِ چک‌باکس‌دار است (پیش‌فرض: تیک‌خورده). کاربر
    می‌تواند ردیف‌ها را از پیش‌نمایش حذف کند و نتیجه را با دکمهٔ «دانلود PDF»
    (چاپ مرورگر) به فایل PDF تبدیل کند. فقط نمایش است — چیزی ذخیره نمی‌شود.
    """
    from .preview_data import preview_context

    return render(request, "core/profile_preview.html", preview_context(request.user.profile))


@login_required(login_url="core:index")
def info_page(request, slug):
    """نمایش صفحات اطلاعاتی/قانونی برنامه (درباره ما، حریم خصوصی و …).

    برای بازدیدکنندگانِ واردنشده هم قابل مشاهده است (با سربرگ ساده).
    """
    page = get_object_or_404(InfoPage, slug=slug, is_active=True)
    ctx = {"page": page}
    if request.user.is_authenticated:
        profile_obj = request.user.profile
        _, ctx["ui_accent"] = profile_ui_appearance(profile_obj)
        ctx["profile"] = profile_obj
        ctx["ticket_unread"] = MagazineTicket.objects.filter(
            recipient=request.user, is_read=False
        ).count()
    return render(request, "core/info_page.html", ctx)


@login_required(login_url="core:index")
def feedback(request):
    """نظرسنجی رضایت کاربران — ثبت بازخورد در دیتابیس."""
    already_sent = request.GET.get("sent") == "1"

    if request.method == "POST":
        try:
            satisfaction = int(request.POST.get("satisfaction") or 0)
        except (TypeError, ValueError):
            satisfaction = 0
        if satisfaction not in (1, 2, 3, 4, 5):
            messages.error(request, "لطفاً امتیاز رضایت کلی (ستاره‌ها) را انتخاب کنید.")
            return redirect("core:feedback")

        sources = [s for s in request.POST.getlist("sources") if s]
        SiteFeedback.objects.create(
            user=request.user,
            satisfaction=satisfaction,
            quality=request.POST.get("quality", "")[:20],
            support_speed=request.POST.get("support_speed", "")[:20],
            recommend=request.POST.get("recommend", "")[:10],
            sources=",".join(sources)[:200],
            improvements=(request.POST.get("improvements") or "").strip(),
        )
        messages.success(request, "نظر شما با موفقیت ثبت شد؛ سپاس از همراهی شما.")
        return redirect(f"{reverse('core:feedback')}?sent=1")

    profile_obj = request.user.profile
    _, ui_accent = profile_ui_appearance(profile_obj)
    return render(request, "core/feedback.html", {
        "profile": profile_obj,
        "ui_accent": ui_accent,
        "already_sent": already_sent,
        "ticket_unread": MagazineTicket.objects.filter(
            recipient=request.user, is_read=False
        ).count(),
    })
