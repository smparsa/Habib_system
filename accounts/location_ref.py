# -*- coding: utf-8 -*-
"""هم‌ارزسازی نام‌های مکانیِ شناسایی‌شده با GPS به رکوردهای مرجع (جدول‌های اطلاعات مکانی).

جریان «دریافت خودکار موقعیت» (GPS/نقشه/IP) نتیجهٔ سرویس‌های بیرونی را مستقیم در
فیلدهای کشور/استان/شهر پروفایل می‌نویسد. این سرویس‌ها گاهی فارسی (Google با
language=fa یا BigDataCloud با localityLanguage=fa) و گاهی انگلیسی (مثل ipapi و
برخی پاسخ‌های GPS) برمی‌گردانند؛ مثلاً «Iran» یا «Tehran» در حالی که فهرست مرجعِ
پروفایل فارسی است («ایران»، «تهران»). این ماژول مقدار سرویس را با رکوردهای
CountryTbl/ProvinceTbl/CityTbl می‌سنجد و در صورت یافتنِ هم‌ارز، «نام رسمی فارسیِ»
رکورد مرجع را برمی‌گرداند تا چیزی که ذخیره می‌شود همیشه با فهرستِ انتخابیِ کاربر
و هدف‌گیری تیکت‌ها یکی باشد.

اگر مقداری در جدول مرجع پیدا نشود (مثلاً کشوری خارجی که هنوز اضافه نشده) مقدار
اصلی دست‌نخورده برمی‌گردد؛ هیچ نامی به‌صورت حدسی تبدیل نمی‌شود.
"""

import re

# ---------------------------------------------------------------------------
# نرمال‌سازی نویسه‌ها
# ---------------------------------------------------------------------------

ZWNJ = "\u200c"

# املای عربی → فارسی (مثل همان نرمال‌سازی جدول نام‌ها)
_ARABIC_FOLD = str.maketrans(
    {
        "ي": "ی",
        "ك": "ک",
        "أ": "ا",
        "إ": "ا",
        "آ": "آ",
        "ئ": "ی",
        "ة": "ه",
        "ۀ": "ه",
        "ؤ": "و",
        "ى": "ی",
    }
)

_FA_PREFIXES = ("استان ", "شهرستان ", "کشور ", "جمهوری اسلامی ایران")
_FA_SUFFIXES = (" استان", " شهرستان")
_EN_PREFIXES = ("province of ", "county of ", "the ")
_EN_SUFFIX_TOKENS = (
    " province",
    " county",
    " governorate",
    " district",
    " city",
    " capital",
)


def fold_fa(text):
    """جمع‌کردن نویسه‌های هم‌ارز عربی/فارسی و حذف نیم‌فاصله و فاصلهٔ اضافی."""
    if not text:
        return ""
    s = str(text).replace(ZWNJ, "").translate(_ARABIC_FOLD)
    # نیم‌فاصله‌ها/فاصله‌های چندگانه را تک‌فاصله کنیم
    s = re.sub(r"\s+", " ", s).strip()
    return s


def norm_fa(text):
    """نسخهٔ قابل‌مقایسهٔ فارسی: بدون پیشوند «استان/شهرستان/کشور» و پسوندهای مشابه."""
    s = fold_fa(text)
    for prefix in _FA_PREFIXES:
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
            break
    for suffix in _FA_SUFFIXES:
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
            break
    return s


def norm_en(text):
    """نسخهٔ قابل‌مقایسهٔ انگلیسی: حروف کوچک و حذف پسوندهای تقسیمات کشوری."""
    if not text:
        return ""
    s = str(text).lower().strip()
    s = re.sub(r"\s*,\s*", " ", s)
    # «تهران، ایران» → فقط «تهران»
    s = re.sub(r"\s+(iran|i\.r\.\s*iran|islamic\s+republic\s+of\s+iran)\s*$", "", s)
    for token in _EN_SUFFIX_TOKENS:
        if s.endswith(token):
            s = s[: -len(token)].strip()
    return s.strip()


def core_key(text):
    """کلید مقایسهٔ سست: بدون فاصله/خط‌تیره/نقطه/کاما، حروف کوچک انگلیسی."""
    if not text:
        return ""
    s = str(text).lower()
    return re.sub(r"[\s\-'._،,]", "", s)


# ---------------------------------------------------------------------------
# نویسه‌گردانی تقریبی فارسی → لاتین (فقط برای جستجو/راهنما؛ نه تبدیل قطعی)
# ---------------------------------------------------------------------------

_FA_TO_EN = {
    "آ": "a", "ا": "a", "ب": "b", "پ": "p", "ت": "t", "ث": "s", "ج": "j",
    "چ": "ch", "ح": "h", "خ": "kh", "د": "d", "ذ": "z", "ر": "r", "ز": "z",
    "ژ": "zh", "س": "s", "ش": "sh", "ص": "s", "ض": "z", "ط": "t", "ظ": "z",
    "ع": "", "غ": "gh", "ف": "f", "ق": "gh", "ک": "k", "گ": "g", "ل": "l",
    "م": "m", "ن": "n", "و": "v", "ه": "h", "ی": "y",
}


def fa_to_en(text):
    """نویسه‌گردانی تقریبی برای ساخت مقدار لاتینِ پیشنهادی ستون *_en جدول مرجع."""
    s = fold_fa(text)
    out = []
    for ch in s:
        if ch == " ":
            out.append(" ")
            continue
        out.append(_FA_TO_EN.get(ch, ch))
    token = "".join(out).strip()
    # پاک‌سازی: توالی حروف تکراری، صامت‌های پشت‌سرهمِ ناخوانا (بدون واکه) می‌مانند
    token = re.sub(r"(.)\1+", r"\1", token)
    return token.strip()


# ---------------------------------------------------------------------------
# نام‌های رسمی انگلیسی استان‌ها و نام‌های شناخته‌شدهٔ شهرستان‌ها
# (برای ستون *_en و تطبیق نتایجِ انگلیسیِ سرویس‌ها؛ کلید = نام فارسیِ رکورد مرجع)
# ---------------------------------------------------------------------------

IR_PROVINCES_EN = {
    "آذربایجان شرقی": "East Azerbaijan",
    "آذربایجان غربی": "West Azerbaijan",
    "اردبیل": "Ardabil",
    "اصفهان": "Isfahan",
    "البرز": "Alborz",
    "ایلام": "Ilam",
    "بوشهر": "Bushehr",
    "تهران": "Tehran",
    "چهارمحال و بختیاری": "Chaharmahal and Bakhtiari",
    "خراسان جنوبی": "South Khorasan",
    "خراسان رضوی": "Razavi Khorasan",
    "خراسان شمالی": "North Khorasan",
    "خوزستان": "Khuzestan",
    "زنجان": "Zanjan",
    "سمنان": "Semnan",
    "سیستان و بلوچستان": "Sistan and Baluchestan",
    "فارس": "Fars",
    "قزوین": "Qazvin",
    "قم": "Qom",
    "کردستان": "Kurdistan",
    "کرمان": "Kerman",
    "کرمانشاه": "Kermanshah",
    "کهگیلویه و بویراحمد": "Kohgiluyeh and Boyer-Ahmad",
    "گلستان": "Golestan",
    "گیلان": "Gilan",
    "لرستان": "Lorestan",
    "مازندران": "Mazandaran",
    "مرکزی": "Markazi",
    "هرمزگان": "Hormozgan",
    "همدان": "Hamadan",
    "یزد": "Yazd",
}

# نام‌های شناخته‌شدهٔ لاتین برای برخی شهرستان‌ها که نویسه‌گردانی ساده برایشان
# شکل متعارف (مثلاً Qom نه Gham) تولید نمی‌کند.
IR_CITY_EN_OVERRIDES = {
    "تهران": "Tehran",
    "کرج": "Karaj",
    "اصفهان": "Isfahan",
    "مشهد": "Mashhad",
    "شیراز": "Shiraz",
    "تبریز": "Tabriz",
    "اهواز": "Ahvaz",
    "قم": "Qom",
    "کرمانشاه": "Kermanshah",
    "ارومیه": "Urmia",
    "رشت": "Rasht",
    "زاهدان": "Zahedan",
    "همدان": "Hamadan",
    "کرمان": "Kerman",
    "یزد": "Yazd",
    "اردبیل": "Ardabil",
    "بندرعباس": "Bandar Abbas",
    "اراک": "Arak",
    "اسلام‌شهر": "Eslamshahr",
    "قزوین": "Qazvin",
    "زنجان": "Zanjan",
    "سنندج": "Sanandaj",
    "خرم‌آباد": "Khorramabad",
    "گرگان": "Gorgan",
    "ساری": "Sari",
    "کاشان": "Kashan",
    "قائم‌شهر": "Qaemshahr",
    "بابلسر": "Babolsar",
    "آمل": "Amol",
    "بابل": "Babol",
    "ساوه": "Saveh",
    "شاهرود": "Shahroud",
    "بجنورد": "Bojnord",
    "سبزوار": "Sabzevar",
    "نیشابور": "Neyshabur",
    "تربت حیدریه": "Torbat-e Heydarieh",
    "کاشمر": "Kashmar",
    "گناباد": "Gonabad",
    "مراغه": "Maragheh",
    "میانه": "Mianeh",
    "مرند": "Marand",
    "اهر": "Ahar",
    "خوی": "Khoy",
    "مهاباد": "Mahabad",
    "بوکان": "Bukan",
    "سقز": "Saqqez",
    "مریوان": "Marivan",
    "دهلران": "Dehloran",
    "آبادان": "Abadan",
    "خرمشهر": "Khorramshahr",
    "دزفول": "Dezful",
    "مسجدسلیمان": "Masjed Soleyman",
    "شهرکرد": "Shahrekord",
    "بروجن": "Borujen",
    "یاسوج": "Yasuj",
    "گچساران": "Gachsaran",
    "بوشهر": "Bushehr",
    "بندر گناوه": "Ganaveh",
    "لار": "Lar",
    "فسا": "Fasa",
    "مرودشت": "Marvdasht",
    "جهرم": "Jahrom",
    "داراب": "Darab",
    "نیریز": "Neyriz",
    "کازرون": "Kazerun",
    "لنگرود": "Langarud",
    "آستارا": "Astara",
    "لاهیجان": "Lahijan",
    "انزلی": "Anzali",
    "بندرانزلی": "Bandar Anzali",
    "نور": "Nur",
    "آمل": "Amol",
    "چالوس": "Chalus",
    "نوشهر": "Nowshahr",
    "تنکابن": "Tonekabon",
    "رامسر": "Ramsar",
    "بهشهر": "Behshahr",
    "گنبد کاووس": "Gonbad-e Kavus",
    "مینودشت": "Minudasht",
    "علی‌آباد": "Aliabad",
    "ایلام": "Ilam",
    "ایذه": "Izeh",
    "شوش": "Shush",
    "شوشتر": "Shushtar",
    "اندیمشک": "Andimeshk",
    "بهبهان": "Behbahan",
    "رامهرمز": "Ramhormoz",
    "شادگان": "Shadegan",
    "ملایر": "Malayer",
    "نهاوند": "Nahavand",
    "تویسرکان": "Tuyserkan",
    "اسدآباد": "Asadabad",
    "بروجرد": "Borujerd",
    "الیگودرز": "Aligudarz",
    "دورود": "Dorud",
    "کوهدشت": "Kuhdasht",
    "پلدختر": "Poldokhtar",
    "نقده": "Naqadeh",
    "پیرانشهر": "Piranshahr",
    "سلماس": "Salmas",
    "ماکو": "Maku",
    "شاهین‌دژ": "Shahin Dezh",
    "تکاب": "Takab",
    "خدابنده": "Khodabandeh",
    "ابهر": "Abhar",
    "ایجرود": "Ijroud",
    "طارم": "Tarom",
    "خلخال": "Khalkhal",
    "گرمی": "Germi",
    "مشگین‌شهر": "Meshgin Shahr",
    "نمین": "Namin",
    "سراب": "Sarab",
    "اهر": "Ahar",
    "هشترود": "Hashtroud",
    "چابهار": "Chabahar",
    "ایرانشهر": "Iranshahr",
    "سراوان": "Saravan",
    "خاش": "Khash",
    "زابل": "Zabol",
    "کنارک": "Konarak",
    "میرجاوه": "Mirjaveh",
    "سیرجان": "Sirjan",
    "رفسنجان": "Rafsanjan",
    "بم": "Bam",
    "جیرفت": "Jiroft",
    "کهنوج": "Kahnooj",
    "بافت": "Baft",
    "زرند": "Zarand",
    "شهر بابک": "Shahr-e Babak",
    "بانه": "Baneh",
    "قروه": "Qorveh",
    "بیجار": "Bijar",
    "کامیاران": "Kamyaran",
    "دیواندره": "Divandarreh",
    "پاوه": "Paveh",
    "هرسین": "Harsin",
    "کنگاور": "Kangavar",
    "صحنه": "Sahneh",
    "گیلانغرب": "Gilan-e Gharb",
    "سرپل ذهاب": "Sarpol-e Zahab",
    "اسلام‌آباد غرب": "Eslamabad-e Gharb",
    "سنقر": "Sonqor",
    "دالاهو": "Dalahu",
    "ثلاث باباجانی": "Salas-e Babajani",
    "نائین": "Naein",
    "اردستان": "Ardestan",
    "گلپایگان": "Golpayegan",
    "خوانسار": "Khansar",
    "فریدن": "Faridan",
    "فریدون‌شهر": "Fereydunshahr",
    "تیران و کرون": "Tiran and Karvan",
    "دهاقان": "Dehaqan",
    "سمیرم": "Semirom",
    "نجف‌آباد": "Najafabad",
    "شهرضا": "Shahreza",
    "مبارکه": "Mobarakeh",
    "لنجان": "Lenjan",
    "فلاورجان": "Falavarjan",
    "خمینی‌شهر": "Khomeynishahr",
    "برخوار": "Borkhar",
    "کوهپایه": "Kuhpayeh",
    "شاهرود": "Shahroud",
    "دامغان": "Damghan",
    "سمنان": "Semnan",
    "گرمسار": "Garmsar",
    "شهرضا": "Shahreza",
    "مهدی‌شهر": "Mahdishahr",
    "میامی": "Mayamey",
    "شفت": "Shaft",
    "فومن": "Fuman",
    "صومعه‌سرا": "Sowme'eh Sara",
    "ماسال": "Masal",
    "رضوانشهر": "Rezvanshahr",
    "املش": "Amlash",
    "سیاهکل": "Siahkal",
    "رودسر": "Rudsar",
    "رودبار": "Rudbar",
    "تالش": "Talesh",
    "کوچصفهان": "Kuch Esfahan",
    "خمام": "Khammam",
    "لشت‌نشا": "Lasht-e Nesha",
    "بندرانزلی": "Bandar-e Anzali",
    "ملارد": "Malard",
    "شهریار": "Shahriar",
    "پاکدشت": "Pakdasht",
    "ورامین": "Varamin",
    "پیشوا": "Pishva",
    "قرچک": "Qarchak",
    "ری": "Rey",
    "شمیرانات": "Shemiranat",
    "فیروزکوه": "Firuzkuh",
    "دماوند": "Damavand",
    "رباط‌کریم": "Robat Karim",
    "بهارستان": "Baharestan",
    "قدس": "Qods",
    "پردیس": "Pardis",
    "نظرآباد": "Nazarabad",
    "ساوجبلاغ": "Savojbolagh",
    "فردیس": "Fardis",
    "اشتهارد": "Eshtehard",
    "طالقان": "Taleqan",
    "نطنز": "Natanz",
    "آران و بیدگل": "Aran va Bidgol",
    "کاشان": "Kashan",
    "بویین‌زهرا": "Buin Zahra",
    "آبیک": "Abyek",
    "تاکستان": "Takestan",
    "البرز(قزوین)": "Alborz",
    "آوج": "Avaj",
    "خمین": "Khomeyn",
    "محلات": "Mahallat",
    "دلیجان": "Delijan",
    "شازند": "Shazand",
    "فراهان": "Farahan",
    "تفرش": "Tafresh",
    "آشتیان": "Ashtian",
    "زرندیه": "Zarandieh",
    "کمیجان": "Komijan",
    "خنداب": "Khondab",
}

# برخی املاهای متداولِ متفاوتِ انگلیسیِ یک نام فارسی (برای تطبیق پاسخِ سرویس‌ها)
IR_NAME_ALIASES_EN = {
    "اصفهان": ["Esfahan"],
    "خوزستان": ["Khuzestan", "Khouzestan"],
    "کرمانشاه": ["Kermanshah", "Kermanshahan"],
    "ارومیه": ["Urmia", "Orumiyeh"],
    "زاهدان": ["Zahedan"],
    "مشهد": ["Mashhad", "Mashad"],
    "اهر": ["Ahar"],
    "قزوین": ["Qazvin", "Ghazvin"],
    "همدان": ["Hamadan", "Hamedan"],
    "لرستان": ["Lorestan", "Luristan"],
    "ایلام": ["Ilam", "Ilām"],
    "بندرعباس": ["Bandar Abbas", "Bandar-e Abbas"],
    "خرم‌آباد": ["Khorramabad", "Khorram Abad"],
    "سیستان و بلوچستان": ["Sistan and Baluchestan", "Sistan and Baluchistan"],
    "چهارمحال و بختیاری": ["Chaharmahal and Bakhtiari", "Chahar Mahal and Bakhtiari"],
    "کردستان": ["Kurdistan", "Kordestan"],
    "کرمان": ["Kerman", "Kerman Province"],
    "خراسان رضوی": ["Razavi Khorasan", "Khorasan-e Razavi"],
    "خراسان شمالی": ["North Khorasan", "Khorasan-e Shomali"],
    "خراسان جنوبی": ["South Khorasan", "Khorasan-e Jonubi"],
    "آذربایجان شرقی": ["East Azerbaijan", "Eastern Azerbaijan", "Azerbaijan Sharghi"],
    "آذربایجان غربی": ["West Azerbaijan", "Western Azerbaijan", "Azerbaijan Gharbi"],
    "کهگیلویه و بویراحمد": [
        "Kohgiluyeh and Boyer-Ahmad", "Kohgiluyeh and Boyer Ahmad",
    ],
    "مازندران": ["Mazandaran", "Mazanderan"],
    "هرمزگان": ["Hormozgan", "Hormozgan Province"],
    "گلستان": ["Golestan", "Gulistan"],
    "تهران": ["Tehran", "Teheran"],
    "یزد": ["Yazd"],
    "اردبیل": ["Ardabil", "Ardebil"],
    "فارس": ["Fars"],
    "سمنان": ["Semnan"],
    "زنجان": ["Zanjan"],
    "گیلان": ["Gilan", "Guilan"],
    "مرکزی": ["Markazi", "Central"],
    "قم": ["Qom", "Ghom"],
    "البرز": ["Alborz", "Alborz Province"],
    "بوشهر": ["Bushehr", "Bushire"],
}


def suggested_en(fa, kind="province"):
    """مقدار لاتینِ پیشنهادی برای یک رکورد مرجع (برای ستون *_en جدول)."""
    fa = fold_fa(fa or "")
    if not fa:
        return ""
    if kind == "province":
        name = IR_PROVINCES_EN.get(fa)
        if name:
            return name
    name = IR_CITY_EN_OVERRIDES.get(fa)
    if name:
        return name
    return fa_to_en(fa)


def _en_candidates(fa, kind):
    """همهٔ شکل‌های لاتینِ احتمالی برای یک نام فارسیِ رکورد مرجع."""
    out = []
    seen = set()
    for name in [suggested_en(fa, kind)] + IR_NAME_ALIASES_EN.get(fa, []):
        key = core_key(name)
        if name and key and key not in seen:
            seen.add(key)
            out.append(name)
    return out


def _en_cores(fa, kind):
    return {core_key(n) for n in _en_candidates(fa, kind)}


# ---------------------------------------------------------------------------
# تطبیق با جدول مرجع
# ---------------------------------------------------------------------------


def _ref_en(model, fa_attr, en_attr, fa_name):
    """نام انگلیسیِ هم‌ارز از جدول مرجع برای یک نام فارسی (یا خالی)."""
    fa_name = (fa_name or "").strip()
    if not fa_name:
        return ""
    en = (
        model.objects.filter(**{fa_attr: fa_name})
        .values_list(en_attr, flat=True)
        .first()
    )
    return (en or "").strip()


def country_en_for(fa_name):
    """نام انگلیسیِ کشور از جدول مرجع برای یک نام فارسی (یا خالی).

    برای ذخیرهٔ «دوزبانه» کشور در پروفایل: Profile.country و فیلدهای تابعیت/
    ملیت/اقامت دائم مقدارِ رسمی فارسی را نگه می‌دارند (هدف‌گیری تیکت‌ها دست‌نخورده)
    و نسخهٔ انگلیسی کنارش در extra_data ذخیره می‌شود تا نمایش با زبان رابط عوض شود.
    اگر نامی در جدول مرجع نباشد (مثلاً ورودِ قدیمی/آزاد) خالی برمی‌گردد.
    """
    from .models import CountryTbl

    return _ref_en(CountryTbl, "country_fa", "country_en", fa_name)


def province_en_for(fa_name):
    """نام انگلیسیِ استان از جدول مرجع برای یک نام فارسی (یا خالی)."""
    from .models import ProvinceTbl

    return _ref_en(ProvinceTbl, "province_fa", "province_en", fa_name)


def city_en_for(fa_name):
    """نام انگلیسیِ شهرستان از جدول مرجع برای یک نام فارسی (یا خالی)."""
    from .models import CityTbl

    return _ref_en(CityTbl, "city_fa", "city_en", fa_name)


def _match_rows(rows, fa_attr, en_attr, fa_value=None, en_value=None, kind="province"):
    """یافتن رکورد مرجعِ هم‌ارز با مقدارِ سرویس.

    اولویت: تطبیقِ دقیقِ فارسی نرمال‌شده، سپس تطبیقِ انگلیسی (ستون *_en، نام‌های
    شناخته‌شده و نویسه‌گردانی). فقط هم‌ارزیِ مطمئن برمی‌گردد؛ در غیر این صورت None.
    """
    fa_norm = norm_fa(fa_value) if fa_value else ""
    en_core = core_key(norm_en(en_value)) if en_value else ""
    fa_keys = {core_key(fold_fa(getattr(r, fa_attr) or "")) for r in rows}

    for row in rows:
        row_fa = fold_fa(getattr(row, fa_attr) or "")
        if fa_norm and core_key(row_fa) == core_key(fa_norm):
            return row
    if not en_core:
        return None

    # آماده‌سازی کلیدهای انگلیسیِ همهٔ ردیف‌ها (یک بار)
    en_map = {}  # core key → row
    for row in rows:
        stored = core_key(getattr(row, en_attr) or "")
        if stored:
            en_map.setdefault(stored, row)
        for alias in _en_cores(getattr(row, fa_attr) or "", kind):
            en_map.setdefault(alias, row)
        # اگر مقدار سرویسِ انگلیسی زیرمجموعهٔ نامِ فارسیِ نویسه‌گردانی‌شده باشد
        # (مثلاً سرویس «Tehran» و رکوردِ فارسیِ بدون مقدار en) کافی نیست؛ هیچ
        # تطبیق سستی بدون تأیید انجام نمی‌شود.
    if fa_norm and core_key(fa_norm) not in fa_keys:
        pass  # تایپِ فارسیِ ناهم‌ارز را با انگلیسی تطبیق نمی‌دهیم
    if en_core in en_map:
        return en_map[en_core]
    return None


def canonicalize_geo(geo):
    """تبدیل نام‌های مکانیِ سرویس (فارسی یا انگلیسی) به نام فارسیِ رکورد مرجع.

    geo: دیکشنری با کلیدهای اختیاری country/province/city (و هر کلید دیگر که
    دست‌نخورده می‌ماند). نتیجه کپی است؛ مقادیرِ «مطمئن» به نام فارسیِ رسمیِ
    رکورد مرجع (مثل Profile.country) تبدیل می‌شوند و بقیه همان‌طور می‌مانند.
    زنجیره رعایت می‌شود: شهرستان فقط وقتی به فارسی رسمی تبدیل می‌شود که استانِ
    بالادستش در جدول مرجع پیدا شده باشد و استان فقط زیر همان کشورِ یافت‌شده.
    """
    from .models import CityTbl, CountryTbl, ProvinceTbl

    out = dict(geo)
    country_v = (geo.get("country") or "").strip()
    province_v = (geo.get("province") or "").strip()
    city_v = (geo.get("city") or "").strip()

    # اگر کشور داده شده ولی در جدول مرجع نیست (مثلاً خارجیِ ثبت‌نشده)، به هیچ
    # نامی دست نمی‌زنیم — استان/شهرِ زیر همان کشورِ ناشناخته نمی‌تواند مطمئن باشد.
    country_match = None
    if country_v:
        country_match = _match_rows(
            list(CountryTbl.objects.all()), "country_fa", "country_en",
            fa_value=country_v, en_value=country_v, kind="country",
        )
        if country_match:
            out["country"] = country_match.country_fa
            out["country_en"] = (country_match.country_en or "").strip()
    elif province_v or city_v:
        # کشور داده نشده: فقط وقتی نام استان/شهر در فهرست یکتاست تبدیل می‌شود؛
        # برای شهر/استانِ بدون کشور، دامنه را محدود نمی‌کنیم.
        pass
    if country_v and not country_match and (province_v or city_v):
        return out

    prov_match = None
    if province_v:
        prov_qs = ProvinceTbl.objects.select_related("country")
        prov_rows = (
            list(prov_qs.filter(country=country_match))
            if country_match else list(prov_qs.all())
        )
        prov_match = _match_rows(
            prov_rows, "province_fa", "province_en",
            fa_value=province_v, en_value=province_v, kind="province",
        )
        if prov_match:
            out["province"] = prov_match.province_fa
            out["province_en"] = (prov_match.province_en or "").strip()

    # شهرستان: ترجیحاً زیر استانِ یافت‌شده؛ اگر استان داده نشده/یافت نشده ولی
    # کشورِ مرجع شناخته‌شده است، در همهٔ شهرهای همان کشور جستجو می‌شود.
    if city_v:
        if prov_match:
            city_rows = list(CityTbl.objects.filter(province=prov_match))
        elif country_match and not prov_match:
            prov_ids = ProvinceTbl.objects.filter(country=country_match).values_list("pk", flat=True)
            city_rows = list(CityTbl.objects.filter(province_id__in=list(prov_ids)))
        elif not country_v:
            # بدون کشور: سراسری جستجو کن اما فقط اگر نام در دیتابیس یکتا باشد
            city_rows = list(CityTbl.objects.all())
        else:
            city_rows = []
        if city_rows:
            city_match = _match_rows(
                city_rows, "city_fa", "city_en",
                fa_value=city_v, en_value=city_v, kind="city",
            )
            if city_match:
                out["city"] = city_match.city_fa
                out["city_en"] = (city_match.city_en or "").strip()
    return out
