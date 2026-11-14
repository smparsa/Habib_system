from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User,
    Profile,
    Job,
    FirstnameTbl,
    FamilynameTbl,
    UserGroup,
    ReservedNationalCode,
    StudyGroup,
    StudyField,
    StudySpecialization,
)


class StudySpecializationInline(admin.TabularInline):
    model = StudySpecialization
    extra = 0
    fk_name = "field"
    fields = ["name", "code", "is_active"]



class UserAdmin(BaseUserAdmin):
    model = User
    ordering = ["-date_joined"]
    list_display = ["mobile_number", "referrer_national_id", "is_active", "is_staff", "date_joined"]
    search_fields = ["mobile_number", "referrer_national_id"]
    fieldsets = (
        (None, {"fields": ("mobile_number", "password")}),
        ("اطلاعات", {"fields": ("referrer_national_id",)}),
        ("دسترسی‌ها", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("mobile_number", "password1", "password2"),
        }),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["national_id", "full_name", "user", "job_title", "department", "status"]
    list_display_links = ["national_id", "full_name"]
    search_fields = ["national_id", "first_name__first_name_fa", "last_name__familyname_fa", "user__mobile_number"]
    ordering = ["national_id"]

    def full_name(self, obj):
        return str(obj)
    full_name.short_description = "نام و نام خانوادگی"

    def user(self, obj):
        return obj.user.mobile_number if obj.user_id else ""
    user.short_description = "کاربر"

    def job_title(self, obj):
        return obj.job_title_id.first_name_fa if obj.job_title_id else ""
    job_title.short_description = "عنوان شغلی"

    def department(self, obj):
        return obj.department or ""
    department.short_description = "بخش"


admin.site.register(User, UserAdmin)


class StudyFieldInline(admin.TabularInline):
    model = StudyField
    extra = 0
    fk_name = "study_group"
    fields = ["name", "code", "is_active"]


@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active", "field_count"]
    list_filter = ["is_active"]
    search_fields = ["name", "code"]
    ordering = ["code"]

    def field_count(self, obj):
        return obj.fields.count()

    field_count.short_description = "تعداد رشته‌ها"


@admin.register(StudyField)
class StudyFieldAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "study_group", "is_active"]
    list_filter = ["study_group", "is_active"]
    search_fields = ["name", "code"]
    ordering = ["study_group__code", "name"]
    inlines = [StudySpecializationInline]


@admin.register(StudySpecialization)
class StudySpecializationAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "field", "is_active"]
    list_filter = ["field__study_group", "is_active"]
    search_fields = ["name", "code"]
    ordering = ["field__study_group__code", "field__name", "name"]


@admin.register(FirstnameTbl)
class FirstnameTblAdmin(admin.ModelAdmin):
    list_display = ["first_name_fa", "first_name_en"]
    search_fields = ["first_name_fa", "first_name_en"]
    ordering = ["first_name_fa"]


@admin.register(FamilynameTbl)
class FamilynameTblAdmin(admin.ModelAdmin):
    list_display = ["familyname_fa", "familyname_en"]
    search_fields = ["familyname_fa", "familyname_en"]
    ordering = ["familyname_fa"]

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = [
        "profile",
        "title",
        "job_code",
        "sector",
        "industry",
        "category",
        "occupation_title",
        "specialization",
        "is_current",
        "organization",
    ]
    list_filter = ["is_current", "sector", "industry"]
    search_fields = [
        "title",
        "job_code",
        "profile__user__mobile_number",
        "profile__national_id",
    ]
    autocomplete_fields = ["profile"]
    raw_id_fields = [
        "sector", "industry", "category", "occupation_title", "specialization",
    ]
    list_select_related = (
        "profile", "sector", "industry", "category", "occupation_title",
        "specialization",
    )


@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_active", "created_at"]
    search_fields = ["name", "code"]
    filter_horizontal = ["members"]


@admin.register(ReservedNationalCode)
class ReservedNationalCodeAdmin(admin.ModelAdmin):
    """کدهای ملی رزروشده/اختصاصی — همان ماژول «کنترل کد ملی» پنل مدیریت."""
    list_display = ["national_id", "access_level", "title", "is_active", "updated_at"]
    list_filter = ["access_level", "is_active"]
    search_fields = ["national_id", "title"]
    ordering = ["national_id"]
