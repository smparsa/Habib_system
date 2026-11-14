from django.urls import path

from . import views

app_name = "accounting"

urlpatterns = [
    # ورود دو مرحله‌ای
    path("", views.index, name="index"),
    path("select/<int:fy_id>/", views.select_fiscal_year, name="select_fy"),
    path("login/<int:fy_id>/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("setup-credentials/", views.setup_credentials, name="setup_credentials"),

    # داشبورد
    path("dashboard/", views.dashboard, name="dashboard"),

    # اشخاص: کاربران اصلی سایت دارای کد ملی + دفتر بدهکار/بستانکار هر شخص
    path("persons/", views.persons_list, name="persons"),
    path("persons/<int:user_id>/ledger/", views.person_ledger_view, name="person_ledger"),

    # راهنمای جامع ماژول
    path("guide/", views.guide, name="guide"),

    # پلان حساب‌ها
    path("accounts/", views.accounts_list, name="accounts"),
    path("accounts/new/", views.account_create, name="account_create"),
    path("accounts/<int:pk>/toggle/", views.account_toggle, name="account_toggle"),
    path("accounts/<int:pk>/ledger/", views.account_ledger, name="account_ledger"),

    # اسناد حسابداری
    path("entries/", views.entries_list, name="entries"),
    path("entries/new/", views.entry_create, name="entry_create"),
    path("entries/<int:pk>/", views.entry_detail, name="entry_detail"),
    path("entries/<int:pk>/post/", views.entry_post, name="entry_post"),
    path("entries/<int:pk>/cancel/", views.entry_cancel, name="entry_cancel"),
    path("entries/<int:pk>/delete/", views.entry_delete, name="entry_delete"),

    # خزانه‌داری: چک
    path("cheques/", views.cheques_list, name="cheques"),
    path("cheques/new/", views.cheque_create, name="cheque_create"),
    path("cheques/<int:pk>/transition/", views.cheque_transition, name="cheque_transition"),

    # گزارش‌ها
    path("reports/trial-balance/", views.reports_trial_balance, name="report_trial_balance"),
    path("reports/income-statement/", views.reports_income_statement, name="report_income"),
    path("reports/balance-sheet/", views.reports_balance_sheet, name="report_balance"),
    path("reports/statement/", views.reports_statement, name="report_statement"),

    # سیستم و تنظیمات
    path("settings/", views.settings_view, name="settings"),
    path("fiscal-years/new/", views.fiscal_year_create, name="fiscal_year_create"),
    path("fiscal-years/<int:fy_id>/close/", views.fiscal_year_close, name="fiscal_year_close"),
]
