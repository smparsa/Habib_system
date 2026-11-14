from django.db import migrations


# نمونه‌های مشاغل رایج ایران در قالب ۵ لایه:
# Sector → Industry → JobCategory → JobTitle → JobSpecialization
SECTORS = [
    {
        "code": "SEC-001",
        "name": "فناوری اطلاعات",
        "description": "نرم‌افزار، شبکه، زیرساخت و خدمات فناوری",
        "industries": [
            {
                "code": "IND-001",
                "name": "نرم‌افزار",
                "categories": [
                    {
                        "code": "CAT-001",
                        "name": "توسعه‌دهنده نرم‌افزار",
                        "titles": [
                            {
                                "code": "TTL-001",
                                "name": "برنامه‌نویس وب",
                                "skills": ["PHP", "Laravel", "Python", "Django", "JavaScript", "React"],
                                "specs": [
                                    {"code": "SPE-001", "name": "توسعه‌دهنده Laravel", "skills": ["Laravel", "PHP"]},
                                    {"code": "SPE-002", "name": "توسعه‌دهنده Django", "skills": ["Django", "Python"]},
                                    {"code": "SPE-003", "name": "توسعه‌دهنده فرانت‌اند React", "skills": ["React", "JavaScript"]},
                                ],
                            },
                            {
                                "code": "TTL-002",
                                "name": "برنامه‌نویس موبایل",
                                "skills": ["Android", "iOS", "Flutter"],
                                "specs": [
                                    {"code": "SPE-004", "name": "توسعه‌دهنده اندروید", "skills": ["Kotlin", "Java"]},
                                    {"code": "SPE-005", "name": "توسعه‌دهنده iOS", "skills": ["Swift"]},
                                    {"code": "SPE-006", "name": "توسعه‌دهنده Flutter", "skills": ["Flutter", "Dart"]},
                                ],
                            },
                            {
                                "code": "TTL-003",
                                "name": "مهندس نرم‌افزار",
                                "skills": ["معماری نرم‌افزار", "طراحی سیستم"],
                                "specs": [
                                    {"code": "SPE-007", "name": "معمار نرم‌افزار", "skills": ["Microservices", "UML"]},
                                ],
                            },
                        ],
                    },
                    {
                        "code": "CAT-002",
                        "name": "مدیریت و رهبری فنی",
                        "titles": [
                            {
                                "code": "TTL-004",
                                "name": "مدیر فنی (CTO)",
                                "skills": ["رهبری تیم", "معماری سازمانی"],
                                "specs": [
                                    {"code": "SPE-008", "name": "معمار سیستم", "skills": ["Cloud", "DevOps"]},
                                ],
                            },
                            {
                                "code": "TTL-005",
                                "name": "مدیر محصول",
                                "skills": ["Product Strategy", "Agile"],
                                "specs": [
                                    {"code": "SPE-009", "name": "تحلیلگر محصول", "skills": ["PRD", "تحلیل بازار"]},
                                ],
                            },
                        ],
                    },
                ],
            },
            {
                "code": "IND-002",
                "name": "شبکه و زیرساخت",
                "categories": [
                    {
                        "code": "CAT-003",
                        "name": "مهندسی شبکه",
                        "titles": [
                            {
                                "code": "TTL-006",
                                "name": "مهندس شبکه",
                                "skills": ["Cisco", "Routing", "Network Security"],
                                "specs": [
                                    {"code": "SPE-010", "name": "مدیریت سرور لینوکس", "skills": ["Linux", "Docker"]},
                                ],
                            },
                            {
                                "code": "TTL-007",
                                "name": "مدیر زیرساخت ابری",
                                "skills": ["Cloud", "Kubernetes"],
                                "specs": [
                                    {"code": "SPE-011", "name": "متخصص DevOps", "skills": ["CI/CD", "Kubernetes"]},
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "code": "SEC-002",
        "name": "خدمات",
        "description": "بانکداری، بیمه، آموزش، بهداشت، فروش و خدمات",
        "industries": [
            {
                "code": "IND-003",
                "name": "بانکداری و بیمه",
                "categories": [
                    {
                        "code": "CAT-004",
                        "name": "مالی و حسابداری",
                        "titles": [
                            {
                                "code": "TTL-008",
                                "name": "حسابدار",
                                "skills": ["حسابداری", "مالیات"],
                                "specs": [
                                    {"code": "SPE-012", "name": "حسابداری صنعتی", "skills": ["بهای تمام‌شده"]},
                                    {"code": "SPE-013", "name": "حسابدار مالیاتی", "skills": ["مالیات", "اظهارنامه"]},
                                ],
                            },
                            {
                                "code": "TTL-009",
                                "name": "تحلیلگر مالی",
                                "skills": ["تحلیل مالی", "سرمایه‌گذاری"],
                                "specs": [
                                    {"code": "SPE-014", "name": "تحلیل‌گر سرمایه‌گذاری", "skills": ["ارزش‌گذاری"]},
                                ],
                            },
                        ],
                    },
                    {
                        "code": "CAT-005",
                        "name": "عملیات بانکی",
                        "titles": [
                            {
                                "code": "TTL-010",
                                "name": "کارشناس بانک",
                                "skills": ["عملیات بانکی", "مشتری مداری"],
                                "specs": [
                                    {"code": "SPE-015", "name": "کارشناس تسهیلات بانکی", "skills": ["تسهیلات", "اعتبارسنجی"]},
                                ],
                            },
                        ],
                    },
                ],
            },
            {
                "code": "IND-004",
                "name": "آموزش",
                "categories": [
                    {
                        "code": "CAT-006",
                        "name": "مدرس و معلم",
                        "titles": [
                            {
                                "code": "TTL-011",
                                "name": "مدرس زبان",
                                "skills": ["انگلیسی", "تدریس"],
                                "specs": [
                                    {"code": "SPE-016", "name": "مدرس آیلتس", "skills": ["IELTS"]},
                                    {"code": "SPE-017", "name": "مدرس تافل", "skills": ["TOEFL"]},
                                ],
                            },
                            {
                                "code": "TTL-012",
                                "name": "مدرس ریاضی",
                                "skills": ["ریاضیات", "کنکور"],
                                "specs": [
                                    {"code": "SPE-018", "name": "مدرس کنکور", "skills": ["ریاضیات کنکور"]},
                                ],
                            },
                            {
                                "code": "TTL-013",
                                "name": "معلم ابتدایی",
                                "skills": ["آموزش ابتدایی", "تربیت"],
                                "specs": [
                                    {"code": "SPE-019", "name": "معلم چندپایه", "skills": ["آموزش چندپایه"]},
                                ],
                            },
                        ],
                    },
                ],
            },
            {
                "code": "IND-005",
                "name": "بهداشت و درمان",
                "categories": [
                    {
                        "code": "CAT-007",
                        "name": "پزشکی",
                        "titles": [
                            {
                                "code": "TTL-014",
                                "name": "پزشک عمومی",
                                "skills": ["طب عمومی"],
                                "specs": [
                                    {"code": "SPE-020", "name": "پزشک خانواده", "skills": ["طب خانواده"]},
                                ],
                            },
                            {
                                "code": "TTL-015",
                                "name": "دندانپزشک",
                                "skills": ["دندانپزشکی"],
                                "specs": [
                                    {"code": "SPE-021", "name": "دندانپزشک ترمیمی", "skills": ["ترمیم"]},
                                ],
                            },
                        ],
                    },
                    {
                        "code": "CAT-008",
                        "name": "پرستاری",
                        "titles": [
                            {
                                "code": "TTL-016",
                                "name": "پرستار",
                                "skills": ["پرستاری", "مراقبت"],
                                "specs": [
                                    {"code": "SPE-022", "name": "پرستار بخش ICU", "skills": ["مراقبت ویژه"]},
                                ],
                            },
                        ],
                    },
                ],
            },
            {
                "code": "IND-006",
                "name": "فروش و بازاریابی",
                "categories": [
                    {
                        "code": "CAT-009",
                        "name": "فروش",
                        "titles": [
                            {
                                "code": "TTL-017",
                                "name": "کارشناس فروش",
                                "skills": ["فروش", "مذاکره"],
                                "specs": [
                                    {"code": "SPE-023", "name": "فروش سازمانی (B2B)", "skills": ["B2B"]},
                                ],
                            },
                            {
                                "code": "TTL-018",
                                "name": "بازاریاب دیجیتال",
                                "skills": ["دیجیتال مارکتینگ", "سئو"],
                                "specs": [
                                    {"code": "SPE-024", "name": "متخصص سئو", "skills": ["SEO"]},
                                ],
                            },
                        ],
                    },
                    {
                        "code": "CAT-010",
                        "name": "خدمات مشتریان",
                        "titles": [
                            {
                                "code": "TTL-019",
                                "name": "کارشناس پشتیبانی مشتری",
                                "skills": ["پشتیبانی", "CRM"],
                                "specs": [
                                    {"code": "SPE-025", "name": "پشتیبان مرکز تماس", "skills": ["Call Center"]},
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "code": "SEC-003",
        "name": "صنعت",
        "description": "ساختمان، خودرو، تولید و صنایع",
        "industries": [
            {
                "code": "IND-007",
                "name": "ساختمان و عمران",
                "categories": [
                    {
                        "code": "CAT-011",
                        "name": "مهندسی عمران",
                        "titles": [
                            {
                                "code": "TTL-020",
                                "name": "مهندس عمران",
                                "skills": ["عمران", "نظارت"],
                                "specs": [
                                    {"code": "SPE-026", "name": "مهندس سازه", "skills": ["طراحی سازه"]},
                                    {"code": "SPE-027", "name": "مهندس اجرا", "skills": ["اجرای ساختمان"]},
                                ],
                            },
                        ],
                    },
                    {
                        "code": "CAT-012",
                        "name": "معماری",
                        "titles": [
                            {
                                "code": "TTL-021",
                                "name": "معمار",
                                "skills": ["معماری", "طراحی"],
                                "specs": [
                                    {"code": "SPE-028", "name": "طراح داخلی", "skills": ["دکوراسیون داخلی"]},
                                ],
                            },
                        ],
                    },
                ],
            },
            {
                "code": "IND-008",
                "name": "خودرو",
                "categories": [
                    {
                        "code": "CAT-013",
                        "name": "فنی و تعمیرات",
                        "titles": [
                            {
                                "code": "TTL-022",
                                "name": "مکانیک خودرو",
                                "skills": ["مکانیک", "تعمیرات"],
                                "specs": [
                                    {"code": "SPE-029", "name": "مکانیک موتور", "skills": ["موتور"]},
                                    {"code": "SPE-030", "name": "برق خودرو", "skills": ["برق خودرو"]},
                                    {"code": "SPE-031", "name": "متخصص جلوبندی", "skills": ["جلوبندی"]},
                                ],
                            },
                        ],
                    },
                ],
            },
            {
                "code": "IND-009",
                "name": "تولید و کارخانه",
                "categories": [
                    {
                        "code": "CAT-014",
                        "name": "کارخانه و تولید",
                        "titles": [
                            {
                                "code": "TTL-023",
                                "name": "اپراتور خط تولید",
                                "skills": ["تولید", "خط تولید"],
                                "specs": [
                                    {"code": "SPE-032", "name": "اپراتور دستگاه CNC", "skills": ["CNC"]},
                                ],
                            },
                            {
                                "code": "TTL-024",
                                "name": "کارشناس کنترل کیفیت",
                                "skills": ["کیفیت", "استاندارد"],
                                "specs": [
                                    {"code": "SPE-033", "name": "کارشناس ISO 9001", "skills": ["ISO"]},
                                ],
                            },
                        ],
                    },
                    {
                        "code": "CAT-015",
                        "name": "مهندسی صنایع",
                        "titles": [
                            {
                                "code": "TTL-025",
                                "name": "مهندس صنایع",
                                "skills": ["بهینه‌سازی", "برنامه‌ریزی تولید"],
                                "specs": [
                                    {"code": "SPE-034", "name": "کارشناس بهینه‌سازی فرآیند", "skills": ["Lean"]},
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "code": "SEC-004",
        "name": "کشاورزی و دامپروری",
        "description": "کشاورزی، باغبانی و پرورش دام",
        "industries": [
            {
                "code": "IND-010",
                "name": "کشاورزی",
                "categories": [
                    {
                        "code": "CAT-016",
                        "name": "باغبانی",
                        "titles": [
                            {
                                "code": "TTL-026",
                                "name": "کارشناس باغبانی",
                                "skills": ["باغبانی", "گلخانه"],
                                "specs": [
                                    {"code": "SPE-035", "name": "مدیر گلخانه", "skills": ["گلخانه"]},
                                ],
                            },
                        ],
                    },
                ],
            },
            {
                "code": "IND-011",
                "name": "دامپروری",
                "categories": [
                    {
                        "code": "CAT-017",
                        "name": "پرورش دام",
                        "titles": [
                            {
                                "code": "TTL-027",
                                "name": "دامدار",
                                "skills": ["پرورش دام", "دامپزشکی"],
                                "specs": [
                                    {"code": "SPE-036", "name": "پرورش گاو شیری", "skills": ["گاوداری"]},
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    },
]


def seed_catalog(apps, schema_editor):
    Sector = apps.get_model("jobs", "Sector")
    Industry = apps.get_model("jobs", "Industry")
    JobCategory = apps.get_model("jobs", "JobCategory")
    JobTitle = apps.get_model("jobs", "JobTitle")
    JobSpecialization = apps.get_model("jobs", "JobSpecialization")

    def ensure(model, code, **fields):
        obj, _ = model.objects.get_or_create(code=code, defaults=fields)
        for key, value in fields.items():
            if getattr(obj, key) != value:
                setattr(obj, key, value)
                obj.save(update_fields=[key])
                break
        return obj

    for sector_data in SECTORS:
        sector = ensure(
            Sector,
            sector_data["code"],
            name=sector_data["name"],
            description=sector_data.get("description", ""),
            is_active=True,
        )
        for industry_data in sector_data["industries"]:
            industry = ensure(
                Industry,
                industry_data["code"],
                sector=sector,
                name=industry_data["name"],
                parent=None,
                level=2,
                is_active=True,
            )
            for category_data in industry_data.get("categories", []):
                category = ensure(
                    JobCategory,
                    category_data["code"],
                    industry=industry,
                    name=category_data["name"],
                    is_active=True,
                )
                for title_data in category_data.get("titles", []):
                    title = ensure(
                        JobTitle,
                        title_data["code"],
                        category=category,
                        name=title_data["name"],
                        skill_tags=title_data.get("skills", []),
                        is_active=True,
                    )
                    for spec_data in title_data.get("specs", []):
                        ensure(
                            JobSpecialization,
                            spec_data["code"],
                            title=title,
                            name=spec_data["name"],
                            is_active=True,
                        )


def unseed_catalog(apps, schema_editor):
    # دادهٔ نمونه حذف نمی‌شود؛ چون ممکن است مشاغل کاربران به آن اشاره کنند (PROTECT)
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_catalog, unseed_catalog),
    ]
