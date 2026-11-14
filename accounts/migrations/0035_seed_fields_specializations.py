"""
Seed the standard Iranian university study-fields catalog under the four exam groups.

Groups (created in 0033) start mostly empty — notably «زبان‌های خارجی» (EG-FL)
has no fields at all. This migration fills the catalog with the standard fields
of Iranian university entrance exam groups (سازمان سنجش) and their common
specializations, using update_or_create on the unique `code` so admin-created
records and previous seeds (0032) are never overwritten or duplicated.
"""

from django.db import migrations

# (name, name_en, code, group_code)
FIELDS = [
    # --- فنی و مهندسی (EG-TM) ---
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
    ("مهندسی نساجی", "Textile Engineering", "ENG-014", "EG-TM"),
    ("مهندسی معدن", "Mining Engineering", "ENG-015", "EG-TM"),
    ("مهندسی هوافضا", "Aerospace Engineering", "ENG-016", "EG-TM"),
    ("مهندسی پزشکی", "Biomedical Engineering", "ENG-017", "EG-TM"),
    ("مهندسی هسته‌ای", "Nuclear Engineering", "ENG-018", "EG-TM"),
    ("مهندسی راه‌آهن", "Railway Engineering", "ENG-019", "EG-TM"),
    ("مهندسی خودرو", "Automotive Engineering", "ENG-020", "EG-TM"),
    ("مهندسی روباتیک", "Robotics Engineering", "ENG-021", "EG-TM"),
    ("نقشه‌برداری و ژئودزی", "Geodesy and Surveying", "ENG-022", "EG-TM"),
    ("مهندسی نرم‌افزار", "Software Engineering", "ENG-023", "EG-TM"),
    # --- علوم پایه (EG-SC) ---
    ("ریاضی و کاربردها", "Mathematics and Applications", "MATH-001", "EG-SC"),
    ("آمار و کاربردها", "Statistics and Applications", "MATH-002", "EG-SC"),
    ("علوم کامپیوتر", "Computer Science", "MATH-003", "EG-SC"),
    ("فیزیک", "Physics", "SCI-001", "EG-SC"),
    ("شیمی", "Chemistry", "SCI-002", "EG-SC"),
    ("زیست‌شناسی", "Biology", "SCI-003", "EG-SC"),
    ("زمین‌شناسی", "Geology", "SCI-004", "EG-SC"),
    ("زیست‌فناوری (سلولی مولکولی)", "Biotechnology (Cell & Molecular)", "SCI-005", "EG-SC"),
    ("میکروبیولوژی", "Microbiology", "SCI-006", "EG-SC"),
    ("علوم و فناوری‌های شعاعی", "Radiology Sciences", "SCI-007", "EG-SC"),
    # --- علوم انسانی و هنر (EG-HU) ---
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
    ("تاریخ", "History", "HUM-012", "EG-HU"),
    ("فلسفه", "Philosophy", "HUM-013", "EG-HU"),
    ("الهیات و معارف اسلامی", "Islamic Theology", "HUM-014", "EG-HU"),
    ("علوم ارتباطات و خبریات", "Media and Communication Studies", "HUM-015", "EG-HU"),
    ("علوم اطلاعات و کتابداری", "Information and Library Science", "HUM-016", "EG-HU"),
    ("مددکاری اجتماعی", "Social Work", "HUM-017", "EG-HU"),
    ("علوم ورزشی", "Sport Sciences", "HUM-018", "EG-HU"),
    ("پزشکی و بالینی", "Medicine and Clinical", "MED-001", "EG-HU"),
    ("دندان‌پزشکی", "Dentistry", "MED-002", "EG-HU"),
    ("داروسازی", "Pharmacy", "MED-003", "EG-HU"),
    ("پرستاری و مامایی", "Nursing and Midwifery", "MED-004", "EG-HU"),
    ("علوم آزمایشگاهی", "Medical Laboratory Sciences", "MED-005", "EG-HU"),
    ("بهداشت و بهداشت عمومی", "Public Health", "MED-006", "EG-HU"),
    ("فیزیوتراپی و توانبخشی", "Physiotherapy and Rehabilitation", "MED-007", "EG-HU"),
    ("علوم تغذیه", "Nutritional Sciences", "MED-008", "EG-HU"),
    ("دامپزشکی", "Veterinary Medicine", "AGR-001", "EG-HU"),
    ("مهندسی کشاورزی", "Agricultural Engineering", "AGR-002", "EG-HU"),
    ("علوم و مهندسی محیط زیست", "Environmental Science and Engineering", "AGR-003", "EG-HU"),
    ("منابع طبیعی و جنگل‌داری", "Natural Resources and Forestry", "AGR-004", "EG-HU"),
    ("علوم و صنایع غذایی", "Food Science and Industry", "AGR-006", "EG-HU"),
    ("نقاشی", "Painting", "ART-001", "EG-HU"),
    ("گرافیک (ارتباط تصویری)", "Graphic Design (Visual Communication)", "ART-002", "EG-HU"),
    ("طراحی صنعتی", "Industrial Design", "ART-003", "EG-HU"),
    ("موسیقی", "Music", "ART-004", "EG-HU"),
    ("بازی‌های رایانه‌ای", "Game Design", "ART-005", "EG-HU"),
    ("عکاسی", "Photography", "ART-006", "EG-HU"),
    ("فیلم و انیمیشن", "Film and Animation", "ART-007", "EG-HU"),
    ("صحنه‌آرایی و طراحی صحنه", "Stage and Scenography Design", "ART-008", "EG-HU"),
    # --- زبان‌های خارجی (EG-FL) — گروه تا امروز خالی بود ---
    ("زبان و ادبیات انگلیسی", "English Language and Literature", "FL-001", "EG-FL"),
    ("مترجمی زبان انگلیسی", "English Translation", "FL-002", "EG-FL"),
    ("آموزش زبان انگلیسی", "English Language Teaching", "FL-003", "EG-FL"),
    ("زبان و ادبیات فرانسوی", "French Language and Literature", "FL-004", "EG-FL"),
    ("مترجمی زبان فرانسوی", "French Translation", "FL-005", "EG-FL"),
    ("زبان و ادبیات آلمانی", "German Language and Literature", "FL-006", "EG-FL"),
    ("مترجمی زبان آلمانی", "German Translation", "FL-007", "EG-FL"),
    ("زبان و ادبیات اسپانیایی", "Spanish Language and Literature", "FL-008", "EG-FL"),
    ("مترجمی زبان اسپانیایی", "Spanish Translation", "FL-009", "EG-FL"),
    ("زبان و ادبیات عربی", "Arabic Language and Literature", "FL-010", "EG-FL"),
    ("زبان روسی", "Russian Language", "FL-011", "EG-FL"),
    ("زبان ایتالیایی", "Italian Language", "FL-012", "EG-FL"),
    ("زبان چینی", "Chinese Language", "FL-013", "EG-FL"),
    ("زبان ترکی", "Turkish Language", "FL-014", "EG-FL"),
    ("زبان و ادبیات کردی", "Kurdish Language and Literature", "FL-015", "EG-FL"),
]

# (name, name_en, field_code, source_tag)
SPECIALIZATIONS = [
    ("مهندسی نرم‌افزار", "Software Engineering", "ENG-002", "cmp"),
    ("هوش مصنوعی و رباتیک", "Artificial Intelligence and Robotics", "ENG-002", "air"),
    ("معماری کامپیوتر و سیستم‌های دیجیتال", "Computer Architecture", "ENG-002", "cad"),
    ("شبکه‌های کامپیوتری", "Computer Networks", "ENG-003", "net"),
    ("امنیت اطلاعات", "Information Security", "ENG-003", "sec"),
    ("تجارت الکترونیک", "E-Commerce", "ENG-003", "ecm"),
    ("مخابرات سیستم", "Telecommunications (Systems)", "ENG-004", "tls"),
    ("مخابرات میدان و موج", "Telecommunications (Fields & Waves)", "ENG-004", "tlw"),
    ("الکترونیک دیجیتال", "Digital Electronics", "ENG-004", "eld"),
    ("کنترل", "Control Engineering", "ENG-004", "ctl"),
    ("قدرت", "Power Engineering", "ENG-004", "pwr"),
    ("بیوالکتریک", "Bioelectric Engineering", "ENG-004", "bio"),
    ("طراحی کاربردی", "Applied Design", "ENG-005", "adz"),
    ("طراحی سیستم‌های نیرو", "Powertrain Systems Design", "ENG-005", "psd"),
    ("تأسیسات حرارتی و برودتی", "HVAC Systems", "ENG-005", "hvc"),
    ("سازه", "Structural Engineering", "ENG-006", "str"),
    ("آب و سازه‌های هیدرولیکی", "Water and Hydraulic Structures", "ENG-006", "hyd"),
    ("خاک و پی", "Soil Mechanics and Foundation", "ENG-006", "sml"),
    ("راه و ترابری", "Road and Transportation", "ENG-006", "rwt"),
    ("مهندسی محیط زیست (عمران)", "Environmental Engineering (Civil)", "ENG-006", "evc"),
    ("نظارت و اجرا", "Supervision and Construction", "ENG-007", "sca"),
    ("مدیریت ساخت", "Construction Management", "ENG-007", "cmt"),
    ("تولید و عملیات", "Production and Operations", "ENG-008", "pro"),
    ("مدیریت پروژه و ساخت", "Project and Construction Management", "ENG-008", "pcm"),
    ("بهینه‌سازی و تحقیق در عملیات", "Optimization and Operations Research", "ENG-008", "oor"),
    ("مهندسی محیط زیست (شیمی)", "Environmental Engineering (Chemical)", "ENG-009", "evh"),
    ("استخراج فلزات", "Extractive Metallurgy", "ENG-010", "exm"),
    ("ریخته‌گری", "Casting", "ENG-010", "cst"),
    ("جوشکاری", "Welding", "ENG-010", "wld"),
    ("بهره‌برداری از منابع نفت", "Petroleum Exploitation", "ENG-011", "pex"),
    ("حفاری و استخراج", "Drilling and Extraction", "ENG-011", "dre"),
    ("فرآورده‌های نفتی", "Refining", "ENG-011", "ref"),
    ("فرآیند (نفت و گاز)", "Process Engineering (Oil & Gas)", "ENG-011", "prg"),
    ("گاز", "Gas Engineering", "ENG-011", "gas"),
    ("بافندگی", "Weaving", "ENG-014", "wvg"),
    ("الیاف", "Fibers", "ENG-014", "flb"),
    ("شیمی و نساجی", "Textile Chemistry", "ENG-014", "txc"),
    ("استخراج", "Extraction (Mining)", "ENG-015", "mxg"),
    ("فرآوری مواد معدنی", "Mineral Processing", "ENG-015", "mpr"),
    ("استخراج معدن", "Mining Extraction", "ENG-015", "mex"),
    ("اکتشاف", "Exploration (Mining)", "ENG-015", "mxp"),
    ("ایمنی صنعتی و HSE", "Industrial Safety and HSE", "ENG-015", "hse"),
    ("آیرودینامیک و پیشرانش", "Aerodynamics and Propulsion", "ENG-016", "adp"),
    ("سازه‌های هوایی", "Aerospace Structures", "ENG-016", "aer"),
    ("مهندسی پزشکی بالینی", "Clinical Biomedical Engineering", "ENG-017", "bmc"),
    ("بیومواد", "Biomaterials", "ENG-017", "bmt"),
    ("پردازش تصاویر پزشکی", "Medical Image Processing", "ENG-017", "bmi"),
    ("ریاضی محض", "Pure Mathematics", "MATH-001", "mth"),
    ("ریاضی کاربردی", "Applied Mathematics", "MATH-001", "mta"),
    ("آنالیز و کاربردها", "Analysis and Applications", "MATH-001", "mna"),
    ("ریاضی مالی", "Financial Mathematics", "MATH-001", "mfi"),
    ("آمار ریاضی", "Mathematical Statistics", "MATH-002", "stm"),
    ("نظریه علوم کامپیوتر", "Theoretical Computer Science", "MATH-003", "cts"),
    ("سیستم‌های کامپیوتری", "Computer Systems", "MATH-003", "css"),
    ("محاسبات علمی", "Scientific Computing", "MATH-003", "csc"),
    ("فیزیک حالت جامد", "Solid State Physics", "SCI-001", "phs"),
    ("فیزیک اتمی و مولکولی", "Atomic and Molecular Physics", "SCI-001", "pha"),
    ("فیزیک هسته‌ای", "Nuclear Physics", "SCI-001", "phn"),
    ("فیزیک ذرات بنیادی", "Particle Physics", "SCI-001", "php"),
    ("فیزیک نجومی و اخترفیزیک", "Astrophysics", "SCI-001", "aph"),
    ("شیمی آلی", "Organic Chemistry", "SCI-002", "chm"),
    ("شیمی تجزیه", "Analytical Chemistry", "SCI-002", "cha"),
    ("شیمی فیزیک", "Physical Chemistry", "SCI-002", "chp"),
    ("شیمی معدنی", "Inorganic Chemistry", "SCI-002", "chi"),
    ("شیمی کاربردی", "Applied Chemistry", "SCI-002", "chc"),
    ("شیمی محیط زیست", "Environmental Chemistry", "SCI-002", "che"),
    ("علوم جانوری", "Animal Biology", "SCI-003", "bio"),
    ("علوم گیاهی", "Plant Biology", "SCI-003", "bpa"),
    ("علوم دریایی", "Marine Biology", "SCI-003", "bma"),
    ("بیوشیمی", "Biochemistry", "SCI-003", "bch"),
    ("بیوفیزیک", "Biophysics", "SCI-003", "bph"),
    ("زیست‌فناوری میکروبی", "Microbial Biotechnology", "SCI-005", "zbt"),
    ("بیوتکنولوژی گیاهی", "Plant Biotechnology", "SCI-005", "pbt"),
    ("زمین‌شناسی ساختمانی و تکتونیک", "Structural Geology and Tectonics", "SCI-004", "glt"),
    ("رسوب‌شناسی و زمین‌شناسی نفت", "Sedimentology and Petroleum Geology", "SCI-004", "gsp"),
    ("کانی‌شناسی و بلورشناسی", "Mineralogy and Crystallography", "SCI-004", "gmc"),
    ("زمین‌فیزیک", "Geophysics", "SCI-004", "gph"),
    ("حقوق خصوصی", "Private Law", "HUM-001", "pvw"),
    ("حقوق عمومی", "Public Law", "HUM-001", "pbl"),
    ("حقوق بین‌الملل", "International Law", "HUM-001", "itl"),
    ("حقوق جزا و جرم‌شناسی", "Criminal Law and Criminology", "HUM-001", "crw"),
    ("حسابداری مدیریت", "Management Accounting", "HUM-002", "acm"),
    ("حسابداری مالی", "Financial Accounting", "HUM-002", "acf"),
    ("حسابرسی", "Auditing", "HUM-002", "aud"),
    ("اقتصاد نظری", "Theoretical Economics", "HUM-003", "eco"),
    ("علوم اقتصادی", "Economic Sciences", "HUM-003", "ecs"),
    ("اقتصاد کشاورزی", "Agricultural Economics", "HUM-003", "eca"),
    ("مدیریت بازرگانی", "Business Management", "HUM-004", "mbz"),
    ("مدیریت دولتی", "Public Management", "HUM-004", "mdl"),
    ("مدیریت صنعتی", "Industrial Management", "HUM-004", "msn"),
    ("مدیریت مالی", "Financial Management", "HUM-004", "mfi"),
    ("مدیریت فناوری اطلاعات", "IT Management", "HUM-004", "mit"),
    ("کارآفرینی", "Entrepreneurship", "HUM-004", "etr"),
    ("روان‌شناسی بالینی", "Clinical Psychology", "HUM-005", "rpb"),
    ("روان‌شناسی تربیتی", "Educational Psychology", "HUM-005", "rpt"),
    ("روان‌شناسی صنعتی و سازمانی", "Industrial and Organizational Psychology", "HUM-005", "rps"),
    ("عصب‌شناسی شناختی", "Cognitive Neuroscience", "HUM-005", "rpn"),
    ("مدیریت و برنامه‌ریزی آموزشی", "Educational Management and Planning", "HUM-006", "tra"),
    ("آموزش ابتدایی", "Elementary Education", "HUM-006", "tra"),
    ("آموزش ریاضی", "Mathematics Education", "HUM-006", "trm"),
    ("آموزش زبان انگلیسی", "English Language Education", "HUM-006", "tre"),
    ("جامعه‌شناسی فرهنگی", "Cultural Sociology", "HUM-007", "jaf"),
    ("پژوهشگری علوم اجتماعی", "Social Science Research", "HUM-007", "jpa"),
    ("آسیب‌شناسی اجتماعی", "Social Pathology", "HUM-007", "jsb"),
    ("روابط بین‌الملل", "International Relations", "HUM-008", "sia"),
    ("علوم سیاسی", "Political Science", "HUM-008", "sia"),
    ("جغرافیای طبیعی", "Physical Geography", "HUM-009", "gta"),
    ("جغرافیای انسانی", "Human Geography", "HUM-009", "gha"),
    ("جغرافیای سیاسی", "Political Geography", "HUM-009", "gsa"),
    ("سنجش از دور و GIS", "Remote Sensing and GIS", "HUM-009", "grs"),
    ("ادبیات کهن", "Classical Persian Literature", "HUM-010", "adh"),
    ("ادبیات معاصر", "Contemporary Persian Literature", "HUM-010", "adm"),
    ("زبان‌شناسی همگانی", "General Linguistics", "HUM-010", "zsh"),
    ("تاریخ ایران باستان", "Ancient Iranian History", "HUM-012", "tib"),
    ("تاریخ اسلام", "Islamic History", "HUM-012", "tim"),
    ("تاریخ معاصر ایران", "Contemporary Iranian History", "HUM-012", "tmi"),
    ("فلسفه اسلامی", "Islamic Philosophy", "HUM-013", "fli"),
    ("فلسفه غرب", "Western Philosophy", "HUM-013", "flg"),
    ("عرفان و تصوف", "Mysticism and Sufism", "HUM-013", "frt"),
    ("علوم قرآن و حدیث", "Quranic Sciences and Hadith", "HUM-014", "aqh"),
    ("فقه و مبانی حقوق", "Jurisprudence and Law Foundations", "HUM-014", "fqh"),
    ("ادیان و عرفان", "Religions and Mysticism", "HUM-014", "dio"),
    ("روزنامه‌نگاری", "Journalism", "HUM-015", "khr"),
    ("روابط عمومی", "Public Relations", "HUM-015", "rom"),
    ("رسانه‌های جدید", "New Media", "HUM-015", "rjd"),
    ("مدیریت اطلاعات", "Information Management", "HUM-016", "eti"),
    ("بازی‌سازی و فناوری‌های نوین", "Game Design and Emerging Technologies", "HUM-016", "bft"),
    ("مددکاری اجتماعی", "Social Work", "HUM-017", "mdk"),
    ("بیومکانیک ورزشی", "Sports Biomechanics", "HUM-018", "vbm"),
    ("فیزیولوژی ورزشی", "Exercise Physiology", "HUM-018", "vph"),
    ("آمادگی جسمانی", "Physical Fitness", "HUM-018", "vft"),
    ("فیزیولوژی پزشکی", "Medical Physiology", "MED-001", "phz"),
    ("انگل‌شناسی", "Parasitology", "MED-001", "ang"),
    ("ویروس‌شناسی", "Virology", "MED-001", "vrs"),
    ("پرستاری داخلی-جراحی", "Internal-Surgical Nursing", "MED-004", "prn"),
    ("پرستاری کودکان", "Pediatric Nursing", "MED-004", "prc"),
    ("مامایی سلامت جامعه", "Community Health Midwifery", "MED-004", "mam"),
    ("بهداشت عمومی", "Public Health", "MED-006", "bhm"),
    ("آمار زیستی و اپیدمیولوژی", "Biostatistics and Epidemiology", "MED-006", "bse"),
    ("آمادگی جسمانی و حرکات ورزشی", "Physical Fitness and Exercise", "MED-006", "phy"),
    ("فیزیوتراپی داخلی و جراحی", "Internal and Surgical Physiotherapy", "MED-007", "ftr"),
    ("علوم غذایی", "Food Sciences", "AGR-006", "agh"),
    ("صنایع غذایی", "Food Industries", "AGR-006", "ags"),
    ("میگوی آب‌های داخلی", "Inland Shrimp Aquaculture", "AGR-005", "ags"),
    ("شیلات", "Fisheries", "AGR-005", "shl"),
    ("فرآوری محصولات شیلاتی", "Fisheries Products Processing", "AGR-005", "shp"),
    ("امور زراعی", "Agronomy", "AGR-002", "agr"),
    ("باغبانی", "Horticulture", "AGR-002", "agb"),
    ("اصلاح نباتات", "Plant Breeding", "AGR-002", "agp"),
    ("سنجش از دور و GIS (محیط زیست)", "Remote Sensing and GIS (Environment)", "AGR-003", "mrs"),
    ("آلودگی محیط زیست", "Environmental Pollution", "AGR-003", "mpl"),
    ("مدیریت جنگل", "Forest Management", "AGR-004", "mja"),
    ("مدیریت مراتع", "Rangeland Management", "AGR-004", "mra"),
    ("نقاشی", "Painting", "ART-001", "nqs"),
    ("تصویرسازی", "Illustration", "ART-001", "tsv"),
    ("گرافیک", "Graphic Design", "ART-002", "grf"),
    ("انیمیشن", "Animation", "ART-002", "ani"),
    ("موسیقی ایرانی", "Persian Music", "ART-004", "msi"),
    ("موسیقی جهانی", "World Music", "ART-004", "msj"),
    ("طراحی بازی", "Game Design", "ART-005", "bzi"),
    ("عکاسی دیجیتال", "Digital Photography", "ART-006", "akd"),
    ("فیلم‌سازی", "Filmmaking", "ART-007", "flm"),
    ("ادبیات نمایشی", "Dramatic Literature", "ART-008", "adn"),
    # --- گرایش‌های زبان‌های خارجی ---
    ("ادبیات انگلیسی", "English Literature", "FL-001", "ela"),
    ("زبان‌شناسی انگلیسی", "English Linguistics", "FL-001", "eli"),
    ("مترجمی ادبی", "Literary Translation", "FL-002", "mtr"),
    ("مترجمی رسانه", "Media Translation", "FL-002", "mtm"),
    ("آموزش زبان به کودکان", "Teaching English to Children", "FL-003", "ate"),
    ("آموزش زبان به بزرگسالان", "Teaching English to Adults", "FL-003", "atb"),
    ("ادبیات فرانسه", "French Literature", "FL-004", "frl"),
    ("ترجمه فرانسه", "French Translation", "FL-005", "frt"),
    ("ادبیات آلمان", "German Literature", "FL-006", "gll"),
    ("ترجمه آلمانی", "German Translation", "FL-007", "glt"),
    ("ادبیات اسپانیا", "Spanish Literature", "FL-008", "spl"),
    ("ترجمه اسپانیایی", "Spanish Translation", "FL-009", "spt"),
    ("ادبیات عرب", "Arabic Literature", "FL-010", "arl"),
    ("ترجمه عربی", "Arabic Translation", "FL-010", "art"),
    ("روسی-ترجمه", "Russian Translation", "FL-011", "rut"),
    ("ایتالیایی-ترجمه", "Italian Translation", "FL-012", "itt"),
    ("چینی-ترجمه", "Chinese Translation", "FL-013", "cht"),
    ("ترکی-ترجمه", "Turkish Translation", "FL-014", "trt"),
    ("کردی-ادبیات", "Kurdish Literature", "FL-015", "krd"),
]


def seed_fields_and_specs(apps, schema_editor):
    StudyGroup = apps.get_model("accounts", "StudyGroup")
    StudyField = apps.get_model("accounts", "StudyField")
    StudySpecialization = apps.get_model("accounts", "StudySpecialization")

    groups_by_code = {g.code: g for g in StudyGroup.objects.all()}

    fields_by_code = {}
    created_fields = 0
    for name, name_en, code, group_code in FIELDS:
        group = groups_by_code.get(group_code)
        if group is None:
            continue
        field, created = StudyField.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "name_en": name_en,
                "study_group": group,
                "source": "فهرست رشته‌های سازمان سنجش (گروه‌های امتحانی)؛ قابل تکمیل از پنل ادمین",
                "source_year": 1404,
                "is_active": True,
            },
        )
        fields_by_code[code] = field
        if created:
            created_fields += 1

    created_specs = 0
    for name, name_en, field_code, tag in SPECIALIZATIONS:
        field = fields_by_code.get(field_code)
        if field is None:
            continue
        spec_code = f"{field_code}-{tag.upper()}"
        _, created = StudySpecialization.objects.update_or_create(
            code=spec_code,
            defaults={
                "field": field,
                "name": name,
                "name_en": name_en,
                "source": "گرایش‌های رشته‌های سازمان سنجش؛ قابل تکمیل از پنل ادمین",
                "source_year": 1404,
                "is_active": True,
            },
        )
        if created:
            created_specs += 1


def unseed_fields_and_specs(apps, schema_editor):
    StudyField = apps.get_model("accounts", "StudyField")
    StudySpecialization = apps.get_model("accounts", "StudySpecialization")
    field_codes = [row[2] for row in FIELDS]
    StudySpecialization.objects.filter(
        source__contains="گرایش‌های رشته‌های سازمان سنجش"
    ).delete()
    StudyField.objects.filter(code__in=field_codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0034_alter_studyfield_options_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_fields_and_specs, unseed_fields_and_specs),
    ]
