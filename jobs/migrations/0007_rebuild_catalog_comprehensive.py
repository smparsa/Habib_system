"""بازسازی کامل کاتالوگ مشاغل از فایل اکسل جامع («بانک جامع مشاغل ایران»).

ساختار فایل جدید (شیت «مشاغل_جامع»، ۶۲۵ ردیف):
    کد شغل | حوزه | دسته | عنوان شغلی | تخصص‌های مرتبط | توضیحات

نکته‌های مهم:
- فایل جدید ستون «صنعت» ندارد؛ برای حفظ پنج‌لایهٔ کاتالوگ (حوزه ← صنعت ← دسته ←
  عنوان ← تخصص‌های مرتبط) زیر هر حوزه یک صنعتِ «عمومی» ساخته می‌شود تا دسته‌ها
  همان‌طور که در اکسل آمده مستقیماً به حوزه متصل شوند.
- ستون «توضیحات» اکسل عیناً در فیلد «توضیحات» هر «تخصص مرتبط» همان ردیف ثبت
  می‌گردد (درخواست کارفرما).
- محتوای قبلی کاتالوگ حذف و با دادهٔ اکسل جایگزین می‌شود؛ کدها مثل قبل
  (SEC-/IND-/CAT-/TTL-/SPE-) بر اساس ترتیب ردیف‌ها تخصیص می‌یابند.
- شغل‌های کاربران (accounts.Job) که به کاتالوگ قبلی اشاره داشتند، پیش از حذف
  snapshot می‌شوند و پس از بازسازی به هم‌ارزشان در کاتالوگ جدید بازنگاشت می‌شوند
  (تطبیق دقیق نام، وگرنه نزدیک‌ترین بر اساس امتیاز توکن + فاصلهٔ ویرایشی)؛
  «کد اختصاصی شغل» هر شغل از شناسه‌های تازه بازمحاسبه می‌شود. زنجیره‌ای که
  هم‌ارز نداشته باشد پاک می‌شود (عنوان متنی شغل حفظ می‌ماند).

بازگشت به عقب (reverse): کاتالوگ حذف نمی‌شود (شغل‌های کاربران به آن اشاره
دارند)؛ هیچ‌کاری انجام نمی‌دهد.
"""

import os

from django.db import migrations

# مسیر فایل مرجع جدید (کنار فایل قبلی در seed_data نگه داشته می‌شود)
XLSX_FILENAME = "jobs_catalog_comprehensive.xlsx"
SHEET_NAME = "مشاغل_جامع"

# جداکننده‌های احتمالی ستون «تخصص‌های مرتبط»
SPEC_SPLITTERS = ("؛", ";", "،", ",")


def _xlsx_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "seed_data", XLSX_FILENAME
    )


def _read_excel_rows(path):
    """خواندن شیت «مشاغل_جامع»: (حوزه، دسته، عنوان شغلی، کلیدواژه‌ها، توضیحات)."""
    import warnings

    import openpyxl

    warnings.filterwarnings("ignore")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[SHEET_NAME] if SHEET_NAME in wb.sheetnames else wb.worksheets[0]
        rows = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                continue  # هدر
            if not row or not any(row):
                continue
            cells = list(row) + [None] * 6
            sector = str(cells[1] or "").strip()
            category = str(cells[2] or "").strip()
            title = str(cells[3] or "").strip()
            raw_specs = str(cells[4] or "").strip()
            description = str(cells[5] or "").strip()
            if not (sector and category and title):
                continue
            keywords = []
            for splitter in SPEC_SPLITTERS:
                raw_specs = raw_specs.replace(splitter, SPEC_SPLITTERS[0])
            for part in raw_specs.split(SPEC_SPLITTERS[0]):
                kw = part.strip()
                if kw and kw not in keywords:
                    keywords.append(kw)
            rows.append((sector, category, title, keywords, description))
        return rows
    finally:
        wb.close()


def _job_snapshot(Job):
    """شناسه‌های کاتالوگِ همهٔ شغل‌های کاربران را برمی‌گرداند."""
    return {
        job.pk: {
            "sector": job.sector_id,
            "industry": job.industry_id,
            "category": job.category_id,
            "title": job.occupation_title_id,
            "spec": job.specialization_id,
        }
        for job in Job.objects.all().only(
            "id", "sector_id", "industry_id", "category_id",
            "occupation_title_id", "specialization_id",
        )
    }


def _name_maps(Sector, Industry, JobCategory, JobTitle, JobSpecialization):
    """نام → pk برای هر پنج سطح (قبل از حذف)."""
    return {
        "sector": dict(Sector.objects.values_list("pk", "name")),
        "industry": dict(Industry.objects.values_list("pk", "name")),
        "category": dict(JobCategory.objects.values_list("pk", "name")),
        "title": dict(JobTitle.objects.values_list("pk", "name")),
        "spec": dict(JobSpecialization.objects.values_list("pk", "name")),
    }


def _tokens(text):
    """توکن‌های قابل مقایسهٔ یک نام (بدون نیم‌فاصله/پیشوند رایج)."""
    stop = {"حوزه", "تخصصی"}
    parts = (text or "").replace("\u200c", " ").replace("-", " ").split()
    return {p for p in parts if p and p not in stop}


def _match_score(old_name, candidate_name):
    """امتیاز تطبیق دو نام: توکن‌های یکسان + توکن‌های پیشوندی (اجرا ⊂ اجرای)."""
    old_tokens = _tokens(old_name)
    if not old_tokens:
        return 0
    cand_tokens = _tokens(candidate_name)
    score = len(old_tokens & cand_tokens)
    for ot in old_tokens:
        if ot in cand_tokens:
            continue
        for ct in cand_tokens:
            if len(ot) >= 4 and (ct.startswith(ot) or ot.startswith(ct)):
                score += 1
                break
    return score


def _levenshtein(a, b):
    """فاصلهٔ ویرایشی برای شکستن مساوی‌های امتیاز (نزدیک‌ترین رشته)."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        cur = [i + 1]
        for j, cb in enumerate(b):
            cur.append(min(prev[j + 1] + 1, cur[j] + 1, prev[j] + (ca != cb)))
        prev = cur
    return prev[-1]


def _nearest(old_name, name_to_pk):
    """نزدیک‌ترین نامِ موجود به نام قدیم (امتیاز توکن؛ مساوی‌ها با فاصلهٔ ویرایشی
    کوتاه‌تر). امتیاز صفر = بدون هم‌پوشانی → None."""
    top, top_score, top_dist = None, 0, None
    for name, pk in name_to_pk.items():
        score = _match_score(old_name, name)
        if score == 0:
            continue
        dist = _levenshtein(old_name, name)
        if score > top_score or (score == top_score and dist < top_dist):
            top, top_score, top_dist = pk, score, dist
    return top


def _chain_from_node(node):
    """زنجیرهٔ کامل (sector…spec) از عمیق‌ترین گرهٔ تطبیق‌یافته (والدها از خود رکورد)."""
    if node is None:
        return None
    if hasattr(node, "title_id"):  # JobSpecialization
        title = node.title
        spec_id = node.pk
    else:  # JobTitle
        title = node
        spec_id = None
    category = title.category
    industry = category.industry
    sector = industry.sector
    return (sector.pk, industry.pk, category.pk, title.pk, spec_id)


def _remap_jobs(Job, snapshot, old_names, spec_global, spec_by_title_pk, titles_by_name):
    """بازنگاشت شغل‌های کاربران به کاتالوگ تازه + بازمحاسبهٔ job_code.

    استراتژی (گرهٔ عمیق‌ترین تطبیق؛ والدها از خود رکورد استخراج می‌شوند):
    ۱) عنوان شغلی (لایهٔ ۴): هم‌نامِ عنوان تازه، وگرنه نزدیک‌ترین؛
    ۲) تخصص مرتبط (لایهٔ ۵): هم‌نام زیر همان عنوان، وگرنه هم‌نام در کل کاتالوگ،
       وگرنه نزدیک‌ترین (اول زیر عنوانِ تطبیق‌یافته، بعد کل کاتالوگ)؛
    ۳) در نبودِ هر هم‌پوشانی، زنجیره پاک می‌شود (عنوان متنی شغل حفظ می‌ماند).
    برای جلوگیری از تضاد قید یکتایی (profile، job_code)، اگر دو شغلِ یک پروفایل
    به زنجیرهٔ یکسان برسند، زنجیرهٔ شغلِ دوم پاک می‌شود (اولویت با اولی).
    """
    from jobs.models import JobSpecialization, JobTitle

    remapped = 0
    used_codes = {}  # profile_id → set of job_code
    for pk, snap in snapshot.items():
        chain = None
        old_spec_id = snap.get("spec")
        old_title_id = snap.get("title")
        old_title_name = old_names["title"].get(old_title_id) if old_title_id else None
        old_spec_name = old_names["spec"].get(old_spec_id) if old_spec_id else None

        # ۱) عنوان شغلی — هم‌نام، وگرنه نزدیک‌ترین (تساوی با بیشینهٔ هم‌پوشانی کلیدواژه)
        title_node = None
        if old_title_name:
            title_pk = titles_by_name.get(old_title_name)
            if title_pk is None:
                best, best_score, best_dist, best_kw = None, 0, None, -1
                for candidate in JobTitle.objects.all().prefetch_related("specializations"):
                    sc = _match_score(old_title_name, candidate.name)
                    if sc == 0:
                        continue
                    dist = _levenshtein(old_title_name, candidate.name)
                    kw = max(
                        [
                            _match_score(old_spec_name or "", s.name)
                            for s in candidate.specializations.all()
                        ]
                        or [0]
                    )
                    if (
                        sc > best_score
                        or (sc == best_score and dist < best_dist)
                        or (sc == best_score and dist == best_dist and kw > best_kw)
                    ):
                        best, best_score = candidate, sc
                        best_dist, best_kw = dist, kw
                title_pk = best.pk if best is not None else None
            if title_pk is not None:
                title_node = JobTitle.objects.filter(pk=title_pk).first()

        # ۲) تخصص مرتبط — دقیق زیر عنوان، وگرنه دقیق در کل کاتالوگ، وگرنه نزدیک‌ترین
        spec_node = None
        if old_spec_name:
            spec_pk = None
            if title_node is not None:
                spec_pk = spec_by_title_pk.get((title_node.pk, old_spec_name))
            if spec_pk is None:
                spec_pk = spec_global.get(old_spec_name)
            if spec_pk is None and title_node is not None:
                pool = {s.name: s.pk for s in title_node.specializations.all()}
                spec_pk = _nearest(old_spec_name, pool)
            if spec_pk is None:
                spec_pk = _nearest(old_spec_name, spec_global)
            if spec_pk is not None:
                spec_node = JobSpecialization.objects.filter(pk=spec_pk).first()

        # ۳) زنجیره از عمیق‌ترین گرهٔ تطبیق‌یافته (تخصص ← عنوان ← هیچ)
        if spec_node is not None:
            chain = _chain_from_node(spec_node)
        elif title_node is not None:
            chain = _chain_from_node(title_node)
        else:
            chain = None

        job = Job.objects.filter(pk=pk).first()
        if job is None:
            continue
        if chain is None:
            chain = (None, None, None, None, None)

        # جلوگیری از کد تکراری برای یک پروفایل (قید یکتای profile+job_code)
        code = "".join(str(x) for x in chain if x is not None)
        if code:
            seen = used_codes.setdefault(job.profile_id, set())
            if code in seen:
                chain = (None, None, None, None, None)
            else:
                seen.add(code)

        (
            job.sector_id,
            job.industry_id,
            job.category_id,
            job.occupation_title_id,
            job.specialization_id,
        ) = chain
        job.job_code = code if any(chain) else None
        job.save(update_fields=[
            "sector", "industry", "category", "occupation_title",
            "specialization", "job_code",
        ])
        remapped += 1
    return remapped


def rebuild_from_excel(apps, schema_editor):
    Sector = apps.get_model("jobs", "Sector")
    Industry = apps.get_model("jobs", "Industry")
    JobCategory = apps.get_model("jobs", "JobCategory")
    JobTitle = apps.get_model("jobs", "JobTitle")
    JobSpecialization = apps.get_model("jobs", "JobSpecialization")
    Job = apps.get_model("accounts", "Job")

    path = _xlsx_path()
    if not os.path.exists(path):
        raise RuntimeError(f"فایل مرجع کاتالوگ یافت نشد: jobs/seed_data/{XLSX_FILENAME}")
    rows = _read_excel_rows(path)
    if not rows:
        raise RuntimeError("فایل اکسل کاتالوگ خالی است؛ بازسازی انجام نشد.")

    # ۱) snapshot شغل‌های کاربران + نقشهٔ نام‌های کاتالوگ قدیم
    snapshot = _job_snapshot(Job)
    old_names = _name_maps(Sector, Industry, JobCategory, JobTitle, JobSpecialization)

    # ۲) حذف کامل کاتالوگ قبلی (اولاً جدا کردن FK شغل‌ها، سپس حذف از عمق به سطح)
    for job in Job.objects.filter(specialization__isnull=False).only("pk"):
        Job.objects.filter(pk=job.pk).update(specialization=None)
    for job in Job.objects.filter(occupation_title__isnull=False).only("pk"):
        Job.objects.filter(pk=job.pk).update(occupation_title=None)
    for job in Job.objects.filter(category__isnull=False).only("pk"):
        Job.objects.filter(pk=job.pk).update(category=None)
    for job in Job.objects.filter(industry__isnull=False).only("pk"):
        Job.objects.filter(pk=job.pk).update(industry=None)
    for job in Job.objects.filter(sector__isnull=False).only("pk"):
        Job.objects.filter(pk=job.pk).update(sector=None)

    JobSpecialization.objects.all().delete()
    JobTitle.objects.all().delete()
    JobCategory.objects.all().delete()
    Industry.objects.all().delete()
    Sector.objects.all().delete()

    # ۳) بازسازی از اکسل — کدها بر اساس ترتیب ردیف‌ها تخصیص می‌یابند
    sector_codes, industry_codes, category_codes = {}, {}, {}
    title_codes = {}
    spec_global = {}        # نام تخصص → pk (نخستین رخداد؛ برای تطبیق جهانی)
    spec_by_title_pk = {}   # (pk عنوان، نام تخصص) → pk (برای تطبیق دقیق زیر عنوان)
    new_maps = {"sector": {}, "industry": {}, "category": {}, "title": {}}
    spec_seq = 0

    for sector, category, title, keywords, description in rows:
        # صنعت در فایل جدید وجود ندارد؛ زیر هر حوزه یک صنعت «عمومی» ساخته می‌شود
        sec_id = new_maps["sector"].get(sector)
        if sec_id is None:
            code = sector_codes.setdefault(sector, f"SEC-{len(sector_codes) + 1:03d}")
            sec_id = Sector.objects.create(name=sector, code=code, is_active=True).pk
            new_maps["sector"][sector] = sec_id

        ind_name = "عمومی"
        ind_key = (sector, ind_name)
        ind_id = new_maps["industry"].get(ind_key)
        if ind_id is None:
            code = industry_codes.setdefault(ind_key, f"IND-{len(industry_codes) + 1:03d}")
            ind_id = Industry.objects.create(
                sector_id=sec_id, name=ind_name, code=code, is_active=True
            ).pk
            new_maps["industry"][ind_key] = ind_id

        cat_id = new_maps["category"].get(category)
        if cat_id is None:
            code = category_codes.setdefault(category, f"CAT-{len(category_codes) + 1:03d}")
            cat_id = JobCategory.objects.create(
                industry_id=ind_id, name=category, code=code, is_active=True
            ).pk
            new_maps["category"][category] = cat_id

        ttl_key = (category, title)
        ttl_id = new_maps["title"].get(ttl_key)
        if ttl_id is None:
            code = title_codes.setdefault(ttl_key, f"TTL-{len(title_codes) + 1:03d}")
            ttl_id = JobTitle.objects.create(
                category_id=cat_id, name=title, code=code, is_active=True
            ).pk
            new_maps["title"][ttl_key] = ttl_id

        for kw in keywords:
            if (ttl_id, kw) in spec_by_title_pk:
                continue
            spec_seq += 1
            spec_id = JobSpecialization.objects.create(
                title_id=ttl_id,
                name=kw,
                code=f"SPE-{spec_seq:03d}",
                description=description,
                is_active=True,
            ).pk
            spec_by_title_pk[(ttl_id, kw)] = spec_id
            spec_global.setdefault(kw, spec_id)

    # ۴) بازنگاشت شغل‌های کاربران به کاتالوگ تازه
    titles_by_name = {}
    for (_cat_name, title_name), pk in new_maps["title"].items():
        titles_by_name.setdefault(title_name, pk)

    _remap_jobs(Job, snapshot, old_names, spec_global, spec_by_title_pk, titles_by_name)


def noop_reverse(apps, schema_editor):
    """کاتالوگ بازسازی‌شده حذف نمی‌شود؛ شغل‌های کاربران به آن وابسته‌اند (PROTECT)."""


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0006_alter_jobspecialization_options_and_more"),
        # شغل‌های کاربران (accounts.Job) بازنگاشت می‌شوند؛ به آخرین مهاجرتِ
        # مدل Job در accounts وابسته است تا مدل در state موجود باشد.
        ("accounts", "0051_alter_job_specialization"),
    ]

    operations = [
        migrations.RunPython(rebuild_from_excel, noop_reverse),
    ]
