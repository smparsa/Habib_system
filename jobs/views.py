"""نقاط پایانی JSON برای انتخاب سلسله‌مراتبی شغل در پروفایل (فقط کاربر لاگین‌شده)."""

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse

from .models import (
    Industry,
    JobCategory,
    JobSpecialization,
    JobTitle,
    Sector,
    breadcrumb,
)

# سطح → (مدل، فیلتر بر اساس والد)
_LEVELS = {
    "industry": (Industry, lambda pid: {"sector_id": pid}),
    "category": (JobCategory, lambda pid: {"industry_id": pid}),
    "occupation_title": (JobTitle, lambda pid: {"category_id": pid}),
    "specialization": (JobSpecialization, lambda pid: {"title_id": pid}),
}

_ORDER = (Sector, Industry, JobCategory, JobTitle, JobSpecialization)


@login_required(login_url="core:index")
def api_options(request):
    """
    گزینه‌های یک سطح بر اساس والد انتخاب‌شده:

        /jobs/api/options/?level=industry&parent_id=1      → صنایع یک حوزه
        /jobs/api/options/?level=category&parent_id=1       → دسته‌های یک صنعت
        /jobs/api/options/?level=occupation_title&...       → عناوین یک دسته
        /jobs/api/options/?level=specialization&...         → تخصص‌های مرتبط یک عنوان
    """
    level = request.GET.get("level", "")
    parent_id = request.GET.get("parent_id")

    if level == "sector":
        items = list(
            Sector.objects.filter(is_active=True).values("id", "name", "code")
        )
        return JsonResponse({"status": "ok", "items": items})

    if level not in _LEVELS or not parent_id:
        return JsonResponse({"status": "ok", "items": []})

    model, parent_filter = _LEVELS[level]
    items = list(
        model.objects.filter(is_active=True, **parent_filter(parent_id)).values(
            "id", "name", "code", "description"
        )
    )
    return JsonResponse({"status": "ok", "items": items})


def _chain_payload(sec, ind, cat, title, spec):
    """ساخت دیکشنری شناسه/نام پنج لایه (هرکدام ممکن است None باشد)."""
    nodes = (sec, ind, cat, title, spec)
    chain = {}
    for cls, node in zip(_ORDER, nodes):
        name = cls.__name__
        key = {
            Sector: "sector",
            Industry: "industry",
            JobCategory: "category",
            JobTitle: "occupation_title",
            JobSpecialization: "specialization",
        }[cls]
        chain[f"{key}_id"] = node.pk if node else None
        chain[f"{key}_name"] = node.name if node else ""
    return chain


@login_required(login_url="core:index")
def api_search(request):
    """
    جستجوی سریع عنوان/تخصص‌های مرتبط در کل کاتالوگ (دیتابیس‌محور، بدون بارگذاری همه در حافظه):

        /jobs/api/search/?q=برنامه

    نتیجه: برگ‌های منطبق با مسیر کامل هر کدام تا کاربر با یک کلیک بتواند
    تمام پنج لایه را پر کند.
    """
    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return JsonResponse({"status": "ok", "items": []})

    results = []
    seen = set()

    def add_result(level, node_id, label, path, chain, description=""):
        key = (level, node_id)
        if key in seen:
            return
        seen.add(key)
        results.append(
            {
                "level": level,
                "id": node_id,
                "label": label,
                "path": path,
                "chain": chain,
                "description": (description or "").strip(),
            }
        )

    specs = (
        JobSpecialization.objects.select_related("title__category__industry__sector")
        .filter(Q(name__icontains=q) | Q(description__icontains=q), is_active=True)
        .order_by("name")[:8]
    )
    for spec in specs:
        title = spec.title
        cat = title.category
        ind = cat.industry
        sec = ind.sector
        add_result(
                "specialization",
                spec.pk,
                spec.name,
                breadcrumb(
                    {
                        "sector": sec,
                        "industry": ind,
                        "category": cat,
                        "occupation_title": title,
                        "specialization": spec,
                    }
                ),
                _chain_payload(sec, ind, cat, title, spec),
                spec.description,
            )

    if len(results) < 12:
        titles = (
            JobTitle.objects.select_related("category__industry__sector")
            .filter(Q(name__icontains=q) | Q(description__icontains=q), is_active=True)
            .order_by("name")[:12]
        )
        for title in titles:
            cat = title.category
            ind = cat.industry
            sec = ind.sector
            add_result(
                "occupation_title",
                title.pk,
                title.name,
                breadcrumb(
                    {
                        "sector": sec,
                        "industry": ind,
                        "category": cat,
                        "occupation_title": title,
                        "specialization": None,
                    }
                ),
                _chain_payload(sec, ind, cat, title, None),
                title.description,
            )

    return JsonResponse({"status": "ok", "items": results[:14]})
