from django.db import migrations


INSTITUTIONS = [
    ("دانشگاه تهران", "University of Tehran", "GOV-UT", "government", "تهران", "تهران"),
    ("دانشگاه صنعتی شریف", "Sharif University of Technology", "GOV-SUT", "government", "تهران", "تهران"),
    ("دانشگاه صنعتی امیرکبیر", "Amirkabir University of Technology", "GOV-AUT", "government", "تهران", "تهران"),
    ("دانشگاه علم و صنعت ایران", "Iran University of Science and Technology", "GOV-IUST", "government", "تهران", "تهران"),
    ("دانشگاه شهید بهشتی", "Shahid Beheshti University", "GOV-SBU", "government", "تهران", "تهران"),
    ("دانشگاه علامه طباطبائی", "Allameh Tabataba'i University", "GOV-ATU", "government", "تهران", "تهران"),
    ("دانشگاه تربیت مدرس", "Tarbiat Modares University", "GOV-TMU", "government", "تهران", "تهران"),
    ("دانشگاه خواجه نصیرالدین طوسی", "K. N. Toosi University of Technology", "GOV-KNTU", "government", "تهران", "تهران"),
    ("دانشگاه صنعتی شریف - پردیس بین‌الملل", "Sharif International Campus", "GOV-SHIC", "government", "تهران", "تهران"),
    ("دانشگاه هنر", "Art University", "GOV-AU", "government", "تهران", "تهران"),
    ("دانشگاه علوم پزشکی تهران", "Tehran University of Medical Sciences", "GOV-TUMS", "government", "تهران", "تهران"),
    ("دانشگاه علوم پزشکی ایران", "Iran University of Medical Sciences", "GOV-IUMS", "government", "تهران", "تهران"),
    ("دانشگاه علوم پزشکی شهید بهشتی", "Shahid Beheshti University of Medical Sciences", "GOV-SBMU", "government", "تهران", "تهران"),
    ("دانشگاه فردوسی مشهد", "Ferdowsi University of Mashhad", "GOV-FUM", "government", "خراسان رضوی", "مشهد"),
    ("دانشگاه شیراز", "Shiraz University", "GOV-SHU", "government", "فارس", "شیراز"),
    ("دانشگاه صنعتی شیراز", "Shiraz University of Technology", "GOV-SUTEC", "government", "فارس", "شیراز"),
    ("دانشگاه اصفهان", "University of Isfahan", "GOV-UI", "government", "اصفهان", "اصفهان"),
    ("دانشگاه صنعتی اصفهان", "Isfahan University of Technology", "GOV-IUT", "government", "اصفهان", "اصفهان"),
    ("دانشگاه تبریز", "University of Tabriz", "GOV-TAB", "government", "آذربایجان شرقی", "تبریز"),
    ("دانشگاه شهید مدنی آذربایجان", "Azarbaijan Shahid Madani University", "GOV-ASMU", "government", "آذربایجان شرقی", "تبریز"),
    ("دانشگاه گیلان", "University of Guilan", "GOV-GU", "government", "گیلان", "رشت"),
    ("دانشگاه مازندران", "University of Mazandaran", "GOV-UMZ", "government", "مازندران", "بابلسر"),
    ("دانشگاه کرمان", "Shahid Bahonar University of Kerman", "GOV-SBUK", "government", "کرمان", "کرمان"),
    ("دانشگاه یزد", "Yazd University", "GOV-YU", "government", "یزد", "یزد"),
    ("دانشگاه ارومیه", "Urmia University", "GOV-UU", "government", "آذربایجان غربی", "ارومیه"),
    ("دانشگاه رازی", "Razi University", "GOV-RU", "government", "کرمانشاه", "کرمانشاه"),
    ("دانشگاه بوعلی سینا", "Bu-Ali Sina University", "GOV-BASU", "government", "همدان", "همدان"),
    ("دانشگاه کاشان", "University of Kashan", "GOV-UK", "government", "اصفهان", "کاشان"),
    ("دانشگاه سمنان", "Semnan University", "GOV-SU", "government", "سمنان", "سمنان"),
    ("دانشگاه زنجان", "University of Zanjan", "GOV-ZNU", "government", "زنجان", "زنجان"),
    ("دانشگاه لرستان", "Lorestan University", "GOV-LU", "government", "لرستان", "خرم‌آباد"),
    ("دانشگاه کردستان", "University of Kurdistan", "GOV-UKURD", "government", "کردستان", "سنندج"),
    ("دانشگاه گلستان", "University of Golestan", "GOV-GU2", "government", "گلستان", "گرگان"),
    ("دانشگاه هرمزگان", "University of Hormozgan", "GOV-UH", "government", "هرمزگان", "بندرعباس"),
    ("دانشگاه سیستان و بلوچستان", "University of Sistan and Baluchestan", "GOV-USB", "government", "سیستان و بلوچستان", "زاهدان"),
    ("دانشگاه شهید چمران اهواز", "Shahid Chamran University of Ahvaz", "GOV-SCU", "government", "خوزستان", "اهواز"),
    ("دانشگاه آزاد اسلامی واحد علوم و تحقیقات", "Islamic Azad University, Science and Research Branch", "AZ-SR", "azad", "تهران", "تهران"),
    ("دانشگاه آزاد اسلامی واحد Tehran مرکزی", "Islamic Azad University, Central Tehran Branch", "AZ-CT", "azad", "تهران", "تهران"),
    ("دانشگاه آزاد اسلامی واحد تهران جنوب", "Islamic Azad University, South Tehran Branch", "AZ-ST", "azad", "تهران", "تهران"),
    ("دانشگاه آزاد اسلامی واحد کرج", "Islamic Azad University, Karaj Branch", "AZ-KAR", "azad", "البرز", "کرج"),
    ("دانشگاه آزاد اسلامی واحد مشهد", "Islamic Azad University, Mashhad Branch", "AZ-MSH", "azad", "خراسان رضوی", "مشهد"),
    ("دانشگاه آزاد اسلامی واحد اصفهان (خوراسگان)", "Islamic Azad University, Khorasgan Branch", "AZ-KHO", "azad", "اصفهان", "اصفهان"),
    ("دانشگاه آزاد اسلامی واحد شیراز", "Islamic Azad University, Shiraz Branch", "AZ-SHI", "azad", "فارس", "شیراز"),
    ("دانشگاه آزاد اسلامی واحد تبریز", "Islamic Azad University, Tabriz Branch", "AZ-TAB", "azad", "آذربایجان شرقی", "تبریز"),
    ("دانشگاه آزاد اسلامی واحد نجف‌آباد", "Islamic Azad University, Najafabad Branch", "AZ-NAJ", "azad", "اصفهان", "نجف‌آباد"),
    ("دانشگاه پیام نور مرکز تهران", "Payame Noor University, Tehran Center", "PNU-TEH", "government", "تهران", "تهران"),
    ("دانشگاه غیرانتفاعی امام رضا (ع)", "Imam Reza Non-Profit University", "NPR-IMAMREZA", "non_profit", "خراسان رضوی", "مشهد"),
    ("دانشگاه غیرانتفاعی علم و فرهنگ", "Science and Culture University", "NPR-SCU", "non_profit", "تهران", "تهران"),
    ("دانشگاه غیرانتفاعی سوره", "Soureh Non-Profit University", "NPR-SOUREH", "non_profit", "تهران", "تهران"),
    ("دانشگاه غیرانتفاعی شمال", "Shomal University", "NPR-SHOMAL", "non_profit", "مازندران", "آمل"),
    ("دانشگاه غیرانتفاعی خیام", "Khayyam University", "NPR-KHAYYAM", "non_profit", "خراسان رضوی", "مشهد"),
    ("مؤسسه آموزش عالی غیرانتفاعی پارس مهر فارس", "Pars Mehr Higher Education Institute", "NPR-PMF", "non_profit", "فارس", "شیراز"),
    ("مؤسسه آموزش عالی انتفاعی علوم و فناوری آریان", "Arian Institute of Higher Education", "PRF-ARIAN", "other_profit", "تهران", "تهران"),
]


FIELDS = [
    ("ریاضی", "Mathematics", "MATH-001", "EG-SC"),
    ("آمار و آمار", "Statistics", "MATH-002", "EG-SC"),
    ("فیزیک", "Physics", "SCI-001", "EG-SC"),
    ("شیمی", "Chemistry", "SCI-002", "EG-SC"),
    ("زیست‌شناسی", "Biology", "SCI-003", "EG-SC"),
    ("زمین‌شناسی", "Geology", "SCI-004", "EG-SC"),
    ("علوم کامپیوتر", "Computer Science", "ENG-001", "EG-TM"),
    ("مهندسی کامپیوتر", "Computer Engineering", "ENG-002", "EG-TM"),
    ("مهندسی فناوری اطلاعات", "Information Technology Engineering", "ENG-003", "EG-TM"),
    ("مهندسی برق", "Electrical Engineering", "ENG-004", "EG-TM"),
    ("مهندسی مکانیک", "Mechanical Engineering", "ENG-005", "EG-TM"),
    ("مهندسی عمران", "Civil Engineering", "ENG-006", "EG-TM"),
    ("مهندسی معماری", "Architecture", "ENG-007", "EG-TM"),
    ("مهندسی صنایع", "Industrial Engineering", "ENG-008", "EG-TM"),
    ("مهندسی شیمی", "Chemical Engineering", "ENG-009", "EG-TM"),
    ("مهندسی مواد و متالورژی", "Materials and Metallurgy Engineering", "ENG-010", "EG-TM"),
    ("مهندسی نفت", "Petroleum Engineering", "ENG-011", "EG-TM"),
    ("مهندسی انرژی", "Energy Engineering", "ENG-012", "EG-TM"),
    ("مهندسی صنایع و سیستم‌های تولید", "Manufacturing and Production Systems", "ENG-013", "EG-TM"),
    ("حقوق", "Law", "HUM-001", "EG-HU"),
    ("حسابداری و مالی", "Accounting and Finance", "HUM-002", "EG-HU"),
    ("اقتصاد", "Economics", "HUM-003", "EG-HU"),
    ("مدیریت", "Management", "HUM-004", "EG-HU"),
    ("روان‌شناسی", "Psychology", "HUM-005", "EG-HU"),
    ("علوم تربیتی و آموزش", "Educational Sciences", "HUM-006", "EG-HU"),
    ("جامعه‌شناسی", "Sociology", "HUM-007", "EG-HU"),
    ("علوم سیاسی", "Political Science", "HUM-008", "EG-HU"),
    ("جغرافیا", "Geography", "HUM-009", "EG-HU"),
    ("زبان و ادبیات فارسی", "Persian Language and Literature", "HUM-010", "EG-HU"),
    ("زبان و ادبیات انگلیسی", "English Language and Literature", "HUM-011", "EG-HU"),
    ("تاریخ", "History", "HUM-012", "EG-HU"),
    ("فلسفه", "Philosophy", "HUM-013", "EG-HU"),
    ("الهیات و معارف اسلامی", "Islamic Theology", "HUM-014", "EG-HU"),
    ("خبریات و ارتباطات", "Media and Communications", "HUM-015", "EG-HU"),
    ("اطلاعات و کتابداری", "Information and Library Science", "HUM-016", "EG-HU"),
    ("پزشکی و بالینی", "Medicine and Clinical", "MED-001", "EG-HU"),
    ("دندان‌پزشکی", "Dentistry", "MED-002", "EG-HU"),
    ("داروسازی", "Pharmacy", "MED-003", "EG-HU"),
    ("پرستاری و مama", "Nursing", "MED-004", "EG-HU"),
    ("علوم آزمایشگاهی", "Medical Laboratory Sciences", "MED-005", "EG-HU"),
    ("بهداشت و بهداشت عمومی", "Public Health", "MED-006", "EG-HU"),
    ("فیزیوتراپی و توانبخشی", "Physiotherapy and Rehabilitation", "MED-007", "EG-HU"),
    ("غذایی و علوم غذایی", "Nutritional Sciences", "MED-008", "EG-HU"),
    ("دامپزشکی", "Veterinary Medicine", "AGR-001", "EG-HU"),
    ("مهندسی کشاورزی", "Agricultural Engineering", "AGR-002", "EG-HU"),
    ("علوم و مهندسی محیط زیست", "Environmental Science and Engineering", "AGR-003", "EG-HU"),
    ("منابع طبیعی و جنگل‌داری", "Natural Resources and Forestry", "AGR-004", "EG-HU"),
    ("علوم آبی", "Aquatic Sciences", "AGR-005", "EG-HU"),
    ("نقاشی", "Painting", "ART-001", "EG-HU"),
    ("گرافیک", "Graphic Design", "ART-002", "EG-HU"),
    ("طراحی صنعتی", "Industrial Design", "ART-003", "EG-HU"),
    ("موسیقی", "Music", "ART-004", "EG-HU"),
]


SPECIALIZATIONS = [
    ("مهندسی نرم‌افزار", "Software Engineering", "ENG-002", "مهندسی کامپیوتر"),
    ("هوش مصنوعی", "Artificial Intelligence", "ENG-002", "مهندسی کامپیوتر"),
    ("معماری کامپیوتر", "Computer Architecture", "ENG-002", "مهندسی کامپیوتر"),
    ("شبکه‌های کامپیوتری", "Computer Networks", "ENG-003", "مهندسی فناوری اطلاعات"),
    ("امنیت اطلاعات", "Information Security", "ENG-003", "مهندسی فناوری اطلاعات"),
    ("مخابرات", "Telecommunications", "ENG-004", "مهندسی برق"),
    ("الکترونیک", "Electronics", "ENG-004", "مهندسی برق"),
    ("قدرت", "Power Engineering", "ENG-004", "مهندسی برق"),
    ("سازه", "Structural Engineering", "ENG-006", "مهندسی عمران"),
    ("آب و سازه‌های هیدرولیکی", "Water and Hydraulic Structures", "ENG-006", "مهندسی عمران"),
    ("برنامه‌ریزی شهری", "Urban Planning", "ENG-007", "مهندسی معماری"),
    ("تولید و عملیات", "Production and Operations", "ENG-008", "مهندسی صنایع"),
    ("مدیریت پروژه", "Project Management", "ENG-008", "مهندسی صنایع"),
    ("حقوق خصوصی", "Private Law", "HUM-001", "حقوق"),
    ("حقوق عمومی", "Public Law", "HUM-001", "حقوق"),
    ("مدیریت بازرگانی", "Business Management", "HUM-004", "مدیریت"),
    ("مدیریت دولتی", "Public Management", "HUM-004", "مدیریت"),
    ("روان‌شناسی بالینی", "Clinical Psychology", "HUM-005", "روان‌شناسی"),
    ("روان‌شناسی تربیتی", "Educational Psychology", "HUM-005", "روان‌شناسی"),
]


def seed_catalog(apps, schema_editor):
    Institution = apps.get_model("accounts", "EducationInstitution")
    Field = apps.get_model("accounts", "StudyField")
    Specialization = apps.get_model("accounts", "StudySpecialization")

    for name, name_en, code, kind, province, city in INSTITUTIONS:
        Institution.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "name_en": name_en,
                "institution_type": kind,
                "province": province,
                "city": city,
                "source": "فهرست پایه مراکز آموزش عالی ایران؛ قابل تکمیل از پنل ادمین",
                "source_year": 1404,
                "is_active": True,
            },
        )

    # در این مرحله StudyGroup هنوز ساخته نشده، پس education_group را متن پر کند
    # و گروه‌های فارسی به‌صورت متن ذخیره کند؛ migrate بعدی (0033) این متن‌ها را
    # به ID گروه‌های mớiivaiva تبدیل می‌کند.
    fields = {}
    for name, name_en, code, group in FIELDS:
        field, _ = Field.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "name_en": name_en,
                "education_group": group,
                "source": "گروه‌های رشته‌ای دفترچه‌های سازمان سنجش؛ قابل تکمیل از پنل ادمین",
                "source_year": 1404,
                "is_active": True,
            },
        )
        fields[code] = field

    for name, name_en, code, field_name in SPECIALIZATIONS:
        parent = next((field for field in fields.values() if field.name == field_name), None)
        if parent is None:
            continue
        spec_code = f"{code}-{name_en[:3].upper().replace(' ', '')}"
        Specialization.objects.update_or_create(
            code=spec_code,
            defaults={
                "field": parent,
                "name": name,
                "name_en": name_en,
                "source": "گرایش‌های پایه دفترچه‌های سازمان سنجش؛ قابل تکمیل از پنل ادمین",
                "source_year": 1404,
                "is_active": True,
            },
        )


def unseed_catalog(apps, schema_editor):
    Institution = apps.get_model("accounts", "EducationInstitution")
    Field = apps.get_model("accounts", "StudyField")
    Specialization = apps.get_model("accounts", "StudySpecialization")
    institution_codes = [row[2] for row in INSTITUTIONS]
    field_codes = [row[2] for row in FIELDS]
    Specialization.objects.filter(source__contains="گرایش‌های پایه دفترچه‌های سازمان سنجش").delete()
    Field.objects.filter(code__in=field_codes).delete()
    Institution.objects.filter(code__in=institution_codes).delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0031_educationinstitution_profile_education_institution_and_more")]
    operations = [migrations.RunPython(seed_catalog, unseed_catalog)]
