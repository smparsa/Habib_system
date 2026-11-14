import datetime
from convertdate import persian, islamic
from django.utils import timezone

PERSIAN_MONTHS = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
                   'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']

ISLAMIC_MONTHS = ['محرم', 'صفر', 'ربیع‌الاول', 'ربیع‌الثانی', 'جمادی‌الاول',
                   'جمادی‌الثانی', 'رجب', 'شعبان', 'رمضان', 'شوال',
                   'ذی‌القعده', 'ذی‌الحجه']

GREGORIAN_MONTHS = ['ژانویه', 'فوریه', 'مارس', 'آوریل', 'مه', 'ژوئن',
                     'جولای', 'آگوست', 'سپتامبر', 'اکتبر', 'نوامبر', 'دسامبر']

WEEKDAYS_FA = ['دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه', 'شنبه', 'یکشنبه']

PERSIAN_DIGITS = '۰۱۲۳۴۵۶۷۸۹'
ENGLISH_DIGITS = '0123456789'


def to_persian_digits(value):
    text = str(value)
    translation = str.maketrans(ENGLISH_DIGITS, PERSIAN_DIGITS)
    return text.translate(translation)


def to_english_digits(value):
    text = str(value)
    translation = str.maketrans(
        PERSIAN_DIGITS + '٠١٢٣٤٥٦٧٨٩',
        ENGLISH_DIGITS + ENGLISH_DIGITS
    )
    return text.translate(translation)


def get_weekday_name(g_year, g_month, g_day):
    try:
        weekday_index = datetime.date(g_year, g_month, g_day).weekday()
        return WEEKDAYS_FA[weekday_index]
    except Exception:
        return ''


def convert_date(calendar_type, year, month, day):
    if not (1 <= month <= 12):
        raise ValueError('ماه باید بین ۱ تا ۱۲ باشد')
    if not (1 <= day <= 31):
        raise ValueError('روز باید بین ۱ تا ۳۱ باشد')

    if calendar_type == 'shamsi':
        g_year, g_month, g_day = persian.to_gregorian(year, month, day)
    elif calendar_type == 'ghamari':
        g_year, g_month, g_day = islamic.to_gregorian(year, month, day)
    elif calendar_type == 'miladi':
        g_year, g_month, g_day = year, month, day
    else:
        raise ValueError('نوع تقویم نامعتبر است')

    shamsi_y, shamsi_m, shamsi_d = persian.from_gregorian(g_year, g_month, g_day)
    ghamari_y, ghamari_m, ghamari_d = islamic.from_gregorian(g_year, g_month, g_day)
    weekday_name = get_weekday_name(g_year, g_month, g_day)

    def build_result(y, m, d, month_name):
        return {
            'year': y, 'month': m, 'day': d,
            'year_fa': to_persian_digits(y),
            'month_fa': to_persian_digits(m),
            'day_fa': to_persian_digits(d),
            'month_name': month_name,
            'formatted': f'{d} {month_name} {y}',
            'formatted_fa': f'{to_persian_digits(d)} {month_name} {to_persian_digits(y)}',
            'numeric': f'{y}/{m}/{d}',
            'numeric_fa': f'{to_persian_digits(y)}/{to_persian_digits(m)}/{to_persian_digits(d)}',
        }

    return {
        'weekday': weekday_name,
        'shamsi': build_result(shamsi_y, shamsi_m, shamsi_d, PERSIAN_MONTHS[shamsi_m - 1]),
        'ghamari': build_result(ghamari_y, ghamari_m, ghamari_d, ISLAMIC_MONTHS[ghamari_m - 1]),
        'miladi': build_result(g_year, g_month, g_day, GREGORIAN_MONTHS[g_month - 1]),
    }


def _to_gregorian_ordinal(calendar_type, y, m, d):
    if calendar_type == 'shamsi':
        gy, gm, gd = persian.to_gregorian(y, m, d)
    elif calendar_type == 'ghamari':
        gy, gm, gd = islamic.to_gregorian(y, m, d)
    elif calendar_type == 'miladi':
        gy, gm, gd = y, m, d
    else:
        raise ValueError('نوع تقویم نامعتبر است')
    return datetime.date(gy, gm, gd).toordinal()


def get_days_in_month(calendar_type, year, month):
    start_ord = _to_gregorian_ordinal(calendar_type, year, month, 1)
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    end_ord = _to_gregorian_ordinal(calendar_type, next_year, next_month, 1)
    return end_ord - start_ord


def get_first_weekday_index(calendar_type, year, month):
    if calendar_type == 'shamsi':
        gy, gm, gd = persian.to_gregorian(year, month, 1)
    elif calendar_type == 'ghamari':
        gy, gm, gd = islamic.to_gregorian(year, month, 1)
    else:
        gy, gm, gd = year, month, 1
    python_weekday = datetime.date(gy, gm, gd).weekday()
    return (python_weekday + 2) % 7


def get_today_in_calendar(calendar_type):
    today = timezone.localdate()
    if calendar_type == 'shamsi':
        y, m, d = persian.from_gregorian(today.year, today.month, today.day)
    elif calendar_type == 'ghamari':
        y, m, d = islamic.from_gregorian(today.year, today.month, today.day)
    else:
        y, m, d = today.year, today.month, today.day
    return {'year': y, 'month': m, 'day': d}


def get_month_name(calendar_type, month):
    if calendar_type == 'shamsi':
        return PERSIAN_MONTHS[month - 1]
    elif calendar_type == 'ghamari':
        return ISLAMIC_MONTHS[month - 1]
    else:
        return GREGORIAN_MONTHS[month - 1]