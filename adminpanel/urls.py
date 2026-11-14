from django.urls import path

from cloudstorage import adminviews as storage_views

from . import views

app_name = "adminpanel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("jobs/", views.catalog_home, name="catalog_home"),
    # ماژول کاربران و پروفایل‌ها
    path("users/", views.users_list, name="users_list"),
    path("users/<int:pk>/toggle/", views.user_toggle, name="user_toggle"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    # ماژول پالایش محتوا: واژه‌ها و عبارت‌های حساس تیکت‌ها
    path("words/", views.words_list, name="words_list"),
    path("words/add/", views.word_add, name="word_add"),
    path("words/<int:pk>/edit/", views.word_edit, name="word_edit"),
    path("words/<int:pk>/toggle/", views.word_toggle, name="word_toggle"),
    path("words/<int:pk>/delete/", views.word_delete, name="word_delete"),
    # ماژول «مخاطبین هدف تیکت»: جوامع هدف تعریف‌شده توسط ادمین
    path("audiences/", views.audiences_list, name="audiences_list"),
    path("audiences/add/", views.audience_add, name="audience_add"),
    path("audiences/<int:pk>/edit/", views.audience_edit, name="audience_edit"),
    path("audiences/<int:pk>/toggle/", views.audience_toggle, name="audience_toggle"),
    path("audiences/<int:pk>/delete/", views.audience_delete, name="audience_delete"),
    # ماژول «انواع تیکت»: دسته‌های قابل تعریف توسط ادمین
    path("ticket-types/", views.ticket_types_list, name="ticket_types_list"),
    path("ticket-types/add/", views.ticket_type_add, name="ticket_type_add"),
    path("ticket-types/<int:pk>/edit/", views.ticket_type_edit, name="ticket_type_edit"),
    path("ticket-types/<int:pk>/toggle/", views.ticket_type_toggle, name="ticket_type_toggle"),
    path("ticket-types/<int:pk>/delete/", views.ticket_type_delete, name="ticket_type_delete"),
    # ماژول «اخبار فوری» هدر برنامه
    path("breaking-news/", views.breaking_news_list, name="breaking_news_list"),
    path("breaking-news/add/", views.breaking_news_add, name="breaking_news_add"),
    path("breaking-news/<int:pk>/edit/", views.breaking_news_edit, name="breaking_news_edit"),
    path("breaking-news/<int:pk>/toggle/", views.breaking_news_toggle, name="breaking_news_toggle"),
    path("breaking-news/<int:pk>/delete/", views.breaking_news_delete, name="breaking_news_delete"),
    # ماژول «تبلیغات»: لوگوی تبلیغاتی کاربران — پخش در نوار متحرک پایین داشبورد
    path("ads/", views.ads_list, name="ads_list"),
    path("ads/<int:pk>/edit/", views.ads_edit, name="ads_edit"),
    path("ads/<int:pk>/move/<str:direction>/", views.ads_move, name="ads_move"),
    path("ads/<int:pk>/toggle/", views.ads_toggle, name="ads_toggle"),
    path("ads/<int:pk>/approve/", views.ads_approve, name="ads_approve"),
    path("ads/<int:pk>/reject/", views.ads_reject, name="ads_reject"),
    path("ads/<int:pk>/delete/", views.ads_delete, name="ads_delete"),
    path("ads/settings/", views.ads_settings, name="ads_settings"),
    # ماژول «اسلایدشوی آمار داشبورد»: ۴ باکس آمار بالای «ماژول‌های کسب‌وکار»
    path("stat-slides/", views.stat_slides_list, name="stat_slides_list"),
    path("stat-slides/add/", views.stat_slide_add, name="stat_slide_add"),
    path("stat-slides/<int:pk>/edit/", views.stat_slide_edit, name="stat_slide_edit"),
    path("stat-slides/<int:pk>/move/<str:direction>/", views.stat_slide_move, name="stat_slide_move"),
    path("stat-slides/<int:pk>/toggle/", views.stat_slide_toggle, name="stat_slide_toggle"),
    path("stat-slides/<int:pk>/approve/", views.stat_slide_approve, name="stat_slide_approve"),
    path("stat-slides/<int:pk>/reject/", views.stat_slide_reject, name="stat_slide_reject"),
    path("stat-slides/<int:pk>/delete/", views.stat_slide_delete, name="stat_slide_delete"),
    path("stat-slides/settings/", views.stat_slides_settings, name="stat_slides_settings"),
    path("stat-slides/boxes/<int:pk>/update/", views.stat_box_update, name="stat_box_update"),
    path("stat-slides/boxes/<int:pk>/toggle/", views.stat_box_toggle, name="stat_box_toggle"),
    # مدیریت «محل‌های تبلیغ هدر»: هر هدری که نوار تبلیغات در آن پخش شود؛ فعال‍/غیرفعال + ترتیب
    path("header-placements/", views.header_placements_list, name="header_placements_list"),
    path("header-placements/add/", views.header_placement_add, name="header_placement_add"),
    path("header-placements/<int:pk>/edit/", views.header_placement_edit, name="header_placement_edit"),
    path("header-placements/<int:pk>/toggle/", views.header_placement_toggle, name="header_placement_toggle"),
    path("header-placements/<int:pk>/delete/", views.header_placement_delete, name="header_placement_delete"),
    # ماژول «سکه و کیف پول»
    path("wallet/settings/", views.wallet_settings, name="wallet_settings"),
    # تنظیمات «سرویس موقعیت»: نقشهٔ نمایشی (نشان/OSM/گوگل) و منبع GPS
    path("location/settings/", views.location_settings, name="location_settings"),
    path("wallet/costs/", views.feature_costs_list, name="feature_costs_list"),
    path("wallet/costs/add/", views.feature_cost_add, name="feature_cost_add"),
    path("wallet/costs/<int:pk>/edit/", views.feature_cost_edit, name="feature_cost_edit"),
    path("wallet/costs/<int:pk>/toggle/", views.feature_cost_toggle, name="feature_cost_toggle"),
    path("wallet/costs/<int:pk>/delete/", views.feature_cost_delete, name="feature_cost_delete"),
    # پاداش‌های سکه: عنوان و میزانِ پاداشِ هر فعالیت (معرف، مطالعه در مجله و ...)
    path("wallet/rewards/", views.reward_rules_list, name="reward_rules_list"),
    path("wallet/rewards/add/", views.reward_rule_add, name="reward_rule_add"),
    path("wallet/rewards/<int:pk>/edit/", views.reward_rule_edit, name="reward_rule_edit"),
    path("wallet/rewards/<int:pk>/toggle/", views.reward_rule_toggle, name="reward_rule_toggle"),
    path("wallet/rewards/<int:pk>/delete/", views.reward_rule_delete, name="reward_rule_delete"),
    path("wallet/orders/", views.wallet_orders, name="wallet_orders"),
    path("wallet/orders/<int:pk>/action/", views.wallet_order_action, name="wallet_order_action"),
    path("wallet/transfers/", views.wallet_transfers, name="wallet_transfers"),
    path("wallet/wallets/", views.wallet_wallets, name="wallet_wallets"),
    # ماژول «اطلاعات تحصیلی»: خانهٔ ماژول + مراکز دانشگاهی + گروه‌های امتحانی،
    # رشته‌ها و گرایش‌های مرجع
    path("education/", views.education_home, name="education_home"),
    path("education/institutions/", views.education_institutions_list, name="education_institutions_list"),
    path("education/institutions/add/", views.education_institution_add, name="education_institution_add"),
    path("education/institutions/<int:pk>/edit/", views.education_institution_edit, name="education_institution_edit"),
    path("education/institutions/<int:pk>/toggle/", views.education_institution_toggle, name="education_institution_toggle"),
    path("education/institutions/<int:pk>/delete/", views.education_institution_delete, name="education_institution_delete"),
    path("education/groups/", views.education_groups_list, name="education_groups_list"),
    path("education/groups/add/", views.education_group_add, name="education_group_add"),
    path("education/groups/<int:pk>/edit/", views.education_group_edit, name="education_group_edit"),
    path("education/groups/<int:pk>/toggle/", views.education_group_toggle, name="education_group_toggle"),
    path("education/groups/<int:pk>/delete/", views.education_group_delete, name="education_group_delete"),
    path("education/fields/", views.education_fields_list, name="education_fields_list"),
    path("education/fields/add/", views.education_field_add, name="education_field_add"),
    path("education/fields/<int:pk>/edit/", views.education_field_edit, name="education_field_edit"),
    path("education/fields/<int:pk>/toggle/", views.education_field_toggle, name="education_field_toggle"),
    path("education/fields/<int:pk>/delete/", views.education_field_delete, name="education_field_delete"),
    path("education/specializations/", views.education_specializations_list, name="education_specializations_list"),
    path("education/specializations/add/", views.education_specialization_add, name="education_specialization_add"),
    path("education/specializations/<int:pk>/edit/", views.education_specialization_edit, name="education_specialization_edit"),
    path("education/specializations/<int:pk>/toggle/", views.education_specialization_toggle, name="education_specialization_toggle"),
    path("education/specializations/<int:pk>/delete/", views.education_specialization_delete, name="education_specialization_delete"),
    # ماژول «اسامی»: جدول نام‌ها و نام خانوادگیِ انتخابیِ پروفایل (تکمیل دیتابیس)
    path("names/", views.names_list, name="names_list"),
    path("names/<str:kind>/add/", views.name_add, name="name_add"),
    path("names/<str:kind>/<int:pk>/edit/", views.name_edit, name="name_edit"),
    path("names/<str:kind>/<int:pk>/delete/", views.name_delete, name="name_delete"),
    # ماژول «اطلاعات مکانی»: جدول مرجع کشور/استان/شهرستانِ محل سکونت (تکمیل دیتابیس)
    path("locations/", views.locations_list, name="locations_list"),
    path("locations/<str:kind>/add/", views.location_add, name="location_add"),
    path("locations/<str:kind>/<int:pk>/edit/", views.location_edit, name="location_edit"),
    path("locations/<str:kind>/<int:pk>/delete/", views.location_delete, name="location_delete"),
    # ماژول «فضای ذخیره‌سازی ابری (Cloud Object Storage)»
    path("storage/", storage_views.storage_home, name="storage_home"),
    path("storage/queues/", storage_views.storage_queues, name="storage_queues"),
    path("storage/reports/", storage_views.storage_reports, name="storage_reports"),
    path("storage/audit/", storage_views.storage_audit, name="storage_audit"),
    path("storage/purge-archives/", storage_views.storage_purge_archives, name="storage_purge_archives"),
    # ماژول «کنترل کد ملی»: کدهای ملیِ رزروشده/اختصاصی که کاربران عادی نمی‌توانند ثبت کنند
    path("national-codes/", views.national_codes_list, name="national_codes_list"),
    path("national-codes/add/", views.national_code_add, name="national_code_add"),
    path("national-codes/<int:pk>/edit/", views.national_code_edit, name="national_code_edit"),
    path("national-codes/<int:pk>/toggle/", views.national_code_toggle, name="national_code_toggle"),
    path("national-codes/<int:pk>/delete/", views.national_code_delete, name="national_code_delete"),
    # ماژول «پشتیبان‌گیری و بازیابی دیتابیس»
    path("backup/", views.backup_home, name="backup_home"),
    path("backup/now/", views.backup_now, name="backup_now"),
    path("backup/download-all/", views.backup_download_all, name="backup_download_all"),
    path("backup/<int:pk>/download/", views.backup_download, name="backup_download"),
    path("backup/<int:pk>/delete/", views.backup_delete, name="backup_delete"),
    path("backup/<int:pk>/restore/", views.backup_restore, name="backup_restore"),
    # پنج لایهٔ کاتالوگ (عملیات‌های تکی باید قبل از فهرست بیایند)
    path("jobs/<str:layer>/add/", views.layer_add, name="layer_add"),
    path("jobs/<str:layer>/<int:pk>/edit/", views.layer_edit, name="layer_edit"),
    path("jobs/<str:layer>/<int:pk>/delete/", views.layer_delete, name="layer_delete"),
    path("jobs/<str:layer>/<int:pk>/toggle/", views.layer_toggle, name="layer_toggle"),
    path("jobs/<str:layer>/", views.layer_list, name="layer_list"),
]
