from django.urls import path

from . import views

app_name = "cloudstorage"

urlpatterns = [
    path("", views.home, name="home"),
    # API های آپلود (JSON)
    path("api/quote/", views.api_quote, name="api_quote"),
    path("api/session/<str:token>/pay/", views.api_pay, name="api_pay"),
    path("api/session/<str:token>/upload/", views.api_upload, name="api_upload"),
    path("api/session/<str:token>/finalize/", views.api_finalize, name="api_finalize"),
    # خرید/مدیریت فضای ابری کاربر
    path("api/space/purchase/", views.api_purchase_space, name="api_purchase_space"),
    # سشن (بازیابی پس از قطع ارتباط)
    path("session/<str:token>/", views.session_detail, name="session_detail"),
    path("session/<str:token>/cancel/", views.session_cancel, name="session_cancel"),
    # مرور و دانلود
    path("browse/", views.browse, name="browse"),
    path("folder/<str:uid>/", views.folder_detail, name="folder_detail"),
    path("folder/<str:uid>/archive/", views.archive_create, name="archive_create"),
    path("folder/<str:uid>/sync/", views.sync_quote, name="sync_quote"),
    path("folder/<str:uid>/sync-download/plan/", views.sync_download_plan, name="sync_download_plan"),
    path("folder/<str:uid>/sync-download/charge/", views.sync_download_charge, name="sync_download_charge"),
    path("folder/<str:uid>/sync-toggle/", views.sync_toggle, name="sync_toggle"),
    path("folder/<str:uid>/delete/", views.folder_delete, name="folder_delete"),
    path("object/<str:uid>/<int:object_id>/download/", views.object_download, name="object_download"),
    # آرشیو زمان‌دار
    path("archive/<str:token>/download/", views.archive_download, name="archive_download"),
]