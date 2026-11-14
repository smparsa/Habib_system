import json
import datetime as dt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .forms import DateConvertForm
from .utils import (
    convert_date, to_english_digits, to_persian_digits,
    get_days_in_month, get_first_weekday_index,
    get_today_in_calendar, get_month_name,
)
from .decorators import ratelimit
from .timezones_data import WORLD_TIMEZONES


@login_required(login_url='core:index')
def calendar_converter_view(request):
    form = DateConvertForm()
    today = timezone.localdate()
    today_dates = convert_date('miladi', today.year, today.month, today.day)

    return render(request, 'calendar_converter/converter.html', {
        'profile': getattr(request.user, 'profile', None),
        'form': form,
        'today_dates_json': json.dumps(today_dates),
        'timezones': WORLD_TIMEZONES,
    })


@login_required(login_url='core:index')
@ratelimit(key_prefix='ajax_convert', limit=60, window=60)
@require_http_methods(['POST'])
def ajax_convert_date(request):
    form = DateConvertForm(request.POST)
    if form.is_valid():
        try:
            result = convert_date(
                form.cleaned_data['calendar_type'],
                form.cleaned_data['year'],
                form.cleaned_data['month'],
                form.cleaned_data['day'],
            )
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    else:
        errors = {field: err[0] for field, err in form.errors.items()}
        return JsonResponse({'success': False, 'error': 'ورودی نامعتبر', 'details': errors}, status=400)


@login_required(login_url='core:index')
@ratelimit(key_prefix='calendar_grid', limit=120, window=60)
@require_http_methods(['GET'])
def calendar_grid_view(request):
    try:
        calendar_type = request.GET.get('calendar_type', 'shamsi')
        year = int(to_english_digits(request.GET.get('year')))
        month = int(to_english_digits(request.GET.get('month')))

        if calendar_type not in ('shamsi', 'ghamari', 'miladi'):
            return JsonResponse({'success': False, 'error': 'نوع تقویم نامعتبر است'}, status=400)
        if not (1 <= month <= 12):
            return JsonResponse({'success': False, 'error': 'ماه نامعتبر است'}, status=400)

        days_in_month = get_days_in_month(calendar_type, year, month)
        first_weekday = get_first_weekday_index(calendar_type, year, month)
        month_name = get_month_name(calendar_type, month)
        today = get_today_in_calendar(calendar_type)

        is_current_month = (today['year'] == year and today['month'] == month)

        return JsonResponse({
            'success': True,
            'data': {
                'year': year,
                'month': month,
                'year_fa': to_persian_digits(year),
                'month_fa': to_persian_digits(month),
                'month_name': month_name,
                'days_in_month': days_in_month,
                'first_weekday': first_weekday,
                'today_day': today['day'] if is_current_month else None,
            }
        })
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'پارامترهای ورودی نامعتبر است'}, status=400)


@csrf_exempt
@ratelimit(key_prefix='api_convert', limit=30, window=60)
@require_http_methods(['GET', 'POST'])
def api_convert_date(request):
    try:
        if request.method == 'GET':
            calendar_type = request.GET.get('calendar_type')
            year = request.GET.get('year')
            month = request.GET.get('month')
            day = request.GET.get('day')
        else:
            if request.content_type == 'application/json':
                body = json.loads(request.body.decode('utf-8'))
            else:
                body = request.POST
            calendar_type = body.get('calendar_type')
            year = body.get('year')
            month = body.get('month')
            day = body.get('day')

        if not all([calendar_type, year, month, day]):
            return JsonResponse({
                'success': False,
                'error': 'پارامترهای calendar_type, year, month, day الزامی هستند'
            }, status=400)

        year = int(to_english_digits(year))
        month = int(to_english_digits(month))
        day = int(to_english_digits(day))

        if calendar_type not in ('shamsi', 'ghamari', 'miladi'):
            return JsonResponse({
                'success': False,
                'error': "calendar_type باید یکی از 'shamsi', 'ghamari', 'miladi' باشد"
            }, status=400)

        result = convert_date(calendar_type, year, month, day)
        return JsonResponse({'success': True, 'data': result})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON نامعتبر'}, status=400)
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'خطای غیرمنتظره: {str(e)}'}, status=500)


@login_required(login_url='core:index')
@ratelimit(key_prefix='server_time', limit=30, window=60)
@require_http_methods(['GET'])
def api_server_time(request):
    now_utc = dt.datetime.now(dt.timezone.utc)
    return JsonResponse({
        'success': True,
        'utc_iso': now_utc.isoformat(),
        'timestamp_ms': int(now_utc.timestamp() * 1000),
    })