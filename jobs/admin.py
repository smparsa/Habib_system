from django.contrib import admin

from .models import (
    Sector,
    Industry,
    JobCategory,
    JobTitle,
    JobSpecialization,
)


class IndustryInline(admin.TabularInline):
    model = Industry
    extra = 0
    fk_name = "sector"
    fields = ["name", "code", "description", "is_active"]


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active", "industry_count"]
    list_filter = ["is_active"]
    search_fields = ["name", "code"]
    ordering = ["code"]

    def industry_count(self, obj):
        return obj.industries.count()

    industry_count.short_description = "تعداد صنایع"


class JobCategoryInline(admin.TabularInline):
    model = JobCategory
    extra = 0
    fk_name = "industry"
    fields = ["name", "code", "is_active"]


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "sector", "parent", "level", "is_active"]
    list_filter = ["sector", "is_active"]
    search_fields = ["name", "code", "description"]
    ordering = ["code"]
    inlines = [JobCategoryInline]


class JobTitleInline(admin.TabularInline):
    model = JobTitle
    extra = 0
    fk_name = "category"
    fields = ["name", "code", "description", "is_active"]


@admin.register(JobCategory)
class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "industry", "is_active"]
    list_filter = ["industry__sector", "is_active"]
    search_fields = ["name", "code", "description"]
    ordering = ["code"]
    inlines = [JobTitleInline]


class JobSpecializationInline(admin.TabularInline):
    model = JobSpecialization
    extra = 0
    fk_name = "title"
    fields = ["name", "code", "description", "is_active"]


@admin.register(JobTitle)
class JobTitleAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "category", "is_active"]
    list_filter = ["category__industry__sector", "is_active"]
    search_fields = ["name", "code", "skill_tags", "description"]
    ordering = ["code"]
    inlines = [JobSpecializationInline]


@admin.register(JobSpecialization)
class JobSpecializationAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "title", "is_active"]
    list_filter = ["title__category__industry__sector", "is_active"]
    search_fields = ["name", "code", "description"]
    ordering = ["code"]
