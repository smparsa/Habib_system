import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
import uuid

from django import forms
from django.utils import timezone
from django import forms
from django.core.files.uploadedfile import UploadedFile

from django.contrib.auth import login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from .location_ref import canonicalize_geo
from django.views.decorators.http import require_http_methods, require_POST

from .forms import JobForm, JobStatusForm
from .models import FameNameTbl, FamilynameTbl, FirstnameTbl, Job, JobStatus, UserDocument
from jobs.models import build_catalog_code
from magazine.views import _mag_next_url

User = get_user_model()

MOBILE_RE = re.compile(r"^09\d{9}$")

logger = logging.getLogger(__name__)


def _fetch_json(url, timeout=6, headers=None):
    """دریافت و پارس JSON از یک سرویس خارجی با هندل خطای امن."""
    try:
        req_headers = {"User-Agent": "HabibHub/1.0"}
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - هر خطای شبکه/پارس را خاموش کن
        logger.warning("geo provider failed: %s (%s)", url[:60], exc)
        return None


def _client_ip(request):
    """آدرس IP واقعی کاربر (پشت پروکسیِ X-Forwarded-For هم کار می‌کند)."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or ""


def _reverse_geo(lat=None, lng=None, ip=None):
    """
    تبدیل به آدرس (city/province/country) با این ترتیب:
    1. سرویس «نشان» (NESHAN_API_KEY) — مناسب ایران و بدون نیاز به VPN
    2. Google Maps Geocoding API (اگر GOOGLE_MAPS_API_KEY در سرور ست شده باشد)
    3. سرویس رایگان بدون کلید (BigDataCloud) برای مختصات
    4. سرویس بر اساس IP (IPAPI) وقتی مختصاتی در دسترس نیست
    کلیدها هرگز سمت کلاینت نمی‌روند؛ فقط اینجا در سرور استفاده می‌شوند.
    """
    result = {"provider": ""}
    neshan_key = os.environ.get("NESHAN_API_KEY", "").strip()
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()

    if neshan_key and lat is not None and lng is not None:
        d = _fetch_json(
            f"https://api.neshan.org/v5/reverse?lat={lat}&lng={lng}",
            headers={"Api-Key": neshan_key},
        )
        if d and d.get("status") == "OK":
            result = {
                "provider": "neshan",
                "address": d.get("formatted_address") or "",
                "city": d.get("city") or "",
                "province": d.get("state") or "",
                "country": "ایران",
            }
            if result.get("city") or result.get("province"):
                return result
            result = {"provider": ""}

    if api_key and lat is not None and lng is not None:
        params = urllib.parse.urlencode(
            {"latlng": f"{lat},{lng}", "key": api_key, "language": "fa"}
        )
        data = _fetch_json(
            "https://maps.googleapis.com/maps/api/geocode/json?" + params
        )
        if data and data.get("status") == "OK" and data.get("results"):
            top = data["results"][0]
            result["provider"] = "google"
            result["address"] = top.get("formatted_address") or ""
            for comp in top.get("address_components", []):
                types = comp.get("types", [])
                if "locality" in types and not result.get("city"):
                    result["city"] = comp.get("long_name") or comp.get("short_name")
                elif "administrative_area_level_1" in types and not result.get("province"):
                    result["province"] = comp.get("long_name")
                elif "country" in types and not result.get("country"):
                    result["country"] = comp.get("long_name")
                elif "postal_code" in types and not result.get("postal_code"):
                    result["postal_code"] = comp.get("long_name")
            if result:
                return result

    if lat is not None and lng is not None:
        d = _fetch_json(
            f"https://api.bigdatacloud.net/data/reverse-geocode-client"
            f"?latitude={lat}&longitude={lng}&localityLanguage=fa"
        )
        if d:
            city = d.get("city") or d.get("locality") or d.get("localityInfo", {}).get(
                "principalSubdivision", ""
            )
            return {
                "provider": "free",
                "city": city or "",
                "province": d.get("principalSubdivision") or "",
                "country": d.get("countryName") or "",
            }
        return result

    if ip:
        # حالت «فقط GPS مرورگر» (تنظیمات پنل مدیریت): بدون مختصاتِ ارسالیِ
        # کاربر، جایگزینِ IP استفاده نمی‌شود؛ نتیجه خالی برمی‌گردد.
        from .location_settings import ip_fallback_allowed

        if not ip_fallback_allowed():
            return result
        d = _fetch_json(f"https://ipapi.co/{ip}/json/")
        if d:
            return {
                "provider": "ip",
                "city": d.get("city") or "",
                "province": d.get("region") or "",
                "country": d.get("country_name") or "",
            }
    return result


def _search_geo(q, lat=None, lng=None):
    """
    جستجوی آدرس/مکان (forward geocode) برای جعبهٔ جستجوی نقشه با این اولویت:
    1. سرویس «نشان» (NESHAN_API_KEY) — بهترین برای آدرس‌های فارسی و ایران
    2. Google Places Text Search (اگر GOOGLE_MAPS_API_KEY در سرور ست شده باشد)
    3. سرویس رایگان بدون کلید (Nominatim / OpenStreetMap)
    کلیدها هرگز سمت کلاینت نمی‌روند؛ فقط اینجا در سرور استفاده می‌شوند.
    خروجی: {"provider": "neshan"|"google"|"free"|"", "items": [...]}
    هر مورد: {"title", "address", "lat", "lng", "type"}.
    """
    result = {"provider": "", "items": []}
    q = (q or "").strip()
    if not q:
        return result
    neshan_key = os.environ.get("NESHAN_API_KEY", "").strip()
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    # مختصات پایه برای مرتب‌سازی نتایجِ نزدیک (پیش‌فرض: تهران)
    bias_lat = lat if lat is not None else 35.6892
    bias_lng = lng if lng is not None else 51.3890

    if neshan_key:
        d = _fetch_json(
            "https://api.neshan.org/v5/search?term=" + urllib.parse.quote(q)
            + f"&lat={bias_lat}&lng={bias_lng}",
            headers={"Api-Key": neshan_key},
        )
        if d and isinstance(d.get("items"), list):
            items = []
            for it in d["items"]:
                loc = it.get("location") or {}
                x, y = loc.get("x"), loc.get("y")
                if x is None or y is None:
                    continue
                try:
                    x, y = float(x), float(y)
                except (TypeError, ValueError):
                    continue
                items.append(
                    {
                        "title": it.get("title") or "",
                        "address": it.get("address") or "",
                        "lat": round(y, 6),
                        "lng": round(x, 6),
                        "type": it.get("type") or "",
                    }
                )
            if items:
                result["provider"] = "neshan"
                result["items"] = items
                return result

    if api_key:
        params = urllib.parse.urlencode(
            {"query": q, "language": "fa", "region": "ir", "key": api_key}
        )
        d = _fetch_json(
            "https://maps.googleapis.com/maps/api/place/textsearch/json?" + params
        )
        if d and d.get("status") == "OK" and isinstance(d.get("results"), list):
            items = []
            for it in d["results"]:
                loc = it.get("geometry", {}).get("location") or {}
                if loc.get("lat") is None or loc.get("lng") is None:
                    continue
                items.append(
                    {
                        "title": it.get("name") or "",
                        "address": it.get("formatted_address") or "",
                        "lat": round(float(loc["lat"]), 6),
                        "lng": round(float(loc["lng"]), 6),
                        "type": "",
                    }
                )
            if items:
                result["provider"] = "google"
                result["items"] = items
                return result

    # سرویس رایگان: Nominatim (OpenStreetMap) — بدون کلید
    params = urllib.parse.urlencode(
        {"format": "json", "q": q, "limit": 5, "accept-language": "fa"}
    )
    d = _fetch_json("https://nominatim.openstreetmap.org/search?" + params)
    if isinstance(d, list):
        items = []
        for it in d:
            if it.get("lat") is None or it.get("lon") is None:
                continue
            try:
                lat_v, lng_v = float(it["lat"]), float(it["lon"])
            except (TypeError, ValueError):
                continue
            name = it.get("display_name") or it.get("name") or ""
            items.append(
                {
                    "title": name,
                    "address": name,
                    "lat": round(lat_v, 6),
                    "lng": round(lng_v, 6),
                    "type": it.get("type") or "",
                }
            )
        if items:
            result["provider"] = "free"
            result["items"] = items
    return result


def _pending_register_location(request, user):
    """
    پس از ساخت کاربر جدید: مختصات GPS (فیلدهای پنهان فرم ورود) یا IP کاربر را به آدرس
    تبدیل کرده و به‌صورت «موقعیت پیشنهادی» در session نگه می‌دارد. چیزی در دیتابیس
    ذخیره نمی‌شود؛ صفحهٔ پروفایل این مقادیر را داخل فرم «اطلاعات مکانی» می‌گذارد تا
    کاربر صحت آن را تأیید کند. انتخاب منبع (provider) بر اساس اولویت: GPS -> IP.
    """
    lat = request.POST.get("reg_lat")
    lng = request.POST.get("reg_lng")
    try:
        lat = float(lat) if lat not in (None, "") else None
        lng = float(lng) if lng not in (None, "") else None
    except (TypeError, ValueError):
        lat = lng = None

    ip = _client_ip(request)
    geo = _reverse_geo(lat=lat, lng=lng, ip=None if lat is not None else ip)
    # نام‌های شناسایی‌شده (فارسی یا انگلیسی) به نام رسمیِ فارسیِ جدول مرجع تبدیل
    # می‌شوند تا «موقعیت پیشنهادی» همیشه با فهرست انتخابیِ کاربر هم‌خوان باشد.
    geo = canonicalize_geo(geo or {})

    pending = {}
    if lat is not None and lng is not None:
        pending["latitude"] = round(lat, 6)
        pending["longitude"] = round(lng, 6)
    for key in ("address", "city", "province", "country", "postal_code"):
        if geo.get(key):
            pending[key] = geo[key]
    if ip:
        pending["last_ip"] = ip

    if pending.get("latitude") is not None or any(
        pending.get(k) for k in ("city", "province", "country")
    ):
        pending["source"] = "gps" if lat is not None else "ip"
        request.session["pending_location"] = pending
        return True
    return False


@require_http_methods(["POST"])
def login_view(request):
    """
    ورود/ثبت‌نام صرفاً با شماره موبایل - بدون ارسال و بررسی کد تایید (OTP).
    اگر کاربر با این شماره موجود باشد، وارد می‌شود؛ در غیر این صورت ساخته می‌شود.
    فیلد «معرف» فقط «کد ملی» کاربری را می‌پذیرد که پیش از این در برنامه ثبت‌نام
    کرده و کد ملی‌اش را در پروفایل ثبت کرده باشد.
    """
    mobile_number = (request.POST.get("mobile_number") or "").strip()
    referrer_nid = (
        (request.POST.get("referrer_national_id") or "").strip() or None
    )

    if not MOBILE_RE.match(mobile_number):
        messages.error(
            request, "شماره موبایل معتبر نیست. باید با 09 شروع شود و ۱۱ رقم باشد."
        )
        return redirect("core:index")

    # ارقام فارسی/عربی کد ملی → انگلیسی؛ فقط ۱۰ رقم پذیرفته می‌شود
    if referrer_nid:
        referrer_nid = referrer_nid.translate(
            str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
        )
        if not (len(referrer_nid) == 10 and referrer_nid.isdigit()):
            messages.error(
                request,
                "کد ملی معرف باید دقیقاً ۱۰ رقم (۰-۹) باشد.",
            )
            return redirect("core:index")
        # «کنترل کد ملی»: کدهای رزروشده (اختصاصی ادمین یا ممنوع برای همه) هرگز
        # نمی‌توانند «کد ملی معرف» باشند؛ معرف باید یک عضوِ عادیِ ثبت‌نام‌شده باشد.
        from .models import reserved_national_code

        if reserved_national_code(referrer_nid):
            messages.error(
                request,
                "این کد ملی رزرو شده است و نمی‌تواند به‌عنوان «کد ملی معرف» استفاده شود.",
            )
            return redirect("core:index")

    # کد ملی معرف باید متعلق به عضوی باشد که قبلاً ثبت‌نام کرده و کد ملی‌اش را
    # در «اطلاعات شخصی» پروفایل خود ثبت کرده است (فقط همین شناسه پذیرفته می‌شود)
    referrer_user = None
    if referrer_nid:
        from .models import Profile

        referrer_user = Profile.objects.select_related("user").filter(
            national_id=referrer_nid
        ).first()
        if referrer_user is None:
            messages.error(
                request,
                "کاربری با این کد ملی در حبیب‌هاب یافت نشد. برای «معرف»، کد ملیِ "
                "کاربری را وارد کنید که قبلاً در برنامه ثبت‌نام کرده و کد ملی‌اش را ثبت کرده است.",
            )
            return redirect("core:index")
        referrer_user = referrer_user.user
        if referrer_user.mobile_number == mobile_number:
            messages.error(request, "نمی‌توانید خودتان را معرفی کنید.")
            return redirect("core:index")

    user, created = User.objects.get_or_create(
        mobile_number=mobile_number,
        defaults={"referrer_national_id": referrer_nid},
    )
    # کاربرِ از قبل‌موجود که هنوز معرف ندارد: در اولین ورودِ بعدی قابل ثبت است
    if referrer_nid and not user.referrer_national_id:
        user.referrer_national_id = referrer_nid
        user.save(update_fields=["referrer_national_id"])
    login(request, user)

    if created:
        if _pending_register_location(request, user):
            messages.success(
                request,
                "موقعیت مکانی شما هنگام ثبت‌نام شناسایی شد؛ برای تثبیت نهایی در بخش "
                "«اطلاعات مکانی» پروفایل آن را تأیید کنید.",
            )
        messages.success(request, "ثبت‌نام و ورود با موفقیت انجام شد.")
    else:
        messages.success(request, "خوش آمدید.")

    # کاربر با لینکِ اشتراک‌گذاری‌شدهٔ مجله آمده است (?focus=...) → به همان مقصد برگرد
    mag_next = _mag_next_url(request)
    if mag_next:
        if user.profile.national_id:
            request.session.pop("mag_next", None)
            return redirect(mag_next)
        # کاربر تازه/بدون کد ملی: مقصد در session می‌ماند؛ پس از ثبت کد ملی در پروفایل
        # صفحهٔ پروفایل خودکار به همان مطلب برمی‌گرداند
        messages.warning(
            request,
            "برای باز کردن مطلبی که برایتان ارسال شده، ابتدا کد ملی خود را در "
            "بخش «اطلاعات شخصی» پروفایل ثبت کنید.",
        )
        return redirect("core:profile")

    # «بعد از ورود، مستقیم به داشبورد»؛ اگر هنوز اطلاعات شخصی (از جمله کد ملی)
    # ثبت نشده است، کاربر را همان‌جا به بخش «اطلاعات شخصی» پروفایل فوکوس می‌کنیم
    # تا ثبت کد ملی انجام شود (بدون آن، دسترسی به مجله/کیف پول ممکن نیست).
    if not user.profile.national_id:
        messages.warning(
            request,
            "برای فعال‌سازی کامل حساب، ابتدا اطلاعات شخصی (از جمله کد ملی) خود را "
            "در بخش «اطلاعات شخصی» پروفایل ثبت کنید.",
        )
        return redirect(reverse("core:profile") + "#personal-info")

    return redirect("core:dashboard")


@require_http_methods(["POST", "GET"])
def logout_view(request):
    logout(request)
    return redirect("core:index")


def _commit_job_form(request, profile, job, is_edit=False):
    """
    اعمال تکمیل‌های خودکار (مهارت/حوزه از روی کاتالوگ) و ذخیرهٔ نمونهٔ job.
    زنجیرهٔ ۵ لایه قبلاً توسط فراخواننده روی نمونه ست شده است.
    چند شغل می‌توانند هم‌زمان «شغل فعلی» باشند؛ فقط شرط «حداقل یکی» اعمال می‌شود.
    """
    # حداقل یک «شغل فعلی» برای هر پروفایل باید باقی بماند
    if not job.is_current and not profile.jobs.filter(is_current=True).exclude(pk=job.pk).exists():
        job.is_current = True
        messages.warning(
            request,
            "حداقل یک شغل باید «شغل فعلی» باشد؛ وضعیت همین شغل حفظ شد.",
        )
    # «بدون شغل / بیکار»: هیچ سطحی از کاتالوگ و جزئیات شغلی لازم نیست؛ پاک می‌شوند
    if getattr(job, "is_unemployed", False):
        for key in ("sector", "industry", "category", "occupation_title", "specialization"):
            setattr(job, key, None)
        job.organization = ""
        job.department = ""
        job.field_of_activity = ""
        job.skills = ""
    # پیشنهاد خودکار مهارت‌ها/حوزه از روی کاتالوگ در صورت خالی بودن
    if not job.skills and job.occupation_title and job.occupation_title.skill_tags:
        job.skills = "، ".join(job.occupation_title.skill_tags)
    if not job.field_of_activity and job.industry:
        job.field_of_activity = job.industry.name
    job.save()
    return job


def _job_code_conflict(profile, job):
    """
    آیا شغلِ جاری (با زنجیرهٔ کاتالوگِ ست‌شده) کد اختصاصی تکراری برای همین پروفایل دارد؟
    کد از روی رکوردهای دیتابیس ساخته می‌شود؛ بنابراین همین شغل قبلاً برای کاربر ثبت شده است.
    """
    code = build_catalog_code(
        job.sector_id,
        job.industry_id,
        job.category_id,
        job.occupation_title_id,
        job.specialization_id,
    )
    if not code:
        return False
    dup = Job.objects.filter(profile=profile, job_code=code)
    if job.pk:
        dup = dup.exclude(pk=job.pk)
    return dup.exists()


def _commit_job_employment_mode(request, job):
    """ثبت «نوع ثبت شغل» (رادیوی الف/ب/ج) روی مدل برای نمایش در کارت شغل."""
    job.employment_mode = _employment_mode(request)
    return job


def _employment_mode(request):
    """
    «نوع ثبت شغل» (رادیوی الف/ب/ج): unemployed = الف (بدون شغل)،
    employee = ج (فقط کارمندی)، free = ب (شغل آزاد — حالت پیش‌فرض).
    """
    if str(request.POST.get("is_unemployed") or "").strip().lower() in ("1", "on", "true", "yes"):
        return "unemployed"
    return (request.POST.get("employment_mode") or "free").strip().lower()


def _apply_job_location(request, job, profile):
    """ثبت «موقعیت مکانی + مختصات GPS» یک شغل (به‌صورت مجزا برای هر شغل).

    مطابق «نوع ثبت شغل» (رادیوی الف/ب/ج) هر بخش مقادیرِ مستقل خودش را دارد و
    مقادیرِ بخشِ غیرفعال پاک می‌شوند تا دو بخش کاملاً مجزا بمانند:
    - الف (بدون شغل): هیچ مکان/GPS ندارد؛ همه پاک می‌شود.
    - ب (شغل آزاد): آدرس/استان/شهر + GPS مجزای free_gps_*؛ GPS بخش «ج» پاک می‌شود.
    - ج (کارمندی): پیش‌فرض «همان محل سکونت» (کپی از پروفایل) یا مقادیر دستیِ فرم +
      GPS مجزای work_gps_*؛ مقادیر بخش «ب» و GPS آن پاک می‌شود.
    اگر مختصات GPS در POST نیامده باشد، GPSِ قبلیِ همان بخش (در ویرایش) دست‌نخورده می‌ماند.
    """
    from .location_ref import canonicalize_geo

    same = str(request.POST.get("work_same_as_residence") or "").strip().lower() in (
        "1", "on", "true", "yes",
    )
    mode = _employment_mode(request)

    def _float_or_none(value):
        try:
            return float(str(value).strip())
        except (TypeError, ValueError):
            return None

    def _int_or_none(value):
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    def _read_gps(prefix):
        """خواندن مختصاتِ گروه prefix از POST با کنترل بازهٔ معتبر جغرافیایی.

        بازهٔ معتبر: عرض ۹۰- تا ۹۰ و طول ۱۸۰- تا ۱۸۰؛ در صورت خالی/نامعتبر بودن،
        None برمی‌گردد (یعنی GPSِ قبلیِ همان بخش — در ویرایش — دست‌نخورده می‌ماند).
        """
        lat = _float_or_none(request.POST.get(f"{prefix}_latitude"))
        lng = _float_or_none(request.POST.get(f"{prefix}_longitude"))
        if (
            lat is None or lng is None
            or not (-90.0 <= lat <= 90.0)
            or not (-180.0 <= lng <= 180.0)
        ):
            return None
        acc = _int_or_none(request.POST.get(f"{prefix}_accuracy"))
        return {
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "acc": acc if acc is not None and acc >= 0 else None,
        }

    def _set_gps(prefix):
        """اعمال مختصاتِ معتبرِ گروه prefix (work_gps یا free_gps) روی فیلدهای مدل."""
        coord = _read_gps(prefix)
        if coord is None:
            return
        setattr(job, f"{prefix}_latitude", coord["lat"])
        setattr(job, f"{prefix}_longitude", coord["lng"])
        setattr(job, f"{prefix}_accuracy", coord["acc"])
        setattr(job, f"{prefix}_updated_at", timezone.now())

    # شغلِ «بدون شغل / بیکار» (الف): نه مکان دارد و نه GPS؛ هر دو بخش پاک می‌شوند
    if mode == "unemployed" or getattr(job, "is_unemployed", False):
        job.work_same_as_residence = False
        job.work_country = ""
        job.work_province = ""
        job.work_city = ""
        job.work_address = ""
        job.free_country = ""
        job.free_province = ""
        job.free_city = ""
        job.free_address = ""
        job.work_gps_latitude = None
        job.work_gps_longitude = None
        job.work_gps_accuracy = None
        job.work_gps_updated_at = None
        job.free_gps_latitude = None
        job.free_gps_longitude = None
        job.free_gps_accuracy = None
        job.free_gps_updated_at = None
        return job

    if mode == "employee":
        # فقط بخش «ج» (کارمندی): مقادیر و GPS بخش «ب» پاک می‌شود تا هیچ ارتباطی
        # با بخش ج نداشته باشد؛ سپس مکان و GPS مجزای همین بخش ثبت می‌شود.
        job.free_country = ""
        job.free_province = ""
        job.free_city = ""
        job.free_address = ""
        job.free_gps_latitude = None
        job.free_gps_longitude = None
        job.free_gps_accuracy = None
        job.free_gps_updated_at = None
        if same and (profile.province or "").strip() and (profile.city or "").strip():
            # اطلاعات مکانی محل زندگی کامل است → کپی و فقط تأیید (فقط بخش «ج»)
            job.work_same_as_residence = True
            job.work_country = profile.country or ""
            job.work_province = profile.province or ""
            job.work_city = profile.city or ""
            # فیلد ستاره‌دار «آدرس محل کار»: اگر آدرسِ محل سکونت خالی باشد، آدرسِ
            # دستیِ فرم نادیده گرفته نمی‌شود (وگرنه تایپ کاربر بدون ذخیره گم می‌شد).
            job.work_address = (profile.address or "").strip() or (request.POST.get("work_address") or "").strip()
        else:
            # پروفایل ناقص: مقادیر دستیِ فرم ذخیره می‌شوند؛ پرچم «همان محل سکونت»
            # به حالت خودش باقی می‌ماند (تیک کاربر → تأییدِ همان مقادیر دستی).
            geo = canonicalize_geo({
                "country": request.POST.get("work_country") or "",
                "province": request.POST.get("work_province") or "",
                "city": request.POST.get("work_city") or "",
            })
            job.work_country = (geo.get("country") or "").strip()
            job.work_province = (geo.get("province") or "").strip()
            job.work_city = (geo.get("city") or "").strip()
            job.work_address = (request.POST.get("work_address") or "").strip()
        _set_gps("work_gps")
        return job

    # فقط بخش «ب» (شغل آزاد): مقادیر و GPS بخش «ج» پاک می‌شود تا دو بخش مجزا بمانند
    job.work_same_as_residence = False
    job.work_country = ""
    job.work_province = ""
    job.work_city = ""
    job.work_address = ""
    job.work_gps_latitude = None
    job.work_gps_longitude = None
    job.work_gps_accuracy = None
    job.work_gps_updated_at = None
    free_geo = canonicalize_geo({
        "country": request.POST.get("free_country") or "",
        "province": request.POST.get("free_province") or "",
        "city": request.POST.get("free_city") or "",
    })
    job.free_country = (free_geo.get("country") or "").strip()
    job.free_province = (free_geo.get("province") or "").strip()
    job.free_city = (free_geo.get("city") or "").strip()
    job.free_address = (request.POST.get("free_address") or "").strip()
    _set_gps("free_gps")
    return job


def _job_location_error(job, mode=None):
    """الزامات مکانی برای ذخیرهٔ شغل (مطابق «نوع ثبت شغل» — رادیوی الف/ب/ج):
    - الف (بدون شغل/بیکار): بدون موقعیت مکانی — مستثنا از همهٔ الزامات.
    - ب (شغل آزاد): «آدرس کامل» + «استان» و «شهر/شهرستان»ِ بخش ب الزامی‌اند؛
      مقادیر بخش «ج» هیچ نقشی در اعتبارسنجی ندارند (بخش‌ها مجزا هستند).
    - ج (کارمندی): «استان» و «شهر/شهرستان» محل کارِ سازمان الزامی است؛
      مقادیر بخش «ب» هیچ نقشی در اعتبارسنجی ندارند (بخش‌ها مجزا هستند)."""
    if getattr(job, "is_unemployed", False):
        return None
    if mode is None:
        mode = "free" if (job.free_address or job.free_province or job.free_city) else "employee"
    if mode == "free":
        # بخش «ب»: آدرس + استان + شهر/شهرستانِ شغل آزاد
        if not (job.free_address or "").strip():
            return "تکمیل «آدرس کامل محل کار» در بخش «ب) شغل آزاد» الزامی است."
        if not (job.free_province or "").strip() or not (job.free_city or "").strip():
            return "تکمیل «استان» و «شهر/شهرستان» محل کارِ بخش «ب) شغل آزاد» الزامی است."
        return None
    # بخش «ج» (کارمندی): استان + شهر/شهرستان محل کار سازمان
    if not (job.work_province or "").strip() or not (job.work_city or "").strip():
        return "تکمیل «استان» و «شهر/شهرستان» محل کار برای ذخیرهٔ شغل الزامی است."
    return None


def _apply_job_gps(request, job):
    """(منسوخ — GPS اکنون در _apply_job_location اعمال می‌شود؛ حفظ‌شده برای سازگاری
    فراخوان‌های قدیمی و تست‌ها: همان منطق بخش «ج» را روی work_gps_* اجرا می‌کند.)"""
    if getattr(job, "is_unemployed", False):
        job.work_gps_latitude = None
        job.work_gps_longitude = None
        job.work_gps_accuracy = None
        job.work_gps_updated_at = None
        return job
    return _apply_job_location(request, job, job.profile if job.profile_id else None) or job


def _job_redirect():
    """بازگشت به پروفایل و لنگرِ بخش «اطلاعات شغلی» تا فوکوس صفحه همان‌جا بماند."""
    return redirect(reverse("core:profile") + "#jobs")


def _job_missing_ticket(request):
    """
    «شغل مورد نظر در فهرست نیست» → ساخت تیکت برای مدیران از طریق موتور تیکت.
    انتخاب فعلی کاربر از سلسله‌مراتب (حتی ناقص) همراه توضیحاتش برای ادمین ارسال می‌شود.
    """
    description = (request.POST.get("missing_job_description") or "").strip()
    if not description:
        messages.error(
            request,
            "برای ارسال تیکت، ابتدا عنوان شغل مورد نظر و توضیحات خود را بنویسید.",
        )
        return _job_redirect()

    from jobs.models import breadcrumb, build_catalog_code, resolve_selection

    def _int_or_none(value):
        try:
            return int(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None

    try:
        chain = resolve_selection(
            sector_id=_int_or_none(request.POST.get("sector_id")),
            industry_id=_int_or_none(request.POST.get("industry_id")),
            category_id=_int_or_none(request.POST.get("category_id")),
            occupation_title_id=_int_or_none(request.POST.get("occupation_title_id")),
            specialization_id=_int_or_none(request.POST.get("specialization_id")),
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return _job_redirect()

    code = build_catalog_code(
        chain["sector"].pk if chain["sector"] else None,
        chain["industry"].pk if chain["industry"] else None,
        chain["category"].pk if chain["category"] else None,
        chain["occupation_title"].pk if chain["occupation_title"] else None,
        chain["specialization"].pk if chain["specialization"] else None,
    )
    path = breadcrumb(chain)

    body = (
        "کاربر شغل مورد نظر خود را در فهرست سلسله‌مراتبی مشاغل نیافت و "
        "درخواست افزودن دارد.\n\n"
    )
    if path:
        body += f"مسیر انتخابی کاربر: {path}\n"
    if code:
        body += f"کد اختصاصیِ انتخاب فعلی: {code}\n"
    body += f"\nتوضیحات کاربر:\n{description}\n"

    from tickets.exceptions import TicketError
    from tickets.services import create_ticket

    try:
        ticket, _ = create_ticket(
            author=request.user,
            subject="درخواست افزودن شغل به فهرست مشاغل",
            description=body,
            category_code="suggestion",
            request=request,
        )
    except TicketError as exc:
        messages.error(request, str(exc))
        return _job_redirect()

    messages.success(
        request,
        f"تیکت شما با شمارهٔ {ticket.number} برای مدیران ارسال شد و انتخاب فعلی شما از فهرست "
        "نیز همراه درخواست ثبت شد. پس از بررسی، شغل به فهرست اضافه می‌شود.",
    )
    return _job_redirect()


@login_required(login_url="core:index")
@require_POST
def job_add(request):
    """
    افزودن یک شغل جدید به پروفایل کاربر - حداکثر ۳ شغل مجاز است.
    دکمهٔ «ارسال تیکت به مدیر» (شغل در فهرست نیست) نیز از همین فرم ارسال می‌شود.
    """
    # درخواست «شغل در فهرست نیست» → تیکت به مدیر؛ پیش از محدودیت تعداد مشاغل
    if request.POST.get("hb_job_action") == "ticket":
        return _job_missing_ticket(request)

    profile = request.user.profile
    current_count = profile.jobs.count()

    if current_count >= Job.MAX_PER_PROFILE:
        messages.error(
            request,
            f"حداکثر {Job.MAX_PER_PROFILE} شغل قابل ثبت است. برای افزودن شغل جدید، ابتدا یکی را حذف کنید.",
        )
        return _job_redirect()

    # «بدون شغل / بیکار» فقط وقتی مجاز است که کاربر هیچ شغلی ثبت نکرده باشد؛
    # اگر کاربرِ شغل‌دار با دستکاریِ فرم رادیوی الف را بفرستد، رد می‌شود.
    if (
        current_count > 0
        and str(request.POST.get("is_unemployed") or "").strip().lower()
        in ("1", "on", "true", "yes")
    ):
        messages.error(
            request,
            "چون حداقل یک شغل ثبت کرده‌اید، گزینهٔ «بدون شغل / بیکار هستم» قابل انتخاب نیست.",
        )
        return _job_redirect()

    form = JobForm(request.POST, request.FILES)
    if form.is_valid():
        chain = form.cleaned_data.get("_chain") or {}
        job = form.save(commit=False)
        job.profile = profile
        job.order = current_count
        # پنج لایهٔ کاتالوگ (حوزه → صنعت → دسته → عنوان → تخصص‌های مرتبط)
        for key in ("sector", "industry", "category", "occupation_title", "specialization"):
            setattr(job, key, chain.get(key))
        # نوع ثبت شغل (الف/ب/ج) برای نمایش در کارت شغل
        _commit_job_employment_mode(request, job)
        # کد اختصاصی (از شناسهٔ رکوردهای دیتابیس) برای همین کاربر باید یکتا بماند؛
        # همان شغلِ کاتالوگ فقط یک‌بار قابل ثبت است، ولی بین کاربران تکرار می‌شود.
        if _job_code_conflict(profile, job):
            messages.error(
                request,
                "این شغل قبلاً برای شما ثبت شده است (کد اختصاصی یکسانی دارد). "
                "برای افزودن شغل تازه، از فهرست یک شغل دیگر انتخاب کنید.",
            )
            return _job_redirect()
        # موقعیت مکانی + مختصات GPS شغلی (مطابق نوع ثبت شغل: الف/ب/ج) — یک‌جا اعمال می‌شود
        _apply_job_location(request, job, profile)
        loc_error = _job_location_error(job, _employment_mode(request))
        if loc_error:
            messages.error(request, loc_error)
            return _job_redirect()
        _commit_job_form(request, profile, job)
        messages.success(
            request,
            "شغل جدید با موفقیت ثبت شد."
            + (f" ({job.catalog_breadcrumb})" if job.catalog_breadcrumb else ""),
        )
    else:
        errors = [
            message
            for field_messages in form.errors.values()
            for message in field_messages
        ]
        messages.error(
            request,
            errors[0] if errors else "اطلاعات وارد شده معتبر نیست. لطفاً دوباره تلاش کنید.",
        )

    return _job_redirect()


@login_required(login_url="core:index")
@require_POST
def job_edit(request, job_id):
    """
    ویرایش یک شغل ثبت‌شده (فقط مالک همان پروفایل): عنوان/زنجیرهٔ کاتالوگ و سایر فیلدها.
    دکمهٔ «ارسال تیکت به مدیر» در حالت ویرایش نیز تیکتِ درخواست شغل می‌سازد.
    """
    # درخواست «شغل در فهرست نیست» → تیکت به مدیر (در حالت ویرایش هم کار می‌کند)
    if request.POST.get("hb_job_action") == "ticket":
        return _job_missing_ticket(request)

    profile = request.user.profile
    job = get_object_or_404(Job, id=job_id, profile=profile)

    # «بدون شغل / بیکار» فقط وقتی مجاز است که کاربر هیچ شغل دیگری نداشته باشد؛
    # اگر کاربرِ شغل‌دار در ویرایش رادیوی الف را بفرستد، رد می‌شود.
    mode_raw = (request.POST.get("employment_mode") or "free").strip().lower()
    if (
        profile.jobs.exclude(pk=job.pk).exists()
        and (
            str(request.POST.get("is_unemployed") or "").strip().lower() in ("1", "on", "true", "yes")
            or mode_raw == "unemployed"
        )
    ):
        messages.error(
            request,
            "چون حداقل یک شغل ثبت کرده‌اید، گزینهٔ «بدون شغل / بیکار هستم» قابل انتخاب نیست.",
        )
        return _job_redirect()

    form = JobForm(request.POST, request.FILES, instance=job)
    if form.is_valid():
        chain = form.cleaned_data.get("_chain") or {}
        job = form.save(commit=False)
        # پنج لایهٔ کاتالوگ (حوزه → صنعت → دسته → عنوان → تخصص‌های مرتبط)
        for key in ("sector", "industry", "category", "occupation_title", "specialization"):
            setattr(job, key, chain.get(key))
        # نوع ثبت شغل (الف/ب/ج) برای نمایش در کارت شغل
        _commit_job_employment_mode(request, job)
        if _job_code_conflict(profile, job):
            messages.error(
                request,
                "این شغل قبلاً برای شما ثبت شده است (کد اختصاصی یکسانی دارد). "
                "برای تغییر، یک شغل دیگر از فهرست انتخاب کنید.",
            )
            return _job_redirect()
        # به‌روزرسانی موقعیت مکانی + مختصات GPS شغلی (مطابق نوع ثبت شغل: الف/ب/ج)
        _apply_job_location(request, job, profile)
        loc_error = _job_location_error(job, _employment_mode(request))
        if loc_error:
            messages.error(request, loc_error)
            return _job_redirect()
        _commit_job_form(request, profile, job, is_edit=True)
        messages.success(
            request,
            "تغییرات شغل ذخیره شد."
            + (f" ({job.catalog_breadcrumb})" if job.catalog_breadcrumb else ""),
        )
    else:
        errors = [
            message
            for field_messages in form.errors.values()
            for message in field_messages
        ]
        messages.error(
            request,
            errors[0] if errors else "اطلاعات وارد شده معتبر نیست. لطفاً دوباره تلاش کنید.",
        )

    return _job_redirect()


@login_required(login_url="core:index")
@require_POST
def job_delete(request, job_id):
    """حذف یکی از مشاغل ثبت‌شدهٔ کاربر (فقط مالک همان پروفایل)."""
    job = get_object_or_404(Job, id=job_id, profile=request.user.profile)
    was_current = job.is_current
    # فایل‌های وابسته (عکس پروفایل شغل + عکس استتوس‌ها) قبل از حذف رکورد از دیسک پاک می‌شوند
    if job.photo:
        job.photo.delete(save=False)
    for status in job.statuses.all():
        if status.image:
            status.image.delete(save=False)
    job.delete()
    # «حداقل یکی از مشاغل باید شغل فعلی باشد»: اگر شغلِ حذف‌شده «شغل فعلی» بود و
    # هیچ شغل فعلی دیگری نمانده، یکی از مشاغل باقی‌مانده به‌صورت خودکار «شغل فعلی» می‌شود.
    if was_current and not request.user.profile.jobs.filter(is_current=True).exists():
        next_current = (
            request.user.profile.jobs.filter(is_current=False)
            .order_by("order", "id")
            .first()
        )
        if next_current is not None:
            next_current.is_current = True
            next_current.save(update_fields=["is_current"])
    messages.success(request, "شغل حذف شد.")
    return _job_redirect()


@login_required(login_url="core:index")
@require_POST
def job_photo_delete(request, job_id):
    """حذف عکس پروفایل یک شغل (فقط مالک همان پروفایل) — فایل هم از دیسک پاک می‌شود."""
    job = get_object_or_404(Job, id=job_id, profile=request.user.profile)
    if job.photo:
        job.photo.delete(save=True)
        messages.success(request, "عکس پروفایل شغل حذف شد.")
    else:
        messages.info(request, "این شغل عکس پروفایلی ندارد.")
    return _job_redirect()


@login_required(login_url="core:index")
@require_POST
def job_photo_add(request, job_id):
    """بارگذاری/تعویض عکس پروفایل یک شغل — مستقیماً از کارت شغل (مشابه «افزودن استتوس»)."""

    job = get_object_or_404(Job, id=job_id, profile=request.user.profile)
    photo = request.FILES.get("photo")
    if not photo:
        messages.error(request, "برای ثبت عکس پروفایل شغل، ابتدا یک فایل عکس انتخاب کنید.")
        return _job_redirect()

    form = JobForm({}, files={"photo": photo})
    photo_field = form.fields["photo"]
    try:
        cleaned = photo_field.clean(photo, None)
    except forms.ValidationError as exc:
        messages.error(request, "; ".join(exc.messages) or "فایل عکس معتبر نیست.")
        return _job_redirect()
    if not isinstance(cleaned, UploadedFile):
        messages.error(request, "فایل عکس معتبر نیست.")
        return _job_redirect()

    # «فقط یک عکس»: فایل قبلی قبل از ذخیرهٔ نسخهٔ جدید از دیسک پاک می‌شود.
    if job.photo:
        job.photo.delete(save=False)
    job.photo = cleaned
    job.save(update_fields=["photo"])
    messages.success(request, f"عکس پروفایل شغل «{job.title}» ثبت شد.")
    return _job_redirect()


@login_required(login_url="core:index")
@require_POST
def job_photo_status_add(request, job_id):
    """بارگذاری عکس استتوس (حداکثر یک مورد) برای یک شغل."""

    job = get_object_or_404(Job, id=job_id, profile=request.user.profile)
    image = request.FILES.get("image")
    if not image:
        messages.error(request, "برای ثبت استتوس، ابتدا یک عکس انتخاب کنید.")
        return _job_redirect()

    form = JobStatusForm(data=request.POST, files={"image": image})
    image_field = form.fields["image"]
    try:
        cleaned = image_field.clean(image, None)
    except forms.ValidationError as exc:
        messages.error(request, "; ".join(exc.messages) or "عکس استتوس معتبر نیست.")
        return _job_redirect()
    if not isinstance(cleaned, UploadedFile):
        messages.error(request, "عکس استتوس معتبر نیست.")
        return _job_redirect()

    # «حداکثر یک استتوس»: فایل قبلی قبل از ذخیرهٔ نسخهٔ جدید از دیسک پاک می‌شود.
    if job.active_statuses.exists():
        oldest = job.active_statuses.order_by("created_at").first()
        oldest.image.delete(save=False)
        oldest.delete()
    status = JobStatus(image=cleaned, caption="")
    status.job = job
    status.save()
    messages.success(request, f"استتوس جدید برای «{job.title}» ثبت شد؛ ۲۴ ساعت بعد به‌صورت خودکار حذف می‌شود.")
    return _job_redirect()


@login_required(login_url="core:index")
@require_POST
def job_status_add(request, job_id):
    """انتشار یک استتوس ۲۴ ساعته برای یک شغل (شبیه استتوس واتساپ)."""

    job = get_object_or_404(Job, id=job_id, profile=request.user.profile)
    image = request.FILES.get("image")
    if not image:
        messages.error(request, "برای انتشار استتوس، ابتدا یک عکس انتخاب کنید.")
        return _job_redirect()

    form = JobStatusForm(data=request.POST, files={"image": image})
    image_field = form.fields["image"]
    try:
        cleaned = image_field.clean(image, None)
    except forms.ValidationError as exc:
        messages.error(request, "; ".join(exc.messages) or "عکس استتوس معتبر نیست.")
        return _job_redirect()
    if not isinstance(cleaned, UploadedFile):
        messages.error(request, "عکس استتوس معتبر نیست.")
        return _job_redirect()

    status = form.save(commit=False)
    status.job = job
    # انقضای ۲۴ ساعت محاسبه سمت مدل، پس فیلد expires_at از فرم حذف شده است.
    status.save()
    messages.success(request, f"استتوس جدید برای «{job.title}» ثبت شد؛ ۲۴ ساعت بعد به‌صورت خودکار حذف می‌شود.")
    return _job_redirect()


@login_required(login_url="core:index")
@require_POST
def job_status_delete(request, job_id, status_id):
    """حذف یک استتوس ۲۴ ساعته محدود شده به مالک شغل."""
    job = get_object_or_404(Job, id=job_id, profile=request.user.profile)
    status = get_object_or_404(
        JobStatus, id=status_id, job=job, expires_at__gt=timezone.now()
    )
    if status.image:
        status.image.delete(save=False)
    status.delete()
    messages.success(request, "استتوس حذف شد.")
    return _job_redirect()


@login_required(login_url="core:index")
@require_POST
def document_add(request):
    """آپلود یک فایل مدرک به بخش «مدارک و فایل‌ها»: ذخیره در «docs/<کد ملی>/<نام فایل>».

    نام فایل خروجی توسط پایگاه فایل سمت سرور تولید می‌شود (چکsumming + UUID) تا
    نام آپلودشده تکراری یا ناامن باشد. در دیتابیس نگه می‌داریم «original_name»
    و «file» (مسیر نسبی). پوشهٔ «<کد ملی>» در DOCS_ROOT در اولین ذخیره ساخته می‌شود.
    """
    profile = request.user.profile
    if not (profile.national_id or "").strip():
        messages.error(request, "برای بارگذاری مدارک ابتدا کد ملی را در بخش اطلاعات شخصی ثبت کنید.")
        return redirect("core:profile")

    form = DocsSectionForm(request.POST, request.FILES, profile=profile)
    if not form.is_valid():
        errors = [
            message
            for field_messages in form.errors.values()
            for message in field_messages
        ]
        messages.error(request, errors[0] if errors else "آپلود ناموفق بود.")
        return redirect("core:profile")

    doc = None
    for field_name, f in form.iter_files():
        uploaded = forms.files.UploadedFile(f.file, f.name)
        ext = os.path.splitext(f.name)[1].lower() or ".bin"
        safe = f"{profile.national_id}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:12]}{ext}"
        # ذخیرهٔ محتویِ فایل در پوشهٔ «<کد ملی>/<نام فایل جدید>» داخل استوریجِ مسیر
        # یونیکِ سمت سرور تولید‌شده. پیش‌نمایش نام فایل روی سمت کلاینت می‌تواند از
        # فایلِ اصل (original_name) استفاده کند تا کاربر بفهمد چه چیزی آپلود کرد.
        user_docs_storage().save(f"{profile.national_id}/{safe}", uploaded)
        doc = UserDocument.objects.create(
            profile=profile,
            file=f"{profile.national_id}/{safe}",
            folder_name=profile.national_id,
            original_name=f.name,
        )
    if doc is None:
        messages.error(request, "هیچ فایلی برای ذخیره انتخاب نشده است.")
        return redirect("core:profile")
    messages.success(request, "مدارک شما با موفقیت ذخیره شد.")
    return redirect("core:profile")


@login_required(login_url="core:index")
@require_POST
def job_toggle_current(request, job_id):
    """
    تغییر وضعیت «شغل فعلی» برای هر شغل در هر زمان.
    چند شغل می‌توانند هم‌زمان «شغل فعلی» باشند؛ فقط آخرین شغل فعلی قابل برداشتن نیست.
    """
    profile = request.user.profile
    job = get_object_or_404(Job, id=job_id, profile=profile)
    if job.is_current and profile.jobs.filter(is_current=True).count() <= 1:
        messages.warning(
            request,
            "حداقل یک شغل باید «شغل فعلی» باشد؛ نمی‌توان آخرین شغل فعلی را غیرفعال کرد.",
        )
    else:
        job.is_current = not job.is_current
        job.save(update_fields=["is_current"])
        if job.is_current:
            messages.success(request, f"«{job.title}» به‌عنوان «شغل فعلی» علامت خورد.")
        else:
            messages.success(request, f"وضعیت «شغل فعلی» از «{job.title}» برداشته شد.")
    return _job_redirect()


@login_required(login_url="core:index")
@require_POST
def job_document_add(request):
    """آپلود لوگوی/مستندات شغل به‌صورت جداگانه از مدارک دیگر + نمایش فوریِ همان‌جا.

    فایل‌ها در پوشهٔ DOCS/<کد ملی کاربر>/jobs/<رتبه شغل>/photos ذخیره می‌شوند.
    نام فایل خروجی توسط پایگاهِ فایل سمت سرور تولید می‌شود (زمان + UUID) تا
    نام آپلودشده تکراری یا ناامن نباشد. پوشهٔ «jobs/<رتبه>/photos/» در اولین ذخیره
    ساخته می‌شود. در دیتابیس تنها مسیرِ نسبی و نامِ اصلی ذخیره می‌شود.
    «فقط یکی»: لوگوی قبلیِ همان شغل (همان پوشه) حذف و نسخهٔ جدید جایگزین می‌شود.

    هدفِ شغل از «job_id» فرم پنهانِ پایین صفحه خوانده می‌شود (در حالت ویرایش،
    همان شغل؛ در حالت افزودن، جدیدترین شغل — app.js آن را به‌روز می‌کند).
    درخواست AJAX (X-Requested-With) با JSON پاسخ داده می‌شود تا app.js بتواند
    پیش‌نمایش را «همان‌جا» بدون رفرش صفحه به‌روزرسانی کند.
    """
    profile = request.user.profile
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    def _redirect_back():
        return redirect("core:profile")

    if not (profile.national_id or "").strip():
        msg = "برای آپلود لوگوی شغل ابتدا کد ملی را در بخش اطلاعات شخصی ثبت کنید."
        if is_ajax:
            return JsonResponse({"ok": False, "error": msg}, status=400)
        messages.error(request, msg)
        return _redirect_back()

    job_id = request.POST.get("job_id")
    if not job_id or not str(job_id).isdigit():
        msg = "برای آپلود لوگو، ابتدا شغل را ثبت کنید؛ سپس فایل را انتخاب کنید."
        if is_ajax:
            return JsonResponse({"ok": False, "error": msg}, status=400)
        messages.error(request, msg)
        return _redirect_back()

    job = Job.objects.filter(id=int(job_id), profile=profile).first()
    if job is None:
        msg = "شغل مورد نظر یافت نشد."
        if is_ajax:
            return JsonResponse({"ok": False, "error": msg}, status=404)
        messages.error(request, msg)
        return _redirect_back()

    doc_file = request.FILES.get("job_doc")
    if not doc_file:
        msg = "برای ثبت لوگوی شغل، ابتدا یک فایل انتخاب کنید."
        if is_ajax:
            return JsonResponse({"ok": False, "error": msg}, status=400)
        messages.error(request, msg)
        return _redirect_back()

    # پوشهٔ مقصد: «jobs/<رتبه>/photos» تحت پوشهٔ کد ملی کاربر
    folder = f"jobs/{job.order}/photos"
    ext = os.path.splitext(doc_file.name)[1].lower() or ".bin"
    safe = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:12]}{ext}"
    file_path = f"{folder}/{safe}"

    user_docs_storage().save(file_path, doc_file)

    # «فقط یکی»: هر فایل قبلی در همین پوشه (لوگوی قبلیِ همین شغل) حذف می‌شود.
    for existing in UserDocument.objects.filter(profile=profile, file__startswith=folder):
        existing.file.delete(save=False)
        existing.delete()

    doc = UserDocument.objects.create(
        profile=profile,
        file=file_path,
        original_name=doc_file.name,
        doc_type="job_photo",
    )
    if is_ajax:
        return JsonResponse({
            "ok": True,
            "doc_id": doc.pk,
            "url": doc.file.url,
            "name": doc.original_name,
            "message": f"لوگوی/مستندات شغل «{job.title}» با موفقیت ذخیره شد.",
        })
    messages.success(request, f"لوگوی/مستندات شغل «{job.title}» با موفقیت ذخیره شد.")
    return _redirect_back()


@login_required(login_url="core:index")
@require_POST
def job_document_delete(request, doc_id):
    """حذف لوگوی/مستندات شغل (فقط مالک) — فایل هم از دیسک پاک می‌شود."""
    doc = get_object_or_404(UserDocument, id=doc_id, profile=request.user.profile)
    if (doc.doc_type or "") != "job_photo":
        messages.error(request, "این فایل لوگوی شغل نیست.")
        return redirect("core:profile")
    doc.file.delete(save=False)
    doc.delete()
    messages.success(request, "لوگوی/مستندات شغل حذف شد.")
    return redirect("core:profile")


@login_required(login_url="core:index")
@require_POST
def document_delete(request):
    """حذف یک مدارک کاربر (فقط مالک پروفایل): فایل از دیسک هم پاک می‌شود."""
    profile = request.user.profile
    doc_id = request.POST.get("doc_id")
    if not doc_id:
        messages.error(request, "شناسه مدرک الزامی است.")
        return redirect("core:profile")

    doc = get_object_or_404(UserDocument, id=doc_id, profile=profile)
    if doc.file:
        doc.file.delete(save=False)
    doc.delete()
    messages.success(request, "مدارک حذف شدند.")
    return redirect("core:profile")


@login_required(login_url="core:index")
@require_POST
def location_lookup(request):
    """
    استخراج موقعیت از GPS مرورگر (یا IP) و تبدیل به آدرس سمت سرور — بدون ذخیره.
    نتیجه به‌صورت JSON برمی‌گردد تا کاربر در صفحهٔ پروفایل آن را بررسی و تأیید کند
    (کلید Google Maps فقط سمت سرور استفاده می‌شود؛ سرویس‌های رایگان جایگزین هستند).
    """
    lat = request.POST.get("lat") or request.POST.get("latitude")
    lng = request.POST.get("lng") or request.POST.get("longitude")
    try:
        lat = float(lat) if lat not in (None, "") else None
        lng = float(lng) if lng not in (None, "") else None
    except (TypeError, ValueError):
        lat = lng = None

    geo = _reverse_geo(
        lat=lat,
        lng=lng,
        ip=None if lat is not None else _client_ip(request),
    )
    # هم‌ارزسازی به رکورد مرجع (فارسی رسمی) پیش از نمایش در فرم برای تأیید کاربر
    geo = canonicalize_geo(geo or {})

    return JsonResponse(
        {
            "status": "ok" if (geo or lat is not None) else "empty",
            "latitude": round(lat, 6) if lat is not None else None,
            "longitude": round(lng, 6) if lng is not None else None,
            "address": geo.get("address") or "",
            "city": geo.get("city") or "",
            "province": geo.get("province") or "",
            "country": geo.get("country") or "",
            "postal_code": geo.get("postal_code") or "",
            "source": "gps" if lat is not None else "ip",
            "provider": geo.get("provider") or "",
        }
    )


@login_required(login_url="core:index")
@require_POST
def location_place_search(request):
    """
    جستجوی آدرس فارسی برای جعبهٔ جستجوی بالای نقشه (forward geocode) — بدون ذخیره.
    اولویت سرویس‌ها: «نشان» → Google Places → رایگان (Nominatim). نتیجه به‌صورت
    JSON با فهرست موارد {title, address, lat, lng} برمی‌گردد تا کاربر یکی را انتخاب
    کند و نشانگر نقشه همان‌جا بیفتد. کلیدها هرگز سمت کلاینت نمی‌روند.
    """
    q = (request.POST.get("q") or "").strip()
    if not q:
        return JsonResponse({"status": "empty", "provider": "", "items": []})
    lat = request.POST.get("lat") or request.POST.get("latitude")
    lng = request.POST.get("lng") or request.POST.get("longitude")
    try:
        lat = float(lat) if lat not in (None, "") else None
        lng = float(lng) if lng not in (None, "") else None
    except (TypeError, ValueError):
        lat = lng = None

    res = _search_geo(q, lat=lat, lng=lng)
    return JsonResponse(
        {
            "status": "ok" if res["items"] else "empty",
            "provider": res["provider"],
            "items": res["items"],
        }
    )


@login_required(login_url="core:index")
@require_POST
def location_update(request):
    """
    دریافت مختصات GPS از مرورگر کاربر، تبدیل به آدرس (سمت سرور و با کلید «نشان»
    در صورت ست بودن NESHAN_API_KEY یا گوگل)، و ذخیرهٔ موقعیت در پروفایل کاربر.
    اگر مختصاتی نیامد (مثلاً کاربر به GPS دسترسی نداد)، با IP سرور تلاش می‌کند.
    """
    profile = request.user.profile

    lat = request.POST.get("lat") or request.POST.get("latitude")
    lng = request.POST.get("lng") or request.POST.get("longitude")
    try:
        lat = float(lat) if lat not in (None, "") else None
        lng = float(lng) if lng not in (None, "") else None
    except (TypeError, ValueError):
        lat = lng = None

    ip = _client_ip(request)
    geo = _reverse_geo(lat=lat, lng=lng, ip=None if lat is not None else ip)
    # ذخیره با نام رسمیِ فارسیِ جدول مرجع (نه نگارش انگلیسیِ سرویسِ بیرونی)
    geo = canonicalize_geo(geo or {})

    # «دقت GPS» (متر) که مرورگر همراه مختصات می‌فرستد — در extra_data نگه‌داری می‌شود
    accuracy = request.POST.get("accuracy") or request.POST.get("gps_accuracy")
    try:
        accuracy = round(float(accuracy), 1) if accuracy not in (None, "") else None
    except (TypeError, ValueError):
        accuracy = None

    update_fields = ["updated_at"]
    extra = dict(profile.extra_data or {})
    extra_changed = False
    if lat is not None and lng is not None:
        profile.latitude = round(lat, 6)
        profile.longitude = round(lng, 6)
        update_fields += ["latitude", "longitude"]
    if accuracy is not None:
        extra["gps_accuracy"] = accuracy
        extra_changed = True
    if geo.get("city"):
        profile.city = geo["city"]
        update_fields.append("city")
    if geo.get("province"):
        profile.province = geo["province"]
        update_fields.append("province")
    if geo.get("country"):
        profile.country = geo["country"]
        update_fields.append("country")
    # ذخیرهٔ دوزبانهٔ مکان: مقدار رسمی فارسی در Profile.country/province/city می‌ماند
    # و نام انگلیسیِ هم‌ارزِ هرکدام کنارش (extra_data["*_en"]) ذخیره می‌شود تا بج‌های
    # خلاصه و انتخاب‌گرها با زبانِ فعالِ رابط نمایش داده شوند.
    for _f in ("country", "province", "city"):
        _en = (geo.get(f"{_f}_en") or "").strip()
        if _en:
            extra[f"{_f}_en"] = _en
            extra_changed = True
    if ip:
        profile.last_ip = ip
        update_fields.append("last_ip")
    if extra_changed:
        profile.extra_data = extra
        update_fields.append("extra_data")
    profile.location_updated_at = timezone.now()
    update_fields.append("location_updated_at")
    profile.save(update_fields=update_fields)

    return JsonResponse(
        {
            "status": "ok",
            "latitude": profile.latitude,
            "longitude": profile.longitude,
            "city": profile.city,
            "province": profile.province,
            "country": profile.country,
            "country_en": (extra.get("country_en") or "").strip()
            if extra_changed else profile.country_en,
            "province_en": (extra.get("province_en") or "").strip()
            if extra_changed else profile.province_en,
            "city_en": (extra.get("city_en") or "").strip()
            if extra_changed else profile.city_en,
            "source": "gps" if lat is not None else "ip",
            "provider": geo.get("provider") or "",
        }
    )


@login_required
@require_http_methods(["GET"])
def name_search(request):
    """جستجوی زندهٔ نام/نام خانوادگی برای انتخاب‌گر خودکار فیلدهای نام پروفایل.

    با هر تایپ کاربر، این ویو دیتابیس جدول‌های مرجع (FirstnameTbl/FamilynameTbl)
    را با یک Query واقعی جستجو می‌کند (فارسی یا لاتین) و حداکثر «limit» نتیجه برمی‌
    گرداند؛ نتایجِ با شروعِ یکسان با عبارت در اولویت‌اند. «gender» فقط برای «نام
    پدر/مادر» فرستاده می‌شود تا فهرست از قبل جنسیت‌دار شود (همان محدودیت فهرست
    های سمت سرور فرم). نتیجه به‌صورت JSON مصرف می‌شود.
    """
    q = (request.GET.get("q") or "").strip()
    kind = request.GET.get("kind", "first")
    gender = request.GET.get("gender", "")
    try:
        limit = max(1, min(int(request.GET.get("limit", 30)), 50))
    except (TypeError, ValueError):
        limit = 30

    if kind == "family":
        qs = FamilynameTbl.objects.all()
        fa_attr, en_attr, has_gender = "familyname_fa", "familyname_en", False
    elif kind == "fame":
        # «شهرت»: جدول مرجع FameNameTbl (تکمیل‌شده توسط ادمین در تب «شهرت‌ها»)
        qs = FameNameTbl.objects.all()
        fa_attr, en_attr, has_gender = "fame_name_fa", "fame_name_en", False
    else:
        qs = FirstnameTbl.objects.all()
        fa_attr, en_attr, has_gender = "first_name_fa", "first_name_en", True
        if gender in ("male", "female"):
            # نام‌های بدون جنسیت هم نمایش داده می‌شوند (مثل فهرست فرم)
            qs = qs.filter(gender__in=[gender, ""])

    if q:
        qs = qs.filter(
            Q(**{f"{fa_attr}__icontains": q})
            | Q(**{f"{en_attr}__icontains": q})
        )
        rank = (
            Case(
                When(**{f"{fa_attr}__startswith": q}, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
            + Case(
                When(**{f"{en_attr}__istartswith": q}, then=Value(0)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        qs = qs.annotate(_rank=rank).order_by("_rank", fa_attr)
    else:
        qs = qs.order_by(fa_attr)

    results = []
    for obj in qs[:limit]:
        fa = getattr(obj, fa_attr)
        en = (getattr(obj, en_attr) or "").strip()
        label = f"{fa} ({en})" if en else fa
        item = {"id": obj.pk, "fa": fa, "en": en, "label": label}
        if has_gender:
            item["gender"] = obj.gender or ""
        results.append(item)
    return JsonResponse({"results": results})


@login_required
@require_http_methods(["GET"])
def study_fields(request):
    """فهرست زندهٔ رشته‌های تحصیلی بر اساس گروه امتحانی انتخاب‌شده (آبشاری).

    مکمل فیلد «گروه امتحانی» جدید در فرم اطلاعات تحصیلی پروفایل: با تغییر گروه،
    فقط رشته‌های فعالِ همان گروه برگردانده می‌شود. بدون پارامتر «group_id» همهٔ
    رشته‌های فعال برگردانده می‌شود (حالتِ بدون گروه/غیرفعال‌بودن JS).
    """
    from .models import StudyField, StudyGroup

    group_id = request.GET.get("group_id") or ""
    try:
        group_id = int(group_id)
    except (TypeError, ValueError):
        group_id = None

    fields_qs = StudyField.objects.filter(is_active=True).select_related("study_group")
    if group_id is not None:
        # گروه غیرفعال هم در صورت ارسال صریح پذیرفته می‌شود تا کاربرِ فعلی دستِ خالی نماند
        if not StudyGroup.objects.filter(pk=group_id).exists():
            return JsonResponse({"results": []})
        fields_qs = fields_qs.filter(study_group_id=group_id)
    fields_qs = fields_qs.order_by("study_group__code", "name")

    results = []
    for field in fields_qs:
        en = (field.name_en or "").strip()
        label = f"{field.name} ({en})" if en else field.name
        results.append({
            "id": field.pk,
            "name": field.name,
            "name_en": en,
            "group_id": field.study_group_id,
            "label": label,
        })
    return JsonResponse({"results": results})


@login_required
@require_http_methods(["GET"])
def study_specializations(request):
    """باگresso زندهٔ گرایش‌های تحصیلی بر اساس رشتهٔ انتخاب‌شده ( cascade).

    axillary به فیلد «رشته تحصیلی» در فرم اطلاعات تحصیلی پروفایل.
    برمی‌گرداند لیستِ گرایش‌های فعالِ مرتبط با رشتهٔ داده‌شده.
    """
    from .models import StudySpecialization

    field_id = request.GET.get("field_id") or ""
    try:
        field_id = int(field_id)
    except (TypeError, ValueError):
        field_id = None

    if field_id is None:
        return JsonResponse({"results": []})

    specs = StudySpecialization.objects.filter(
        field_id=field_id, is_active=True, field__is_active=True
    ).select_related("field").order_by("name")

    results = []
    for spec in specs:
        en = (spec.name_en or "").strip()
        label = f"{spec.name} ({en})" if en else spec.name
        results.append({"id": spec.pk, "name": spec.name, "name_en": en, "label": label})
    return JsonResponse({"results": results})


def location_search(request):
    """جستجوی زندهٔ کشور/استان/شهرستان برای فیلدهای «اطلاعات مکانی» پروفایل.

    مشابه name_search اما روی جدول‌های مرجع مکان (CountryTbl/ProvinceTbl/CityTbl)
    که ادمین از ماژول «اطلاعات مکانی» در پنل مدیریت تکمیل می‌کند. با هر تایپ، یک
    Query واقعی به دیتابیس زده می‌شود (فارسی یا لاتین) و حداکثر «limit» نتیجهٔ
    با شروعِ یکسان در اولویت برمی‌گردد.

    پارامتر «parent» مقدارِ فیلدِ بالادست است تا فهرست «استان» بر اساس کشورِ
    انتخابی و فهرست «شهرستان» بر اساس استانِ انتخابی کوتاه شود؛ اگر مقدارِ parent
    در جدول مرجع یافت نشود (مثلاً کشورِ خارجیِ شناسایی‌شده با GPS)، فیلتر نادیده
    گرفته می‌شود تا کاربر بتواند آزادانه جستجو کند.
    """
    from .models import CityTbl, CountryTbl, ProvinceTbl

    q = (request.GET.get("q") or "").strip()
    kind = request.GET.get("kind", "country")
    parent = (request.GET.get("parent") or "").strip()
    try:
        limit = max(1, min(int(request.GET.get("limit", 30)), 50))
    except (TypeError, ValueError):
        limit = 30

    def _apply_query(qs, fa_attr, en_attr):
        if q:
            qs = qs.filter(
                Q(**{f"{fa_attr}__icontains": q})
                | Q(**{f"{en_attr}__icontains": q})
            )
            rank = (
                Case(
                    When(**{f"{fa_attr}__startswith": q}, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
                + Case(
                    When(**{f"{en_attr}__istartswith": q}, then=Value(0)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )
            qs = qs.annotate(_rank=rank).order_by("_rank", fa_attr)
        else:
            qs = qs.order_by(fa_attr)
        return qs

    if kind == "province":
        qs = ProvinceTbl.objects.select_related("country").all()
        # کوتاه‌کردن بر اساس کشورِ بالادست (اگر مطابق جدول مرجع باشد)
        if parent and CountryTbl.objects.filter(country_fa=parent).exists():
            qs = qs.filter(country__country_fa=parent)
        qs = _apply_query(qs, "province_fa", "province_en")
    elif kind == "city":
        qs = CityTbl.objects.select_related("province__country").all()
        if parent:
            prov_ids = list(
                ProvinceTbl.objects.filter(province_fa=parent).values_list("pk", flat=True)
            )
            if prov_ids:
                qs = qs.filter(province__in=prov_ids)
        qs = _apply_query(qs, "city_fa", "city_en")
    else:
        kind = "country"
        qs = CountryTbl.objects.all()
        qs = _apply_query(qs, "country_fa", "country_en")

    results = []
    for obj in qs[:limit]:
        fa_attr = f"{kind}_fa"
        en_attr = f"{kind}_en"
        fa = getattr(obj, fa_attr)
        en = (getattr(obj, en_attr) or "").strip()
        label = f"{fa} ({en})" if en else fa
        item = {"id": obj.pk, "fa": fa, "en": en, "label": label}
        # مسیرِ بالادست برای نمایش (مثلاً شهرستان ← استان ← کشور)
        if kind == "province":
            item["hint"] = obj.country.country_fa
        elif kind == "city":
            item["hint"] = obj.province.province_fa
        else:
            item["hint"] = ""
        results.append(item)
    return JsonResponse({"results": results})


@login_required(login_url="core:index")
def document_download(request, doc_id):
    """دانلود امن یکی از مدارک کاربر.

    تنها صاحب مدرک یا کاربر staff به فایل دسترسی دارد (فایل‌ها خارج از MEDIA_ROOT
    و بدون URL عمومی ذخیره می‌شوند، پس همه‌جا از همین مسیر کنترل‌شده سرو می‌شوند).
    """
    doc = get_object_or_404(
        UserDocument.objects.select_related("profile"), pk=doc_id
    )
    if not request.user.is_staff and doc.profile.user_id != request.user.id:
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied
    if not doc.file or not doc.file.storage.exists(doc.file.name):
        messages.error(request, "فایل این مدرک یافت نشد.")
        return redirect("core:profile")
    # ?inline=1 → نمایش داخل صفحه (بندانگشتی تصاویر)؛ حالت پیش‌فرض: دانلود
    as_attachment = request.GET.get("inline") != "1"
    response = FileResponse(doc.file.open("rb"), as_attachment=as_attachment)
    return response


@login_required
@require_http_methods(["GET"])
def family_nid_lookup(request):
    """فراخوانی خودکار مشخصات فردِ ثبت‌نام‌شده از کد ملی (بخش اطلاعات خانواده).

    کاربر کد ملی فرزند (یا همسر) را وارد می‌کند؛ اگر این فرد قبلاً در سیستم
    ثبت‌نام کرده باشد، نام/نام خانوادگی‌اش از سیستم فراخوانی می‌شود تا کاربر
    مجبور به تایپ مجدد نباشد. پاسخ JSON است؛ در نبودِ رکورد هم 200 برمی‌گردد
    (found=false) چون «نبودن در سیستم» خطا نیست — در این حالت کاربر نام را
    از فهرست مرجع انتخاب می‌کند.
    """
    from .models import Profile

    # حالت دسته‌ای: «nids=a,b,c» برای فراخوانی نمایشِ نامِ همهٔ ردیف‌های
    # ذخیره‌شدهٔ قبلی با یک درخواست (ویرایش پروفایل).
    nids_param = (request.GET.get("nids") or "").strip()
    if nids_param:
        nids = [n.strip() for n in nids_param.split(",") if n.strip()][:30]
        valid = [n for n in nids if re.fullmatch(r"\d{10}", n)]
        profiles = {
            p.national_id: p
            for p in Profile.objects.filter(national_id__in=valid)
            .select_related("first_name", "last_name")
        }
        results = {}
        for n in nids:
            p = profiles.get(n)
            if p is None:
                results[n] = {"found": False}
                continue
            first, last = p.first_name, p.last_name
            results[n] = {
                "found": True,
                "first_name_fa": first.first_name_fa if first else "",
                "family_name_fa": last.familyname_fa if last else "",
            }
        return JsonResponse({"results": results})

    nid = (request.GET.get("nid") or "").strip()
    if not re.fullmatch(r"\d{10}", nid or ""):
        return JsonResponse({"found": False, "error": "کد ملی باید دقیقاً ۱۰ رقم (۰-۹) باشد."})
    rec = (
        Profile.objects.filter(national_id=nid)
        .select_related("first_name", "last_name")
        .only(
            "id", "national_id",
            "first_name__first_name_fa", "first_name__first_name_en",
            "last_name__familyname_fa", "last_name__familyname_en",
            "user__mobile_number",
        )
        .first()
    )
    if rec is None:
        return JsonResponse({"found": False})
    first = rec.first_name
    last = rec.last_name
    return JsonResponse({
        "found": True,
        "first_name_id": rec.first_name_id,
        "family_name_id": rec.last_name_id,
        "first_name_fa": first.first_name_fa if first else "",
        "first_name_en": (first.first_name_en if first else "") or "",
        "family_name_fa": last.familyname_fa if last else "",
        "family_name_en": (last.familyname_en if last else "") or "",
    })
