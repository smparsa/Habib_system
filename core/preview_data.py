"""ساخت دادهٔ «پیش‌نمایش اطلاعات من».

خروجی: فهرستی از بخش‌ها؛ هر بخش شامل شناسه، عنوان، آیکون و ردیف‌هایی است که
هر ردیف (برچسب، مقدار) به‌صورت یک چک‌باکسِ پیش‌فرضِ تیک‌خورده نمایش داده می‌شود.
فقط فیلدهای «تکمیل‌شده» (و ضروری) در پیش‌نمایش می‌آیند؛ ردیف‌های خالی حذف‌اند
تا خروجی PDF تمیز بماند. هیچ داده‌ای اینجا ذخیره نمی‌شود — نمایش صرف است.
"""

from django.utils import timezone


def _clean(value):
    """مقدار غیرخالی به‌صورت رشته؛ None/خالی → None (ردیف حذف می‌شود)."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _num(value):
    """نمایش خوانای اعداد بدون صفرهای زائد اعشار."""
    if value in (None, ""):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return _clean(value)
    if f == int(f):
        return str(int(f))
    return ("%g" % f)


def _coord(lat, lng, acc=None):
    """مختصات GPS به‌صورت یک رشتهٔ یک‌خطی."""
    if lat in (None, "") or lng in (None, ""):
        return None
    text = "%.6f, %.6f" % (float(lat), float(lng))
    if acc:
        text += " (دقت: %s متر)" % _num(acc)
    return text


def _extra(profile):
    return profile.extra_data or {}


def _choice_label(choices, value):
    for code, label in choices or ():
        if code == value:
            return str(label)
    return _clean(value)


def build_preview_sections(profile):
    """فهرست بخش‌های پیش‌نمایش را از دادهٔ واقعی پروفایل می‌سازد."""
    p = profile
    extra = _extra(p)
    jobs = list(
        p.jobs.select_related(
            "sector", "industry", "category", "occupation_title", "specialization"
        ).all()
    )
    sections = []

    def add(sid, title, icon, rows):
        rows = [(label, _clean(value)) for label, value in rows]
        rows = [(label, value) for label, value in rows if value is not None]
        if rows:
            sections.append({"id": sid, "title": title, "icon": icon, "rows": rows})

    # ۱) اطلاعات شخصی (فیلدهای ضروری + تکمیل‌شده)
    personal = [
        ("نام", p.first_name),
        ("نام خانوادگی", p.last_name),
        ("پسوند فامیل", p.family_suffix),
        ("شهرت", p.fame_name),
        ("کد ملی", p.national_id),
        ("تاریخ تولد", p.date_of_birth),
        ("جنسیت", _choice_label(p._meta.get_field("gender").choices, p.gender)),
        ("تابعیت", p.citizenship),
        ("ملیت", p.nationality),
        ("اقامت دائم", p.permanent_residence),
        ("دین", _choice_label(p._meta.get_field("religion").choices, p.religion)),
        ("مذهب", _choice_label(p._meta.get_field("sect").choices, p.sect)),
        ("بیوگرافی", p.bio),
    ]
    add("personal", "اطلاعات شخصی", "bi-person-badge", personal)

    # ۲) اطلاعات خانواده
    family_extra = extra.get("family") or {}
    family = [
        ("نام پدر", p.father_name),
        ("نام مادر", p.mother_name),
        ("وضعیت تاهل", _choice_label(
            p._meta.get_field("marital_status").choices, p.marital_status)),
        ("تماس اضطراری", p.emergency_contact),
        ("تعداد همسر(های) قانونی", _num(family_extra.get("spouses_count"))),
        ("تعداد فرزندان پسر", _num(family_extra.get("sons_count"))),
        ("تعداد فرزندان دختر", _num(family_extra.get("daughters_count"))),
        ("افراد تحت تکفل", _num(family_extra.get("dependents_count"))),
        ("همسر(ها)", "، ".join(family_extra.get("spouses") or [])),
        ("فرزندان پسر", "، ".join(family_extra.get("sons") or [])),
        ("فرزندان دختر", "، ".join(family_extra.get("daughters") or [])),
    ]
    add("family", "اطلاعات خانواده", "bi-people", family)

    # ۳) اطلاعات مکانی (محل سکونت) — فیلدهای ضروری آدرس
    location = [
        ("کشور", p.country),
        ("استان", p.province),
        ("شهر / شهرستان", p.city),
        ("آدرس", p.address),
        ("کد پستی", p.postal_code),
        ("مختصات GPS", _coord(p.latitude, p.longitude,
                              extra.get("gps_accuracy"))),
    ]
    add("location", "اطلاعات مکانی (محل سکونت)", "bi-geo-alt", location)

    # ۴) اطلاعات ارتباطی
    social = extra.get("social") or {}
    social_labels = {
        "bale": "بله (Bale)", "eitaa": "ایتا (Eitaa)", "rubika": "روبیکا (Rubika)",
        "telegram": "تلگرام (Telegram)", "whatsapp": "واتساپ (WhatsApp)",
        "instagram": "اینستاگرام (Instagram)", "facebook": "فیس‌بوک (Facebook)",
        "x": "ایکس / توییتر (X)", "youtube": "یوتیوب (YouTube)",
        "linkedin": "لینکدین (LinkedIn)",
    }
    contact = [
        ("ایمیل", p.email),
        ("شماره موبایل", p.user.mobile_number),
        ("تلفن ثابت", p.phone),
        ("تلفن شخصی", p.personal_phone),
        ("وب‌سایت شخصی", extra.get("website")),
    ] + [(social_labels.get(key, key), value) for key, value in social.items()]
    add("contact", "اطلاعات ارتباطی", "bi-telephone", contact)

    # ۵) اطلاعات شغلی — هر شغل (الف/ب/ج) به‌صورت تفکیکی با فیلدهای ضروریِ همان حالت
    for index, job in enumerate(jobs, 1):
        mode = job.employment_mode or ("unemployed" if job.is_unemployed else "free")
        if mode == "unemployed" or job.is_unemployed:
            title = "شغل %d — الف) بدون شغل / بیکار" % index
            rows = [
                ("وضعیت اشتغال", "بدون شغل / بیکار هستم"),
                ("شغل فعلی", "بله" if job.is_current else None),
            ]
        elif mode == "employee":
            title = "شغل %d — ج) شغل وابسته (کارمندی)" % index
            rows = [
                ("سازمان / شرکت", job.organization),
                ("واحد سازمانی", job.department),
                ("نوع استخدام", _choice_label(
                    job._meta.get_field("employment_type").choices,
                    job.employment_type)),
                ("تاریخ شروع", job.hire_date),
                ("عنوان شغلی", job.title),
                ("حوزه فعالیت", job.field_of_activity),
                ("مهارت‌های تخصصی", job.skills),
                ("شغل فعلی", "بله" if job.is_current else None),
                ("مسیر شغل از فهرست سلسله‌مراتبی", job.catalog_breadcrumb),
                ("کشور محل کار", job.work_country),
                ("استان محل کار", job.work_province),
                ("شهر / شهرستان محل کار", job.work_city),
                ("آدرس محل کار سازمان", job.work_address),
                ("مختصات GPS محل کار (بخش ج)", _coord(
                    job.work_gps_latitude, job.work_gps_longitude,
                    job.work_gps_accuracy)),
            ]
        else:
            title = "شغل %d — ب) شغل آزاد" % index
            rows = [
                ("عنوان شغلی", job.title),
                ("حوزه فعالیت", job.field_of_activity),
                ("مهارت‌های تخصصی", job.skills),
                ("شغل فعلی", "بله" if job.is_current else None),
                ("مسیر شغل از فهرست سلسله‌مراتبی", job.catalog_breadcrumb),
                ("کشور محل کار (شغل آزاد)", job.free_country),
                ("استان محل کار (شغل آزاد)", job.free_province),
                ("شهر / شهرستان محل کار (شغل آزاد)", job.free_city),
                ("آدرس کامل محل کار (شغل آزاد)", job.free_address),
                ("مختصات GPS محل کار (شغل آزاد)", _coord(
                    job.free_gps_latitude, job.free_gps_longitude,
                    job.free_gps_accuracy)),
            ]
        add("job_%d" % job.pk, title, "bi-briefcase", rows)

    # ۶) اطلاعات سازمانی (بخش اختیاری)
    org = [
        ("شماره پرسنلی", p.personnel_id),
        ("کد سازمانی", p.org_code),
        ("مدیر مستقیم", (extra.get("organization") or {}).get("manager_name")),
        ("محل خدمت", (extra.get("organization") or {}).get("workplace")),
        ("شعبه", p.branch),
        ("گروه کاری", p.work_group),
        ("وضعیت همکاری", _choice_label(
            p._meta.get_field("employment_type").choices, p.employment_type)),
        ("تاریخ شروع همکاری", p.hire_date),
    ]
    add("organization", "اطلاعات سازمانی", "bi-building", org)

    # ۷) اطلاعات تحصیلی
    edu_extra = extra.get("education") or {}
    education = [
        ("آخرین مدرک", p.degree),
        ("گروه امتحانی", edu_extra.get("study_group")),
        ("مرکز دانشگاهی", p.university),
        ("رشته تحصیلی", p.field_of_study),
        ("گرایش تحصیلی", (
            p.study_specialization.name
            if p.study_specialization else p.study_specialization
        ) if p.study_specialization else None),
        ("سال فارغ‌التحصیلی", _num(p.graduation_year)),
        ("معدل", _num(p.gpa)),
        ("دوره‌های آموزشی", edu_extra.get("courses")),
        ("زبان‌های خارجی", edu_extra.get("languages")),
        ("سطح هر زبان", edu_extra.get("language_levels")),
    ]
    add("education", "اطلاعات تحصیلی", "bi-mortarboard", education)

    # ۸) مهارت‌ها
    skills_extra = extra.get("skills") or {}
    skills = [
        ("مهارت‌های فنی", skills_extra.get("technical_skills")),
        ("مهارت‌های نرم", skills_extra.get("soft_skills")),
        ("نرم‌افزارهای مسلط", skills_extra.get("software")),
        ("زبان‌های برنامه‌نویسی", skills_extra.get("programming_languages")),
        ("سطح مهارت", skills_extra.get("skill_level")),
        ("علایق شغلی", skills_extra.get("career_interests")),
    ]
    add("skills", "مهارت‌ها", "bi-tools", skills)

    # ۹) سوابق آموزشی
    training_extra = extra.get("training") or {}
    training = [
        ("کلاس‌ها", training_extra.get("classes")),
        ("وبینارها", training_extra.get("webinars")),
        ("گواهینامه‌ها", training_extra.get("certificates")),
        ("امتیازات آموزشی", training_extra.get("training_score")),
        ("آزمون‌ها", training_extra.get("exams")),
    ]
    add("training", "سوابق آموزشی", "bi-journals", training)

    # ۱۰) اطلاعات مالی (بانکی) — فقط وقتی واقعاً تکمیل شده (نام بانک مقدار
    # پیش‌فرض دارد؛ ملاکِ «تکمیل‌شده» بودن، شبا یا شماره حساب است)
    financial = []
    if (p.iban or p.account_number or "").strip():
        financial = [
            ("شماره شبا", p.iban),
            ("نام بانک", p.bank_name),
            ("شماره حساب", p.account_number),
        ]
    add("financial", "اطلاعات مالی (بانکی)", "bi-bank", financial)

    # ۱۱) اطلاعات سلامت
    health_extra = extra.get("health") or {}
    health = [
        ("گروه خونی", health_extra.get("blood_group")),
        ("حساسیت‌ها", health_extra.get("allergies")),
        ("وضعیت بیمه درمان", health_extra.get("insurance_status")),
        ("پزشک معتمد", health_extra.get("trusted_doctor")),
        ("شرایط اضطراری", health_extra.get("emergency_conditions")),
    ]
    add("health", "اطلاعات سلامت", "bi-heart-pulse", health)

    # ۱۲) مدارک و فایل‌ها
    documents = [
        (doc.get_doc_type_display() or doc.doc_type, doc.original_name)
        for doc in p.documents.all()
    ]
    add("documents", "مدارک و فایل‌ها", "bi-archive", documents)

    # ۱۳) تنظیمات شخصی
    ui = extra.get("ui_settings") or {}
    settings_rows = [
        ("تم نرم‌افزار", _choice_label(
            (("dark", "تیره"), ("light", "روشن")), ui.get("theme"))),
        ("رنگ رابط کاربری", ui.get("accent")),
    ]
    add("ui_settings", "تنظیمات شخصی", "bi-sliders2", settings_rows)

    return sections


def preview_context(profile):
    """کانتکست کامل صفحهٔ پیش‌نمایش."""
    sections = build_preview_sections(profile)
    return {
        "profile": profile,
        "sections": sections,
        "generated_at": timezone.localtime(),
        "row_count": sum(len(s["rows"]) for s in sections),
    }
