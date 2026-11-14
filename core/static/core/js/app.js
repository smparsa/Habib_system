/* ============================================   HABIBHUB - Application JavaScript   Multi-Language | RTL/LTR | SPA Routing   ============================================ */// ---------- Language Dictionary ----------
const translations = {  en: {    // General    
app_name: 'HabibHub',    tagline: 'All Tools · One Hub',    welcome: 'Welcome',    dashboard: 'Dashboard',    profile: 'My Profile',    profile_resume: 'My Profile - Resume',    settings: 'Settings',    logout: 'Logout',    save: 'Save',    cancel: 'Cancel',    edit: 'Edit',    delete: 'Delete',    add: 'Add',    search: 'Search...',    notifications: 'Notifications',    language: 'Language',    theme: 'Theme',    dark_mode: 'Dark Mode',    light_mode: 'Light Mode',    // Login    
login_title: 'Welcome to HabibHub',    login_subtitle: 'Sign in to access your business tools',    mobile_number: 'Mobile Number',    verify_code: 'Verification Code',    send_code: 'Send Code',    verify: 'Verify',    resend_code: 'Resend Code',    referrer: 'Referrer National ID',    continue_with: 'Or continue with',    google: 'Google',    no_account: 'Don’t have an account?',    sign_up: 'Sign Up',    have_account: 'Already have an account?',    sign_in: 'Sign In',    // Dashboard    
stats_overview: 'Overview',    total_users: 'اسلایدشو D',    active_projects: 'اسلایدشو C',    monthly_revenue: 'اسلایدشو B',    pending_tasks: 'اسلایدشو A',    modules: 'Business Modules',    recent_activity: 'Recent Activity',    view_all: 'View All',    // Modules    
accounting: 'Accounting',    hr: 'HR',    crm: 'CRM',    projects: 'Projects',    ads: 'Ads',    office: 'Office',    inventory: 'Inventory',    sales: 'Sales',    finance: 'Finance',    support: 'Support',    documents: 'Documents',    calendar: 'Calendar',    ai_assistant: 'AI Assistant',    // Profile sections    
personal_info: 'Personal Information',    job_info: 'Job Information',    education: 'Education',    organization: 'Organization',    financial: 'Financial Information',    system_access: 'System Access',    security: 'Security',    skills: 'Skills',    projects_info: 'Projects',    health: 'Health Information',    family: 'Family Information',    location: 'Location',    system_settings: 'System Settings',    communication: 'Communication',    training: 'Training History',    work_history: 'Work History',    interests: 'Interests & Preferences',    vehicle: 'Vehicle Information',    equipment: 'Equipment',    documents_files: 'Documents & Files',    scoring: 'Scoring & Performance',    workflow: 'Workflow',    ai_info: 'AI Information',    activity_history: 'Activity History',    custom_fields: 'Custom Fields',    // Fields    
first_name: 'First Name',    last_name: 'Last Name',    family_suffix: 'Family Suffix',    fame_name: 'Fame Name',    father_name: 'Father Name',    mother_name: 'Mother Name',    date_of_birth: 'Date of Birth',    national_id: 'National ID',    gender: 'Gender',    male: 'Male',    female: 'Female',    marital_status: 'Marital Status',    single: 'Single',    married: 'Married',    separated: 'Separated',    religion: 'Religion',    sect: 'Sect',    citizenship: 'Citizenship',    nationality: 'Nationality',    permanent_residence: 'Permanent Residence',    job_title: 'Job Title',    department: 'Department',    employment_type: 'Employment Type',    hire_date: 'Hire Date',    degree: 'Degree',    field_of_study: 'Field of Study',    university: 'University',    graduation_year: 'Graduation Year',    gpa: 'GPA',    personnel_id: 'Personnel ID',    org_code: 'Org Code',    manager: 'Direct Manager',    branch: 'Branch',    work_group: 'Work Group',    status: 'Status',    active: 'Active',    inactive: 'Inactive',    account_number: 'Account Number',    iban: 'IBAN',    bank_name: 'Bank Name',    salary: 'Base Salary',    username: 'Username',    role: 'Role',    last_login: 'Last Login',    two_factor: 'Two-Factor Auth',    enabled: 'Enabled',    disabled: 'Disabled',    address: 'Address',    city: 'City',    province: 'Province',    country: 'Country',    postal_code: 'Postal Code',    email: 'Email',    phone: 'Phone',    emergency_contact: 'Emergency Contact',    bio: 'Bio',    profile_picture: 'Profile Picture',    drag_drop: 'Drag & drop files here or click to browse',    // Messages    
saved_success: 'Profile saved successfully!',    code_sent: 'Verification code sent!',    invalid_code: 'Invalid verification code',    welcome_back: 'Welcome back, ',    coming_soon: 'Coming Soon',    feature_coming_soon: 'This feature will be available soon.',  },  fa: {    // General    
app_name: 'حبیب‌هاب',    tagline: 'همه ابزارها · یک هاب',    welcome: 'خوش آمدید',    dashboard: 'داشبورد',    profile: 'پروفایل من',    profile_resume: 'پروفایل من-رزومه',    settings: 'تنظیمات',    logout: 'خروج',    save: 'ذخیره',    cancel: 'انصراف',    edit: 'ویرایش',    delete: 'حذف',    add: 'افزودن',    search: 'جستجو...',    notifications: 'اعلان‌ها',    language: 'زبان',    theme: 'تم',    dark_mode: 'حالت تاریک',    light_mode: 'حالت روشن',    // Login    
login_title: 'به حبیب‌هاب خوش آمدید',    login_subtitle: 'برای دسترسی به ابزارهای کسب‌وکار خود وارد شوید',    mobile_number: 'شماره موبایل',    verify_code: 'کد تأیید',    send_code: 'ارسال کد',    verify: 'تأیید',    resend_code: 'ارسال مجدد',    referrer: 'کد ملی معرف',    continue_with: 'یا ادامه با',    google: 'گوگل',    no_account: 'حساب کاربری ندارید؟',    sign_up: 'ثبت‌نام',    have_account: 'حساب کاربری دارید؟',    sign_in: 'ورود',    // Dashboard    
stats_overview: 'نمای کلی',    total_users: 'اسلایدشو D',    active_projects: 'اسلایدشو C',    monthly_revenue: 'اسلایدشو B',    pending_tasks: 'اسلایدشو A',    modules: 'ماژول‌های کسب‌وکار',    recent_activity: 'فعالیت‌های اخیر',    view_all: 'مشاهده همه',    // Modules    
accounting: 'حسابداری',    hr: 'منابع انسانی',    crm: 'مدیریت ارتباط با مشتری',    projects: 'پروژه‌ها',    ads: 'تبلیغات',    office: 'دفتر',    inventory: 'انبار',    sales: 'فروش',    finance: 'مالی',    support: 'پشتیبانی',    documents: 'اسناد',    calendar: 'تقویم',    ai_assistant: 'دستیار هوشمند',    // Profile sections    
personal_info: 'اطلاعات شخصی',    job_info: 'اطلاعات شغلی',    education: 'اطلاعات تحصیلی',    organization: 'اطلاعات سازمانی',    financial: 'اطلاعات مالی',    system_access: 'اطلاعات دسترسی سیستم',    security: 'اطلاعات امنیتی',    skills: 'مهارت‌ها',    projects_info: 'پروژه‌ها',    health: 'اطلاعات سلامت',    family: 'اطلاعات خانواده',    location: 'اطلاعات مکانی',    system_settings: 'تنظیمات شخصی سیستم',    communication: 'اطلاعات ارتباطی',    training: 'سوابق آموزشی',    work_history: 'سوابق کاری',    interests: 'علایق و ترجیحات',    vehicle: 'اطلاعات خودرو',    equipment: 'اطلاعات تجهیزات',    documents_files: 'مدارک و فایل‌ها',    scoring: 'امتیازدهی و عملکرد',    workflow: 'گردش کار',    ai_info: 'اطلاعات هوش مصنوعی',    activity_history: 'تاریخچه فعالیت',    custom_fields: 'اطلاعات سفارشی',    // Fields    
first_name: 'نام',    last_name: 'نام خانوادگی',    family_suffix: 'پسوند فامیل',    fame_name: 'شهرت',    father_name: 'نام پدر',    mother_name: 'نام مادر',    date_of_birth: 'تاریخ تولد',    national_id: 'کد ملی',    gender: 'جنسیت',    male: 'مرد',    female: 'زن',    marital_status: 'وضعیت تأهل',    single: 'مجرد',    married: 'متأهل',    separated: 'جداشده',    religion: 'دین',    sect: 'مذهب',    citizenship: 'تابعیت',    nationality: 'ملیت',    permanent_residence: 'اقامت دائم',    job_title: 'عنوان شغلی',    department: 'واحد سازمانی',    employment_type: 'نوع استخدام',    hire_date: 'تاریخ استخدام',    degree: 'آخرین مدرک',    field_of_study: 'رشته تحصیلی',    university: 'دانشگاه',    graduation_year: 'سال فارغ‌التحصیلی',    gpa: 'معدل',    personnel_id: 'شماره پرسنلی',    org_code: 'کد سازمانی',    manager: 'مدیر مستقیم',    branch: 'شعبه',    work_group: 'گروه کاری',    status: 'وضعیت',    active: 'فعال',    inactive: 'غیرفعال',    account_number: 'شماره حساب',    iban: 'شماره شبا',    bank_name: 'نام بانک',    salary: 'حقوق پایه',    username: 'نام کاربری',    role: 'نقش کاربری',    last_login: 'آخرین ورود',    two_factor: 'احراز هویت دومرحله‌ای',    enabled: 'فعال',    disabled: 'غیرفعال',    address: 'آدرس',    city: 'شهر',    province: 'استان',    country: 'کشور',    postal_code: 'کد پستی',    email: 'ایمیل',    phone: 'تلفن',    emergency_contact: 'تماس اضطراری',    bio: 'بیوگرافی',    profile_picture: 'تصویر پروفایل',    drag_drop: 'فایل‌ها را اینجا بکشید یا برای انتخاب کلیک کنید',    // Messages    
saved_success: 'پروفایل با موفقیت ذخیره شد!',    code_sent: 'کد تأیید ارسال شد!',    invalid_code: 'کد تأیید نامعتبر است',    welcome_back: 'خوش آمدید، ',    coming_soon: 'به زودی',    feature_coming_soon: 'این قابلیت به زودی در دسترس خواهد بود.',  },  zh: {    // General    
app_name: 'HabibHub',    tagline: '所有工具 · 一个中心',    welcome: '欢迎',    dashboard: '仪表板',    profile: '我的资料',    profile_resume: '我的资料-简历',    settings: '设置',    logout: '退出',    save: '保存',    cancel: '取消',    edit: '编辑',    delete: '删除',    add: '添加',    search: '搜索...',    notifications: '通知',    language: '语言',    theme: '主题',    dark_mode: '深色模式',    light_mode: '浅色模式',    // Login    
login_title: '欢迎使用 HabibHub',    login_subtitle: '登录以访问您的业务工具',    mobile_number: '手机号码',    verify_code: '验证码',    send_code: '发送验证码',    verify: '验证',    resend_code: '重新发送',    referrer: '推荐人身份证号',    continue_with: '或使用以下方式继续',    google: '谷歌',    no_account: '没有账户？',    sign_up: '注册',    have_account: '已有账户？',    sign_in: '登录',    // Dashboard    
stats_overview: '概览',    total_users: 'اسلایدشو D',    active_projects: 'اسلایدشو C',    monthly_revenue: 'اسلایدشو B',    pending_tasks: 'اسلایدشو A',    modules: '业务模块',    recent_activity: '最近活动',    view_all: '查看全部',    // Modules    
accounting: '会计',    hr: '人力资源',    crm: '客户关系管理',    projects: '项目',    ads: '广告',    office: '办公',    inventory: '库存',    sales: '销售',    finance: '财务',    support: '支持',    documents: '文档',    calendar: '日历',    ai_assistant: 'AI助手',    // Profile sections    
personal_info: '个人信息',    job_info: '工作信息',    education: '教育背景',    organization: '组织信息',    financial: '财务信息',    system_access: '系统访问',    security: '安全信息',    skills: '技能',    projects_info: '项目',    health: '健康信息',    family: '家庭信息',    location: '位置信息',    system_settings: '系统设置',    communication: '通讯信息',    training: '培训记录',    work_history: '工作经历',    interests: '兴趣与偏好',    vehicle: '车辆信息',    equipment: '设备信息',    documents_files: '文件与文档',    scoring: '评分与绩效',    workflow: '工作流程',    ai_info: 'AI信息',    activity_history: '活动历史',    custom_fields: '自定义字段',    // Fields    
first_name: '名',    last_name: '姓',    family_suffix: 'نام خانوادگی افزوده',    fame_name: '名称',    father_name: '父亲姓名',    mother_name: '母亲姓名',    date_of_birth: '出生日期',    national_id: '身份证号',    gender: '性别',    male: '男',    female: '女',    marital_status: '婚姻状况',    single: '单身',    married: '已婚',    separated: '分居',    religion: '宗教',    sect: '教派',    citizenship: '国籍',    nationality: '民族',    permanent_residence: '永久居留',    job_title: '职位',    department: '部门',    employment_type: '雇佣类型',    hire_date: '入职日期',    degree: '最高学历',    field_of_study: '专业',    university: '大学',    graduation_year: '毕业年份',    gpa: '平均绩点',    personnel_id: '员工编号',    org_code: '组织代码',    manager: '直属经理',    branch: '分支',    work_group: '工作组',    status: '状态',    active: '活跃',    inactive: '非活跃',    account_number: '银行账号',    iban: 'IBAN',    bank_name: '银行名称',    salary: '基本工资',    username: '用户名',    role: '角色',    last_login: '最后登录',    two_factor: '双重认证',    enabled: '已启用',    disabled: '已禁用',    address: '地址',    city: '城市',    province: '省份',    country: '国家',    postal_code: '邮政编码',    email: '电子邮件',    phone: '电话',    emergency_contact: '紧急联系人',    bio: '个人简介',    profile_picture: '头像',    drag_drop: '拖放文件到此处或点击浏览',    // Messages    
saved_success: '资料保存成功！',    code_sent: '验证码已发送！',    invalid_code: '验证码无效',    welcome_back: '欢迎回来，',    coming_soon: '即将推出',    feature_coming_soon: '此功能即将上线。',  },  ar: {    // General    
app_name: 'حبيب هاب',    tagline: 'جميع الأدوات · مركز واحد',    welcome: 'أهلاً بك',    dashboard: 'لوحة التحكم',    profile: 'ملفي الشخصي',    profile_resume: 'ملفي الشخصي - السيرة الذاتية',    settings: 'الإعدادات',    logout: 'تسجيل الخروج',    save: 'حفظ',    cancel: 'إلغاء',    edit: 'تعديل',    delete: 'حذف',    add: 'إضافة',    search: 'بحث...',    notifications: 'الإشعارات',    language: 'اللغة',    theme: 'المظهر',    dark_mode: 'الوضع الداكن',    light_mode: 'الوضع الفاتح',    // Login    
login_title: 'أهلاً بك في حبيب هاب',    login_subtitle: 'سجل الدخول للوصول إلى أدوات عملك',    mobile_number: 'رقم الجوال',    verify_code: 'رمز التحقق',    send_code: 'إرسال الرمز',    verify: 'تحقق',    resend_code: 'إعادة الإرسال',    referrer: 'الرقم الوطني للمحيل',    continue_with: 'أو تابع باستخدام',    google: 'جوجل',    no_account: 'ليس لديك حساب؟',    sign_up: 'إنشاء حساب',    have_account: 'لديك حساب بالفعل؟',    sign_in: 'تسجيل الدخول',    // Dashboard    
stats_overview: 'نظرة عامة',    total_users: 'اسلایدشو D',    active_projects: 'اسلایدشو C',    monthly_revenue: 'اسلایدشو B',    pending_tasks: 'اسلایدشو A',    modules: 'وحدات الأعمال',    recent_activity: 'النشاطات الأخيرة',    view_all: 'عرض الكل',    // Modules    
accounting: 'المحاسبة',    hr: 'الموارد البشرية',    crm: 'إدارة العملاء',    projects: 'المشاريع',    ads: 'الإعلانات',    office: 'المكتب',    inventory: 'المخزون',    sales: 'المبيعات',    finance: 'المالية',    support: 'الدعم',    documents: 'المستندات',    calendar: 'التقويم',    ai_assistant: 'المساعد الذكي',    // Profile sections    
personal_info: 'المعلومات الشخصية',    job_info: 'المعلومات الوظيفية',    education: 'التعليم',    organization: 'المعلومات التنظيمية',    financial: 'المعلومات المالية',    system_access: 'وصول النظام',    security: 'الأمان',    skills: 'المهارات',    projects_info: 'المشاريع',    health: 'المعلومات الصحية',    family: 'معلومات العائلة',    location: 'الموقع',    system_settings: 'إعدادات النظام',    communication: 'الاتصالات',    training: 'سجل التدريب',    work_history: 'سجل العمل',    interests: 'الاهتمامات والتفضيلات',    vehicle: 'معلومات المركبة',    equipment: 'المعدات',    documents_files: 'المستندات والملفات',    scoring: 'التقييم والأداء',    workflow: 'سير العمل',    ai_info: 'معلومات الذكاء الاصطناعي',    activity_history: 'سجل النشاط',    custom_fields: 'حقول مخصصة',    // Fields    
first_name: 'الاسم الأول',    last_name: 'اسم العائلة',    family_suffix: 'لاحقة العائلة',    fame_name: 'الشهرة',    father_name: 'اسم الأب',    mother_name: 'اسم الأم',    date_of_birth: 'تاريخ الميلاد',    national_id: 'الرقم الوطني',    gender: 'الجنس',    male: 'ذكر',    female: 'أنثى',    marital_status: 'الحالة الاجتماعية',    single: 'أعزب',    married: 'متزوج',    separated: 'منفصل',    religion: 'الديانة',    sect: 'المذهب',    citizenship: 'الجنسية',    nationality: 'القومية',    permanent_residence: 'الإقامة الدائمة',    job_title: 'المسمى الوظيفي',    department: 'القسم',    employment_type: 'نوع التوظيف',    hire_date: 'تاريخ التعيين',    degree: 'آخر شهادة',    field_of_study: 'مجال الدراسة',    university: 'الجامعة',    graduation_year: 'سنة التخرج',    gpa: 'المعدل',    personnel_id: 'الرقم الوظيفي',    org_code: 'الرمز التنظيمي',    manager: 'المدير المباشر',    branch: 'الفرع',    work_group: 'مجموعة العمل',    status: 'الحالة',    active: 'نشط',    inactive: 'غير نشط',    account_number: 'رقم الحساب',    iban: 'رقم الآيبان',    bank_name: 'اسم البنك',    salary: 'الراتب الأساسي',    username: 'اسم المستخدم',    role: 'الدور',    last_login: 'آخر دخول',    two_factor: 'المصادقة الثنائية',    enabled: 'مفعل',    disabled: 'معطل',    address: 'العنوان',    city: 'المدينة',    province: 'المحافظة',    country: 'الدولة',    postal_code: 'الرمز البريدي',    email: 'البريد الإلكتروني',    phone: 'الهاتف',    emergency_contact: 'جهة الاتصال الطارئة',    bio: 'نبذة',    profile_picture: 'الصورة الشخصية',    drag_drop: 'اسحب الملفات هنا أو انقر للتصفح',    // Messages    
saved_success: 'تم حفظ الملف الشخصي بنجاح!',    code_sent: 'تم إرسال رمز التحقق!',    invalid_code: 'رمز التحقق غير صالح',    welcome_back: 'أهلاً بعودتك، ',    coming_soon: 'قريباً',    feature_coming_soon: 'ستتوفر هذه الميزة قريباً.',  }};// RTL languages
const rtlLangs = ['fa', 'ar'];// ---------- State ----------
let currentLang = localStorage.getItem('hb-lang') || 'fa';let sidebarCollapsed = localStorage.getItem('hb-sidebar') === 'true';let currentUser = JSON.parse(localStorage.getItem('hb-user') || 'null');// ---------- Appearance (تم و رنگ رابط) ----------
// تم و رنگ تأکیدی از تنظیمات سمت سرور (meta data-hb-theme / data-hb-accent)
// می‌آیند؛ کاربر فقط از بخش «تنظیمات شخصی سیستم» آن‌ها را تغییر می‌دهد.
function hbHexToRgb(hex) {  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex || '').trim());  if (!m) return null;  const n = parseInt(m[1], 16);  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };}
function hbMix(hex, base, ratio) {  const c = hbHexToRgb(hex);  const b = hbHexToRgb(base);  if (!c || !b) return base;  const mix = (x, y) => Math.round(x * ratio + y * (1 - ratio));  return '#' + [mix(c.r, b.r), mix(c.g, b.g), mix(c.b, b.b)].map(v => v.toString(16).padStart(2, '0')).join('');}
function applyUiAccent(accent) {  const rgb = hbHexToRgb(accent);  if (!rgb) return;  const dark = document.body.dataset.hbTheme !== 'light';  const root = document.documentElement.style;  root.setProperty('--hb-gold-500', hbMix(accent, '#b8860b', 0.55));  root.setProperty('--hb-gold-400', accent);  root.setProperty('--hb-gold-300', hbMix(accent, '#d4af37', 0.6));  root.setProperty('--hb-gold-200', hbMix(accent, '#e8c84a', 0.6));  root.setProperty('--hb-gold-100', hbMix(accent, '#f0d878', 0.6));  const a = accent.replace('#', '');  const rgba = (alpha) => `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha})`;  const alphas = ['01', '03', '05', '06', '08', '10', '12', '14', '15', '16', '18', '20', '22', '25', '28', '30', '35', '40', '45', '50', '55', '60', '90'];  alphas.forEach(alpha => {    root.setProperty('--hb-accent-' + alpha, rgba(parseInt(alpha, 10) / 100));  });  root.setProperty('--hb-accent-solid', accent);  // سلکت‌های فرم آیکون chevron رنگی دارند (پیش‌فرض طلاییِ ثابت)
  root.setProperty('--hb-accent-url', `url("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%23${a}' viewBox='0 0 16 16'><path d='M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708.708l-6 6a.5.5 0 0 1-.708 0l-6-6a.5.5 0 0 1 0-.708z'/></svg>")`);}
function applyUiTheme() {
  const theme = document.body.dataset.hbTheme === 'light' ? 'light' : 'dark';
  document.body.classList.toggle('hb-theme-light', theme === 'light');
  document.documentElement.setAttribute('data-hb-theme', theme);
  if (theme === 'dark') {
    // پیش‌فرض: حذف overrideها (سبز/آبی دست‌نخورده)
    document.documentElement.style.removeProperty('--hb-text-primary');
    document.documentElement.style.removeProperty('--hb-text-secondary');
    document.documentElement.style.removeProperty('--hb-text-muted');
  } else {
    document.documentElement.style.setProperty('--hb-text-primary', '#111827');
    document.documentElement.style.setProperty('--hb-text-secondary', '#374151');
    document.documentElement.style.setProperty('--hb-text-muted', '#6b7280');
  }
  applyUiAccent(document.body.dataset.hbAccent || '#c9a227');
}
function initUiAppearance() { applyUiTheme(); }
document.addEventListener('DOMContentLoaded', () => {  initLanguage();  initUiAppearance();  initSidebar();  initNavigation();  initForms();  initModules();  initToasts();  initMobileMenu();  initSectionToggles();  initSolarDatepicker();  initJobCascade();  initLocation();  initLocationLookup();  initLocationMap();  initLocationAddressSearch();  initRegisterLocation();  initNameAutocomplete();  initFamilySection();  initLocationAutocomplete();  initJobLocation();  initJobUnemployedToggle();  initEducationCascade();  initCountrySelect();  initJobGps();  initJobPhotoPreview();  initJobFormValidation();  initNewsTicker();
  initJobStatusCountdowns();
  initWalletPage();
  initPleaseWait();  if (document.querySelector('.hb-login-page')) {    initLogin();  }});// ---------- Language ----------
function initLanguage() {  applyLanguage(currentLang);  document.querySelectorAll('.hb-lang-item').forEach(item => {    item.addEventListener('click', () => {      const lang = item.dataset.lang;      applyLanguage(lang);      document.querySelector('.hb-lang-dropdown').classList.remove('open');    });  });  document.querySelectorAll('.hb-lang-toggle').forEach(btn => {    btn.addEventListener('click', (e) => {      e.stopPropagation();      const dropdown = btn.closest('.hb-lang-dropdown');      dropdown.classList.toggle('open');    });  });  document.addEventListener('click', () => {    document.querySelectorAll('.hb-lang-dropdown').forEach(d => d.classList.remove('open'));  });}function applyLanguage(lang) {  currentLang = lang;  localStorage.setItem('hb-lang', lang);  document.documentElement.lang = lang;  const isRTL = rtlLangs.includes(lang);  document.body.dir = isRTL ? 'rtl' : 'ltr';  // Update all translatable elements  
document.querySelectorAll('[data-i18n]').forEach(el => {    const key = el.dataset.i18n;    if (translations[lang] && translations[lang][key]) {      if (el.tagName === 'INPUT' && el.placeholder) {        el.placeholder = translations[lang][key];      } else {        el.textContent = translations[lang][key];      }    }  });  // Update active state in dropdown  
document.querySelectorAll('.hb-lang-item').forEach(item => {    item.classList.toggle('active', item.dataset.lang === lang);  });  // Update document title  
const pageTitle = document.querySelector('[data-page-title]');  if (pageTitle) {    const key = pageTitle.dataset.pageTitle;    const t = translations[lang][key] || key;    document.title = `${t} - HabibHub`;  }  applyCountryLabels(lang);  applyLocationValues(lang);  applyBilingualSelects(lang);  applyUiTheme();}function t(key) {  return translations[currentLang]?.[key] || key;}// ---------- Theme & Accent ----------// ---------- Sidebar ----------
function initSidebar() {  const sidebar = document.querySelector('.hb-sidebar');  const toggle = document.querySelector('.hb-sidebar-toggle');  if (!sidebar || !toggle) return;  if (sidebarCollapsed) {    sidebar.classList.add('hb-sidebar-collapsed');  }  toggle.addEventListener('click', () => {    sidebarCollapsed = !sidebarCollapsed;    sidebar.classList.toggle('hb-sidebar-collapsed');    localStorage.setItem('hb-sidebar', sidebarCollapsed);  });}// ---------- Navigation ----------
function initNavigation() {  const currentPath = window.location.pathname.split('/').pop() || 'index.html';  document.querySelectorAll('.hb-sidebar-link').forEach(link => {    const href = link.getAttribute('href');    if (href && href.includes(currentPath)) {      link.classList.add('active');    }  });}// ---------- Mobile Menu ----------
function initMobileMenu() {  const toggle = document.querySelector('.hb-mobile-toggle');  const sidebar = document.querySelector('.hb-sidebar');  const overlay = document.querySelector('.hb-overlay');  if (!toggle || !sidebar) return;  toggle.addEventListener('click', () => {    sidebar.classList.toggle('mobile-open');    if (overlay) overlay.classList.toggle('active');  });  if (overlay) {    overlay.addEventListener('click', () => {      sidebar.classList.remove('mobile-open');      overlay.classList.remove('active');    });  }}// ---------- Login ----------
function initLogin() {  const step1 = document.getElementById('login-step-1');  const step2 = document.getElementById('login-step-2');  const step3 = document.getElementById('login-step-3');  const dots = document.querySelectorAll('.hb-step-dot');  const sendCodeBtn = document.getElementById('btn-send-code');  const verifyBtn = document.getElementById('btn-verify');  const resendBtn = document.getElementById('btn-resend');  const switchSignup = document.getElementById('switch-signup');  const switchSignin = document.getElementById('switch-signin');  const formTitle = document.getElementById('form-title');  const formSubtitle = document.getElementById('form-subtitle');  let isSignup = false;  function setStep(step) {    [step1, step2, step3].forEach((s, i) => {      if (s) s.style.display = i + 1 === step ? 'block' : 'none';    });    dots.forEach((d, i) => d.classList.toggle('active', i + 1 === step));  }  if (sendCodeBtn) {    sendCodeBtn.addEventListener('click', (e) => {      const mobile = document.getElementById('mobile-number')?.value;      if (!mobile || !/^09\d{9}$/.test(mobile)) {        e.preventDefault();        showToast(t('invalid_code'), 'error');        return;      }      // فرم مستقیماً به سرور جنگو ارسال می‌شود (بدون کد تایید)    
});  }  if (verifyBtn) {    verifyBtn.addEventListener('click', () => {      const code = Array.from(document.querySelectorAll('.hb-verify-code input')).map(i => i.value).join('');      if (code !== '123456') {        showToast(t('invalid_code'), 'error');        return;      }      setStep(3);    });  }  if (resendBtn) {    resendBtn.addEventListener('click', () => {      showToast(t('code_sent'), 'success');    });  }  if (switchSignup) {    switchSignup.addEventListener('click', (e) => {      e.preventDefault();      isSignup = true;      if (formTitle) formTitle.textContent = t('sign_up');      if (formSubtitle) formSubtitle.textContent = t('no_account');      switchSignup.style.display = 'none';      if (switchSignin) switchSignin.style.display = 'inline';    });  }  if (switchSignin) {    switchSignin.addEventListener('click', (e) => {      e.preventDefault();      isSignup = false;      if (formTitle) formTitle.textContent = t('sign_in');      if (formSubtitle) formSubtitle.textContent = t('have_account');      switchSignin.style.display = 'none';      if (switchSignup) switchSignup.style.display = 'inline';    });  }  // (دکمهٔ نهایی ورود دیگر استفاده نمی‌شود؛ ورود واقعی از طریق فرم سرور در core:index انجام می‌شود)  // Verify code auto-advance  
document.querySelectorAll('.hb-verify-code input').forEach((input, index, inputs) => {    input.addEventListener('input', () => {      if (input.value.length === 1 && index < inputs.length - 1) {        inputs[index + 1].focus();      }    });    input.addEventListener('keydown', (e) => {      if (e.key === 'Backspace' && !input.value && index > 0) {        inputs[index - 1].focus();      }    });  });}// ---------- Register Location ----------
// در صفحهٔ ورود/ثبت‌نام: موقعیت GPS کاربر را (با اجازهٔ مرورگر) می‌گیرد و در فیلدهای
// پنهان فرم می‌گذارد تا هنگام ساخت حساب، سرور آن را به‌عنوان «موقعیت پیشنهادی» در
// بخش اطلاعات مکانی پروفایل قرار دهد (بدون ذخیرهٔ نهایی؛ کاربر بعداً تأیید می‌کند).
function initRegisterLocation() {
  // بدون هیچ پیام/دکمه‌ای (پیام هشدار GPS و دکمهٔ «فعال‌سازی GPS» حذف شده‌اند):
  // اگر مرورگر اجازه دهد، موقعیت بی‌صدا در فیلدهای پنهان فرم می‌نشیند تا هنگام
  // ساخت حساب، سرور آن را به‌عنوان «موقعیت پیشنهادی» در «اطلاعات مکانی» پروفایل
  // قرار دهد؛ در غیر این صورت بی‌صدا رد می‌شود (جایگزین IP هنگام ثبت‌نام).
  const latInput = document.getElementById('reg-lat');
  const lngInput = document.getElementById('reg-lng');
  if (!latInput || !lngInput) return;
  if (!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      latInput.value = pos.coords.latitude;
      lngInput.value = pos.coords.longitude;
    },
    () => { /* بدون GPS ادامه داده می‌شود — بدون پیام هشدار */ },
    { timeout: 8000, maximumAge: 600000, enableHighAccuracy: true }
  );
}

// ---------- GPS Activation (معادل اندروید) ----------
// در اندروید برنامه با isProviderEnabled() وضعیت GPS را می‌خواند و اگر خاموش بود در یک
// AlertDialog از کاربر می‌پرسد و با ACTION_LOCATION_SOURCE_SETTINGS او را به تنظیمات
// می‌فرستد. مرورگر اجازه نمی‌دهد برنامهٔ وب خودش GPS را روشن کند؛ معادل این الگو در وب:
//   ۱) navigator.permissions → وضعیت دسترسی به موقعیت (≈ isProviderEnabled)
//   ۲) پنجرهٔ مجوزِ خودِ مرورگر → «تصمیم کاربر» برای فعال‌کردن GPS یا رد آن
//   ۳) گفتگوی هشدار با «نحوهٔ فعال‌سازی» و «ادامه بدون GPS» (≈ AlertDialog اندروید)

// حالت «منبع موقعیت (GPS)» انتخاب‌شده در پنل مدیریت (از متای سرور) — all | browser | mobile
function hbGpsMode() {
  const el = document.querySelector('meta[name="gps-mode-config"]');
  const mode = el ? (el.getAttribute('content') || '').trim() : '';
  return (mode === 'browser' || mode === 'mobile') ? mode : 'all';
}
// مختصات از پلِ اپلیکیشن بومی (WebView اندروید/آیفون) — فقط وقتی جاسازی شده باشد
async function hbNativeCoords() {
  try {
    if (window.HabibNative && typeof window.HabibNative.getLocation === 'function') {
      const c = await window.HabibNative.getLocation();
      if (c && c.lat != null && c.lng != null) {
        return {
          lat: parseFloat(c.lat),
          lng: parseFloat(c.lng),
          accuracy: c.accuracy != null ? Math.round(parseFloat(c.accuracy)) : null,
        };
      }
    }
  } catch (e) { /* پل موجود نیست یا خطا داد → ادامه با GPS مرورگر */ }
  return null;
}
// در حالت «موبایل»، حتی فراخوانی‌های مستقیمِ navigator.geolocation (مثل صفحهٔ
// ثبت‌نام) هم ابتدا از پلِ بومی پاسخ می‌گیرند — بدون تغییرِ تک‌تکِ فراخواننده‌ها.
(function patchNativeGeolocation() {
  const original = (typeof navigator !== 'undefined' && navigator.geolocation)
    ? navigator.geolocation.getCurrentPosition
    : null;
  if (!original || window.__hbPatchedNativeGeo) return;
  window.__hbPatchedNativeGeo = true;
  window.__hbNativeGeoOriginal = original;
  navigator.geolocation.getCurrentPosition = async (success, error) => {
    if (hbGpsMode() === 'mobile') {
      const c = await hbNativeCoords();
      if (c) {
        success({ coords: { latitude: c.lat, longitude: c.lng, accuracy: c.accuracy } });
        return;
      }
    }
    original.call(navigator, success, error);
  };
})();
// درخواست مختصات GPS (مشترک بین همهٔ بخش‌ها): در حالت «موبایل» اول پلِ بومی،
// بعد GPS مرورگر؛ در حالت «همه» فقط GPS مرورگر. در صورت عدم دسترسی null برمی‌گردد.
async function hbRequestCoords() {
  if (hbGpsMode() === 'mobile') {
    const c = await hbNativeCoords();
    if (c) return c;
  }
  return hbBrowserCoords();
}
function hbBrowserCoords() {
  // درخواست مختصات GPS؛ اگر کاربر اجازه ندهد (یا GPS در دسترس نباشد) null برمی‌گردد
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({
        lat: pos.coords.latitude,
        lng: pos.coords.longitude,
        accuracy: pos.coords.accuracy != null ? Math.round(pos.coords.accuracy) : null,
      }),
      () => resolve(null),
      { timeout: 8000, maximumAge: 600000, enableHighAccuracy: true }
    );
  });
}

// دریافت مختصات GPS (مشترک بین همهٔ بخش‌ها) - در صورت عدم دسترسی null برمی‌گرداند
function hbGetCoords() { return hbRequestCoords(); }

function hbGeoState() {
  // وضعیت دسترسی به موقعیت (معادل isProviderEnabled):
  // 'granted' | 'prompt' | 'denied' | 'unsupported' | 'unknown'
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve('unsupported');
    if (!navigator.permissions || !navigator.permissions.query) return resolve('unknown');
    navigator.permissions.query({ name: 'geolocation' })
      .then((p) => resolve(p.state))
      .catch(() => resolve('unknown'));
  });
}

// گفتگوی هشدار «GPS فعال نیست» — یک نمونهٔ سراسری که با نیاز کاربر باز/بسته می‌شود
let _gpsOverlay = null;
let _gpsPending = null;
function _gpsResolve(choice) {
  const fn = _gpsPending;
  _gpsPending = null;
  if (_gpsOverlay) _gpsOverlay.classList.remove('open');
  document.body.style.overflow = '';
  if (fn) fn(choice);
}
function hbGpsDialog() {
  if (_gpsOverlay) return _gpsOverlay;
  const ov = document.createElement('div');
  ov.className = 'hb-gps-overlay';
  ov.innerHTML =
    '<div class="hb-gps-dialog" role="alertdialog" aria-modal="true" aria-labelledby="hb-gps-title">' +
      '<button type="button" class="hb-gps-close" data-gps-close aria-label="بستن">&times;</button>' +
      '<div class="hb-gps-icon"><i class="bi bi-crosshair"></i></div>' +
      '<h3 id="hb-gps-title">GPS (موقعیت‌یابی) فعال نیست</h3>' +
      '<p class="hb-gps-msg">برای دریافت خودکار موقعیت دقیق، مرورگر به دسترسی موقعیت نیاز دارد. برنامهٔ وب نمی‌تواند خودش GPS را روشن کند؛ این تصمیم فقط با شماست.</p>' +
      '<div class="hb-gps-help" data-gps-help hidden>' +
        '<b>نحوهٔ فعال‌سازی دسترسی موقعیت:</b><ul>' +
        '<li><b>گوشی اندروید:</b> تنظیمات ← موقعیت ← «روشن»؛ سپس در مرورگر، روی آیکون قفل کنار نوار آدرس بزنید و «مجاز کردن موقعیت» را انتخاب کنید.</li>' +
        '<li><b>رایانه (کروم/ادج):</b> کنار نوار آدرس روی آیکون قفل کلیک کنید ← «تنظیمات سایت» ← «موقعیت» ← «اجازه»؛ سپس صفحه را تازه‌سازی کنید.</li>' +
        '<li><b>آیفون/سافاری:</b> تنظیمات ← حریم خصوصی و امنیت ← خدمات موقعیت ← مرورگر ← «هنگام استفاده».</li>' +
        '</ul></div>' +
      '<div class="hb-gps-actions">' +
        '<button type="button" class="hb-btn hb-btn-primary hb-btn-sm" data-gps-retry><i class="bi bi-arrow-clockwise"></i> دوباره تلاش کن</button>' +
        '<button type="button" class="hb-btn hb-btn-outline hb-btn-sm" data-gps-help-toggle>نحوهٔ فعال‌سازی</button>' +
        '<button type="button" class="hb-btn hb-btn-dark hb-btn-sm" data-gps-skip><i class="bi bi-slash-circle"></i> ادامه بدون GPS</button>' +
      '</div>' +
    '</div>';
  ov.querySelector('[data-gps-close]').addEventListener('click', () => _gpsResolve('skip'));
  ov.querySelector('[data-gps-retry]').addEventListener('click', () => _gpsResolve('retry'));
  ov.querySelector('[data-gps-skip]').addEventListener('click', () => _gpsResolve('skip'));
  ov.querySelector('[data-gps-help-toggle]').addEventListener('click', (e) => {
    const help = ov.querySelector('[data-gps-help]');
    help.hidden = !help.hidden;
    e.currentTarget.classList.toggle('active', !help.hidden);
  });
  ov.addEventListener('click', (e) => { if (e.target === ov) _gpsResolve('skip'); });
  document.body.appendChild(ov);
  _gpsOverlay = ov;
  return ov;
}
function hbOpenGpsDialog() {
  const ov = hbGpsDialog();
  ov.classList.add('open');
  document.body.style.overflow = 'hidden';
  return new Promise((resolve) => { _gpsPending = resolve; });
}

// «اطمینان از GPS»: وضعیت را می‌خواند و اگر GPS خاموش/رد شده بود از کاربر می‌پرسد
// (گفتگوی هشدار). خروجی: مختصات دقیق، یا null یعنی «ادامه بدون GPS» (جایگزین IP).
async function hbEnsureGps() {
  const state = await hbGeoState();
  if (state === 'granted') return hbRequestCoords();
  if (state === 'prompt' || state === 'unknown') {
    const c = await hbRequestCoords(); // پنجرهٔ خود مرورگر = تصمیم کاربر
    if (c) return c;
  }
  // GPS خاموش یا رد شده → از کاربر می‌پرسیم (معادل AlertDialog اندروید)
  const choice = await hbOpenGpsDialog();
  if (choice !== 'retry') return null;
  return hbRequestCoords();
}

// ---------- Forms ----------
function initForms() {
  const form = document.querySelector('[data-personal-info-form]');
  if (!form) return;
  const fields = {
    first_name: {
      field: form.querySelector('select[name="first_name"]'),
      msg: 'لطفاً نام را انتخاب کنید.'
    },
    last_name: {
      field: form.querySelector('select[name="last_name"]'),
      msg: 'لطفاً نام خانوادگی را انتخاب کنید.'
    },
    gender: {
      field: form.querySelector('select[name="gender"]'),
      msg: 'لطفاً جنسیت را انتخاب کنید.'
    },
    religion: {
      field: form.querySelector('select[name="religion"]'),
      msg: 'لطفاً دین را انتخاب کنید.'
    },
    sect: {
      field: form.querySelector('select[name="sect"]'),
      msg: 'لطفاً مذهب را انتخاب کنید.'
    },
    date_of_birth: {
      field: form.querySelector('[data-shamsi-gregorian]'),
      focus: form.querySelector('[data-shamsi-input]'),
      msg: 'لطفاً تاریخ تولد را انتخاب کنید.'
    },
    national_id: {
      field: form.querySelector('input[name="national_id"]'),
      msg: 'کد ملی الزامی است.'
    }
  };
  const order = ['first_name', 'last_name', 'national_id', 'date_of_birth', 'gender', 'religion', 'sect'];
  // برای فیلدهای نام، کنترلِ دیدنیِ واقعی همان جعبهٔ جستجوی انتخاب‌گر خودکار است
  // (نه <select> پنهان) — فوکوس و خطاها روی همان اعمال می‌شود.
  const visibleField = (entry) => {
    if (!entry || !entry.field) return null;
    const ac = entry.field.closest('.hb-autocomplete');
    return ac ? ac.querySelector('.hb-autocomplete-input') : entry.field;
  };
  const focusEl = (entry) => entry.focus || visibleField(entry) || entry.field;
  const clearError = (entry) => {
    if (!entry || !entry.field) return;
    const field = visibleField(entry);
    if (field) field.style.borderColor = '';
    const group = entry.field.closest('.hb-form-group');
    if (group) {
      const err = group.querySelector('.hb-field-error-js');
      if (err) err.remove();
    }
  };
  const showError = (entry, message) => {
    clearError(entry);
    const field = visibleField(entry);
    if (field) field.style.borderColor = '#e74c3c';
    const group = entry.field.closest('.hb-form-group');
    if (group) {
      const div = document.createElement('div');
      div.className = 'hb-field-error hb-field-error-js';
      div.innerHTML = '<i class="bi bi-exclamation-circle"></i> ' + message;
      group.appendChild(div);
    }
  };
  // با تغییر مقدار توسط کاربر، خطای همان فیلد پاک می‌شود
  Object.values(fields).forEach((entry) => {
    if (entry.field) entry.field.addEventListener('change', () => clearError(entry));
  });
  form.addEventListener('submit', (e) => {
    const bad = [];
    order.forEach((name) => {
      const entry = fields[name];
      if (!entry.field) return;
      const value = entry.field.value != null ? String(entry.field.value).trim() : '';
      if (value === '') {
        bad.push({ entry, msg: entry.msg });
      } else if (name === 'national_id' && !/^\d{10}$/.test(value)) {
        bad.push({ entry, msg: 'کد ملی باید دقیقاً ۱۰ رقم (۰-۹) باشد.' });
      }
    });
    order.forEach((name) => {
      if (!bad.some((x) => x.entry === fields[name].entry)) clearError(fields[name]);
    });
    if (bad.length) {
      e.preventDefault();
      bad.forEach((x) => showError(x.entry, x.msg));
      const first = focusEl(bad[0].entry);
      if (first) {
        first.focus();
        first.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      showToast(bad[0].msg, 'error');
    }
  });
  // اگر فرم پس از خطای سرور دوباره رندر شد، روی اولین فیلد خطادار فوکوس کن
  const serverError = form.querySelector('[data-field-error]');
  if (serverError) {
    const entry = fields[serverError.getAttribute('data-field-error')];
    if (entry && entry.field) {
      entry.field.style.borderColor = '#e74c3c';
      const el = focusEl(entry);
      el.focus({ preventScroll: true });
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }
}// ---------- Modules ----------
function initModules() {  document.querySelectorAll('.hb-module-card').forEach(card => {    card.addEventListener('click', () => {      // ماژول‌های واقعی (data-href) کاربر را به صفحهٔ آن می‌برند؛ بقیه «به زودی»
      const href = card.getAttribute('data-href');
      if (href) { window.location.href = href; return; }
      showToast(t('feature_coming_soon'), 'warning');
    });
  });}// ---------- Section Toggles ----------
function initSectionToggles() {  document.querySelectorAll('.hb-section-header').forEach(header => {    header.addEventListener('click', () => {      const card = header.closest('.hb-section-card');      card.classList.toggle('active');      const icon = header.querySelector('.hb-section-toggle');      if (icon) {        icon.style.transform = card.classList.contains('active') ? 'rotate(180deg)' : 'rotate(0deg)';      }    });  });  // همهٔ بخش‌ها پیش‌فرض بسته‌اند و کاربر خودش باز می‌کند؛ تنها استثنا: بخشِ
  // دارای خطای سمت سرور (data-field-error) به‌صورت خودکار باز می‌شود تا کاربر
  // پیام خطا و فیلد مربوطه را ببیند (لینک‌های لنگر مثل #financial هم جداگانه
  // در همان صفحه باز می‌شوند).
  document.querySelectorAll('.hb-section-card').forEach(card => {    if (!card.classList.contains('active') && card.querySelector('[data-field-error]')) {      card.classList.add('active');      const icon = card.querySelector('.hb-section-toggle');      if (icon) icon.style.transform = 'rotate(180deg)';    }  });}// ---------- Location ----------
// به محض ورود به داشبورد، موقعیت فعلی کاربر استخراج، در سرور به آدرس تبدیل و در
// دیتابیس ذخیره می‌شود (کلید Google Maps فقط سمت سرور استفاده می‌شود).
function initLocation() {
  const el = document.querySelector('.hb-header-location');
  if (!el) return; // فقط صفحاتی که بج موقعیت دارند (داشبورد)
  const textEl = el.querySelector('.hb-header-location-text');
  const setLabel = (s) => { if (textEl) textEl.textContent = s; };
  const setUnavailable = () => setLabel('موقعیت در دسترس نیست');
  let busy = false;

  // خواندن توکن CSRF از کوکی (Django آن را ست می‌کند)
  const csrfMatch = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
  const csrfToken = csrfMatch ? decodeURIComponent(csrfMatch[1]) : null;

  // وقتی GPS خاموش/رد شده: بج به اعلانِ غیرمزاحمِ «GPS خاموش است» تبدیل می‌شود (کلیک‌کردنی)
  const warnOn = () => {
    el.style.borderColor = 'rgba(218,54,51,0.55)';
    el.style.background = 'rgba(218,54,51,0.1)';
    el.style.cursor = 'pointer';
    el.title = 'GPS خاموش است؛ برای دریافت موقعیت دقیق کلیک کنید';
  };
  const warnOff = () => {
    el.style.borderColor = 'var(--hb-border)';
    el.style.background = 'rgba(201,162,39,0.08)';
    el.style.cursor = 'pointer';
    el.title = 'موقعیت شما — برای به‌روزرسانی کلیک کنید';
  };

  // ثبت/به‌روزرسانی موقعیت سمت سرور (مختصات GPS یا سقوط خودکار به IP)
  const update = (coord) => {
    const body = new URLSearchParams();
    if (coord) {
      body.append('lat', coord.lat);
      body.append('lng', coord.lng);
      body.append('source', 'gps');
      if (coord.accuracy != null) body.append('accuracy', coord.accuracy);
    } else {
      body.append('source', 'ip');
    }
    return fetch('/accounts/location/update/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': csrfToken || '',
      },
      body: body.toString(),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data && data.status === 'ok' && (data.city || data.country || data.province)) {
          const enOf = function (v, vEn) { return (currentLang === 'en' && vEn) ? vEn : v; };
          const countryName = enOf(data.country, data.country_en);
          const label = [countryName, data.province, data.city].filter(Boolean).join('، ');
          const short = data.city || data.province || data.country;
          const shortEn = data.city ? data.city_en : (data.province ? data.province_en : data.country_en);
          setLabel('📍 ' + enOf(short, shortEn));
          renderLocationWidget(data);
          showToast('موقعیت شما ثبت شد: ' + label, 'success');
          return true;
        }
        setUnavailable();
        return false;
      })
      .catch(() => { setUnavailable(); renderLocationWidget({}); return false; });
  };

  // کلیک روی بج: اگر GPS خاموش است گفتگو باز می‌شود و کاربر تصمیم می‌گیرد
  // (≈ AlertDialog اندروید). در صورت فعال‌شدن، موقعیت دقیق GPS ثبت می‌شود.
  el.addEventListener('click', async () => {
    if (busy) return;
    busy = true;
    const prev = textEl ? textEl.textContent : '';
    setLabel('در حال دریافت موقعیت…');
    const coord = await hbEnsureGps();
    if (coord) {
      warnOff();
      await update(coord);
    } else {
      setLabel(prev || 'موقعیت در دسترس نیست');
    }
    busy = false;
  });

  // تشخیص خودکار هنگام ورود: بدون پنجرهٔ مزاحم؛ اگر GPS خاموش بود فقط اطلاع بده
  (async () => {
    const state = await hbGeoState();
    if (state === 'denied' || state === 'unsupported') {
      const ok = await update(null); // جایگزین IP — غیرمزاحم
      warnOn();
      if (ok) setLabel('GPS خاموش است؛ برای موقعیت دقیق کلیک کنید');
      return;
    }
    // granted / prompt / unknown: درخواست مختصات (در حالت prompt خودِ مرورگر می‌پرسد)
    const c = await hbRequestCoords();
    if (c) { warnOff(); await update(c); return; }
    const ok2 = await update(null);
    warnOn();
    if (ok2) setLabel('GPS خاموش است؛ برای موقعیت دقیق کلیک کنید');
  })();
}

// ---------- Location Widget (داشبورد) ----------
// نمایش خلاصهٔ موقعیت کاربر روی داشبورد و به‌روزرسانی زنده پس از دریافت موقعیت.
function renderLocationWidget(data) {
  const widget = document.querySelector('[data-loc-widget]');
  if (!widget) return;
  const placeEl = widget.querySelector('[data-loc-widget-place]');
  const addrEl = widget.querySelector('[data-loc-widget-address]');
  const coordsEl = widget.querySelector('[data-loc-widget-coords]');
  const timeEl = widget.querySelector('[data-loc-widget-time]');
  // کشور/استان/شهرستان هرکدام به‌صورت دوزبانه (data-loc-fa/en) ساخته می‌شوند تا
  // با تغییر زبانِ رابط، نام‌های داخل خلاصهٔ موقعیت هم عوض شوند.
  if (placeEl) {
    placeEl.innerHTML = '';
    const parts = [];
    [['country', 'country_en'], ['province', 'province_en'], ['city', 'city_en']].forEach(function (pair) {
      const v = data[pair[0]];
      if (!v) return;
      const span = document.createElement('span');
      span.setAttribute('data-loc-fa', v);
      const vEn = data[pair[1]];
      if (vEn) span.setAttribute('data-loc-en', vEn);
      span.textContent = (currentLang === 'en' && vEn) ? vEn : v;
      parts.push(span);
    });
    if (parts.length) {
      parts.forEach(function (p, i) {
        if (i > 0) placeEl.appendChild(document.createTextNode('، '));
        placeEl.appendChild(p);
      });
    } else {
      placeEl.textContent = 'موقعیت در دسترس نیست';
    }
  }
  if (addrEl && data.address) addrEl.textContent = data.address;
  if (coordsEl) {
    coordsEl.textContent = (data.latitude != null && data.longitude != null)
      ? data.latitude + ', ' + data.longitude
      : '';
  }
  if (timeEl) timeEl.textContent = 'به‌روزرسانی: ' + new Date().toLocaleTimeString('fa-IR');
}

// ---------- Location Lookup (پروفایل) ----------
// در بخش «اطلاعات مکانی» پروفایل فقط مختصات GPS دستگاه دریافت می‌شود (دکمهٔ
// «دریافت GPS») و در همان فیلد نمایش داده می‌شود؛ هیچ نقشه/تبدیل‌به‌آدرسی در این
// بخش نیست. کشور ثابت «ایران» است و استان/شهرستان از فهرست مرجع انتخاب می‌شود.
function initLocationLookup() {
  const form = document.querySelector('[data-location-form]');
  if (!form) return;
  const btn = form.querySelector('[data-locate-btn]');
  const status = form.querySelector('[data-locate-status]');
  const coordsInput = form.querySelector('[data-loc-coords]');
  const gpsAccBadge = document.querySelector('[data-gps-accuracy]');
  const gpsAccInput = form.querySelector('[name="gps_accuracy"]');
  if (!btn) return;

  const setStatus = (text, ok) => {
    if (!status) return;
    status.textContent = text;
    status.style.color = ok === false ? '#ff8a80' : (ok ? 'var(--hb-success)' : '');
  };
  const setCoords = (lat, lng) => {
    const set = (name, val) => {
      const el = form.querySelector('[name="' + name + '"]');
      if (el) el.value = val;
    };
    const rLat = parseFloat(Number(lat).toFixed(6));
    const rLng = parseFloat(Number(lng).toFixed(6));
    set('latitude', rLat);
    set('longitude', rLng);
    if (coordsInput) coordsInput.value = rLat + ', ' + rLng;
  };
  // «دقت GPS» (متر) — نمایش در کنار مختصات و نگهداری در فیلد پنهانِ فرم
  // تا هنگام «تأیید و ذخیره موقعیت» همراه اطلاعات مکانی در دیتابیس ذخیره شود.
  const setAccuracy = (m) => {
    const val = (m === null || m === undefined || isNaN(parseFloat(m)))
      ? ''
      : String(Math.round(parseFloat(m)));
    if (gpsAccBadge) gpsAccBadge.textContent = val === '' ? '' : 'دقت GPS: ±' + toFa(val) + ' متر';
    if (gpsAccInput) gpsAccInput.value = val;
  };
  // دقت ثبت‌شدهٔ قبلی (اگر باشد) همان ابتدا نمایش داده شود
  if (gpsAccInput && gpsAccInput.value) setAccuracy(gpsAccInput.value);

  btn.addEventListener('click', async () => {
    if (btn.disabled) return;
    btn.disabled = true;
    const orig = btn.innerHTML;
    btn.innerHTML = '<i class="bi bi-crosshair"></i> در حال دریافت…';
    setStatus('در حال دریافت موقعیت از GPS…');
    const coord = await hbEnsureGps();
    btn.innerHTML = orig;
    btn.disabled = false;
    if (!coord) {
      // بدون GPS (خاموش/رد/ناپشتیبان): مختصات ثبت نمی‌شود؛ کاربر دستی ادامه می‌دهد
      setStatus('دسترسی به GPS ممکن نشد؛ مختصات ثبت نشد. استان/شهرستان و آدرس را می‌توانید دستی وارد کنید.', false);
      showToast('موقعیت GPS دریافت نشد.', 'warning');
      return;
    }
    setCoords(coord.lat, coord.lng);
    setAccuracy(coord.accuracy);
    setStatus('موقعیت GPS دریافت و در فرم ثبت شد؛ در صورت صحت روی «تأیید و ذخیره موقعیت» کلیک کنید.', true);
    showToast('مختصات GPS دریافت شد.', 'success');
  });

  initLocationCascade(form);
}

// ---------- آبشار استان ← شهر/شهرستان (اطلاعات مکانی و محل کار) ----------
// فهرست‌های «استان» و «شهر/شهرستان» از جدول مرجع ساخته می‌شوند؛ شهرستان‌ها در
// گروه‌های <optgroup label="استان"> رندر شده‌اند تا آبشارِ مشترکِ زیر فقط گروهِ
// استانِ انتخابی را نشان دهد. چون گزینه‌ها حذف نمی‌شوند (فقط نمایش/پنهان)، مقدارِ
// قبلیِ شهرستان هنگام کپی از محل سکونت یا بارگذاری شغل برای ویرایش همیشه قابل
// انتخاب می‌ماند. با تغییر «استان»، اگر شهرستانِ قبلی به آن استان تعلق نداشته باشد
// خالی می‌شود.
function initLocationCascade(form) {
  if (!form) return;
  // هر فرم می‌تواند چند جفت «استان ← شهر/شهرستان» داشته باشد (مثلاً فرم شغل:
  // یک جفت برای بخش «ب» شغل آزاد و یک جفت برای بخش «ج» کارمندی)؛ هر جفت
  // مستقل آبشار می‌شود — استان و شهرستانِ هم‌ردیفِ خودش را پیدا می‌کنیم.
  Array.prototype.forEach.call(form.querySelectorAll('select.hb-loc-province'), function (provSel) {
    if (provSel.__hbCascadeBound) return;
    const row = provSel.closest('.hb-form-row') || form;
    const citySel = row.querySelector('select.hb-loc-city');
    if (!citySel) return;
    provSel.__hbCascadeBound = true;

    function sync() {
      const prov = provSel.value;
      const current = citySel.value;
      let cityMatches = false;
      Array.prototype.forEach.call(citySel.querySelectorAll('optgroup'), (group) => {
        // نامِ فارسیِ گروه (data-fa) مرجعِ آبشار است؛ برچسبِ نمایشی ممکن است با
        // تغییر زبان انگلیسی شده باشد، پس فقط با data-fa مقایسه می‌شود.
        const provKey = group.getAttribute('data-fa') || group.getAttribute('label');
        const show = provKey === prov;
        group.hidden = !show;
        if (show && current) {
          Array.prototype.forEach.call(group.querySelectorAll('option'), (o) => {
            if (o.value === current) cityMatches = true;
          });
        }
      });
      // اگر استان خالی یا شهرستانِ انتخابی متعلق به استانِ دیگری باشد → خالی می‌شود
      if (!prov || (current && !cityMatches)) citySel.value = '';
    }

    provSel.addEventListener('change', sync);
    sync(); // وضعیت اولیه (پروفایل ذخیره‌شده، کپی از محل سکونت یا ویرایش شغل)
  });
}

// ---------- Provider Badge (بخش اطلاعات مکانی) ----------
// نشان کوچک «سرویس فعال»: نشان / گوگل / رایگان. مقدار اولیه در قالب بر اساس
// کلیدهای سرور تعیین می‌شود و با هر پاسخِ جستجوی آدرس یا تبدیل مختصات به آدرس
// (data.provider) به‌روز می‌شود تا همیشه «سرویسِ در حال استفاده» را نشان دهد.
function setMapProvider(name) {
  const badge = document.querySelector('[data-map-provider]');
  if (!badge) return;
  const labels = {
    neshan: { text: 'نشان (Neshan)', icon: 'bi-pin-map' },
    google: { text: 'گوگل (Google)', icon: 'bi-google' },
    free: { text: 'رایگان', icon: 'bi-globe2' },
    ip: { text: 'رایگان', icon: 'bi-globe2' },
  };
  const entry = labels[name];
  if (!entry) return;
  const textEl = badge.querySelector('[data-map-provider-text]');
  const iconEl = badge.querySelector('i');
  if (textEl) textEl.textContent = entry.text;
  if (iconEl) iconEl.className = 'bi ' + entry.icon;
  badge.setAttribute('data-provider', name === 'ip' ? 'free' : name);
}

// ---------- جستجوی آدرس بالای نقشه (بخش اطلاعات مکانی) ----------
// کاربر آدرس فارسی را در جعبه تایپ می‌کند و با Enter یا دکمهٔ «جستجو» عبارت به
// سرور می‌رود (accounts:location_place_search)؛ اولویت سرویس‌ها همان زنجیرهٔ
// معمول است: نشان → گوگل → رایگان. با انتخاب هر نتیجه، نشانگر قرمز روی همان
// نقطه می‌افتد، مختصات فرم به‌روز و آدرس کامل (استان/شهر/...) استخراج می‌شود.
function initLocationAddressSearch() {
  const wrap = document.querySelector('[data-map-search]');
  if (!wrap) return;
  const input = wrap.querySelector('[data-map-search-input]');
  const btn = wrap.querySelector('[data-map-search-btn]');
  const list = wrap.querySelector('[data-map-search-results]');
  if (!input || !btn || !list) return;

  const csrfMatch = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
  const csrfToken = csrfMatch ? decodeURIComponent(csrfMatch[1]) : '';
  const form = document.querySelector('[data-location-form]');
  let controller = null;

  // مختصات کنونیِ فرم به‌عنوان «مختصات پایه» برای مرتب‌سازی نتایج نزدیک به موقعیت
  const biasCoords = () => {
    const read = (name) => {
      const el = form && form.querySelector('[name="' + name + '"]');
      const v = el ? parseFloat(el.value) : NaN;
      return isNaN(v) ? null : v;
    };
    return { lat: read('latitude'), lng: read('longitude') };
  };

  function close() {
    list.hidden = true;
    list.innerHTML = '';
  }

  function render(items) {
    list.innerHTML = '';
    if (!items.length) {
      const empty = document.createElement('div');
      empty.className = 'hb-autocomplete-empty';
      empty.textContent = 'نتیجه‌ای یافت نشد؛ عبارت دیگری را امتحان کنید.';
      list.appendChild(empty);
    } else {
      items.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'hb-autocomplete-item';
        row.setAttribute('role', 'option');
        if (item.title) {
          const title = document.createElement('span');
          title.textContent = item.title;
          row.appendChild(title);
        }
        if (item.address && item.address !== item.title) {
          const addr = document.createElement('small');
          addr.textContent = item.address;
          row.appendChild(addr);
        }
        row.addEventListener('mousedown', (e) => {
          e.preventDefault(); // blur را جلو بیندازد تا کلیک از دست نرود
          pick(item);
        });
        list.appendChild(row);
      });
    }
    list.hidden = false;
  }

  function pick(item) {
    input.value = item.title || item.address || '';
    close();
    // نشانگر قرمز را روی نتیجه می‌برد و مختصات فرم + آدرس را به‌روز می‌کند
    if (window.__hbMapPickLocation) {
      window.__hbMapPickLocation(item.lat, item.lng);
    } else {
      mapOnChanged(item.lat, item.lng);
    }
    if (item.provider) setMapProvider(item.provider);
    showToast('موقعیت «' + (item.title || 'انتخاب‌شده') + '» روی نقشه تنظیم شد؛ در صورت صحت تأیید و ذخیره کنید.', 'success');
  }

  async function search() {
    const q = input.value.trim();
    if (!q) { close(); return; }
    if (controller) controller.abort();
    controller = new AbortController();
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-arrow-repeat"></i> جستجو';
    const b = biasCoords();
    const body = new URLSearchParams({ q: q });
    if (b.lat != null) body.append('lat', b.lat);
    if (b.lng != null) body.append('lng', b.lng);
    try {
      const resp = await fetch('/accounts/location/search-place/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': csrfToken,
        },
        body: body.toString(),
        signal: controller.signal,
      });
      const data = await resp.json();
      if (data && data.provider) setMapProvider(data.provider);
      const items = (data && data.items ? data.items : []).map((it) =>
        Object.assign({}, it, { provider: data.provider })
      );
      render(items);
    } catch (err) {
      if (err && err.name === 'AbortError') return;
      render([]);
      showToast('خطا در جستجوی آدرس؛ دوباره تلاش کنید.', 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = orig;
    }
  }

  btn.addEventListener('click', search);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); search(); }
    else if (e.key === 'Escape') close();
  });
  input.addEventListener('focus', () => { if (list.innerHTML) list.hidden = false; });
  document.addEventListener('click', (e) => {
    if (!wrap.contains(e.target)) close();
  });
}

// ---------- Location Map (پروفایل) ----------
// نمایش موقعیت روی نقشهٔ تعاملی «نشان» (Neshan) — و در نبودِ کلید آن، Google Maps.
// اولویت: NESHAN_API_KEY > GOOGLE_MAPS_API_KEY؛ بدون هیچ کلیدی، پیام راهنما داخل
// قاب نقشه نمایش داده می‌شود. کلیک روی نقشه یا کشیدن نشانگر، مختصات را تنظیم می‌کند
// و پس از توقف، آدرس (کشور/استان/شهر/...) از سرور دریافت و داخل فرم قرار می‌گیرد.
// ذخیره در دیتابیس فقط با دکمهٔ «تأیید و ذخیره موقعیت» انجام می‌شود.
function initLocationMap() {
  const el = document.getElementById('hb-location-map');
  if (!el || window.__hbMapReady) return;
  // انتخابِ نقشه بر اساس متای «map-provider-config» (ارائه‌دهنده‌ای که ادمین در
  // تنظیمات سرویس موقعیت تعیین کرده و سرور بر اساس کلیدهای در دسترس نهایی کرده)
  // و در نبودِ کلیدِ آن، سقوط به ترتیبِ نشان ← گوگل ← OpenStreetMap (بدون کلید).
  const neshanKey = metaContent('neshan-maps-key');
  const googleKey = metaContent('google-maps-key');
  const cfg = metaContent('map-provider-config');
  const order = cfg
    ? [cfg].concat(['neshan', 'google', 'osm'].filter((p) => p !== cfg))
    : ['neshan', 'google', 'osm'];
  for (const p of order) {
    if (p === 'neshan' && neshanKey) { loadNeshanMap(neshanKey); return; }
    if (p === 'google' && googleKey) { loadGoogleMap(googleKey); return; }
    if (p === 'osm') { loadOsmMap(); return; } // OSM همیشه در دسترس است (بدون کلید)
  }
  mapNoKeyNotice(
    'برای نمایش نقشه هیچ ارائه‌دهنده‌ای در دسترس نیست؛ موقعیت را با دکمهٔ GPS یا به‌صورت دستی وارد کنید.'
  );
}

// خواندن مقدار یک متای پیکربندی سرویس موقعیت از سربرگ صفحه (مثل انتخاب نقشه/حالت GPS)
function metaContent(name) {
  const el = document.querySelector('meta[name="' + name + '"]');
  return el ? (el.getAttribute('content') || '').trim() : '';
}

// پیام راهنما داخل قاب نقشه وقتی Google Maps در دسترس نیست (بدون کلید یا خطای بارگذاری)
function mapNoKeyNotice(msg) {
  const el = document.getElementById('hb-location-map');
  if (!el) return;
  el.innerHTML =
    '<div style="height:100%;display:flex;align-items:center;justify-content:center;' +
    'padding:1.5rem;text-align:center;color:var(--hb-text-muted);font-size:0.85rem;line-height:2;">' +
    '<i class="bi bi-map" style="margin-left:0.4rem;color:var(--hb-gold-300);"></i>' + msg +
    '</div>';
}

let mapStartHadSaved = false; // آیا فرم از قبل مختصات ذخیره‌شده دارد؟
function mapStartPosition() {
  const form = document.querySelector('[data-location-form]');
  const read = (name) => {
    const el = form && form.querySelector('[name="' + name + '"]');
    const v = el ? parseFloat(el.value) : NaN;
    return isNaN(v) ? null : v;
  };
  const lat = read('latitude');
  const lng = read('longitude');
  mapStartHadSaved = lat !== null && lng !== null;
  if (mapStartHadSaved) return { lat, lng };
  return { lat: 35.6892, lng: 51.3890 }; // تهران به‌عنوان نمای پیش‌فرض
}

function locUpdateFormCoords(lat, lng) {
  const form = document.querySelector('[data-location-form]');
  if (!form) return;
  const roundedLat = parseFloat(lat.toFixed(6));
  const roundedLng = parseFloat(lng.toFixed(6));
  const set = (name, val) => {
    const el = form.querySelector('[name="' + name + '"]');
    if (el) el.value = val;
  };
  set('latitude', roundedLat);
  set('longitude', roundedLng);
  const coordsInput = form.querySelector('[data-loc-coords]');
  if (coordsInput) coordsInput.value = roundedLat + ', ' + roundedLng;
}

let _locQueryTimer = null;
function locReverseGeocode(lat, lng) {
  clearTimeout(_locQueryTimer);
  _locQueryTimer = setTimeout(() => {
    const csrfMatch = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    fetch('/accounts/location/lookup/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': csrfMatch ? decodeURIComponent(csrfMatch[1]) : '',
      },
      body: 'lat=' + encodeURIComponent(lat) + '&lng=' + encodeURIComponent(lng),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data && data.provider) setMapProvider(data.provider);
        const status = document.querySelector('[data-locate-status]');
        if (!data || data.status !== 'ok') {
          if (status) {
            status.textContent = 'نشانی دقیقی یافت نشد؛ می‌توانید آدرس را دستی وارد کنید.';
            status.style.color = '#ff8a80';
          }
          return;
        }
        const form = document.querySelector('[data-location-form]');
        if (form) {
          ['country', 'province', 'city', 'address', 'postal_code'].forEach((k) => {
            const el = form.querySelector('[name="' + k + '"]');
            const v = data[k];
            if (el && v !== undefined && v !== null && String(v).trim() !== '') el.value = v;
          });
        }
        const found = ['country', 'province', 'city', 'address'].some((k) => data[k]);
        if (status) {
          status.textContent = found
            ? 'موقعیت تنظیم شد؛ در صورت صحت روی «تأیید و ذخیره موقعیت» کلیک کنید.'
            : 'فقط مختصات ثبت شد؛ می‌توانید آدرس را دستی وارد کنید.';
          status.style.color = found ? 'var(--hb-success)' : '#ff8a80';
        }
      })
      .catch(() => {});
  }, 700);
}

function mapOnChanged(lat, lng) {
  locUpdateFormCoords(lat, lng);
  locReverseGeocode(lat, lng);
}

// نقشهٔ تعاملی «نشان» — SDK رسمی نشان بر پایهٔ Leaflet است (بدون وابستگی به سرورهای
// خارجی؛ در ایران بدون VPN هم کار می‌کند). نیازمند NESHAN_API_KEY روی سرور؛ کلید هرگز
// در درخواست‌های معکوسِ آدرس استفاده نمی‌شود و فقط برای بارگذاری نقشه سمت مرورگر است.
// نقشهٔ OpenStreetMap — Leaflet استاندارد (CDN) + کاشی‌های آزاد OSM؛ بدون هیچ
// کلیدی کار می‌کند. وقتی ادمین «OpenStreetMap» را انتخاب کند یا کلیدِ ارائه‌دهندهٔ
// انتخابی روی سرور نباشد، همین نقشه نمایش داده می‌شود تا کاربر همیشه نقشه‌ای
// تعاملی داشته باشد (کلیک/کشیدن/جستجوی آدرس مثل نقشهٔ نشان عمل می‌کند).
function loadOsmMap() {
  if (window.__hbMapReady) return;
  if (window.L && window.L.Map) { buildOsmMap(); return; }
  if (window.__hbInitOsmMap) { return; } // در حال بارگذاری است
  window.__hbInitOsmMap = () => {
    clearTimeout(window.__hbMapFallbackTimer);
    buildOsmMap();
  };
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css';
  document.head.appendChild(link);
  const script = document.createElement('script');
  script.src = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js';
  script.async = true;
  script.onload = () => { if (window.__hbInitOsmMap) window.__hbInitOsmMap(); };
  script.onerror = () => {
    window.__hbInitOsmMap = null;
    const status = document.querySelector('[data-locate-status]');
    if (status) {
      status.textContent = 'بارگذاری نقشهٔ OpenStreetMap ممکن نشد؛ موقعیت را با GPS یا دستی وارد کنید.';
      status.style.color = '#ff8a80';
    }
    mapNoKeyNotice(
      'بارگذاری نقشهٔ OpenStreetMap ممکن نشد (شبکه در دسترس نیست)؛ ' +
      'موقعیت را با دکمهٔ GPS یا به‌صورت دستی وارد کنید.'
    );
  };
  document.head.appendChild(script);
  // اگر CDN یا کاشی‌ها پاسخ ندادند، پیام راهنما داخل قاب نقشه نمایش داده می‌شود
  window.__hbMapFallbackTimer = setTimeout(() => {
    if (!window.__hbMapReady) {
      mapNoKeyNotice(
        'بارگذاری نقشهٔ OpenStreetMap طول کشید؛ اتصال شبکه را بررسی کنید.'
      );
    }
  }, 10000);
}

function buildOsmMap() {
  if (window.__hbMapReady) return;
  const el = document.getElementById('hb-location-map');
  if (!el || !window.L || !window.L.Map) return;
  const start = mapStartPosition();
  const map = new L.Map(el, {
    center: [start.lat, start.lng],
    zoom: 15,
  });
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);
  // نشانگر قرمز: موقعیت انتخاب‌شده (قابل کشیدن) — همان ظاهرِ نقشهٔ نشان
  const pinIcon = L.divIcon({
    className: 'hb-map-pin-wrap',
    html: '<div class="hb-map-pin"></div>',
    iconSize: [36, 44],
    iconAnchor: [18, 40],
  });
  const marker = L.marker([start.lat, start.lng], {
    icon: pinIcon,
    draggable: true,
    title: 'موقعیت شما — برای تنظیم بکشید یا روی نقشه کلیک کنید',
  }).addTo(map);
  // نقطهٔ آبی: موقعیت فعلی GPS کاربر (فقط نمایشی؛ انتخاب نهایی با نشانگر قرمز است)
  let mapUserMoved = false;
  const dot = L.circleMarker([start.lat, start.lng], {
    radius: 8,
    color: '#4fc3f7',
    weight: 2,
    fillColor: '#29b6f6',
    fillOpacity: 0.9,
    interactive: false,
  }).addTo(map);
  const setDotVisible = (v) => dot.setStyle({ opacity: v ? 1 : 0, fillOpacity: v ? 0.9 : 0 });
  setDotVisible(false);
  window.__hbCurrentPos = (lat, lng) => {
    dot.setLatLng([lat, lng]);
    setDotVisible(true);
    if (!mapUserMoved && !mapStartHadSaved) {
      marker.setLatLng([lat, lng]);
      map.panTo([lat, lng]);
      map.setZoom(15);
      mapOnChanged(lat, lng);
    } else if (!mapUserMoved) {
      map.panTo([lat, lng]);
      map.setZoom(15); // فقط مرکز نقشه روی موقعیت فعلی
    }
  };
  map.on('click', (e) => {
    mapUserMoved = true;
    marker.setLatLng(e.latlng);
    mapOnChanged(e.latlng.lat, e.latlng.lng);
  });
  marker.on('dragend', () => {
    mapUserMoved = true;
    const p = marker.getLatLng();
    mapOnChanged(p.lat, p.lng);
  });
  window.__hbMapMove = (lat, lng) => {
    map.panTo([lat, lng]);
    map.setZoom(15);
    marker.setLatLng([lat, lng]);
    locUpdateFormCoords(lat, lng);
  };
  // انتخاب نتیجهٔ جستجوی آدرس: نشانگر قرمز روی همان نقطه می‌افتد (مثل کلیک روی نقشه)
  window.__hbMapPickLocation = (lat, lng) => {
    mapUserMoved = true;
    marker.setLatLng([lat, lng]);
    map.panTo([lat, lng]);
    map.setZoom(15);
    mapOnChanged(lat, lng);
  };
  window.__hbMapResize = () => { if (map && map.invalidateSize) map.invalidateSize(); };
  window.__hbMapReady = true;
  hookMapSectionResize();
  hbGetCoords().then((c) => { if (c && window.__hbCurrentPos) window.__hbCurrentPos(c.lat, c.lng); });
}

function loadNeshanMap(key) {
  if (window.L && window.L.Map) { buildNeshanMap(key); return; }
  if (window.__hbInitNeshanMap) { return; } // در حال بارگذاری است
  window.__hbInitNeshanMap = () => {
    clearTimeout(window.__hbMapFallbackTimer);
    buildNeshanMap(key);
  };
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = 'https://static.neshan.org/sdk/leaflet/v1.9.4/neshan-sdk/v1.0.8/index.css';
  document.head.appendChild(link);
  const script = document.createElement('script');
  script.src = 'https://static.neshan.org/sdk/leaflet/v1.9.4/neshan-sdk/v1.0.8/index.js';
  script.async = true;
  script.onload = () => window.__hbInitNeshanMap();
  script.onerror = () => {
    window.__hbInitNeshanMap = null;
    const status = document.querySelector('[data-locate-status]');
    if (status) {
      status.textContent = 'بارگذاری نقشهٔ نشان ممکن نشد؛ موقعیت را با GPS یا دستی وارد کنید.';
      status.style.color = '#ff8a80';
    }
    mapNoKeyNotice(
      'بارگذاری نقشهٔ نشان ممکن نشد (کلید نامعتبر است یا شبکه در دسترس نیست)؛ ' +
      'موقعیت را با دکمهٔ GPS یا به‌صورت دستی وارد کنید.'
    );
  };
  document.head.appendChild(script);
  // اگر SDK نشان پاسخ نداد (کلید نامعتبر/شبکه)، پیام راهنما داخل قاب نقشه نمایش داده می‌شود
  window.__hbMapFallbackTimer = setTimeout(() => {
    if (!window.__hbMapReady) {
      mapNoKeyNotice(
        'بارگذاری نقشهٔ نشان طول کشید؛ اگر کلید NESHAN_API_KEY معتبر است، اتصال شبکه را بررسی کنید.'
      );
    }
  }, 10000);
}

function buildNeshanMap(key) {
  if (window.__hbMapReady) return;
  const el = document.getElementById('hb-location-map');
  if (!el || !window.L || !window.L.Map) return;
  const start = mapStartPosition();
  const map = new L.Map(el, {
    key,
    maptype: 'dreamy',
    poi: true,
    traffic: false,
    center: [start.lat, start.lng],
    zoom: 15,
  });
  // نشانگر قرمز: موقعیت انتخاب‌شده (قابل کشیدن)
  const pinIcon = L.divIcon({
    className: 'hb-map-pin-wrap',
    html: '<div class="hb-map-pin"></div>',
    iconSize: [36, 44],
    iconAnchor: [18, 40],
  });
  const marker = L.marker([start.lat, start.lng], {
    icon: pinIcon,
    draggable: true,
    title: 'موقعیت شما — برای تنظیم بکشید یا روی نقشه کلیک کنید',
  }).addTo(map);
  // نقطهٔ آبی: موقعیت فعلی GPS کاربر (فقط نمایشی؛ انتخاب نهایی با نشانگر قرمز است)
  let mapUserMoved = false;
  const dot = L.circleMarker([start.lat, start.lng], {
    radius: 8,
    color: '#4fc3f7',
    weight: 2,
    fillColor: '#29b6f6',
    fillOpacity: 0.9,
    interactive: false,
  }).addTo(map);
  const setDotVisible = (v) => dot.setStyle({ opacity: v ? 1 : 0, fillOpacity: v ? 0.9 : 0 });
  setDotVisible(false);
  window.__hbCurrentPos = (lat, lng) => {
    dot.setLatLng([lat, lng]);
    setDotVisible(true);
    if (!mapUserMoved && !mapStartHadSaved) {
      marker.setLatLng([lat, lng]);
      map.panTo([lat, lng]);
      map.setZoom(15);
      mapOnChanged(lat, lng);
    } else if (!mapUserMoved) {
      map.panTo([lat, lng]);
      map.setZoom(15); // فقط مرکز نقشه روی موقعیت فعلی
    }
  };
  map.on('click', (e) => {
    mapUserMoved = true;
    marker.setLatLng(e.latlng);
    mapOnChanged(e.latlng.lat, e.latlng.lng);
  });
  marker.on('dragend', () => {
    mapUserMoved = true;
    const p = marker.getLatLng();
    mapOnChanged(p.lat, p.lng);
  });
  window.__hbMapMove = (lat, lng) => {
    map.panTo([lat, lng]);
    map.setZoom(15);
    marker.setLatLng([lat, lng]);
    locUpdateFormCoords(lat, lng);
  };
  // انتخاب نتیجهٔ جستجوی آدرس: نشانگر قرمز روی همان نقطه می‌افتد (مثل کلیک روی نقشه)
  window.__hbMapPickLocation = (lat, lng) => {
    mapUserMoved = true;
    marker.setLatLng([lat, lng]);
    map.panTo([lat, lng]);
    map.setZoom(15);
    mapOnChanged(lat, lng);
  };
  window.__hbMapResize = () => { if (map && map.invalidateSize) map.invalidateSize(); };
  window.__hbMapReady = true;
  hookMapSectionResize();
  hbGetCoords().then((c) => { if (c && window.__hbCurrentPos) window.__hbCurrentPos(c.lat, c.lng); });
}

function loadGoogleMap(key) {
  if (window.google && window.google.maps) { buildGoogleMap(); return; }
  if (window.__hbInitGoogleMap) { return; } // در حال بارگذاری است
  window.__hbInitGoogleMap = () => {
    clearTimeout(window.__hbMapFallbackTimer);
    buildGoogleMap();
  };
  const script = document.createElement('script');
  script.src = 'https://maps.googleapis.com/maps/api/js?key=' + encodeURIComponent(key)
    + '&callback=__hbInitGoogleMap&language=fa';
  script.async = true;
  script.onerror = () => {
    window.__hbInitGoogleMap = null;
    const status = document.querySelector('[data-locate-status]');
    if (status) {
      status.textContent = 'بارگذاری Google Maps ممکن نشد؛ موقعیت را با GPS یا دستی وارد کنید.';
      status.style.color = '#ff8a80';
    }
    mapNoKeyNotice(
      'بارگذاری Google Maps ممکن نشد (کلید نامعتبر است یا شبکه در دسترس نیست)؛ ' +
      'موقعیت را با دکمهٔ GPS یا به‌صورت دستی وارد کنید.'
    );
  };
  document.head.appendChild(script);
  // اگر Google Maps (کلید نامعتبر/شبکه) پاسخ نداد، پیام راهنما داخل قاب نقشه نمایش داده می‌شود
  window.__hbMapFallbackTimer = setTimeout(() => {
    if (!window.__hbMapReady) {
      mapNoKeyNotice(
        'بارگذاری Google Maps طول کشید؛ اگر کلید GOOGLE_MAPS_API_KEY معتبر است، اتصال شبکه را بررسی کنید.'
      );
    }
  }, 8000);
}

function buildGoogleMap() {
  if (window.__hbMapReady) return;
  const el = document.getElementById('hb-location-map');
  if (!el || !window.google || !window.google.maps) return;
  const start = mapStartPosition();
  const center = new google.maps.LatLng(start.lat, start.lng);
  const map = new google.maps.Map(el, {
    center,
    zoom: 15,
    streetViewControl: false,
    fullscreenControl: false,
    styles: [
      { elementType: 'geometry', stylers: [{ color: '#151b2c' }] },
      { elementType: 'labels.text.fill', stylers: [{ color: '#9aa3b8' }] },
      { elementType: 'labels.text.stroke', stylers: [{ color: '#151b2c' }] },
      { featureType: 'administrative', elementType: 'geometry.stroke', stylers: [{ color: '#2c3657' }] },
      { featureType: 'poi', elementType: 'geometry', stylers: [{ color: '#1c2338' }] },
      { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#242e4d' }] },
      { featureType: 'road', elementType: 'labels.text.fill', stylers: [{ color: '#c9a227' }] },
      { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0e1424' }] },
    ],
  });
  const marker = new google.maps.Marker({
    position: center,
    map,
    draggable: true,
    title: 'موقعیت شما — برای تنظیم بکشید یا روی نقشه کلیک کنید',
  });
  // نقطهٔ آبی: موقعیت فعلی GPS کاربر (فقط نمایشی؛ انتخاب نهایی با نشانگر قرمز است)
  let mapUserMoved = false;
  const dot = new google.maps.Marker({
    position: center,
    map,
    zIndex: 1,
    icon: { url: 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png' },
    title: 'موقعیت فعلی شما (GPS)',
    visible: false,
  });
  window.__hbCurrentPos = (lat, lng) => {
    const ll = new google.maps.LatLng(lat, lng);
    dot.setPosition(ll);
    dot.setVisible(true);
    if (!mapUserMoved && !mapStartHadSaved) {
      marker.setPosition(ll);
      map.panTo(ll);
      map.setZoom(15);
      mapOnChanged(lat, lng);
    } else if (!mapUserMoved) {
      map.panTo(ll);
      map.setZoom(15); // فقط مرکز نقشه روی موقعیت فعلی
    }
  };
  google.maps.event.addListener(map, 'click', (e) => {
    mapUserMoved = true;
    marker.setPosition(e.latLng);
    mapOnChanged(e.latLng.lat(), e.latLng.lng());
  });
  google.maps.event.addListener(marker, 'dragend', () => {
    mapUserMoved = true;
    const p = marker.getPosition();
    mapOnChanged(p.lat(), p.lng());
  });
  window.__hbMapMove = (lat, lng) => {
    const ll = new google.maps.LatLng(lat, lng);
    map.panTo(ll);
    map.setZoom(15);
    marker.setPosition(ll);
    locUpdateFormCoords(lat, lng);
  };
  // انتخاب نتیجهٔ جستجوی آدرس: نشانگر قرمز روی همان نقطه می‌افتد (مثل کلیک روی نقشه)
  window.__hbMapPickLocation = (lat, lng) => {
    mapUserMoved = true;
    const ll = new google.maps.LatLng(lat, lng);
    marker.setPosition(ll);
    map.panTo(ll);
    map.setZoom(15);
    mapOnChanged(lat, lng);
  };
  window.__hbMapResize = () => google.maps.event.trigger(map, 'resize');
  window.__hbMapReady = true;
  hookMapSectionResize();
  hbGetCoords().then((c) => { if (c && window.__hbCurrentPos) window.__hbCurrentPos(c.lat, c.lng); });
}

function hookMapSectionResize() {
  const el = document.getElementById('hb-location-map');
  if (!el) return;
  const card = el.closest('.hb-section-card');
  const header = card && card.querySelector('.hb-section-header');
  if (!header) return;
  // وقتی کاربر بخش «اطلاعات مکانی» را باز می‌کند نقشه را دوباره اندازه بگیر
  header.addEventListener('click', () => {
    setTimeout(() => { if (window.__hbMapResize) window.__hbMapResize(); }, 300);
  });
}

// ---------- Toast ----------
function initToasts() {  if (!document.querySelector('.hb-toast-container')) {    const container = document.createElement('div');    container.className = 'hb-toast-container';    document.body.appendChild(container);  }}function showToast(message, type = 'info') {  const container = document.querySelector('.hb-toast-container');  const toast = document.createElement('div');  toast.className = `hb-toast ${type}`;  const icons = { success: 'bi-check-circle-fill', error: 'bi-x-circle-fill', warning: 'bi-exclamation-triangle-fill', info: 'bi-info-circle-fill' };  toast.innerHTML = `<i class='bi ${icons[type] || icons.info}'></i><span>${message}</span>`;  container.appendChild(toast);  setTimeout(() => {    toast.style.opacity = '0';    toast.style.transform = 'translateY(20px)';    setTimeout(() => toast.remove(), 300);  }, 3500);}// ---------- File Upload ----------
document.querySelectorAll('.hb-file-upload').forEach(zone => {  zone.addEventListener('click', () => {    const input = zone.querySelector('input[type=file]') || document.createElement('input');    input.type = 'file';    input.click();  });  zone.addEventListener('dragover', (e) => {    e.preventDefault();    zone.style.borderColor = 'var(--hb-gold-400)';    zone.style.background = 'rgba(201,162,39,0.05)';  });  zone.addEventListener('dragleave', () => {    zone.style.borderColor = '';    zone.style.background = '';  });  zone.addEventListener('drop', (e) => {    e.preventDefault();    zone.style.borderColor = '';    zone.style.background = '';    showToast('Files uploaded successfully!', 'success');  });});// ---------- User Menu ----------
document.querySelectorAll('.hb-user-menu-toggle').forEach(toggle => {  toggle.addEventListener('click', (e) => {    e.stopPropagation();    const menu = toggle.closest('.hb-user-menu')?.querySelector('.hb-user-menu-dropdown');    if (menu) menu.classList.toggle('open');  });});document.addEventListener('click', () => {  document.querySelectorAll('.hb-user-menu-dropdown').forEach(m => m.classList.remove('open'));});

// ---------- Shamsi (Jalali) Date Picker ----------
// تبدیل شمسی<->میلادی با تقویم داخلی مرورگر (Intl با ca-persian) که دقیق است و
// سال کبیسه را درباره درست هندل می‌کند، بدون هیچ وابستگی خارجی.
const _faFmt = new Intl.DateTimeFormat('en-u-ca-persian', { year: 'numeric', month: 'numeric', day: 'numeric', timeZone: 'UTC' });

function faPartsUTC(d) {
  const p = _faFmt.formatToParts(d);
  let y = 0, m = 0, day = 0;
  for (const part of p) {
    if (part.type === 'year') y = +part.value;
    else if (part.type === 'month') m = +part.value;
    else if (part.type === 'day') day = +part.value;
  }
  return { y, m, day };
}
function toJalaliDate(gy, gm, gd) { return faPartsUTC(new Date(Date.UTC(gy, gm - 1, gd))); }
function _cmpTriple(a, b) {
  return a.y !== b.y ? a.y - b.y : (a.m !== b.m ? a.m - b.m : a.day - b.day);
}
function toGregorianDate(jy, jm, jd) {
  // جستجوی دودویی بر حسب تعداد روز از مرجع: روزِ (شمسی jy/jm/jd) را پیدا می‌کند
  let lo = TimeUTC(1500, 0, 1), hi = TimeUTC(2200, 0, 1);
  const target = { y: jy, m: jm, day: jd };
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (_cmpTriple(faPartsUTC(new Date(mid * 86400000)), target) < 0) lo = mid + 1;
    else hi = mid;
  }
  const d = new Date(lo * 86400000);
  return { gy: d.getUTCFullYear(), gm: d.getUTCMonth() + 1, gd: d.getUTCDate() };
}
function TimeUTC(y, m, d) { return Math.round(Date.UTC(y, m, d) / 86400000); }
function todayJalali() { return faPartsUTC(new Date()); }
function jMonthLen(jy, jm) {
  if (jm <= 6) return 31;
  if (jm <= 11) return 30;
  // اسفند: ۲۹ روز، و ۳۰ روز در سال کبیسه (فاصلهٔ اول اسفند تا اول فروردینِ بعد)
  const e = toGregorianDate(jy, 12, 1);
  const f = toGregorianDate(jy + 1, 1, 1);
  return Math.round((TimeUTC(f.gy, f.gm - 1, f.gd) - TimeUTC(e.gy, e.gm - 1, e.gd)));
}
function calculateAge(jy, jm, jd) {
  const today = todayJalali();
  let age = today.y - jy;
  if (today.m < jm || (today.m === jm && today.day < jd)) age -= 1;
  return Math.max(age, 0);
}

const JALALI_MONTHS = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'];
const FA_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
function toFa(s) { return String(s).replace(/[0-9]/g, (x) => FA_DIGITS[+x]); }
function pad2(n) { return (n < 10 ? '0' : '') + n; }

function initSolarDatepicker() {
  document.querySelectorAll('[data-shamsi-picker]').forEach((picker) => {
    const input = picker.querySelector('[data-shamsi-input]');
    const gregInput = picker.querySelector('[data-shamsi-gregorian]');
    const popup = picker.querySelector('[data-shamsi-popup]');
    const info = picker.querySelector('[data-shamsi-info]');
    if (!input || !gregInput || !popup) return;

    const nowJ = todayJalali();
    const view = { j: nowJ.y, m: nowJ.m, d: null };
    // حالت «بدون کنترل سن» (مثلاً تاریخ استخدام): pickerِ تاریخ تولد فقط ۷ تا ۱۲۰ سال را
    // می‌پذیرد؛ با data-shamsi-no-age کنترل سن برداشته می‌شود و سال‌های آینده هم مجازند.
    const noAge = picker.hasAttribute('data-shamsi-no-age');

    popup.innerHTML =
      '<div class="hb-shamsi-nav">' +
        '<button type="button" data-prev aria-label="ماه قبل">‹</button>' +
        '<span class="hb-shamsi-title"></span>' +
        '<button type="button" data-next aria-label="ماه بعد">›</button>' +
      '</div>' +
      '<div class="hb-shamsi-quick">' +
        '<select data-sel-year aria-label="انتخاب سریع سال" title="انتخاب سریع سال"></select>' +
        '<select data-sel-month aria-label="انتخاب سریع ماه" title="انتخاب سریع ماه"></select>' +
      '</div>' +
      '<div class="hb-shamsi-dow">' + ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'].map((w) => '<span>' + w + '</span>').join('') + '</div>' +
      '<div class="hb-shamsi-grid"></div>';
    const title = popup.querySelector('.hb-shamsi-title');
    const grid = popup.querySelector('.hb-shamsi-grid');

    let lastValid = null; // آخرین تاریخ معتبر اعمال‌شده (برای برگرداندن تقویم هنگام خطا)

    function showAgeError(age) {
      const msg = (age < 7)
        ? 'سن نمی‌تواند کمتر از ۷ سال باشد. تاریخ دیگری انتخاب کنید.'
        : 'سن نمی‌تواند بیشتر از ۱۲۰ سال باشد. تاریخ دیگری انتخاب کنید.';
      if (info) {
        info.innerHTML = '<i class="bi bi-exclamation-circle" style="color:#e74c3c;"></i> ' + msg;
        info.style.display = 'block';
        info.style.background = 'rgba(231,76,60,0.1)';
        info.style.color = '#ff8a80';
      }
      input.style.borderColor = '#e74c3c';
      showToast(msg, 'error');
    }

    function clearAgeError() {
      if (info) {
        info.style.background = '';
        info.style.color = '';
      }
      input.style.borderColor = '';
    }

    function applyResult(o) {
      const g = toGregorianDate(o.j, o.m, o.d);
      // اعتبارسنجی سن (فقط تاریخ تولد): ۷ تا ۱۲۰ سال مجاز است — در حالت no-age
      // (تاریخ استخدام و…) هر تاریخی پذیرفته می‌شود.
      const age = calculateAge(o.j, o.m, o.d);
      if (!noAge && (age < 7 || age > 120)) {
        showAgeError(age);
        // برگرداندن تقویم به آخرین تاریخ معتبر (یا حالت خالی)
        if (lastValid) {
          view.j = lastValid.j; view.m = lastValid.m; view.d = lastValid.d;
          input.value = lastValid.text;
          gregInput.value = lastValid.greg;
        } else {
          view.d = null;
          input.value = '';
          gregInput.value = '';
        }
        render();
        return;
      }
      clearAgeError();
      input.value = toFa(o.j) + '/' + toFa(pad2(o.m)) + '/' + toFa(pad2(o.d));
      gregInput.value = g.gy + '-' + pad2(g.gm) + '-' + pad2(g.gd);
      lastValid = { j: o.j, m: o.m, d: o.d, text: input.value, greg: gregInput.value };
      if (info) {
        info.innerHTML = noAge
          ? 'میلادی: ' + toFa(g.gy) + '-' + toFa(pad2(g.gm)) + '-' + toFa(pad2(g.gd))
          : 'میلادی: ' + toFa(g.gy) + '-' + toFa(pad2(g.gm)) + '-' + toFa(pad2(g.gd)) +
            ' &nbsp;•&nbsp; سن: <b>' + toFa(age) + '</b> سال';
        info.style.display = 'block';
      }
    }
    function render() {
      title.textContent = JALALI_MONTHS[view.m - 1] + ' ' + toFa(view.j);
      const len = jMonthLen(view.j, view.m);
      const fg = toGregorianDate(view.j, view.m, 1);
      // روز هفته: از Date میلادیِ روز اول ماه
      const firstDow = (new Date(Date.UTC(fg.gy, fg.gm - 1, fg.gd)).getUTCDay() + 1) % 7; // شنبه = 0
      let html = '';
      for (let i = 0; i < firstDow; i++) html += '<span class="off"></span>';
      for (let d = 1; d <= len; d++) {
        let cls = 'day';
        if (d === view.d) cls += ' sel';
        if (view.j === nowJ.y && view.m === nowJ.m && d === nowJ.day) cls += ' today';
        html += '<span class="' + cls + '" data-day="' + d + '">' + toFa(d) + '</span>';
      }
      grid.innerHTML = html;
      if (selYear && selMonth) { selYear.value = String(view.j); selMonth.value = String(view.m); }
    }
    function toggle() {
      popup.hidden = !popup.hidden;
      if (!popup.hidden) render();
    }

    // انتخاب سریع ماه و سال‌ها — در حالت تاریخ تولد فقط سال‌های گذشته (۷ تا ۱۲۰ سال
    // قبل) معنی‌دار است؛ در حالت بدون کنترل سن (تاریخ استخدام و…) سال‌های آینده هم می‌آید.
    const selYear = popup.querySelector('[data-sel-year]');
    const selMonth = popup.querySelector('[data-sel-month]');
    const yearOpts = [];
    if (noAge) {
      for (let y = nowJ.y - 80; y <= nowJ.y + 80; y++) yearOpts.push('<option value="' + y + '">' + toFa(y) + '</option>');
    } else {
      for (let y = nowJ.y; y >= nowJ.y - 130; y--) yearOpts.push('<option value="' + y + '">' + toFa(y) + '</option>');
    }
    selYear.innerHTML = yearOpts.join('');
    selMonth.innerHTML = JALALI_MONTHS.map((m, i) => '<option value="' + (i + 1) + '">' + m + '</option>').join('');
    selYear.addEventListener('change', () => { view.j = parseInt(selYear.value, 10); view.d = null; render(); });
    selMonth.addEventListener('change', () => { view.m = parseInt(selMonth.value, 10); view.d = null; render(); });

    grid.addEventListener('click', (e) => {
      const el = e.target.closest('[data-day]');
      if (el) {
        view.d = parseInt(el.getAttribute('data-day'), 10);
        applyResult(view);
        popup.hidden = true;
      }
    });
    popup.querySelector('[data-prev]').addEventListener('click', () => { view.m--; if (view.m < 1) { view.m = 12; view.j--; } render(); });
    popup.querySelector('[data-next]').addEventListener('click', () => { view.m++; if (view.m > 12) { view.m = 1; view.j++; } render(); });
    input.addEventListener('click', (e) => { e.stopPropagation(); toggle(); });
    document.addEventListener('click', (e) => { if (!picker.contains(e.target)) popup.hidden = true; });

    // مقدار اولیه از تاریخ میلادیِ ذخیره‌شده در پروفایل
    if (gregInput.value) {
      const p = gregInput.value.split('-').map((x) => parseInt(x, 10));
      if (p.length === 3 && p[0]) {
        const jj = toJalaliDate(p[0], p[1], p[2]);
        view.j = jj.y; view.m = jj.m; view.d = jj.day;
        applyResult(view);
      }
    }
  });
}

// ---------- Job catalog cascade (5-layer picker in profile) ----------
function initJobCascade() {
  const cascade = document.getElementById('hb-job-cascade');
  if (!cascade) return;
  const form = cascade.closest('form');
  if (!form) return;

  // 5 لایه: حوزه → صنعت → دسته → عنوان → تخصص‌های مرتبط
  const ORDER = ['sector', 'industry', 'category', 'title', 'spec'];
  const HIDDEN = {
    sector: 'sector_id',
    industry: 'industry_id',
    category: 'category_id',
    title: 'occupation_title_id',
    spec: 'specialization_id',
  };
  const API = {
    industry: 'industry',
    category: 'category',
    title: 'occupation_title',
    spec: 'specialization',
  };

  const selects = {};
  ORDER.forEach((k) => { selects[k] = document.getElementById('hb-job-' + k); });
  const qinput = document.getElementById('hb-job-q');
  const qres = document.getElementById('hb-job-qres');
  const preview = document.getElementById('hb-job-preview');
  const missingChain = document.getElementById('hb-job-missing-chain');
  const confirmPanel = document.getElementById('hb-job-confirm');
  const confirmChain = document.getElementById('hb-job-confirm-chain');
  const confirmYes = document.getElementById('hb-job-confirm-yes');
  const confirmNo = document.getElementById('hb-job-confirm-no');
  let pendingChain = null;
  let selectedDesc = ''; // description of the deepest level the user confirms (t해주 especial description)
  let resultsCache = [];
  let debounce = null;

  function hiddenFor(levelKey) {
    return form.querySelector('[name="' + HIDDEN[levelKey] + '"]');
  }
  function setHidden(levelKey, val) {
    const el = hiddenFor(levelKey);
    if (el) el.value = val || '';
  }
  function selectValue(levelKey) {
    const s = selects[levelKey];
    return s && !s.disabled && s.value ? s.value : '';
  }
  function resetSelect(levelKey) {
    const s = selects[levelKey];
    if (!s) return;
    s.innerHTML = "<option value=''>—</option>";
    s.disabled = true;
  }
  function resetFrom(idx) {
    for (let j = idx; j < ORDER.length; j++) {
      resetSelect(ORDER[j]);
      setHidden(ORDER[j], '');
    }
  }
  async function jobFetch(url) {
    const res = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  }

  // پر کردن گزینه‌های یک سطح بر اساس والد؛ در صورت وجود، مقدار دلخواه را انتخاب می‌کند
  async function loadLevel(levelKey, parentId, desiredId) {
    const s = selects[levelKey];
    if (!s || !parentId) { resetSelect(levelKey); return false; }
    s.innerHTML = "<option value=''>—</option>";
    s.disabled = true;
    try {
      const data = await jobFetch('/jobs/api/options/?level=' + API[levelKey] + '&parent_id=' + encodeURIComponent(parentId));
      const items = (data && data.items) || [];
      items.forEach((it) => {
        const opt = document.createElement('option');
        opt.value = String(it.id);
        opt.textContent = it.name;
        s.appendChild(opt);
      });
      if (items.length) {
        s.disabled = false;
        items.forEach((it) => {
          const opt = s.querySelector('option[value="' + String(it.id) + '"]');
          if (opt && it.description) opt.dataset.description = it.description;
        });
        if (desiredId) s.value = String(desiredId);
      }
      return items.length > 0;
    } catch (e) {
      return false;
    }
  }

  // خلاصهٔ انتخاب فعلی داخل باکس «شغل مورد نظر خود را در فهرست نیافتید؟» —
  // همان چیزی که همراه تیکت برای مدیر ارسال می‌شود
  function updateMissingChain() {
    if (!missingChain) return;
    const parts = [];
    ORDER.forEach((k) => {
      const v = selectValue(k);
      if (v && selects[k].selectedOptions[0]) parts.push(selects[k].selectedOptions[0].textContent.trim());
    });
    if (!parts.length) { missingChain.style.display = 'none'; missingChain.innerHTML = ''; return; }
    missingChain.style.display = 'flex';
    missingChain.innerHTML = '';
    const icon = document.createElement('i');
    icon.className = 'bi bi-send';
    const span = document.createElement('span');
    span.textContent = 'در صورت ارسال، این مسیر همراه درخواست برای مدیر ارسال می‌شود: ';
    const b = document.createElement('b');
    b.textContent = parts.join(' › ');
    span.appendChild(b);
    missingChain.appendChild(icon);
    missingChain.appendChild(span);
  }

  function updatePreview() {
    updateMissingChain();
    const parts = [];
    const ids = [];
    ORDER.forEach((k) => {
      const v = selectValue(k);
      if (v) { parts.push(selects[k].selectedOptions[0].textContent.trim()); ids.push(v); }
    });
    if (!parts.length) { preview.style.display = 'none'; return; }
    preview.style.display = 'block';
    preview.innerHTML = '';
    const wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;align-items:center;gap:0.4rem;';
    const icon = document.createElement('i');
    icon.className = 'bi bi-check2-circle';
    const span = document.createElement('span');
    span.innerHTML = 'مسیر انتخاب‌شده: ';
    const b = document.createElement('b');
    b.textContent = parts.join(' › ');
    span.appendChild(b);
    wrap.appendChild(icon);
    wrap.appendChild(span);
    preview.appendChild(wrap);
    // کد اختصاصی شغل: شناسهٔ رکوردهای دیتابیسِ سطوحِ انتخاب‌شده پشت سر هم (مثل 37112026)
    const code = ids.join('');
    if (code) {
      const row = document.createElement('div');
      row.style.cssText = 'margin-top:0.4rem;display:flex;align-items:center;gap:0.45rem;flex-wrap:wrap;font-size:0.78rem;';
      const ci = document.createElement('i');
      ci.className = 'bi bi-upc-scan';
      ci.style.color = 'var(--hb-gold-300)';
      const label = document.createElement('span');
      label.style.color = 'var(--hb-text-muted)';
      label.textContent = 'کد اختصاصی شغل (از رکوردهای دیتابیس):';
      const chip = document.createElement('span');
      chip.style.cssText = 'font-family:ui-monospace,Consolas,monospace;letter-spacing:1px;color:var(--hb-gold-300);background:rgba(184,134,11,0.1);border:1px solid rgba(184,134,11,0.25);border-radius:6px;padding:0.05rem 0.5rem;';
      chip.setAttribute('dir', 'ltr');
      chip.textContent = code;
      row.appendChild(ci);
      row.appendChild(label);
      row.appendChild(chip);
      preview.appendChild(row);
    }
    // توضیحات لایهٔ عمیق‌ترین سطوحِ انتخاب‌شده در پیش‌نمایش زنجیرهٔ پروفایل
    if (selectedDesc) {
      const row = document.createElement('div');
      row.style.cssText = 'margin-top:0.4rem;font-size:0.78rem;color:var(--hb-text-secondary);background:rgba(88,166,255,0.06);border:1px solid rgba(88,166,255,0.22);border-radius:6px;padding:0.4rem 0.7rem;';
      const icon = document.createElement('i');
      icon.className = 'bi bi-info-circle';
      icon.style.color = 'var(--hb-info)';
      const txt = document.createElement('span');
      txt.textContent = 'توضیحات تخصص/عنوان:';
      const desc = document.createElement('span');
      desc.textContent = selectedDesc;
      row.appendChild(icon);
      row.appendChild(txt);
      row.appendChild(desc);
      preview.appendChild(row);
    }
  }

  // «توضیح کوتاه شغل (اختیاری)»: کادر فقط‌خواندنی که فقط به فیلد «توضیحات»
  // کاتالوگ (عمیق‌ترین سطحِ انتخاب‌شده؛ ترجیحاً لایهٔ ۵ «تخصص‌های مرتبط»)
  // متصل است — کاربر نمی‌تواند آن را ویرایش کند.
  const specDescBox = document.getElementById('hb-job-spec-desc');
  const specDescText = document.getElementById('hb-job-spec-desc-text');
  const specDescEmpty = document.getElementById('hb-job-spec-desc-empty');
  function showSpecDesc(text) {
    const t = String(text || '').trim();
    if (specDescBox) specDescBox.style.display = t ? 'flex' : 'none';
    if (specDescText) specDescText.textContent = t;
    if (specDescEmpty) specDescEmpty.style.display = t ? 'none' : 'block';
  }
  function updateSpecDesc() {
    // از عمیق‌ترین سطح انتخاب‌شده شروع کن؛ لایهٔ ۵ (تخصص) در اولویت است
    for (let j = ORDER.length - 1; j >= 0; j--) {
      const s = selects[ORDER[j]];
      if (s && s.value && s.selectedOptions[0]) {
        const d = s.selectedOptions[0].dataset.description || '';
        if (d.trim()) { showSpecDesc(d); return; }
      }
    }
    showSpecDesc('');
  }

  function titleInput() { return form.querySelector('[name="title"]'); }

  // عنوانِ فرم از «عمیق‌ترین» سطح انتخاب‌شده در فهرست تکمیل می‌شود (همانند سرور)
  function syncTitleFromSelects() {
    const t = titleInput();
    if (!t) return;
    let label = '';
    for (let j = ORDER.length - 1; j >= 0; j--) {
      const s = selects[ORDER[j]];
      if (s && s.value && s.selectedOptions[0]) { label = s.selectedOptions[0].textContent.trim(); break; }
    }
    t.value = label;
  }

  function syncTitleFromChain(chain) {
    const t = titleInput();
    if (!t) return;
    t.value = chain.specialization_name || chain.occupation_title_name || chain.category_name || chain.industry_name || chain.sector_name || '';
  }

  // انتخاب دستی یک سطح → پاک کردن لایه‌های عمیق‌تر و بارگذاری سطح بعدی
  async function handlePick(levelKey) {
    hideConfirm();
    const idx = ORDER.indexOf(levelKey);
    const val = selectValue(levelKey);
    resetFrom(idx + 1);
    setHidden(levelKey, val);
    if (!val) { syncTitleFromSelects(); updatePreview(); updateSpecDesc(); document.dispatchEvent(new CustomEvent('hb:job-changed')); return; }
    const next = ORDER[idx + 1];
    if (next) await loadLevel(next, val, null);
    syncTitleFromSelects();
    updatePreview();
    updateSpecDesc();
    document.dispatchEvent(new CustomEvent('hb:job-changed'));
  }

  ORDER.forEach((k, i) => {
    const s = selects[k];
    if (s) {
      s.addEventListener('change', () => { handlePick(k); });
      // لایهٔ اول از قبل در سرور رندر شده؛ اگر از قبل مقداری دارد بارگذاری را ادامه بده
      if (i === 0 && s.value) handlePick(k);
    }
  });

  // پیش‌پرکردن فهرست سلسله‌مراتبی از زنجیرهٔ کاتالوگِ شغلِ ذخیره‌شده (حالت ویرایش):
  // بدون این، فهرست خالی به‌نظر می‌رسد و اگر کاربر بدون دست‌زدن به آن ذخیره کند،
  // زنجیرهٔ قبلی از بین می‌رود (رفعِ «دکمهٔ ویرایش شغل درست کار نمی‌کند»).
  // این بلاک باید داخل initJobCascade باشد — loadLevel/hiddenFor/… محلی همین تابع‌اند.
  (function initCascadeEditPrefill() {
    let editData = null;
    try {
      const el = document.getElementById('hb-job-edit-data');
      editData = el ? JSON.parse(el.textContent || 'null') : null;
    } catch (e) { editData = null; }
    if (!editData || editData.employment_mode === 'unemployed') return;
    const sectorId = String(editData.sector_id || '');
    if (!sectorId) return;
    (async function () {
      try {
        const s0 = selects.sector;
        if (!s0) return;
        s0.value = sectorId;
        setHidden('sector', sectorId);
        const indId = String(editData.industry_id || '');
        if (!indId || !(await loadLevel('industry', sectorId, indId))) return;
        setHidden('industry', indId);
        const catId = String(editData.category_id || '');
        if (!catId || !(await loadLevel('category', indId, catId))) return;
        setHidden('category', catId);
        const titleId = String(editData.occupation_title_id || '');
        if (!titleId || !(await loadLevel('title', catId, titleId))) return;
        setHidden('title', titleId);
        const specId = String(editData.specialization_id || '');
        if (specId && (await loadLevel('spec', titleId, specId))) {
          setHidden('spec', specId);
        }
    syncTitleFromSelects();
    updatePreview();
    showSpecDesc((editData && editData.specialization_description) || (editData && editData.occupation_title_description) || '');
    document.dispatchEvent(new CustomEvent('hb:job-changed'));
  } catch (e) { /* پیش‌پرکردن اختیاری است — خطا کل ویرایش را نباید بترکاند */ }
    })();
  })();

  // -------- جستجوی سریع در کل کاتالوگ --------
  function hideResults() {
    qres.style.display = 'none';
    qres.innerHTML = '';
    resultsCache = [];
  }

  qinput.addEventListener('input', () => {
    hideConfirm();
    clearTimeout(debounce);
    const term = qinput.value.trim();
    if (term.length < 2) { hideResults(); return; }
    debounce = setTimeout(async () => {
      try {
        const data = await jobFetch('/jobs/api/search/?q=' + encodeURIComponent(term));
        resultsCache = (data && data.items) || [];
        qres.innerHTML = '';
        if (!resultsCache.length) {
          qres.style.display = 'block';
          const empty = document.createElement('div');
          empty.className = 'hb-cq-item';
          empty.textContent = 'نتیجه‌ای یافت نشد.';
          qres.appendChild(empty);
          return;
        }
        resultsCache.forEach((it, i) => {
          const item = document.createElement('div');
          item.className = 'hb-cq-item';
          const label = document.createElement('div');
          label.className = 'hb-cq-label';
          label.textContent = it.label;
          const path = document.createElement('div');
          path.className = 'hb-cq-path';
          path.textContent = it.path;
          item.appendChild(label);
          item.appendChild(path);
          if (it.description) {
            const desc = document.createElement('div');
            desc.className = 'hb-cq-desc';
            desc.innerHTML = '<i>توضیحات: </i>';
            desc.appendChild(document.createTextNode(it.description));
            item.appendChild(desc);
          }
          item.addEventListener('click', () => {
            hideResults();
            showConfirm(it);
          });
          qres.appendChild(item);
        });
        qres.style.display = 'block';
      } catch (e) {
        hideResults();
      }
    }, 260);
  });
  qinput.addEventListener('focus', () => { if (resultsCache.length) qres.style.display = 'block'; });
  document.addEventListener('click', (e) => {
    if (!cascade.contains(e.target)) hideResults();
  });

  // -------- تایید سلسله‌مراتب شغل یافت‌شده از جستجو --------
  const CONFIRM_LEVELS = [
    ['sector_name', 'حوزه'],
    ['industry_name', 'صنعت'],
    ['category_name', 'دسته'],
    ['occupation_title_name', 'عنوان'],
    ['specialization_name', 'تخصص‌های مرتبط'],
  ];

  function showConfirm(item) {
    const chain = (item && item.chain) || null;
    if (!confirmPanel || !chain) { if (chain) applyChain(chain); return; }
    pendingChain = chain;
    confirmChain.innerHTML = '';
    CONFIRM_LEVELS.forEach((pair, i) => {
      const name = chain[pair[0]] || '';
      if (!name) return;
      const row = document.createElement('div');
      row.className = 'hb-job-confirm-row';
      const lvl = document.createElement('span');
      lvl.className = 'hb-job-confirm-level';
      lvl.textContent = (i + 1) + '. ' + pair[1] + ':';
      const val = document.createElement('span');
      val.className = 'hb-job-confirm-name';
      val.textContent = name;
      row.appendChild(lvl);
      row.appendChild(val);
      confirmChain.appendChild(row);
    });
    // کد اختصاصی از شناسهٔ رکوردهای دیتابیسِ همان زنجیره
    const code = CONFIRM_LEVELS
      .map((pair) => chain[pair[0].replace('_name', '_id')])
      .filter((v) => v)
      .join('');
    if (code) {
      const row = document.createElement('div');
      row.className = 'hb-job-confirm-row';
      const lvl = document.createElement('span');
      lvl.className = 'hb-job-confirm-level';
      lvl.textContent = 'کد اختصاصی: ';
      const val = document.createElement('span');
      val.className = 'hb-job-confirm-name';
      val.style.direction = 'ltr';
      val.style.fontFamily = 'ui-monospace,Consolas,monospace';
      val.style.letterSpacing = '1px';
      val.textContent = code;
      row.appendChild(lvl);
      row.appendChild(val);
      confirmChain.appendChild(row);
    }
    confirmPanel.style.display = 'block';
    if (confirmYes) confirmYes.focus();
  }

  function hideConfirm() {
    if (confirmPanel) confirmPanel.style.display = 'none';
    pendingChain = null;
  }

  if (confirmYes) confirmYes.addEventListener('click', () => {
    if (pendingChain) applyChain(pendingChain);
    hideConfirm();
  });
  if (confirmNo) confirmNo.addEventListener('click', hideConfirm);

  // پر کردن هر پنج لایه از روی یک نتیجهٔ جستجو
  async function applyChain(chain) {
    // لایهٔ اول (حوزه) از قبل در سمت سرور رندر شده؛ فقط لایه‌های عمیق‌تر را بازنشانی کن
    resetFrom(1);
    selects.sector.value = chain.sector_id ? String(chain.sector_id) : '';
    setHidden('sector', chain.sector_id || '');
    if (chain.industry_id) {
      if (await loadLevel('industry', chain.sector_id, chain.industry_id)) {
        setHidden('industry', chain.industry_id);
        if (chain.category_id && (await loadLevel('category', chain.industry_id, chain.category_id))) {
          setHidden('category', chain.category_id);
          if (chain.occupation_title_id && (await loadLevel('title', chain.category_id, chain.occupation_title_id))) {
            setHidden('title', chain.occupation_title_id);
            if (chain.specialization_id && (await loadLevel('spec', chain.occupation_title_id, chain.specialization_id))) {
              setHidden('spec', chain.specialization_id);
            }
          }
        }
      }
    }
    syncTitleFromChain(chain);
    selectedDesc = chain.specialization_name
      ? (chain.specialization_description || '')
      : (chain.occupation_title_description || '');
    updatePreview();
    showSpecDesc(selectedDesc);
    document.dispatchEvent(new CustomEvent('hb:job-changed'));
  }

  // اگر از فرم شغل با لنگر #jobs برگشته‌ایم، بخش «اطلاعات شغلی» را باز و نمایان کن
  // دسترسی خارجی برای پاک‌کردن کامل زنجیرهٔ انتخاب شغل (مثلاً هنگام «بدون شغل / بیکار»)
  window.__hbJobCascade = {
    resetCascade: function () {
      resetFrom(0);
      const q = document.getElementById('hb-job-q');
      if (q) q.value = '';
      hideResults();
      hideConfirm();
      const t = titleInput();
      if (t) t.value = '';
      selectedDesc = '';
      updatePreview();
      showSpecDesc('');
    },
  };

  if (window.location.hash === '#jobs') {
    const jobsCard = document.getElementById('jobs');
    if (jobsCard) {
      jobsCard.classList.add('active');
      const icon = jobsCard.querySelector('.hb-section-toggle');
      if (icon) icon.style.transform = 'rotate(180deg)';
      setTimeout(() => jobsCard.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80);
    }
  }
}

// ---------- آدرس محل کار (فرم شغل) ----------
// هر شغل یک آدرس دارد: پیش‌فرض «آدرس محل زندگی» (بخش اطلاعات مکانی) است — در
// این حالت کشور/استان/شهرستان و آدرسِ محل زندگی همین‌جا کپی می‌شود تا کاربر فقط
// تأیید کند و فیلدها غیرفعال می‌شوند؛ اگر بخش «اطلاعات مکانی» هنوز تکمیل نشده
// باشد، فیلدها خالی و قابل‌ویرایش می‌مانند تا کاربر استان/شهرستان را دستی پر کند
// (در هر صورت تکمیل استان و شهر/شهرستان الزامی است). با برداشتن تیک، کاربر
// می‌تواند برای همین شغل یک آدرس مجزا (کشور ایران ثابت + استان/شهرستان و آدرس)
// وارد کند. مختصات GPS/نقشه در مشاغل وجود ندارد؛ فقط «اطلاعات مکانی» محل زندگی
// مختصات را نگه می‌دارد.
function initJobLocation() {
  const form = document.getElementById('job-form');
  if (!form) return;
  const resEl = document.getElementById('hb-job-residence');
  const provSel = form.querySelector('select.hb-loc-province:not([data-free-loc])');

  const setVal = (name, val) => {
    let el = form.querySelector('[name="' + name + '"]');
    // اگر فیلد اصلی (مثلاً کارکشور محل کار) پنهان است، به فیلد نمایشیِ هم‌نامِ class برمی‌گردیم
    if ((!el || el.type === 'hidden') && name === 'work_country') {
      const display = form.querySelector('.hb-loc-country-static:not([data-free-loc-display])');
      if (display && display.type !== 'hidden') el = display;
    }
    if (el) el.value = (val === null || val === undefined) ? '' : val;
  };
  function residence() {
    try { return resEl ? JSON.parse(resEl.textContent || '{}') : {}; } catch (e) { return {}; }
  }
  function fillFromResidence() {
    const r = residence();
    setVal('work_country', r.country || 'ایران');
    setVal('work_province', r.province || '');
    setVal('work_city', r.city || '');
    setVal('work_address', r.address || '');
    // نمایشِ ثابتِ «کشور محل کار» هم با محل سکونت هم‌گام می‌شود (دوزبانه)
    const staticCountry = form.querySelector('.hb-loc-country-static:not([data-free-loc-display])');
    if (staticCountry) {
      staticCountry.value = r.country || 'ایران';
      staticCountry.setAttribute('data-loc-fa', r.country || 'ایران');
      if (r.country_en) staticCountry.setAttribute('data-loc-en', r.country_en);
      else staticCountry.removeAttribute('data-loc-en');
    }
    if (provSel) provSel.dispatchEvent(new Event('change')); // فهرست شهرستان هماهنگ شود
  }
  // پیش‌پرکردن از سکونت فقط برای بخش «ج» (کارمندی) است؛ اگر رادیوی الف/ب/ج
  // در فرم حاضر باشد، فقط وقتی بخش «ج» فعال است اجرا می‌شود تا فیلدهای بخش «ب»
  // هرگز از محل سکونت پر نشوند (بخش‌ها مجزا هستند).
  function activeMode() {
    const checked = form.querySelector('[data-job-kind-radio]:checked');
    return checked ? checked.value : 'free';
  }
  function applyState() {
    // در حالت ویرایش (فرم از قبل با مقادیر ذخیره‌شدهٔ شغل پر است) از سکونت پر نمی‌کنیم
    if (form.hasAttribute('data-job-edit')) return;
    if (!form.querySelector('[data-job-kind-radio]') || activeMode() === 'employee') {
      fillFromResidence();
    }
  }

  // بخش «ب» (شغل آزاد): فیلدهای مکانِ این بخش هیچ ارتباطی با محل سکونت و بخش «ج»
  // ندارند — فقط آبشارِ استان ← شهر/شهرستانِ خودش تنظیم می‌شود (کشور ایران ثابت).
  // در حالت ویرایش، مقدارِ ذخیره‌شدهٔ شغل باید بماند (فقط آبشار هماهنگ می‌شود).
  const freeProvSel = form.querySelector('select.hb-loc-province[data-free-loc]');
  const freeStaticCountry = form.querySelector('.hb-loc-country-static[data-free-loc-display]');
  if (freeProvSel) {
    const freeCountryHidden = form.querySelector('[name="free_country"]');
    if (!form.hasAttribute('data-job-edit') && freeCountryHidden && !(freeCountryHidden.value || '').trim()) freeCountryHidden.value = 'ایران';
    if (freeStaticCountry) {
      const v = (freeCountryHidden && freeCountryHidden.value) || 'ایران';
      freeStaticCountry.value = v;
      freeStaticCountry.setAttribute('data-loc-fa', v);
      if (r2en(v)) freeStaticCountry.setAttribute('data-loc-en', r2en(v));
    }
    freeProvSel.dispatchEvent(new Event('change'));
  }

  // نام انگلیسیِ کشور از گزینه‌های دوزبانهٔ خودِ فرم خوانده می‌شود (data-fa/data-en)
  function r2en(fa) {
    let en = '';
    Array.prototype.forEach.call(form.querySelectorAll('select.hb-loc-province[data-free-loc] option'), function (o) {
      if (o.getAttribute('data-fa') === fa) en = o.getAttribute('data-en') || '';
    });
    return en;
  }

  initLocationCascade(form);
  applyState();
  window.__hbJobLoc = { apply: applyState, fillFromResidence };
}

// ---------- «نوع ثبت شغل» الف/ب/ج (فرم شغل) ----------
// تفکیک فرم شغل به سه زیربخشِ مجزا با دکمه‌های رادیویی (هر بار فقط یکی):
//   الف) «بدون شغل / بیکار هستم» — فقط وضعیت اشتغالِ «بدون شغل» ثبت می‌شود.
//   ب) «شغل آزاد» — عکس پروفایلِ این شغل + آدرس محل کارِ همین بخش.
//   ج) «شغل وابسته (کارمندی)» — سازمان/واحد/نوع استخدام/تاریخ استخدام/حوزه فعالیت/
//        مهارت‌ها به‌همراه آدرس محل کارِ سازمان.
// انتخابِ شغل از فهرست سلسله‌مراتبی (حوزه ← صنعت ← دسته ← عنوان ← تخصص‌های مرتبط؛ کاتالوگ
// دیتابیس) بین «ب» و «ج» مشترک است و با جابجایی رادیوها حفظ می‌شود — پاک‌سازی
// آن فقط هنگام ارسالِ فرم در حالت «الف» انجام می‌شود. فیلد پنهانِ employment_mode
// هم با گزینهٔ انتخابی همگام می‌شود تا سمت سرور هم بداند کدام بخش ارسال شده است.
function initJobUnemployedToggle() {
  const form = document.getElementById('job-form');
  if (!form) return;
  const modeInput = form.querySelector('[name="employment_mode"]');
  const radios = Array.prototype.slice.call(form.querySelectorAll('[data-job-kind-radio]'));
  if (!radios.length) return;

  const mode = () => {
    const checked = radios.find(function (r) { return r.checked; });
    return checked ? checked.value : 'free';
  };

  // ردیف‌های هر بخش: فهرست سلسله‌مراتبی (کاتالوگ دیتابیس) بین «ب» و «ج» مشترک
  // است؛ فقط در «الف» غیرفعال می‌شود و با جابجایی رادیوها پاک نمی‌گردد.
  const cascadeRows = Array.prototype.slice.call(form.querySelectorAll('[data-job-cascade-fields]'));
  const freeRows = Array.prototype.slice.call(form.querySelectorAll('[data-job-free-fields], [data-job-free-gps-fields]'));
  const employeeRows = Array.prototype.slice.call(form.querySelectorAll('[data-job-employee-fields], [data-job-gps-fields]'));
  // ردیف مشترک (عکس پروفایل شغل): در هر دو حالت «ب» و «ج» فعال است و فقط در «الف»
  // (بدون شغل) خاموش می‌شود — به‌رغم نشانهٔ ب/جِ اضافه‌اش یک‌بار غیرفعال می‌شود.
  const sharedRows = Array.prototype.slice.call(form.querySelectorAll('[data-job-photo-fields]'));
  // ردیف مشترک «شغل فعلی»: چون هر سه شغل (ب و ج) می‌توانند هم‌زمان شغل فعلی باشند،
  // این ردیف هم مثل عکس فقط در «الف» خاموش می‌شود.
  const currentRows = Array.prototype.slice.call(form.querySelectorAll('[data-job-current-fields]'));
  // ردیف «توضیح کوتاه شغل» (متصل به لایهٔ ۵ کاتالوگ): مثل خودِ فهرست سلسله‌مراتبی
  // در «ب» و «ج» فعال است و فقط در «الف» خاموش می‌شود — نباید در otherRows
  // (مخصوص بخش «ج») بیفتد وگرنه در حالت «ب» به‌اشتباه غیرفعال می‌شد.
  const specDescRows = Array.prototype.slice.call(form.querySelectorAll('[data-job-spec-desc-fields]'));
  const otherRows = Array.prototype.slice.call(form.querySelectorAll('[data-job-details-fields]')).filter(function (row) {
    return cascadeRows.indexOf(row) === -1 && freeRows.indexOf(row) === -1 && employeeRows.indexOf(row) === -1 && sharedRows.indexOf(row) === -1 && currentRows.indexOf(row) === -1 && specDescRows.indexOf(row) === -1;
  });

  function setRows(rows, active) {
    rows.forEach(function (row) {
      row.style.opacity = active ? '1' : '0.45';
      row.style.pointerEvents = active ? 'auto' : 'none';
      row.querySelectorAll('input, select, textarea, button').forEach(function (el) {
        // فیلدهای پنهانِ زنجیره همیشه فعال بمانند (انتخاب‌ها در سطح DOM نگه داشته شوند)
        if (el.classList.contains('hb-chain-field')) return;
        el.disabled = !active;
      });
    });
  }

  function applyState() {
    const m = mode();
    // فهرست سلسله‌مراتبی (کاتالوگ دیتابیس) + توضیح کوتاهِ متصل به آن در «ب» و «ج»
    // فعال است؛ فقط در «الف» خاموش می‌شوند
    setRows(cascadeRows, m !== 'unemployed');
    setRows(specDescRows, m !== 'unemployed');
    setRows(freeRows, m === 'free');
    setRows(employeeRows, m === 'employee');
    // عکس پروفایل شغل + GPS: مشترک بین «ب» و «ج»؛ فقط در «الف» خاموش می‌شوند
    setRows(sharedRows, m !== 'unemployed');
    // «شغل فعلی»: مشترک بین «ب» و «ج»؛ فقط در «الف» خاموش می‌شود
    setRows(currentRows, m !== 'unemployed');
    setRows(otherRows, m === 'employee');
    Array.prototype.forEach.call(form.querySelectorAll('[data-job-part="free"], [data-job-part="employee"]'), function (head) {
      head.classList.toggle('hb-job-off', head.getAttribute('data-job-part') !== m);
    });
    // هایلایتِ کارتِ انتخاب‌شده از چهار فریم «نوع ثبت شغل» + حالت غیرفعالِ کارتِ قفل‌شده
    form.querySelectorAll('[data-job-kind-card]').forEach(function (card) {
      const r = card.querySelector('[data-job-kind-radio]');
      if (!r) return;
      card.classList.toggle('hb-job-kind-active', !!(r.checked && !r.disabled));
      card.classList.toggle('hb-job-kind-disabled', !!r.disabled);
    });
    // همگام‌سازی فیلد پنهانِ employment_mode با گزینهٔ رادیویی + نشانهٔ «حفظ
    // زنجیرهٔ ذخیره‌شده» در حالت ویرایش (تا انتخاب قبلی شغل بی‌دلیل حذف نشود)
    if (modeInput) modeInput.value = (m === 'unemployed') ? 'unemployed' : (m === 'employee' ? 'employee' : 'free');
    const keepInput = form.querySelector('[name="keep_chain"]');
    if (keepInput && form.hasAttribute('data-job-edit')) keepInput.value = '1';
    // انتخاب‌های فهرست (selectها و فیلدهای پنهان زنجیره) عمداً حفظ می‌شوند تا
    // جابجایی بین رادیوها آنها را از بین نبرد؛ پاک‌سازی نهایی فقط هنگام ارسال
    // فرم در حالت «الف» انجام می‌شود (پایین‌تر).
    const missing = document.getElementById('job-missing-block');
    if (missing) missing.style.display = (m === 'unemployed') ? 'none' : '';
    // در حالت ویرایش، پس از هر تغییر رادیو، مقادیر بخش فعالِ ذخیره‌شده بازخوانی شود
    if (editValues) applyEditValues(editValues, m);
  }

  // حالت ویرایش: مقادیر ذخیره‌شدهٔ شغل (توسط سرور در script زیر ریخته می‌شود).
  // با جابجایی رادیوها، فیلدهای بخش فعال از همین داده پر می‌شود تا کاربر دیدهٔ
  // واقعیِ شغل ذخیره‌شده را ویرایش کند (بخش‌ها مجزا هستند).
  const editEl = document.getElementById('hb-job-edit-data');
  let editValues = null;
  try { editValues = editEl ? JSON.parse(editEl.textContent || 'null') : null; } catch (e) { editValues = null; }
  function applyEditValues(d, m) {
    if (!d) return;
    const set = function (name, val) {
      const el = form.querySelector('[name="' + name + '"]');
      if (el) el.value = (val === null || val === undefined) ? '' : val;
    };
    // چک‌باکس‌ها (مثل «شغل فعلی») با set مقداردهی می‌شوند؛ ورودی‌های checkbox
    // به‌جای value باید checked شوند وگرنه با "True"/"False" خراب می‌شوند.
    const setCheck = function (name, val) {
      const el = form.querySelector('[name="' + name + '"]');
      if (el && el.type === 'checkbox') el.checked = !!val && val !== 'False';
    };
    if (m === 'free') {
      set('free_address', d.free_address);
      set('free_province', d.free_province);
      set('free_city', d.free_city);
      set('free_country', d.free_country || 'ایران');
      // مختصات GPS بخش «ب» در فیلدهای پنهان/نمایشِ همین گروه بارگذاری می‌شود
      const fg = { lat: form.querySelector('[data-free-gps-lat]'), lng: form.querySelector('[data-free-gps-lng]'), acc: form.querySelector('[data-free-gps-acc]'), disp: form.querySelector('[data-free-gps-display]') };
      if (fg.lat && fg.lng && fg.disp) {
        const lat = (d.free_gps_latitude === null || d.free_gps_latitude === undefined || d.free_gps_latitude === '') ? null : Number(d.free_gps_latitude);
        const lng = (d.free_gps_longitude === null || d.free_gps_longitude === undefined || d.free_gps_longitude === '') ? null : Number(d.free_gps_longitude);
        const acc = (d.free_gps_accuracy === null || d.free_gps_accuracy === undefined || d.free_gps_accuracy === '') ? null : Number(d.free_gps_accuracy);
        fg.lat.value = (lat !== null && !isNaN(lat)) ? String(lat) : '';
        fg.lng.value = (lng !== null && !isNaN(lng)) ? String(lng) : '';
        if (fg.acc) fg.acc.value = (acc !== null && !isNaN(acc)) ? String(acc) : '';
        fg.disp.value = (lat !== null && lng !== null && !isNaN(lat) && !isNaN(lng)) ? (lat + ', ' + lng) : '';
      }
    } else if (m === 'employee') {
      set('work_province', d.work_province);
      set('work_city', d.work_city);
      set('work_address', d.work_address);
      set('work_country', d.work_country);
      set('organization', d.organization);
      set('department', d.department);
      set('employment_type', d.employment_type);
      set('hire_date', d.hire_date);
      // همگام‌سازی نمایشِ شمسیِ «تاریخ استخدام» با فیلد پنهانِ میلادیِ به‌روزشده
      // (انتخابگر شمسی فقط هنگام بارگذاری صفحه مقدار اولیه را می‌خواند).
      (function syncHireShamsi() {
        const picker = form.querySelector('[data-shamsi-picker]');
        if (!picker) return;
        const shInput = picker.querySelector('[data-shamsi-input]');
        const gregInput = picker.querySelector('[data-shamsi-gregorian]');
        if (!shInput || !gregInput) return;
        gregInput.value = d.hire_date || '';
        const p = String(d.hire_date || '').split('-').map((x) => parseInt(x, 10));
        if (p.length === 3 && p[0] && !isNaN(p[0])) {
          const jj = toJalaliDate(p[0], p[1], p[2]);
          shInput.value = toFa(jj.y) + '/' + toFa(pad2(jj.m)) + '/' + toFa(pad2(jj.day));
        } else {
          shInput.value = '';
        }
      })();
      set('field_of_activity', d.field_of_activity);
      set('skills', d.skills);
      setCheck('is_current', d.is_current);
      // مختصات GPS بخش «ج» در گروه خودش بارگذاری می‌شود
      const wg = { lat: form.querySelector('[data-job-gps-lat]'), lng: form.querySelector('[data-job-gps-lng]'), acc: form.querySelector('[data-job-gps-acc]'), disp: form.querySelector('[data-job-gps-display]') };
      if (wg.lat && wg.lng && wg.disp) {
        const lat = (d.work_gps_latitude === null || d.work_gps_latitude === undefined || d.work_gps_latitude === '') ? null : Number(d.work_gps_latitude);
        const lng = (d.work_gps_longitude === null || d.work_gps_longitude === undefined || d.work_gps_longitude === '') ? null : Number(d.work_gps_longitude);
        const acc = (d.work_gps_accuracy === null || d.work_gps_accuracy === undefined || d.work_gps_accuracy === '') ? null : Number(d.work_gps_accuracy);
        wg.lat.value = (lat !== null && !isNaN(lat)) ? String(lat) : '';
        wg.lng.value = (lng !== null && !isNaN(lng)) ? String(lng) : '';
        if (wg.acc) wg.acc.value = (acc !== null && !isNaN(acc)) ? String(acc) : '';
        wg.disp.value = (lat !== null && lng !== null && !isNaN(lat) && !isNaN(lng)) ? (lat + ', ' + lng) : '';
      }
    }
  }
  if (editValues) {
    // انتخاب رادیوی مربوط به حالت ذخیره‌شده و پرکردن فیلدهای همان بخش.
    // پیش‌پرکردن فهرست سلسله‌مراتبی (کاتالوگ) هم در initJobCascade انجام می‌شود؛
    // اینجا فقط رادیو و بخشِ فعال تنظیم می‌شود تا ترتیب اجرا معتبر بماند.
    const saved = editValues.employment_mode || 'free';
    radios.forEach(function (r) { r.checked = (r.value === saved); });
    applyState();
  }

  // قفلِ گزینهٔ «الف) بدون شغل / بیکار هستم»: وقتی کاربر حداقل یک شغل ثبت‌شده
  // دارد (نشانهٔ سمت سرور: data-has-jobs روی body)، رادیوی «الف» باید همیشه
  // غیرفعال بماند — حتی اگر ادمین به یک شغلِ بیکار ویرایش بدهد یا کاربر شغل
  // تازه‌ای ثبت کند. علامت‌گذاریِ هر رادیو در فرم‌های شغل اعمال می‌شود.
  function enforceUnemployedLock() {
    const unemployedRadio = form.querySelector('[data-job-kind-radio="unemployed"]');
    if (!unemployedRadio) return;
    if ((document.body.dataset.hasJobs || '') === '1') {
      // حداقل یک شغل (آزاد/کارمندی) ثبت شده → «الف» قفل می‌ماند
      if (!unemployedRadio.disabled) {
        unemployedRadio.disabled = true;
        unemployedRadio.title = 'چون حداقل یک شغل ثبت کرده‌اید، گزینهٔ «بدون شغل» غیرفعال است.';
        // اگر به هر دلیل انتخابِ «الف» فعال شده بود، به «ب» بازگردانده می‌شود
        if (unemployedRadio.checked) {
          const freeRadio = form.querySelector('[data-job-kind-radio="free"]');
          if (freeRadio) { freeRadio.checked = true; applyState(); }
        }
      }
    } else if (unemployedRadio.disabled) {
      // همهٔ مشاغل حذف شده‌اند → «الف» دوباره فعال می‌شود (و پیش‌فرض انتخاب است)
      unemployedRadio.disabled = false;
      unemployedRadio.removeAttribute('title');
      unemployedRadio.checked = true;
      applyState();
    }
  }
  enforceUnemployedLock();

  radios.forEach(function (radio) {
    radio.addEventListener('change', function () {
      if (radio.checked) applyState();
    });
  });
  if (!editValues) applyState();

  // پس از افزودن/حذف شغل، «data-has-jobs» روی body عوض می‌شود؛ قفلِ رادیوی «الف»
  // به‌صورت زنده به‌روز می‌شود تا بدون رفرش صفحه درست بماند.
  window.addEventListener('hb:jobs-changed', enforceUnemployedLock);
  const obs = (window.MutationObserver) ? new MutationObserver(function () { enforceUnemployedLock(); }) : null;
  if (obs) obs.observe(document.body, { attributes: true, attributeFilter: ['data-has-jobs'] });

  // پاک‌سازیِ انتخاب‌های فهرست فقط هنگام «ارسال در حالت الف» انجام می‌شود؛ وگرنه
  // سرور آن را «انتخاب شغل واقعی» تفسیر می‌کند (اولویت انتخاب بر بیکار). ارسال
  // «تیکت» مستثناست تا انتخاب فعلی (حتی ناقص) همراه درخواست برای مدیر برود.
  form.addEventListener('submit', function (e) {
    if (mode() !== 'unemployed') return;
    const submitter = e.submitter
      || (document.activeElement && document.activeElement.tagName === 'BUTTON' ? document.activeElement : null);
    if (submitter && submitter.name === 'hb_job_action') return;
    ['sector_id', 'industry_id', 'category_id', 'occupation_title_id', 'specialization_id'].forEach(function (name) {
      const el = form.querySelector('[name="' + name + '"]');
      if (el) el.value = '';
    });
    const t = form.querySelector('[name="title"]');
    if (t) t.value = '';
  });

  // گزینهٔ «د) بدون تعریف اطلاعات شغلی»: زمانی قابل انتخاب است که کاربر هیچ شغلی
  // نداشته باشد؛ در غیر این صورت پنهان و غیرفعال می‌شود. در صورتی که همهٔ
  // مشاغل حذف شده‌اند، دوباره نمایش داده می‌شود تا کاربر بتواند حالت پیش‌فرض
  // خود را انتخاب کند.
  const uninitializedRadio = form.querySelector('[data-job-kind-radio="uninitialized"]');
  if (uninitializedRadio) {
    const updateUninitialized = () => {
      const n = form.querySelectorAll('[name="employment_kind"]:checked').length;
      const hasJobs = (document.body.dataset.hasJobs || '0') === '1';
      const show = n === 0 || !hasJobs;
      uninitializedRadio.disabled = !show;
      // کارت/برچسبِ گزینهٔ «د» هم همراه خودِ رادیو پنهان/نمایان می‌شود
      const kindCard = uninitializedRadio.closest('[data-job-kind-card]') || uninitializedRadio.closest('label');
      if (kindCard) kindCard.style.display = show ? '' : 'none';
      else uninitializedRadio.style.display = show ? '' : 'none';
      // «د» در پارسِ HTML برندهٔ checked است (آخرین رادیوی چک‌شدهٔ گروه)؛ اگر
      // پنهان شد ولی همچنان چک‌مانده بود، انتخاب به «ب) شغل آزاد» برمی‌گردد تا
      // فرم بدون حالتِ فعال نماند و فیلدهای هیچ بخشی قفلِ کامل نشود.
      if (!show && uninitializedRadio.checked) {
        uninitializedRadio.checked = false;
        const freeRadio = form.querySelector('[data-job-kind-radio="free"]');
        if (freeRadio && !freeRadio.disabled) freeRadio.checked = true;
        else {
          const empRadio = form.querySelector('[data-job-kind-radio="employee"]');
          if (empRadio) empRadio.checked = true;
        }
        applyState();
      }
    };
    updateUninitialized();
    form.addEventListener('change', () => {
      if (form.querySelector('[name="employment_kind"]:checked'))
        updateUninitialized();
    });
    window.addEventListener('hb:jobs-changed', updateUninitialized);
    const obs = (window.MutationObserver) ? new MutationObserver(updateUninitialized) : null;
    if (obs) obs.observe(document.body, { attributes: true, attributeFilter: ['data-has-jobs'] });
  }
}

// ---------- GPS محل کار (فرم شغل) + شمارش معکوس استتوس‌ها ----------
// «فیلد جدید GPS»: دکمهٔ «دریافت GPS» (Send your Current Location) مختصات سنسور
// موقعیت دستگاه را می‌گیرد و در فیلدهای پنهانِ فرم ثبت می‌کند؛ کاربر با ذخیرهٔ فرم،
// مختصات را به‌صورت مجزا برای همین شغل ثبت می‌کند (مستقل از محل سکونت و شغل‌های دیگر).
function toFaDigits(x) {
  return String(x).replace(/[0-9]/g, function (d) { return '۰۱۲۳۴۵۶۷۸۹'[+d]; });
}

function initJobGps() {
  const form = document.getElementById('job-form');
  if (!form) return;
  // دو گروه GPSِ مجزا: بخش «ج» (data-job-gps-*) و بخش «ب» (data-free-gps-*)؛
  // هر گروه دکمهٔ دریافت/پاک کردن و فیلدهای پنهان خودش را دارد.
  function wireGroup(sel) {
    const btn = form.querySelector('[' + sel + '-btn]');
    const clearBtn = form.querySelector('[' + sel + '-clear]');
    const display = form.querySelector('[' + sel + '-display]');
    const status = form.querySelector('[' + sel + '-status]');
    if (!btn || !display) return;

    const latInput = form.querySelector('[' + sel + '-lat]');
    const lngInput = form.querySelector('[' + sel + '-lng]');
    const accInput = form.querySelector('[' + sel + '-acc]');

    const setStatus = (text, color) => {
      if (status) {
        status.textContent = text;
        status.style.color = color || '';
      }
    };
    const setValues = (lat, lng, acc) => {
      if (latInput) latInput.value = (lat === null || lat === undefined) ? '' : String(lat);
      if (lngInput) lngInput.value = (lng === null || lng === undefined) ? '' : String(lng);
      if (accInput) accInput.value = (acc === null || acc === undefined) ? '' : String(acc);
      display.value = (lat === null || lat === undefined || lng === null || lng === undefined) ? '' : (lat + ', ' + lng);
    };

    btn.addEventListener('click', async () => {
      if (btn.disabled) return;
      btn.disabled = true;
      const orig = btn.innerHTML;
      btn.innerHTML = '<i class="bi bi-crosshair"></i> در حال دریافت…';
      setStatus('در حال دریافت موقعیت از GPS دستگاه…');
      const coord = await hbEnsureGps(); // گفتگوی فعال‌سازی GPS هم در صورت نیاز باز می‌شود
      btn.innerHTML = orig;
      btn.disabled = false;
      if (!coord) {
        setStatus('دسترسی به GPS ممکن نشد؛ مختصات ثبت نشد. می‌توانید دوباره تلاش کنید.', '#ff8a80');
        showToast('موقعیت GPS دریافت نشد.', 'warning');
        return;
      }
      setValues(coord.lat, coord.lng, coord.accuracy);
      const accTxt = coord.accuracy != null ? ' — دقت ±' + toFaDigits(coord.accuracy) + ' متر' : '';
      setStatus('مختصات GPS دریافت شد' + accTxt + '؛ همراه با ذخیرهٔ فرمِ شغل ثبت می‌شود.', 'var(--hb-success)');
      showToast('مختصات GPS محل کار دریافت شد.', 'success');
    });

    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        setValues(null, null, null);
        setStatus('مختصات پاک شد؛ در صورت ذخیرهٔ فرم، GPSِ جدید ثبت نمی‌شود.');
      });
    }

    return { setValues, setStatus };
  }

  const workGroup = wireGroup('data-job-gps');   // بخش «ج» (کارمندی)
  const freeGroup = wireGroup('data-free-gps');  // بخش «ب» (شغل آزاد)

  // حالت ویرایش: مختصات GPS ذخیره‌شدهٔ همین شغل در گروهِ بخشِ فعال بارگذاری می‌شود
  let editEl = null;
  try { editEl = document.getElementById('hb-job-edit-data'); } catch (e) { editEl = null; }
  if (editEl && form.hasAttribute('data-job-edit')) {
    try {
      const d = JSON.parse(editEl.textContent || 'null');
      if (d) {
        const isFree = (d.employment_mode === 'free');
        const g = isFree ? freeGroup : workGroup;
        const latRaw = isFree ? d.free_gps_latitude : d.work_gps_latitude;
        const lngRaw = isFree ? d.free_gps_longitude : d.work_gps_longitude;
        const accRaw = isFree ? d.free_gps_accuracy : d.work_gps_accuracy;
        if (g) {
          const lat = (latRaw === null || latRaw === undefined || latRaw === '') ? null : Number(latRaw);
          const lng = (lngRaw === null || lngRaw === undefined || lngRaw === '') ? null : Number(lngRaw);
          const acc = (accRaw === null || accRaw === undefined || accRaw === '') ? null : Number(accRaw);
          if (lat !== null && lng !== null && !isNaN(lat) && !isNaN(lng)) {
            g.setValues(lat, lng, (acc !== null && !isNaN(acc)) ? acc : null);
            g.setStatus('مختصات GPS ذخیره‌شدهٔ این شغل بارگذاری شد؛ می‌توانید دوباره دریافت یا پاک کنید.');
          }
        }
      }
    } catch (e) { /* دادهٔ ویرایش نامعتبر است — بی‌خیال */ }
  }
}

// پیش‌نمایش عکس پروفایل شغل هنگام انتخاب فایل در فرم افزودن
// handles both job_photo (job-specific) and photo (job/profile).
function initJobPhotoPreview() {
  const form = document.getElementById('job-form');
  if (!form) return;
  const inputs = form.querySelectorAll('.hb-job-photo-input');
  const preview = document.getElementById('hb-job-photo-preview');
  const empty = document.getElementById('hb-job-photo-empty');
  if (!preview) return;

  function refresh(file) {
    if (!file) {
      preview.style.display = 'none';
      preview.removeAttribute('src');
      if (empty) empty.style.display = '';
      return;
    }
    if (!file.type || file.type.indexOf('image/') !== 0) {
      preview.style.display = 'none';
      preview.removeAttribute('src');
      if (empty) empty.style.display = '';
      return;
    }
    const url = URL.createObjectURL(file);
    preview.src = url;
    preview.style.display = '';
    if (empty) empty.style.display = 'none';
  }

  inputs.forEach((input) => {
    if (input.tagName === 'SELECT') return;
    input.addEventListener('change', () => {
      refresh(input.files && input.files[0] ? input.files[0] : null);
    });
  });

  // هنگامی که فرم از سمت سرور برای ویرایش پر می‌شود، برای فیلد فعلی هم टکست (مؤقت)
  // گیر می‌کند تا پیش‌نمایش هم به‌روزرسانی شود.
  form.addEventListener('change', (e) => {
    if (e.target && e.target.classList.contains('hb-job-photo-input')) {
      const file = e.target.files && e.target.files[0];
      refresh(file ? file : null);
    }
  });
}

// ---------- اعتبارسنجی فیلدهای ستاره‌دار فرم شغل (بخش‌های «ب» و «ج») ----------
// فیلدهای ستاره‌دارِ بخش «ب) شغل آزاد» (استان/شهر-شهرستان/آدرس کامل محل کار) و
// بخش «ج) شغل وابسته (کارمندی)» (استان/شهر-شهرستان/آدرس محل کار سازمان) الزامی‌اند.
// در صورت خالی بودن هرکدام هنگام ارسال فرم:
//   ۱) پیام خطا «داخل همان فریم اطلاعات شغلی» (جعبهٔ #hb-job-error-box داخل فرم)
//      نمایش داده می‌شود — نه فقط پیام بالای صفحه؛
//   ۲) فیلد ناقص قرمز می‌شود و پیام کوتاه «الزامی بودن» زیر همان فیلد می‌نشیند؛
//   ۳) فریم اطلاعات شغلی (اگر بسته است) باز، و فوکوس + اسکرول روی نخستین فیلد
//      ناقص می‌رود و ارسال فرم متوقف می‌شود.
// حالت‌های «الف) بدون شغل» و «د) بدون تعریف» (بدون فیلد مکان) و ارسال
// «تیکت شغل یافت نشد» (hb_job_action=ticket) مستثنا هستند.
function initJobFormValidation() {
  const form = document.getElementById('job-form');
  if (!form) return;
  const jobsCard = document.getElementById('jobs');
  const errorBox = document.getElementById('hb-job-error-box');

  const mode = () => {
    const checked = form.querySelector('[data-job-kind-radio]:checked');
    return checked ? checked.value : 'free';
  };

  // فیلدهای ستاره‌دار هر بخش (برچسب‌ها همان متنِ کنار ستارهٔ قرمزِ فرم است)
  const REQUIRED_FIELDS = {
    free: [
      { name: 'free_province', label: 'استان محل کار (شغل آزاد)' },
      { name: 'free_city', label: 'شهر / شهرستان محل کار (شغل آزاد)' },
      { name: 'free_address', label: 'آدرس کامل محل کار (شغل آزاد)' },
    ],
    employee: [
      { name: 'work_province', label: 'استان محل کار (بخش ج — کارمندی)' },
      { name: 'work_city', label: 'شهر / شهرستان محل کار (بخش ج — کارمندی)' },
      { name: 'work_address', label: 'آدرس محل کار (بخش ج — کارمندی)' },
    ],
  };

  const isEmpty = (el) => !el || String(el.value || '').trim() === '';

  const clearFieldError = (item) => {
    const el = form.querySelector('[name="' + item.name + '"]');
    if (!el) return;
    el.classList.remove('hb-invalid-field');
    const group = el.closest('.hb-form-group');
    if (group) {
      const err = group.querySelector('.hb-field-error-js');
      if (err) err.remove();
    }
  };

  const hideErrorBox = () => {
    if (errorBox) {
      errorBox.style.display = 'none';
      errorBox.innerHTML = '';
    }
  };

  const clearAllErrors = () => {
    Object.keys(REQUIRED_FIELDS).forEach(function (k) {
      REQUIRED_FIELDS[k].forEach(clearFieldError);
    });
    hideErrorBox();
  };

  const markFieldError = (item) => {
    const el = form.querySelector('[name="' + item.name + '"]');
    if (!el) return null;
    el.classList.add('hb-invalid-field');
    const group = el.closest('.hb-form-group');
    if (group && !group.querySelector('.hb-field-error-js')) {
      const div = document.createElement('div');
      div.className = 'hb-field-error hb-field-error-js';
      div.innerHTML = '<i class="bi bi-exclamation-circle"></i> تکمیل این فیلد ستاره‌دار الزامی است.';
      group.appendChild(div);
    }
    return el;
  };

  // با اصلاحِ مقدار توسط کاربر، خطای همان فیلد پاک و ردیفِ آن از جعبهٔ خطای
  // فریم حذف می‌شود؛ جعبه وقتی بسته می‌شود که هیچ مورد ناقصی نمانده باشد.
  Object.keys(REQUIRED_FIELDS).forEach(function (k) {
    REQUIRED_FIELDS[k].forEach(function (item) {
      const el = form.querySelector('[name="' + item.name + '"]');
      if (!el) return;
      const clearIfFixed = () => {
        if (isEmpty(el)) return;
        clearFieldError(item);
        if (errorBox) {
          const li = errorBox.querySelector('li[data-field="' + item.name + '"]');
          if (li) li.remove();
          if (!errorBox.querySelector('li')) hideErrorBox();
        }
      };
      el.addEventListener('change', clearIfFixed);
      el.addEventListener('input', clearIfFixed);
    });
  });

  // تغییر «نوع ثبت شغل» (الف/ب/ج/د) → خطاهای فریم پاک می‌شود تا بخشِ تازه از
  // خطاهای بخش قبلی ارث نبرد.
  form.addEventListener('change', (e) => {
    if (e.target && e.target.matches && e.target.matches('[data-job-kind-radio]')) clearAllErrors();
  });

  form.addEventListener('submit', function (e) {
    // ارسال «تیکت شغل یافت نشد» از همین فرم انجام می‌شود و نباید متوقف شود
    const submitter = e.submitter
      || (document.activeElement && document.activeElement.tagName === 'BUTTON' ? document.activeElement : null);
    if (submitter && submitter.name === 'hb_job_action') return;

    const m = mode();
    const required = REQUIRED_FIELDS[m];
    if (!required) { clearAllErrors(); return; } // «الف»/«د»: بدون فیلد مکان

    const missing = required.filter((item) => isEmpty(form.querySelector('[name="' + item.name + '"]')));

    // خطاهای قبلی پاک می‌شوند تا فقط مواردِ فعلی نمایش داده شوند
    Object.keys(REQUIRED_FIELDS).forEach(function (k) {
      REQUIRED_FIELDS[k].forEach(clearFieldError);
    });

    if (!missing.length) { hideErrorBox(); return; }

    e.preventDefault();

    // ۱) پیام خطا داخل همان فریم اطلاعات شغلی (جعبهٔ بالای فرم)
    if (errorBox) {
      const sectionTitle = m === 'free' ? 'ب) شغل آزاد' : 'ج) شغل وابسته (کارمندی)';
      errorBox.innerHTML =
        '<i class="bi bi-exclamation-triangle"></i>' +
        '<div><b>تکمیل فیلدهای ستاره‌دار بخش «' + sectionTitle + '» الزامی است:</b>' +
        '<ul>' + missing.map((item) => '<li data-field="' + item.name + '">' + item.label + '</li>').join('') + '</ul></div>';
      errorBox.style.display = 'flex';
    }

    // ۲) قرمزکردن فیلدهای ناقص + پیام کوتاه زیر هر فیلد
    let firstEl = null;
    missing.forEach(function (item) {
      const el = markFieldError(item);
      if (el && !firstEl) firstEl = el;
    });

    // ۳) بازکردن فریم اطلاعات شغلی (اگر بسته است) + فوکوس و اسکرول به نخستین فیلد ناقص
    if (jobsCard && !jobsCard.classList.contains('active')) jobsCard.classList.add('active');
    if (firstEl) {
      try { firstEl.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (err) { firstEl.scrollIntoView(); }
      setTimeout(() => {
        try { firstEl.focus({ preventScroll: true }); } catch (err) { firstEl.focus(); }
      }, 250);
    }
  });
}

// ---------- نوار «اخبار فوری» هدر (ماژول ادمین: BreakingNews) ----------
// پخشِ متن‌های خبریِ فقط‌خواندنی به‌صورت خطی و متحرک (حرکت از چپ به راست) در هدر.
// چند خبرِ فعال به‌ترتیب پشت‌سرهم پخش می‌شوند؛ سرعتِ هر خبر (ثانیه برای هر دور)
// از تنظیم ادمین می‌آید. داده‌ها از context processor (hb-news-data) می‌آید و هر
// ۶۰ ثانیه دوباره از سرور خوانده می‌شود تا خبرِ تازه/منقضی‌شده خودکار به‌روز شود.
function initNewsTicker() {
  const dataEl = document.getElementById('hb-news-data');
  const ticker = document.querySelector('[data-news-ticker]');
  if (!dataEl || !ticker) return;

  let items = [];
  try { items = JSON.parse(dataEl.textContent || '[]') || []; } catch (e) { items = []; }
  if (!items.length) { ticker.style.display = 'none'; return; }

  const textEl = ticker.querySelector('[data-news-text]');
  if (!textEl) return;

  // بازچرخشِ آرامِ هر خبر با requestAnimationFrame؛ سرعت = ثانیه برای هر دور
  let itemIndex = 0;
  let rafId = null;
  let startTs = null;

  const playCurrent = () => {
    const item = items[itemIndex % items.length];
    const speedSec = Math.min(120, Math.max(5, parseInt(item.speed, 10) || 30));
    textEl.textContent = item.text || '';
    const distance = textEl.offsetWidth + ticker.querySelector('.hb-news-ticker-viewport').offsetWidth;
    textEl.style.transform = 'translateX(-' + distance + 'px)'; // شروع: بیرونِ سمت چپ
    startTs = null;
    if (rafId) cancelAnimationFrame(rafId);
    const step = (ts) => {
      if (startTs === null) startTs = ts;
      const progress = Math.min((ts - startTs) / (speedSec * 1000), 1);
      // از چپ (خارج دید) به راست (خارج دید): حرکت از چپ به راست
      textEl.style.transform = 'translateX(' + (-distance + distance * 2 * progress) + 'px)';
      if (progress < 1) {
        rafId = requestAnimationFrame(step);
      } else {
        itemIndex += 1;
        playCurrent(); // خبر بعدی (پشت‌سرهم)
      }
    };
    rafId = requestAnimationFrame(step);
  };

  playCurrent();

  // به‌روزرسانیِ دوره‌ای فهرست خبرهای فعال (بدون رفرش صفحه)
  setInterval(() => {
    fetch(window.location.pathname, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then((r) => r.text())
      .then((html) => {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const fresh = doc.getElementById('hb-news-data');
        if (!fresh) return;
        const next = JSON.parse(fresh.textContent || '[]');
        const sig = JSON.stringify(next);
        if (sig !== JSON.stringify(items)) {
          items = next;
          if (!items.length) { ticker.style.display = 'none'; return; }
          ticker.style.display = '';
          itemIndex = 0;
          playCurrent();
        }
      })
      .catch(() => { /* بی‌صدا */ });
  }, 60000);
}

// استتوس‌های ۲۴ ساعته: شمارش معکوسِ زنده تا انقضا؛ صفر شدن، ردیف را خاکستری و
// متن آن را «منقضی شد» می‌کند (حذف نهایی سمت سرور/پاکسازی تنبل انجام می‌شود).
function initJobStatusCountdowns() {
  const nodes = document.querySelectorAll('[data-status-countdown]');
  if (!nodes.length) return;
  const fmt = (s) => {
    if (s >= 3600) {
      const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
      return toFaDigits(h) + ' ساعت و ' + toFaDigits(m) + ' دقیقه دیگر';
    }
    if (s >= 60) return toFaDigits(Math.floor(s / 60)) + ' دقیقه دیگر';
    return toFaDigits(Math.max(s, 0)) + ' ثانیه دیگر';
  };
  const tick = () => {
    const now = Date.now();
    nodes.forEach((el) => {
      if (el.dataset.statusDone === '1') return;
      const exp = el.getAttribute('data-status-expires');
      const t = exp ? Date.parse(exp) : NaN;
      if (isNaN(t)) return;
      const left = Math.floor((t - now) / 1000);
      if (left <= 0) {
        el.textContent = 'منقضی شد';
        const card = el.closest('.hb-status-card');
        if (card) card.style.opacity = '0.4';
        el.dataset.statusDone = '1';
        return;
      }
      el.textContent = fmt(left);
    });
  };
  tick();
  setInterval(tick, 30000);
}

// ---------- کش سبک سمت کلاینت برای جستجوی نام‌ها ----------
// جستجوهای تکراری برای یک عبارت/نوع/جنسیتِ یکسان دوباره به سرور فرستاده نمی‌شوند؛
// نتیجه برای مدت کوتاهی (TTL) در حافظهٔ مرورگر می‌ماند و وقتی تعداد ورودی‌ها از سقف
// گذشت، قدیمی‌ترین ورودی حذف می‌شود. کلید شامل kind/gender است تا پدر/مادر با
// جنسیت متفاوت، کش جداگانه داشته باشند.
const HB_NAME_CACHE_TTL_MS = 5 * 60 * 1000; // ۵ دقیقه
const HB_NAME_CACHE_MAX = 120;
const hbNameSearchCache = new Map();

function hbNameCacheGet(key) {
  const entry = hbNameSearchCache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.at > HB_NAME_CACHE_TTL_MS) {
    hbNameSearchCache.delete(key);
    return null;
  }
  return entry.results;
}

function hbNameCacheSet(key, results) {
  if (hbNameSearchCache.size >= HB_NAME_CACHE_MAX) {
    // ساده: قدیمی‌ترین (اولین) ورودی حذف می‌شود
    const firstKey = hbNameSearchCache.keys().next().value;
    if (firstKey !== undefined) hbNameSearchCache.delete(firstKey);
  }
  hbNameSearchCache.set(key, { at: Date.now(), results: results });
}

// ---------- انتخاب‌گر خودکار نام‌ها (جستجوی زنده در دیتابیس) ----------
// فیلدهای نامِ جدول‌های مرجع (هزاران گزینه) با یک جعبهٔ متنیِ قابل‌تایپ جایگزین
// می‌شوند: کاربر بخشی از نام را تایپ می‌کند (مکان‌نما هنگام نوشتن داخل جعبه است)
// و هر بار یک Query واقعی به سرور فرستاده می‌شود (accounts:name_search)؛ نتیجه به
//‌صورت فهرست پیشنهادی زیر جعبه می‌آید و با کلیک یا کیبورد (↑/↓/Enter/Esc) انتخاب
// می‌شود. مقدار نهایی داخل همان <select> اصلی (پنهان) قرار می‌گیرد تا فرم و
// اعتبارسنجی سرور دست‌نخورده بماند؛ بدون JS خودِ <select> (فهرست کامل) نمایش داده
// می‌شود. attributes: data-hb-kind (first|family)، data-hb-gender (male|female|'')
//
// دو قابلیت اضافه:
//  ۱) «نشانگر مقدار انتخابی»: زیر هر فیلد نام، مقدارِ انتخاب‌شده به‌صورت متن فارسی
//     به‌همراه لاتین (مثلاً «علی (Ali)») نمایش داده می‌شود تا کاربر مقدارِ ثبت‌شده
//     را پیش از ذخیره هم ببیند. با ویرایش دستیِ جعبه، نشانگر پنهان می‌شود.
//  ۲) «کش سمت کلاینت»: نتایج جستجو برای عبارت‌های تکراری (hbNameCacheGet/Set).
function initNameAutocomplete() {
  document.querySelectorAll('select.hb-name-select').forEach(function (sel) {
    if (sel.dataset.hbNameAutocomplete) return;
    sel.dataset.hbNameAutocomplete = '1';

    const kind = sel.getAttribute('data-hb-kind') || 'first';
    const gender = sel.getAttribute('data-hb-gender') || '';
    const hint = sel.getAttribute('data-hb-filter-hint') || 'تایپ کنید و از فهرست انتخاب کنید…';
    // kindهای ممکن: first (نام‌ها)، family (نام‌های خانوادگی)، fame (شهرت‌ها)
    const url = '/accounts/names/search/';

    const wrap = document.createElement('div');
    wrap.className = 'hb-autocomplete';

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'hb-form-control hb-autocomplete-input';
    input.autocomplete = 'off';
    input.placeholder = hint;
    input.dir = 'rtl';
    input.setAttribute('aria-autocomplete', 'list');

    const list = document.createElement('div');
    list.className = 'hb-autocomplete-list';
    list.hidden = true;
    list.setAttribute('role', 'listbox');

    wrap.appendChild(input);
    wrap.appendChild(list);
    sel.parentNode.insertBefore(wrap, sel);
    wrap.appendChild(sel); // <select> داخل کانتینر می‌ماند (ارسال فرم + بدون JS)
    sel.classList.add('hb-autocomplete-native'); // با JS پنهان می‌شود (CSS)

    // --- نشانگر «مقدار انتخابی» زیر فیلد (فارسی + لاتین) ---
    // تا کاربر مقدارِ واقعاً انتخاب‌شده/ذخیره‌شده را پیش از ارسال فرم هم ببیند.
    const readout = document.createElement('div');
    readout.className = 'hb-autocomplete-readout';
    readout.hidden = true;
    readout.setAttribute('role', 'status');
    readout.setAttribute('aria-live', 'polite');

    // برچسب «علی (Ali)» را به فارسی و لاتین جدا می‌کند (بدون لاتین هم کار می‌کند)
    function parseBilingual(text) {
      const raw = String(text || '').trim();
      if (!raw || raw === '---------' || raw === '---') return null;
      const m = raw.match(/^(.*?)\s*\(([^()]*)\)$/);
      if (m && String(m[2]).trim()) {
        return { fa: String(m[1]).trim(), en: String(m[2]).trim() };
      }
      return { fa: raw, en: '' };
    }

    function showReadout(item) {
      const fa = (item && item.fa) ? String(item.fa).trim() : '';
      const en = (item && item.en) ? String(item.en).trim() : '';
      if (!fa && !en) { hideReadout(); return; }
      readout.innerHTML = '';
      const icon = document.createElement('i');
      icon.className = 'bi bi-check-circle-fill';
      readout.appendChild(icon);
      const main = document.createElement('span');
      main.textContent = fa;
      readout.appendChild(main);
      if (en) {
        const latin = document.createElement('small');
        latin.dir = 'ltr';
        latin.textContent = en;
        readout.appendChild(latin);
      }
      readout.hidden = false;
    }

    function hideReadout() {
      readout.hidden = true;
      readout.innerHTML = '';
    }

    // هنگام بارگذاری اولیه (ویرایش پروفایل): مقدارِ ثبت‌شدهٔ قبلی نشان داده می‌شود
    function readoutFromSelect() {
      const opt = sel.options[sel.selectedIndex];
      if (!opt || String(opt.value) === '') { hideReadout(); return; }
      const parts = parseBilingual(opt.text);
      if (!parts) { hideReadout(); return; }
      showReadout(parts);
    }

    wrap.appendChild(readout);

    // مقدار اولیه (مثلاً هنگام ویرایش پروفایل): برچسب انتخابِ فعلی در جعبه نمایش داده می‌شود
    const selected = sel.options[sel.selectedIndex];
    if (selected && String(selected.value) !== '') {
      input.value = selected.text.trim();
    }
    readoutFromSelect();

    // باز شدن فهرست هنگام کلیک/فوکوس — مثل منوی کشویی «استان» که با کلیک باز می‌شود؛
    // اگر جعبه خالی باشد فهرستِ اولیه از گزینه‌های خودِ <select> (بدون درخواست شبکه)
    // و اگر مقداری داشته باشد (مثلاً «علی (Ali)») همان مقدار به‌عنوان فیلتر به کار می‌رود.
    function openList() {
      const raw = input.value.trim();
      const needle = raw.replace(/\s*\([^()]*\)\s*$/, '').trim().toLowerCase();
      const items = [];
      for (let i = 1; i < sel.options.length && items.length < 30; i++) {
        const opt = sel.options[i];
        const parts = parseBilingual(opt.text);
        if (!parts) continue;
        if (needle) {
          const fa = parts.fa.toLowerCase();
          const en = parts.en.toLowerCase();
          if (fa.indexOf(needle) === -1 && en.indexOf(needle) === -1) continue;
        }
        items.push({ id: opt.value, fa: parts.fa, en: parts.en, label: opt.text.trim() });
      }
      if (items.length) render(items);
    }

    input.addEventListener('focus', function () {
      input.select();
      openList();
    });
    input.addEventListener('click', function () {
      if (list.hidden) openList();
    });

    let timer = null;
    let controller = null;
    let activeIndex = -1;
    let lastQuery = null;

    function close() {
      list.hidden = true;
      list.innerHTML = '';
      activeIndex = -1;
    }

    function setValue(item) {
      sel.value = item.id;
      input.value = item.label;
      sel.dispatchEvent(new Event('change', { bubbles: true }));
      showReadout(item);
      close();
    }

    function setActive(i) {
      activeIndex = i;
      const rows = list.querySelectorAll('.hb-autocomplete-item');
      rows.forEach(function (r, idx) {
        r.classList.toggle('active', idx === i);
      });
      const cur = rows[i];
      if (cur) cur.scrollIntoView({ block: 'nearest' });
    }

    function render(items) {
      list.innerHTML = '';
      if (!items.length) {
        const empty = document.createElement('div');
        empty.className = 'hb-autocomplete-empty';
        empty.textContent = 'موردی یافت نشد — اگر نام خود را نیافتید با ادمین هماهنگ کنید';
        list.appendChild(empty);
      } else {
        items.forEach(function (item, i) {
          const row = document.createElement('div');
          row.className = 'hb-autocomplete-item';
          row.setAttribute('role', 'option');
          row._hbItem = item;
          const en = item.en ? '<small>' + item.en + '</small>' : '';
          row.innerHTML = '<span>' + item.fa + '</span>' + en;
          row.addEventListener('mousedown', function (e) {
            e.preventDefault(); // blur را جلو بیندازد تا کلیک از دست نرود
            setValue(item);
          });
          row.addEventListener('mouseenter', function () {
            setActive(i);
          });
          list.appendChild(row);
        });
        setActive(0);
      }
      list.hidden = false;
    }

    async function search(force) {
      const q = input.value.trim();
      if (timer) { clearTimeout(timer); timer = null; }
      if (!force && q === lastQuery) return;
      lastQuery = q;
      if (!q) {
        // خالی کردن جعبه = انتخاب قبلی باطل می‌شود (مقدار ناخواسته ارسال نشود)
        if (sel.value !== '') {
          sel.value = '';
          sel.dispatchEvent(new Event('change', { bubbles: true }));
        }
        hideReadout();
        close();
        return;
      }
      const cacheKey = kind + '\u0000' + gender + '\u0000' + q;
      const cached = hbNameCacheGet(cacheKey);
      if (cached) {
        if (input.value.trim() !== q) return; // کاربر در بین راه بیشتر تایپ کرده
        render(cached);
        return;
      }
      if (controller) controller.abort();
      controller = new AbortController();
      list.innerHTML = '';
      const loading = document.createElement('div');
      loading.className = 'hb-autocomplete-empty';
      loading.textContent = 'در حال جستجو…';
      list.appendChild(loading);
      list.hidden = false;
      try {
        const resp = await fetch(
          url + '?q=' + encodeURIComponent(q) + '&kind=' + encodeURIComponent(kind) + '&gender=' + encodeURIComponent(gender),
          { signal: controller.signal }
        );
        if (!resp.ok) throw new Error('http ' + resp.status);
        const data = await resp.json();
        const results = data.results || [];
        hbNameCacheSet(cacheKey, results);
        if (input.value.trim() !== q) return; // کاربر در بین راه بیشتر تایپ کرده
        render(results);
      } catch (err) {
        if (err.name !== 'AbortError') {
          list.innerHTML = '';
          const empty = document.createElement('div');
          empty.className = 'hb-autocomplete-empty';
          empty.textContent = 'خطا در جستجو — دوباره تلاش کنید';
          list.appendChild(empty);
        }
      }
    }

    input.addEventListener('input', function () {
      // هر ویرایش دستی، انتخاب قبلی را باطل می‌کند تا چیزی ناخواسته ارسال نشود
      sel.value = '';
      hideReadout();
      if (timer) clearTimeout(timer);
      timer = setTimeout(function () { search(false); }, 200);
    });

    input.addEventListener('keydown', function (e) {
      const rows = function () { return list.querySelectorAll('.hb-autocomplete-item'); };
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const r = rows();
        if (!list.hidden && r.length) setActive((activeIndex + 1) % r.length);
        else search(true);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const r = rows();
        if (!list.hidden && r.length) setActive((activeIndex - 1 + r.length) % r.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const r = rows();
        if (!list.hidden && r[activeIndex] && r[activeIndex]._hbItem) {
          setValue(r[activeIndex]._hbItem);
        } else {
          search(true); // بدون انتخاب، Enter فقط فهرست را به‌روز می‌کند
        }
      } else if (e.key === 'Escape') {
        close();
      }
    });

    input.addEventListener('blur', function () {
      // کمی صبر تا کلیک روی آیتم‌ها فرصت داشته باشد (mousedown جلوتر از blur است)
      setTimeout(close, 150);
    });
  });
}

// ---------- انتخاب‌گر خودکار کشور/استان/شهرستان (اطلاعات مکانی) ----------
// فیلدهای «اطلاعات مکانی» پروفایل (کشور/استان/شهر) با تایپِ کاربر، جدول‌های مرجع
// (CountryTbl/ProvinceTbl/CityTbl که ادمین از ماژول «اطلاعات مکانی» پنل مدیریت
// تکمیل می‌کند) را با یک Query واقعی جستجو می‌کنند (accounts:location_search) و
// نتیجه به‌صورت فهرست پیشنهادی زیر همان جعبهٔ متنی می‌آید؛ کاربر با کلیک یا کیبورد
// انتخاب می‌کند و مقدارِ رسمی (نام فارسیِ رکورد مرجع) داخل همان جعبه نوشته می‌شود
// تا در Profile.country/province/city ذخیره شود.
//
// چون خودِ فیلدها متن‌اند (نه FK)، جریان GPS/نقشه که مقدار را مستقیم در جعبه می‌نویسد
// دست‌نخورده می‌ماند. فهرست «استان» با کشورِ بالادست و «شهرستان» با استانِ بالادست
// کوتاه می‌شود (فقط وقتی مقدارِ بالادست در جدول مرجع باشد). از همان کش سمت کلاینتِ
// جستجوی نام‌ها استفاده می‌شود تا جستجوهای تکراری دوباره به سرور نروند.
// ---------- بج‌ها/ویجت‌های «مکان»: نمایش با زبان فعال ----------
// مقدارِ ذخیره‌شدهٔ نام‌های مکان فارسی است (کشور/استان/شهرستان و تابعیت/ملیت/
// اقامت دائم) و نسخهٔ انگلیسیِ هم‌ارز کنارش در data-loc-en می‌نشیند؛ با تغییر زبان
// رابط، متنِ بج‌های خلاصه، ویجتِ موقعیت، فهرستِ محل کارِ شغل‌ها و فیلدهای ثابتِ
// کشور هم‌زمان عوض می‌شود (فارسی پیش‌فرض، انگلیسی وقتی زبانِ رابط en است). روی
// ورودی‌ها (فیلدِ ثابتِ کشور) مقدار عوض می‌شود.
function applyLocationValues(lang) {
  document.querySelectorAll('[data-loc-fa]').forEach(function (el) {
    const fa = el.getAttribute('data-loc-fa') || '';
    const en = el.getAttribute('data-loc-en') || '';
    const show = (lang === 'en' && en) ? en : fa;
    if (el.tagName === 'INPUT') {
      el.value = show || el.value;
    } else {
      el.textContent = show || el.textContent;
    }
  });
}

// ---------- فهرست‌های انتخابی دوزبانه (استان/شهرستان و ...) ----------
// گزینه‌های <select data-bilingual> برچسب فارسی دارند و روی هر گزینه
// data-fa/data-en می‌نشیند؛ با تغییر زبان، برچسبِ گزینه‌ها عوض می‌شود (مقدارِ
// ارسالی همچنان فارسی است). برچسبِ <optgroup> شهرستان‌ها نامِ فارسیِ استان است؛
// نام فارسی در data-fa نگه داشته می‌شود و نسخهٔ انگلیسی از گزینهٔ هم‌نامِ فهرستِ
// «استان» همان فرم خوانده می‌شود تا آبشار (initLocationCascade) با data-fa و
// بدون وابستگی به برچسبِ نمایشیِ ترجمه‌شده کار کند.
function applyBilingualSelects(lang) {
  document.querySelectorAll('select[data-bilingual]').forEach(function (sel) {
    Array.prototype.forEach.call(sel.options, function (opt) {
      if (String(opt.value) === '') return;
      opt.textContent = (lang === 'en' && opt.dataset.en)
        ? opt.dataset.en
        : (opt.dataset.fa || opt.textContent);
    });
    Array.prototype.forEach.call(sel.querySelectorAll('optgroup'), function (group) {
      let fa = group.getAttribute('data-fa');
      if (!fa) {
        fa = group.getAttribute('label') || '';
        group.setAttribute('data-fa', fa);
      }
      if (!fa) return;
      let en = group.getAttribute('data-en') || '';
      if (!en && sel.classList.contains('hb-loc-city')) {
        const form = sel.closest('form');
        const provSel = form && form.querySelector('select.hb-loc-province');
        if (provSel) {
          Array.prototype.forEach.call(provSel.options, function (o) {
            if (o.getAttribute('data-fa') === fa) en = o.getAttribute('data-en') || '';
          });
        }
      }
      group.setAttribute('label', (lang === 'en' && en) ? en : fa);
    });
  });
}

// ---------- Country Select (تابعیت/ملیت/اقامت دائم): دو زبانه + جستجوی تایپی ----------
// منوی کشویی کشورها (<select class='hb-country-select'> با همهٔ گزینه‌ها) به یک
// جستجوگر تایپیِ سمت کلاینت تبدیل می‌شود؛ مقدارِ ذخیره‌شده همان نام فارسی است و
// برچسب هر گزینه (data-fa / data-en) هنگام تغییر زبان عوض می‌شود (فارسی پیش‌فرض،
// انگلیسی وقتی زبان رابط انگلیسی است). بدون JS هم <select> معمولی ارسال می‌شود.
function applyCountryLabels(lang) {
  document.querySelectorAll('select.hb-country-select').forEach(function (sel) {
    Array.prototype.forEach.call(sel.options, function (opt) {
      if (String(opt.value) === '') return;
      opt.textContent = (lang === 'en' && opt.dataset.en)
        ? opt.dataset.en
        : (opt.dataset.fa || opt.textContent);
    });
    // جعبهٔ جستجو نیز برچسبِ مقدارِ انتخابی را به زبانِ تازه نشان می‌دهد
    const wrap = sel.closest('.hb-autocomplete');
    const input = wrap && wrap.querySelector('.hb-autocomplete-input');
    const selected = sel.options[sel.selectedIndex];
    if (input && selected && String(selected.value) !== '') {
      input.value = selected.textContent.trim();
    }
  });
}

function initEducationCascade() {
  const form = document.querySelector('[data-education-form]');
  if (!form) return;

  const degreeField = form.querySelector('select[name="degree"]');
  const institutionRow = document.getElementById('hb-education-institution-row');
  const fieldRow = document.getElementById('hb-education-field-row');
  const specField = form.querySelector('select[name="study_specialization"]');
  const fieldField = form.querySelector('select[name="study_field"]');
  const institutionField = form.querySelector('select[name="education_institution"]');

  if (degreeField) {
    degreeField.addEventListener('change', () => {
      const degree = degreeField.value;
      // اگر دیپلم باشد، فیلدهای دانشگاه و رشته غیرفعال می‌شوند
      const isDiploma = degree === 'دیپلم';
      if (institutionRow) {
        institutionRow.style.opacity = isDiploma ? '0.4' : '1';
        institutionRow.style.pointerEvents = isDiploma ? 'none' : 'auto';
      }
      if (fieldRow) {
        fieldRow.style.opacity = isDiploma ? '0.4' : '1';
        fieldRow.style.pointerEvents = isDiploma ? 'none' : 'auto';
      }
      // اگر دیپلم انتخاب شد، مقادیر قبلی پاک شوند
      if (isDiploma) {
        if (institutionField) institutionField.value = '';
        if (fieldField) fieldField.value = '';
        if (specField) specField.value = '';
      }
    });
    // اجرا اولیه: اگر قبلاً دیپلم انتخاب شده باشد
    if (degreeField.value === 'دیپلم') {
      degreeField.dispatchEvent(new Event('change'));
    }
  }

  // آبشاری گروه امتحانی ← رشته: با تغییر گروه، فهرست رشته‌ها با fetch تازه
  // می‌شود (فقط رشته‌های فعال همان گروه؛ بدون گروه = همهٔ رشته‌ها). گروه‌بندی
  // <optgroup> حفظ می‌شود تا بدون JS هم فهرست مرتب بماند.
  const groupField = form.querySelector('select[name="study_group"]');
  if (groupField && fieldField) {
    const emptyFieldLabel = '— انتخاب کنید —';
    let fieldsFetchInProgress = false;
    const loadFields = function (keepFieldId) {
      const groupId = groupField.value || '';
      if (fieldsFetchInProgress) return;
      fieldsFetchInProgress = true;
      fieldField.disabled = true;
      fieldField.innerHTML = '<option value="">در حال بارگذاری…</option>';
      const url = '/accounts/education/fields/' + (groupId ? ('?group_id=' + encodeURIComponent(groupId)) : '');
      fetch(url)
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          const results = data.results || [];
          let html = '<option value="">' + emptyFieldLabel + '</option>';
          const byGroup = {};
          results.forEach(function (f) {
            const gid = f.group_id == null ? 'none' : String(f.group_id);
            (byGroup[gid] = byGroup[gid] || []).push(f);
          });
          // گروه‌های شناخته‌شده به ترتیبِ خودشان؛ هر گروه برچسبِ optgroup خودش را دارد
          Array.prototype.forEach.call(groupField.options, function (opt) {
            if (String(opt.value) === '') return;
            const items = byGroup[opt.value];
            if (!items || !items.length) return;
            html += '<optgroup label="' + opt.textContent.trim().replace(/"/g, '&quot;') + '">';
            items.forEach(function (f) {
              html += '<option value="' + f.id + '">' + f.label.replace(/"/g, '&quot;') + '</option>';
            });
            html += '</optgroup>';
          });
          // رشته‌های بدون گروهِ شناخته‌شده (احتیاط)
          const orphans = byGroup['none'] || [];
          if (orphans.length) {
            html += '<optgroup label="بدون گروه">';
            orphans.forEach(function (f) {
              html += '<option value="' + f.id + '">' + f.label.replace(/"/g, '&quot;') + '</option>';
            });
            html += '</optgroup>';
          }
          fieldField.innerHTML = html;
          fieldField.disabled = false;
          if (keepFieldId && results.some(function (f) { return String(f.id) === String(keepFieldId); })) {
            fieldField.value = String(keepFieldId);
          } else {
            fieldField.value = '';
          }
          // فهرست گرایش‌ها هم باید با رشتهٔ (نو) هماهنگ شود
          fieldField.dispatchEvent(new Event('change', { bubbles: true }));
        })
        .catch(function () {
          fieldField.disabled = false;
          fieldField.innerHTML = '<option value="">' + emptyFieldLabel + '</option>';
        })
        .finally(function () {
          fieldsFetchInProgress = false;
        });
    };
    groupField.addEventListener('change', function () {
      loadFields(null);
    });
    // بارگذاری اولیه: اگر پروفایل رشتهٔ ذخیره‌شده دارد، فهرست با همان رشته ساخته شود
    if (groupField.value || fieldField.value) {
      loadFields(fieldField.value || null);
    }
  }

  // آبشاری رشته ← گرایش: وقتی رشته تغییر کند گرایش‌های مجاز fetch می‌شوند
  if (fieldField && specField) {
    let specFetchInProgress = false;
    fieldField.addEventListener('change', () => {
      const fieldId = fieldField.value;
      // Disable while fetching
      if (fieldId === '') {
        specField.innerHTML = '<option value="">— بدون گرایش / انتخاب کنید —</option>';
        specField.value = '';
        specField.disabled = false;
        return;
      }
      if (specFetchInProgress) return;
      specFetchInProgress = true;
      specField.disabled = true;
      specField.innerHTML = '<option value="">در حال بارگذاری…</option>';
      fetch(`/accounts/education/specializations/?field_id=${encodeURIComponent(fieldId)}`)
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          const results = data.results || [];
          let html = '<option value="">— بدون گرایش / انتخاب کنید —</option>';
          results.forEach(function (spec) {
            html += `<option value="${spec.id}">${spec.label}</option>`;
          });
          specField.innerHTML = html;
          specField.disabled = results.length === 0;
          // If previously selected specialization no longer belongs to this field, clear it
          const prevSpecId = specField.dataset.prevSpecId;
          if (prevSpecId && results.length > 0 && !results.some(function (s) { return String(s.id) === prevSpecId; })) {
            specField.value = '';
          }
        })
        .catch(function () {
          specField.innerHTML = '<option value="">— بدون گرایش / انتخاب کنید —</option>';
          specField.disabled = false;
        })
        .finally(function () {
          specFetchInProgress = false;
        });
    });
    // Save previously selected specialization ID before re-rendering
    specField.addEventListener('change', () => {
      if (specField.value) {
        specField.dataset.prevSpecId = specField.value;
      }
    });
  }
}

function initCountrySelect() {
  document.querySelectorAll('select.hb-country-select').forEach(function (sel) {
    if (sel.dataset.hbCountryDone) return;
    sel.dataset.hbCountryDone = '1';

    const wrap = document.createElement('div');
    wrap.className = 'hb-autocomplete';
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'hb-form-control hb-autocomplete-input';
    input.autocomplete = 'off';
    input.dir = 'rtl';
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-expanded', 'false');
    const list = document.createElement('div');
    list.className = 'hb-autocomplete-list';
    list.hidden = true;
    list.setAttribute('role', 'listbox');

    wrap.appendChild(input);
    wrap.appendChild(list);
    sel.parentNode.insertBefore(wrap, sel);
    wrap.appendChild(sel);
    sel.classList.add('hb-autocomplete-native');

    // مقدارِ انتخاب‌شده/ذخیره‌شده از ابتدا داخل جعبه دیده شود
    const selected = sel.options[sel.selectedIndex];
    if (selected && String(selected.value) !== '') {
      input.value = selected.textContent.trim();
    }

    let activeIndex = -1;

    function currentLabel(opt) {
      return (currentLang === 'en' && opt.dataset.en)
        ? opt.dataset.en
        : (opt.dataset.fa || opt.textContent);
    }

    function matches(opt, q) {
      const needle = String(q || '').trim().toLowerCase();
      if (!needle) return true;
      const fa = String(opt.dataset.fa || '').toLowerCase();
      const en = String(opt.dataset.en || '').toLowerCase();
      return fa.indexOf(needle) !== -1 || en.indexOf(needle) !== -1;
    }

    function close() {
      list.hidden = true;
      list.innerHTML = '';
      activeIndex = -1;
      input.setAttribute('aria-expanded', 'false');
    }

    function pick(opt) {
      sel.value = opt.value;
      input.value = currentLabel(opt);
      sel.dispatchEvent(new Event('change', { bubbles: true }));
      close();
    }

    function setActive(i) {
      const rows = list.querySelectorAll('.hb-autocomplete-item');
      if (!rows.length) { activeIndex = -1; return; }
      if (i < 0) i = 0;
      if (i >= rows.length) i = rows.length - 1;
      activeIndex = i;
      rows.forEach(function (r, idx) { r.classList.toggle('active', idx === i); });
      rows[i].scrollIntoView({ block: 'nearest' });
    }

    function render(q) {
      list.innerHTML = '';
      activeIndex = -1;
      let shown = 0;
      Array.prototype.forEach.call(sel.options, function (opt) {
        if (String(opt.value) === '') return;
        if (!matches(opt, q)) return;
        const row = document.createElement('div');
        row.className = 'hb-autocomplete-item';
        row.setAttribute('role', 'option');
        row._hbCountryOpt = opt;
        const main = document.createElement('span');
        main.textContent = currentLabel(opt);
        row.appendChild(main);
        if (opt.dataset.en) {
          const sm = document.createElement('small');
          sm.textContent = opt.dataset.en;
          row.appendChild(sm);
        }
        row.addEventListener('mousedown', function (e) {
          e.preventDefault(); // تا blur جعبه پیش از کلیک بسته نشود
          pick(opt);
        });
        row.addEventListener('mouseenter', function () { setActive(shown); });
        list.appendChild(row);
        shown++;
      });
      if (!shown) {
        const empty = document.createElement('div');
        empty.className = 'hb-autocomplete-empty';
        empty.textContent = 'کشوری یافت نشد';
        list.appendChild(empty);
      }
      list.hidden = false;
      input.setAttribute('aria-expanded', 'true');
    }

    input.addEventListener('focus', function () {
      input.select();
      if (!String(input.value).trim()) render('');
    });
    input.addEventListener('input', function () { render(input.value); });
    input.addEventListener('blur', function () {
      // بدون انتخاب، برچسبِ مقدارِ ذخیره‌شده برمی‌گردد
      const selOpt = sel.options[sel.selectedIndex];
      if (selOpt && String(selOpt.value) !== '') {
        input.value = currentLabel(selOpt);
      }
      setTimeout(close, 120);
    });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); render(input.value); setActive(activeIndex + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); render(input.value); setActive(activeIndex - 1); }
      else if (e.key === 'Enter') {
        const row = list.querySelectorAll('.hb-autocomplete-item')[activeIndex];
        if (row && row._hbCountryOpt) { e.preventDefault(); pick(row._hbCountryOpt); }
      }
      else if (e.key === 'Escape') { close(); }
    });
  });
}

function initLocationAutocomplete() {
  document.querySelectorAll('input.hb-loc-autocomplete').forEach(function (input) {
    if (input.dataset.hbLocDone) return;
    input.dataset.hbLocDone = '1';

    const kind = input.getAttribute('data-hb-loc-kind') || 'country';
    const hint = input.getAttribute('data-hb-filter-hint') || 'تایپ کنید و از فهرست انتخاب کنید…';
    if (!input.placeholder) input.placeholder = hint;
    input.autocomplete = 'off';
    const url = '/accounts/locations/search/';

    const wrap = document.createElement('div');
    wrap.className = 'hb-autocomplete';
    const list = document.createElement('div');
    list.className = 'hb-autocomplete-list';
    list.hidden = true;
    list.setAttribute('role', 'listbox');
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    wrap.appendChild(list);
    input.classList.add('hb-autocomplete-input');

    // فیلدِ بالادست برای کوتاه‌کردن فهرست (استان←کشور، شهرستان←استان)
    const parentKind = { province: 'country', city: 'province' }[kind] || '';
    function parentText() {
      if (!parentKind) return '';
      const form = input.closest('form');
      const parent = form
        ? form.querySelector('input[data-hb-loc-kind="' + parentKind + '"]')
        : null;
      return parent ? String(parent.value || '').trim() : '';
    }

    // هشدار نرم: مقدارِ داخل جعبه در جدول مرجع نیست (ننویسی اشتباه ارسال نشود)
    const warn = document.createElement('div');
    warn.hidden = true;
    warn.style.cssText = 'display:flex;align-items:center;gap:0.35rem;margin-top:0.3rem;font-size:0.76rem;color:#e2a33a;line-height:1.6;';
    wrap.appendChild(warn);
    function showWarn(msg) {
      warn.innerHTML = '';
      const icon = document.createElement('i');
      icon.className = 'bi bi-exclamation-triangle';
      warn.appendChild(icon);
      warn.appendChild(document.createTextNode(msg));
      warn.hidden = false;
    }
    function hideWarn() { warn.hidden = true; warn.innerHTML = ''; }

    let timer = null;
    let controller = null;
    let activeIndex = -1;
    let lastQuery = null;
    let lastParent = null;

    function close() {
      list.hidden = true;
      list.innerHTML = '';
      activeIndex = -1;
    }

    function setValue(item) {
      input.value = item.fa;
      hideWarn();
      close();
      // تغییر شهرستان/استان می‌تواند فیلدِ زیردست را بی‌ربط کند؛ کاربر خودش آن را
      // از فهرستِ تازه انتخاب می‌کند (بدون حذف خودکارِ مقادیر GPS/دستی).
    }

    function setActive(i) {
      activeIndex = i;
      const rows = list.querySelectorAll('.hb-autocomplete-item');
      rows.forEach(function (r, idx) { r.classList.toggle('active', idx === i); });
      const cur = rows[i];
      if (cur) cur.scrollIntoView({ block: 'nearest' });
    }

    function render(items) {
      list.innerHTML = '';
      if (!items.length) {
        const empty = document.createElement('div');
        empty.className = 'hb-autocomplete-empty';
        empty.textContent = 'موردی یافت نشد — اگر نامِ محل را نیافتید با ادمین هماهنگ کنید';
        list.appendChild(empty);
      } else {
        items.forEach(function (item, i) {
          const row = document.createElement('div');
          row.className = 'hb-autocomplete-item';
          row.setAttribute('role', 'option');
          row._hbItem = item;
          const main = document.createElement('span');
          main.textContent = item.fa;
          row.appendChild(main);
          const extra = String(item.hint || item.en || '').trim();
          if (extra) {
            const sm = document.createElement('small');
            sm.textContent = extra;
            sm.style.direction = 'rtl';
            row.appendChild(sm);
          }
          row.addEventListener('mousedown', function (e) {
            e.preventDefault(); // blur را جلو بیندازد تا کلیک از دست نرود
            setValue(item);
          });
          row.addEventListener('mouseenter', function () { setActive(i); });
          list.appendChild(row);
        });
        setActive(0);
      }
      list.hidden = false;
    }

    async function search(force) {
      const q = input.value.trim();
      if (timer) { clearTimeout(timer); timer = null; }
      const parent = parentText();
      if (!force && q === lastQuery && parent === lastParent) return;
      lastQuery = q;
      lastParent = parent;
      if (!q) { hideWarn(); close(); return; }
      const cacheKey = 'L\u0000' + kind + '\u0000' + parent + '\u0000' + q;
      const cached = hbNameCacheGet(cacheKey);
      if (cached) {
        if (input.value.trim() !== q) return;
        render(cached);
        return;
      }
      if (controller) controller.abort();
      controller = new AbortController();
      list.innerHTML = '';
      const loading = document.createElement('div');
      loading.className = 'hb-autocomplete-empty';
      loading.textContent = 'در حال جستجو…';
      list.appendChild(loading);
      list.hidden = false;
      try {
        const resp = await fetch(
          url + '?q=' + encodeURIComponent(q) + '&kind=' + encodeURIComponent(kind)
            + '&parent=' + encodeURIComponent(parent),
          { signal: controller.signal }
        );
        if (!resp.ok) throw new Error('http ' + resp.status);
        const data = await resp.json();
        const results = data.results || [];
        hbNameCacheSet(cacheKey, results);
        if (input.value.trim() !== q) return; // کاربر در بین راه بیشتر تایپ کرده
        render(results);
      } catch (err) {
        if (err.name !== 'AbortError') {
          list.innerHTML = '';
          const empty = document.createElement('div');
          empty.className = 'hb-autocomplete-empty';
          empty.textContent = 'خطا در جستجو — دوباره تلاش کنید';
          list.appendChild(empty);
        }
      }
    }

    input.addEventListener('input', function () {
      hideWarn();
      if (timer) clearTimeout(timer);
      timer = setTimeout(function () { search(false); }, 200);
    });

    input.addEventListener('keydown', function (e) {
      const rows = function () { return list.querySelectorAll('.hb-autocomplete-item'); };
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const r = rows();
        if (!list.hidden && r.length) setActive((activeIndex + 1) % r.length);
        else search(true);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const r = rows();
        if (!list.hidden && r.length) setActive((activeIndex - 1 + r.length) % r.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const r = rows();
        if (!list.hidden && r[activeIndex] && r[activeIndex]._hbItem) {
          setValue(r[activeIndex]._hbItem);
        } else {
          search(true);
        }
      } else if (e.key === 'Escape') {
        close();
      }
    });

    input.addEventListener('blur', function () {
      setTimeout(function () {
        close();
        // پس از کنار رفتن از فیلد: اگر مقدار غیرخالی در جدول مرجع نیست، هشدار نرم
        const v = input.value.trim();
        if (!v) { hideWarn(); return; }
        const cacheKey = 'L\u0000' + kind + '\u0000' + parentText() + '\u0000' + v;
        const cached = hbNameCacheGet(cacheKey);
        const check = function (results) {
          const exact = (results || []).some(function (it) {
            return it.fa === v || (it.en && String(it.en).toLowerCase() === v.toLowerCase());
          });
          if (exact) hideWarn();
          else showWarn('این مقدار در فهرست مرجع نیست؛ برای ثبتِ دقیق، از فهرست پیشنهادی انتخاب کنید.');
        };
        if (cached) { check(cached); return; }
        fetch(url + '?q=' + encodeURIComponent(v) + '&kind=' + encodeURIComponent(kind)
          + '&parent=' + encodeURIComponent(parentText()))
          .then(function (r) { return r.json(); })
          .then(function (data) {
            hbNameCacheSet(cacheKey, data.results || []);
            if (document.activeElement !== input) check(data.results || []);
          })
          .catch(function () {});
      }, 180);
    });
  });
}
// ---------- Family section (اطلاعات خانواده) ----------
// ردیف‌های داینامیک همسر/فرزندان بر پایهٔ «کد ملی»: کاربر فقط کد ملی وارد
// می‌کند؛ اگر فرد ثبت‌نام کرده باشد نامش از سیستم فراخوانی می‌شود. کد ملی‌ها
// فقط در پایگاه داده ذخیره می‌شوند و نمایش نام همیشه از سیستم می‌آید.
// داده‌های ذخیره‌شدهٔ قبلی در <script id='family-section-data'> است.

// خطای بخش خانواده فقط داخل همین بخش اعلان می‌شود (باکس قرمز داخل کارت) و
// روی اولین فیلد خطادار اسکرول/فوکوس می‌شود. کد ملی‌ها اختیاری‌اند؛ پس وقتی
// فیلدهای الزامی (نام پدر/مادر/وضعیت تأهل) تکمیل باشند، اصلاً اعلانی رندر نمی‌شود.
function focusFamilySectionErrors() {
  var form = document.querySelector("form input[name='action'][value='family']");
  if (!form) return;
  form = form.closest('form');
  var errBox = form.querySelector('.hb-family-error-box');
  var firstFieldError = form.querySelector('.hb-field-error[data-field-error]');
  if (errBox || firstFieldError) {
    var card = form.closest('.hb-section-card');
    if (card && !card.classList.contains('active')) card.classList.add('active');
    if (firstFieldError) {
      var input = form.querySelector('[name="' + firstFieldError.getAttribute('data-field-error') + '"]');
      if (input) {
        input.style.borderColor = '#e74c3c';
        setTimeout(function () {
          input.focus({ preventScroll: true });
          input.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 150);
      }
    } else if (errBox) {
      setTimeout(function () {
        errBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 150);
    }
  }
}
// اعلان موفقیت بخش خانواده فقط داخل کارت «اطلاعات خانواده» می‌آید (به‌جای
// messages سراسری که در همهٔ بخش‌ها تکرار می‌شد): کارت باز، روی پیام اسکرول و
// بعد از چند ثانیه پیام خودبه‌خود محو می‌شود.
function showFamilySavedMessage() {
  var msg = document.getElementById('hb-family-saved-msg');
  if (!msg) return;
  var card = msg.closest('.hb-section-card');
  if (card && !card.classList.contains('active')) card.classList.add('active');
  setTimeout(function () {
    msg.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, 150);
  setTimeout(function () {
    msg.style.transition = 'opacity 0.5s';
    msg.style.opacity = '0';
    setTimeout(function () { msg.remove(); }, 500);
  }, 5000);
}

function initFamilySection() {
  var wrap = document.getElementById('family-spouse-wrap');
  var tpl = document.getElementById('family-person-row-tpl');
  var dataEl = document.getElementById('family-section-data');
  if (!wrap || !tpl || !dataEl) return;

  var MAX_ROWS = 10;
  var containers = {
    spouse: document.getElementById('family-spouse-rows'),
    sons: document.getElementById('family-sons-rows'),
    daughters: document.getElementById('family-daughters-rows')
  };

  var saved = {};
  try { saved = JSON.parse(dataEl.textContent || '{}') || {}; } catch (e) { saved = {}; }

  function pad2(n) { return (n < 10 ? '0' : '') + n; }

  function buildRow(group, idx, person) {
    var node = tpl.content.firstElementChild.cloneNode(true);
    node.setAttribute('data-group', group);
    var nid = node.querySelector('[data-family-field="national_id"]');
    nid.name = group + '_' + idx + '_national_id';
    if (person && person.national_id) nid.value = String(person.national_id);
    if (person && person.matched) {
      var fb = node.querySelector('.hb-nid-feedback');
      if (fb) {
        fb.hidden = false;
        fb.style.color = 'var(--hb-success)';
        fb.textContent = 'در سیستم ثبت‌نام شده — در حال فراخوانی نام…';
      }
    }
    return node;
  }

  function reindex(group) {
    var rows = containers[group].querySelectorAll('.hb-person-row');
    Array.prototype.forEach.call(rows, function (row, i) {
      row.querySelector('[data-family-field="national_id"]').name =
        group + '_' + pad2(i) + '_national_id';
    });
  }

  function addRow(group, person) {
    var c = containers[group];
    if (!c) return;
    if (c.querySelectorAll('.hb-person-row').length >= MAX_ROWS) return;
    c.appendChild(buildRow(group, pad2(c.querySelectorAll('.hb-person-row').length), person));
    reindex(group);
  }

  function removeHiddenNids(group) {
    // کد ملی ردیف‌های حذف‌شده نباید در POST بماند
    var form = containers[group].closest('form');
    if (!form) return;
    var re = new RegExp('^' + group + '_\\d+_national_id$');
    Array.prototype.forEach.call(form.querySelectorAll('input[name]'), function (el) {
      if (re.test(el.name) && !containers[group].contains(el)) el.remove();
    });
  }

  // فعال/غیرفعال‌سازی یک گروه (تعداد + ردیف‌ها + دکمهٔ افزودن):
  // کد ملی‌ها اختیاری‌اند؛ «افزودن ردیف کد ملی» همیشه در بخشِ فعال در دسترس است.
  function setGroupEnabled(group, enabled) {
    var input = document.querySelector('[data-family-count="' + group + '"]');
    var btn = document.querySelector('[data-family-add="' + group + '"]');
    if (btn) btn.disabled = !enabled;
    if (input) input.disabled = !enabled;
    if (!enabled) {
      var c = containers[group];
      if (c) {
        Array.prototype.forEach.call(c.querySelectorAll('.hb-person-row'), function (r) { r.remove(); });
        removeHiddenNids(group);
      }
      if (input) input.value = '';
    }
  }

  // دکمهٔ افزودن هر گروه فقط بر اساس فعال‌بودنِ بخشِ آن به‌روز می‌شود
  function syncAddButtons() {
    ['spouse', 'sons', 'daughters'].forEach(function (group) {
      var input = document.querySelector('[data-family-count="' + group + '"]');
      var btn = document.querySelector('[data-family-add="' + group + '"]');
      if (!btn) return;
      btn.disabled = !input || input.disabled;
    });
  }

  // همسر فقط در وضعیت «متاهل»؛ فرزندان در «متاهل» و «جداشده» فعال‌اند —
  // در وضعیت «مجرد» همسر و فرزندان غیرفعال و پاک می‌شوند.
  function syncFamilyState() {
    var marital = document.querySelector('select[name="marital_status"]');
    if (!marital) return;
    var married = marital.value === 'married';
    var childrenActive = married || marital.value === 'separated';
    wrap.hidden = !married;
    var childrenWrap = document.getElementById('family-children-wrap');
    if (childrenWrap) childrenWrap.hidden = !childrenActive;
    setGroupEnabled('spouse', married);
    setGroupEnabled('sons', childrenActive);
    setGroupEnabled('daughters', childrenActive);
  }

  // تعداد فقط سقفِ ردیف‌ها را تعیین می‌کند (کد ملی اختیاری است):
  // * افزایش تعداد، ردیف خالی می‌سازد (رفتار قبلی حفظ شده)؛
  // * کاهش تعداد فقط ردیف‌های خالی (بدون کد ملی) را حذف می‌کند و ردیف‌های
  //   دارای کد ملی حفظ می‌شوند؛
  // * خالی‌گذاشتن تعداد هیچ ردیفی را حذف نمی‌کند.
  function syncRows(group) {
    var input = document.querySelector('[data-family-count="' + group + '"]');
    if (!input) return;
    var want = parseInt(input.value, 10);
    if (isNaN(want)) return; // تعداد خالی = بدون سقف
    want = Math.max(0, Math.min(MAX_ROWS, want));
    var c = containers[group];
    var rows = c.querySelectorAll('.hb-person-row');
    for (var i = rows.length; i < want; i++) addRow(group, null);
    rows = c.querySelectorAll('.hb-person-row');
    if (rows.length > want) {
      var keep = [];
      var capacity = want; // ظرفیت باقی‌مانده برای ردیف‌های خالی
      Array.prototype.forEach.call(rows, function (row) {
        var nid = row.querySelector('[data-family-field="national_id"]');
        var filled = nid && (nid.value || '').trim().length > 0;
        if (filled) keep.push(row);
        else if (capacity > 0) { keep.push(row); capacity--; }
      });
      Array.prototype.forEach.call(rows, function (row) {
        if (keep.indexOf(row) === -1) row.remove();
      });
      removeHiddenNids(group);
      reindex(group);
    }
  }

  // فراخوانی نمایشِ نامِ همهٔ ردیف‌های ذخیره‌شده با یک درخواست دسته‌ای
  function resolveSavedNames() {
    var byNid = {};
    Object.keys(containers).forEach(function (group) {
      Array.prototype.forEach.call(containers[group].querySelectorAll('.hb-person-row'), function (row) {
        var input = row.querySelector('[data-family-field="national_id"]');
        if (input && input.value) byNid[input.value.trim()] = row;
      });
    });
    var nids = Object.keys(byNid);
    if (!nids.length) return;
    fetch('/accounts/family/nid-lookup/?nids=' + encodeURIComponent(nids.join(',')),
      { headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var results = (data && data.results) || {};
        nids.forEach(function (n) {
          var row = byNid[n];
          var info = results[n];
          var fb = row ? row.querySelector('.hb-nid-feedback') : null;
          if (!fb) return;
          if (info && info.found) {
            var label = [info.first_name_fa, info.family_name_fa].filter(Boolean).join(' ');
            fb.hidden = false;
            fb.style.color = 'var(--hb-success)';
            fb.textContent = label ? ('ثبت‌نام‌شده: ' + label) : 'در سیستم ثبت‌نام شده';
          } else {
            fb.hidden = false;
            fb.style.color = 'var(--hb-text-muted)';
            fb.textContent = 'هنوز در سیستم ثبت‌نام نکرده — پس از ثبت‌نام، نام او خودکار نمایش داده می‌شود';
          }
        });
      })
      .catch(function () {});
  }

  // فراخوانی تکی هنگام تایپ کد ملی
  function lookupNid(row, nidInput) {
    var fb = row.querySelector('.hb-nid-feedback');
    if (!fb) return;
    fetch('/accounts/family/nid-lookup/?nid=' + encodeURIComponent(nidInput.value.trim()),
      { headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data || data.error) return;
        if (data.found) {
          var label = [data.first_name_fa, data.family_name_fa].filter(Boolean).join(' ');
          fb.hidden = false;
          fb.style.color = 'var(--hb-success)';
          fb.textContent = 'از سیستم فراخوانی شد: ' + (label || 'ثبت‌نام‌شده');
        } else {
          fb.hidden = false;
          fb.style.color = 'var(--hb-text-muted)';
          fb.textContent = 'در سیستم ثبت‌نام نکرده — پس از ثبت‌نام، نام او خودکار نمایش داده می‌شود';
        }
      })
      .catch(function () {});
  }

  // بازیابی ردیف‌های ذخیره‌شدهٔ قبلی (حالت ویرایش)
  (function restore() {
    (saved.spouses || []).forEach(function (p) { addRow('spouse', p); });
    (saved.sons || []).forEach(function (p) { addRow('sons', p); });
    (saved.daughters || []).forEach(function (p) { addRow('daughters', p); });
    ['spouse', 'sons', 'daughters'].forEach(function (group) {
      var input = document.querySelector('[data-family-count="' + group + '"]');
      var key = group === 'spouse' ? 'spouses_count' : group + '_count';
      var listKey = group === 'spouse' ? 'spouses' : group;
      if (input && !input.value) {
        input.value = (saved[listKey] || []).length || (saved[key] != null ? saved[key] : '');
      }
      syncRows(group);
    });  syncFamilyState();
  resolveSavedNames();
  focusFamilySectionErrors();
  showFamilySavedMessage();
  })();

  // رویدادها
  var marital = document.querySelector('select[name="marital_status"]');
  if (marital) marital.addEventListener('change', syncFamilyState);

  document.querySelectorAll('.hb-family-add').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (btn.disabled) return;
      var group = btn.getAttribute('data-family-add');
      if (containers[group].querySelectorAll('.hb-person-row').length >= MAX_ROWS) return;
      addRow(group, null);
      var input = document.querySelector('[data-family-count="' + group + '"]');
      var n = containers[group].querySelectorAll('.hb-person-row').length;
      // تعداد فقط در صورت کوچک‌تربودن از ردیف‌ها به‌روز می‌شود (سقف است، نه الزام)
      if (input && ((parseInt(input.value, 10) || 0) < n)) input.value = n;
    });
  });

  Object.keys(containers).forEach(function (group) {
    containers[group].addEventListener('click', function (e) {
      var btn = e.target.closest('.hb-family-remove');
      if (!btn) return;
      var row = btn.closest('.hb-person-row');
      if (row) {
        row.remove();
        reindex(group);
        var input = document.querySelector('[data-family-count="' + group + '"]');
        if (input) input.value = containers[group].querySelectorAll('.hb-person-row').length;
        syncAddButtons();
      }
    });
    containers[group].addEventListener('input', function (e) {
      var nid = e.target.closest('[data-family-field="national_id"]');
      if (!nid) return;
      var row = nid.closest('.hb-person-row');
      var fb = row ? row.querySelector('.hb-nid-feedback') : null;
      var val = nid.value.replace(/[^0-9\u06F0-\u06F9\u0660-\u0669]/g, '');
      // تبدیل ارقام فارسی/عربی به لاتین تا در سرور پذیرفته شود
      val = val.replace(/[\u06F0-\u06F9]/g, function (ch) { return String.fromCharCode(ch.charCodeAt(0) - 0x06F0 + 48); }).replace(/[\u0660-\u0669]/g, function (ch) { return String.fromCharCode(ch.charCodeAt(0) - 0x0660 + 48); });
      if (val !== nid.value) nid.value = val;
      if (fb) { fb.hidden = true; fb.textContent = ''; }
      if (val.length !== 10) return;
      clearTimeout(nid._hbNidTimer);
      nid._hbNidTimer = setTimeout(function () { lookupNid(row, nid); }, 350);
    });
  });

  // تعداد ← تعداد ردیف (همسر/پسر/دختر) + به‌روزرسانی دکمهٔ افزودن
  ['spouse', 'sons', 'daughters'].forEach(function (group) {
    var input = document.querySelector('[data-family-count="' + group + '"]');
    if (input) input.addEventListener('input', function () { syncRows(group); syncAddButtons(); });
  });
}

// ---------- اورلی سراسری «لطفاً منتظر بمانید» (Please Wait) ----------
// پیاده‌سازی در core/js/please_wait.js است (مستقل از app.js تا در همهٔ صفحه‌ها، حتی بدونِ app.js
// مثل تیکت‌ها/حسابداری/بازی‌ها، کار کند). اینجا فقط مطمئن می‌شویم بارگذاری شده است؛ بارگذاری مجدد
// بی‌اثر است (پرچم window.__hbPwBound). آدرس فایل از روی آدرس خودِ app.js ساخته می‌شود.
const HB_APP_SRC = (document.currentScript && document.currentScript.src) || '';

function initPleaseWait() {
  if (window.__hbPwBound || document.querySelector('script[src*="core/js/please_wait.js"]')) return;
  const s = document.createElement('script');
  s.src = (HB_APP_SRC ? HB_APP_SRC.replace(/core\/js\/app\.js.*$/, '') : '/static/') + 'core/js/please_wait.js?v=1';
  document.head.appendChild(s);
}

// ---------- Wallet: خرید/فروش/انتقال سکه ----------
// - خطای درون-فریمی (مثل «حداقل خرید 10.00 سکه است.») زیر فیلد مربوطه + فوکوس
// - «اطلاعات سفارش و حساب مقصد» و «اطلاعات سفارش بر حسب ریال» زیر فیلد تعداد سکه
// - جست‌وجوی زندهٔ کد ملی گیرندهٔ انتقال → نمایش نام کاربر
function initWalletPage() {
  if (!document.getElementById('id_buy_coins') && !document.getElementById('id_receiver_national_id')) return;

  // ---- ۱) خطای درون-فریمی از پارامترهای URL ----
  (function showWalletError() {
    var params = new URLSearchParams(window.location.search);
    var err = params.get('wallet_err');
    if (!err) return;
    var action = params.get('wallet_action') || 'buy';
    var field = params.get('wallet_field') || 'coins';
    var frame = document.querySelector('[data-wallet-frame="' + action + '"]');
    if (frame) {
      var targetId = action === 'transfer' && field === 'receiver_national_id'
        ? 'id_receiver_national_id' : 'id_' + (action === 'transfer' ? 'transfer_' : '') + 'coins';
      var input = frame.querySelector('#' + targetId) || frame.querySelector('input[name="coins"]');
      var holder = frame.querySelector('[data-wallet-error]');
      if (input) {
        input.classList.add('hb-input-error');
        if (holder) {
          holder.textContent = err;
          holder.hidden = false;
          if (input.insertAdjacentElement) {
            input.insertAdjacentElement('afterend', holder);
          }
        }
      }
      frame.scrollIntoView({ behavior: 'smooth', block: 'center' });
      if (input) setTimeout(function () { input.focus({ preventScroll: true }); }, 250);
    }
    // پاک‌کردن پارامترها از نوار آدرس تا با رفرش، خطا دوباره نشان داده نشود
    params.delete('wallet_err'); params.delete('wallet_field'); params.delete('wallet_action');
    var qs = params.toString();
    var cleanUrl = window.location.pathname + (qs ? '?' + qs : '');
    window.history.replaceState({}, '', cleanUrl);
  })();

  // ---- ۲) اطلاعات سفارش و حساب مقصد + سفارش بر حسب ریال (زیر فیلد تعداد سکه) ----
  var FACTS = {};
  (function readFacts() {
    var frame = document.querySelector('[data-wallet-frame="buy"]');
    if (!frame) return;
    FACTS.rate = parseFloat(frame.getAttribute('data-rate')) || 0;
    FACTS.minBuy = parseFloat(frame.getAttribute('data-min-buy')) || 0;
    FACTS.maxBuy = parseFloat(frame.getAttribute('data-max-buy')) || 0;
  })();

  function fmt(n) { return (Math.round(n * 100) / 100).toLocaleString('en-US', { maximumFractionDigits: 2 }); }

  var buyInput = document.getElementById('id_buy_coins');
  var sellInput = document.getElementById('id_sell_coins');
  var destBox = document.getElementById('wallet-dest-info');
  var rialBox = document.getElementById('wallet-rial-info');
  function refreshBuyInfo() {
    var val = parseFloat((buyInput && buyInput.value) || '');
    if (destBox) destBox.hidden = !val || val <= 0;
    if (rialBox) rialBox.hidden = !val || val <= 0;
    if (!val || val <= 0) return;
    if (destBox) {
      var total = val * FACTS.rate;
      var el = destBox.querySelector('[data-dest-total]');
      if (el) el.textContent = fmt(total) + ' ریال';
      var elCoins = destBox.querySelector('[data-dest-coins]');
      if (elCoins) elCoins.textContent = fmt(val) + ' سکه';
      var elRate = destBox.querySelector('[data-dest-rate]');
      if (elRate) elRate.textContent = fmt(FACTS.rate) + ' ریال';
    }
    if (rialBox) {
      var el2 = rialBox.querySelector('[data-rial-total]');
      if (el2) el2.textContent = fmt(val * FACTS.rate) + ' ریال';
      var el2c = rialBox.querySelector('[data-rial-coins]');
      if (el2c) el2c.textContent = fmt(val) + ' سکه';
      var el2r = rialBox.querySelector('[data-rial-rate]');
      if (el2r) el2r.textContent = fmt(FACTS.rate) + ' ریال';
    }
  }
  if (buyInput) buyInput.addEventListener('input', refreshBuyInfo);

  // ---- ۳) کد ملی گیرنده: فقط عدد + فهرست آبشاری Query (مثل فیلد نام پروفایل) ----
  var nidInput = document.getElementById('id_receiver_national_id');
  var nameBox = document.getElementById('wallet-receiver-name');
  if (nidInput && nameBox) {
    var nidTimer = null; var nidReqSeq = 0;
    function toLatinDigits(s) {
      return String(s)
        .replace(/[\u06F0-\u06F9]/g, function (ch) { return String.fromCharCode(ch.charCodeAt(0) - 0x06F0 + 48); })
        .replace(/[\u0660-\u0669]/g, function (ch) { return String.fromCharCode(ch.charCodeAt(0) - 0x0660 + 48); });
    }
    // فهرست آبشاری زیر فیلد (هم‌کلاس با انتخاب‌گر نام پروفایل)
    var nidWrap = nidInput.closest('.hb-autocomplete');
    if (!nidWrap) {
      nidWrap = document.createElement('div');
      nidWrap.className = 'hb-autocomplete';
      nidInput.parentNode.insertBefore(nidWrap, nidInput);
      nidWrap.appendChild(nidInput);
    }
    var nidList = nidWrap.querySelector('.hb-autocomplete-list');
    if (!nidList) {
      nidList = document.createElement('div');
      nidList.className = 'hb-autocomplete-list';
      nidList.hidden = true;
      nidList.setAttribute('role', 'listbox');
      nidWrap.appendChild(nidList);
    }
    var nidActive = -1;
    function nidCloseList() { nidList.hidden = true; nidList.innerHTML = ''; nidActive = -1; }
    function nidSanitize() {
      var raw = toLatinDigits(nidInput.value).replace(/\D/g, '').slice(0, 10);
      if (raw !== nidInput.value) nidInput.value = raw;
      return raw;
    }
    function nidChoose(item) {
      var nid = item.getAttribute('data-nid') || '';
      if (!nid) return;
      nidInput.value = nid;
      nidCloseList();
      nidInput.setAttribute('data-hb-nid-picked', '1');
      nidExactLookup(nid);
    }
    function nidRender(results) {
      nidList.innerHTML = '';
      nidActive = -1;
      if (!results.length) {
        var empty = document.createElement('div');
        empty.className = 'hb-autocomplete-empty';
        empty.textContent = 'کاربری با این کد ملی یافت نشد.';
        nidList.appendChild(empty);
        nidList.hidden = false;
        return;
      }
      results.forEach(function (r) {
        var item = document.createElement('div');
        item.className = 'hb-autocomplete-item';
        item.setAttribute('role', 'option');
        item.setAttribute('data-nid', r.national_id || '');
        var nm = document.createElement('span');
        nm.textContent = r.full_name || '—';
        var cd = document.createElement('small');
        cd.textContent = r.national_id || '';
        item.appendChild(nm); item.appendChild(cd);
        item.addEventListener('mousedown', function (e) { e.preventDefault(); nidChoose(item); });
        nidList.appendChild(item);
      });
      nidList.hidden = false;
    }
    function nidQueryList() {
      var q = nidSanitize();
      var seq = ++nidReqSeq;
      if (q.length < 4) { nidCloseList(); return; }
      fetch('/wallet/transfer/lookup/?q=' + encodeURIComponent(q), {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      })
        .then(function (r) { return r.json(); })
        .then(function (data) { if (seq === nidReqSeq) nidRender((data && data.results) || []); })
        .catch(function () { /* بی‌صدا: شبکه نباید تایپ را بشکند */ });
    }
    function nidExactLookup(raw) {
      if (raw !== nidInput.value) nidInput.value = raw;
      if (raw.length !== 10) {
        nameBox.hidden = true; nameBox.removeAttribute('data-receiver-name');
        return;
      }
      fetch('/wallet/transfer/lookup/?national_id=' + encodeURIComponent(raw), {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data && data.found) {
            nameBox.hidden = false;
            nameBox.setAttribute('data-receiver-name', data.full_name || '');
            var el = nameBox.querySelector('[data-receiver-fullname]');
            if (el) el.textContent = data.full_name || '';
            var mob = nameBox.querySelector('[data-receiver-mobile]');
            if (mob) mob.textContent = data.mobile_number || '';
            var nid2 = nameBox.querySelector('[data-receiver-nid]');
            if (nid2) nid2.textContent = data.national_id || raw;
            nidCloseList();
          } else {
            nameBox.hidden = true;
            nameBox.removeAttribute('data-receiver-name');
            // «یافت نشد» فقط وقتی کاربر در حال تایپ است در فهرست نمایش داده می‌شود
            if (document.activeElement === nidInput) nidRender([]);
          }
        })
        .catch(function () { /* بی‌صدا: شبکه نباید تایپ را بشکند */ });
    }
    nidInput.addEventListener('input', function () {
      nidSanitize();
      nameBox.hidden = true; nameBox.removeAttribute('data-receiver-name');
      nidInput.removeAttribute('data-hb-nid-picked');
      clearTimeout(nidTimer);
      nidTimer = setTimeout(function () {
        var raw = nidInput.value;
        if (raw.length === 10) nidExactLookup(raw);
        else if (raw.length >= 4) nidQueryList();
        else nidCloseList();
      }, 250);
    });
    nidInput.addEventListener('focus', function () {
      if (nidInput.value.length >= 4 && nidInput.value.length < 10) nidQueryList();
    });
    nidInput.addEventListener('keydown', function (e) {
      if (nidList.hidden) return;
      var items = Array.prototype.slice.call(nidList.querySelectorAll('.hb-autocomplete-item'));
      if (!items.length) return;
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        nidActive = e.key === 'ArrowDown'
          ? (nidActive + 1) % items.length
          : (nidActive <= 0 ? items.length - 1 : nidActive - 1);
        items.forEach(function (it, i) { it.classList.toggle('active', i === nidActive); });
      } else if (e.key === 'Enter') {
        if (nidActive >= 0 && items[nidActive]) { e.preventDefault(); nidChoose(items[nidActive]); }
      } else if (e.key === 'Escape') {
        nidCloseList();
      }
    });
    document.addEventListener('click', function (e) {
      if (!nidWrap.contains(e.target)) nidCloseList();
    });
    // اگر سرور فرم را با خطا برگرداند، کد ملیِ موجود دوباره جست‌وجو می‌شود
    if (nidInput.value) nidExactLookup(nidInput.value);
  }

  // ---- ۴) تأیید دوباره پیش از ارسال «انتقال سکه» ----
  var transferForm = document.querySelector('[data-wallet-frame="transfer"] form');
  if (transferForm) {
    transferForm.addEventListener('submit', function (e) {
      var nameBox = document.getElementById('wallet-receiver-name');
      if (!nameBox || nameBox.hidden || !nameBox.getAttribute('data-receiver-name')) {
        e.preventDefault();
        alert('ابتدا کد ملی گیرنده را وارد کنید و نام او را انتخاب/تأیید کنید.');
        if (nidInput) nidInput.focus();
        return;
      }
      if (transferForm.dataset.confirmedOnce === '1') return; // دومین تأیید
      e.preventDefault();
      var amount = (document.getElementById('id_transfer_coins') || {}).value || '';
      var receiverName = nameBox.getAttribute('data-receiver-name');
      if (window.confirm('تأیید اول: آیا از انتقال ' + amount + ' سکه به «' + receiverName + '» مطمئن هستید؟')) {
        transferForm.dataset.confirmedOnce = '1';
        if (window.confirm('تأیید دوم: انتقال سکه پس از انجام غیرقابل بازگشت است؛ انجام شود؟')) {
          // ارسال برنامه‌ایِ فرم رویداد submit ندارد؛ اورلی «لطفاً منتظر بمانید» دستی مسلح می‌شود
          if (window.hbPleaseWait) window.hbPleaseWait.arm();
          transferForm.submit();
        } else {
          delete transferForm.dataset.confirmedOnce;
        }
      }
    });
  }

  refreshBuyInfo();

  // ---- ۶) مدیریتِ بارگذاری Передِ عملیات طولانی (پنل مدیریت/پشتیبانی) ----
  // فعال‌سازی پردازشِ اجرا: وقتی یک فرم (یا هر المان مرتبط) داده‌ای می‌فرستد و
  // «data-loading>1» است، پانلو «سپس منتظر بمانید» و قفل‌کردن صفحه فعال می‌شود تا
  // کاربر تا اتمام عملیات نتواند چندین درخواست بفرستد یا تغییرات نامتاناً بدهد.
  let adminLoaderHeld = false;   // این لودر یک «نگه‌دارندهٔ» اورلی واحد است (جلوگیری از دوبار begin/end)
  let adminLoaderTimer = null;
  function toggleAdminLoader(active, label) {
    const P = window.hbPleaseWait;
    if (active) {
      // مانع از ارسال چندین درخواست همزمان و از تغییرات حیاتی در حین Process
      document.querySelectorAll('form[data-loading]').forEach(function (f) {
        f.querySelectorAll('button[type="submit"], input[type="submit"]').forEach(function (b) {
          b.disabled = true;
          b.setAttribute('data-loading-restore', '1');
        });
      });
      if (P && !adminLoaderHeld) {
        adminLoaderHeld = true;
        P.begin(label || '', 0);                // پنل مدیریت: فوری (بدون تأخیر ۲ ثانیه‌ای)
      } else if (P && label) {
        P.label(label);
      }
      // پس از ۳ ثانیه اگر هنوز عملیات انجام نشد، پیام را عوض می‌کند
      if (adminLoaderTimer) clearTimeout(adminLoaderTimer);
      adminLoaderTimer = setTimeout(function () {
        if (adminLoaderHeld && window.hbPleaseWait) window.hbPleaseWait.label('هنوز در حال پردازش است. لطفاً صبر کنید.');
      }, 3000);
    } else {
      if (adminLoaderTimer) { clearTimeout(adminLoaderTimer); adminLoaderTimer = null; }
      if (P && adminLoaderHeld) { adminLoaderHeld = false; P.end(); }
      document.querySelectorAll('form[data-loading]').forEach(function (f) {
        f.querySelectorAll('button[type="submit"], input[type="submit"][data-loading-restore="1"]').forEach(function (b) {
          b.disabled = false;
          b.removeAttribute('data-loading-restore');
        });
      });
    }
  }

  document.addEventListener('submit', function (e) {
    const form = e.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (e.defaultPrevented) return;            // مثلاً confirm() لغو شد: لودر نباید بیاید
    const loading = form.getAttribute('data-loading');
    if (loading) {
      if (loading === '1' || loading === 'true') {
        toggleAdminLoader(true);
      } else {
        // «data-loading=<عنوان عملیات>»: عنوان زیر «لطفاً منتظر بمانید…» نمایش داده می‌شود
        toggleAdminLoader(true, loading);
      }
    }
  });

  // در پایان هر عملیات، از دکمهٔ ارسالی فعال می‌شود مگر آن‌که فرم صریحاً بست
  // (data-loading="close") باشد.
  document.addEventListener('click', function (e) {
    const btn = e.target.closest('button, input[type="submit"], a[href$="submit"], button[style]');
    if (!btn) return;
    const form = btn.closest('form');
    if (!form) return;
    const loading = form.getAttribute('data-loading');
    if (!loading) return;
    // اگر فرم خودِ ارسالی دارای پارامتر «close» است، پس از click، پانو را بسته
    if (e.detail === 'admin-close-loader') {
      toggleAdminLoader(false);
    }
    // بسته‌ی کلید قبل از فوراً ارسال برای جلوگیری از درخواستهای سریع‌تر
    if (loading === '1' || loading === 'true') {
      const submitter = e.submitter || btn;
      if (submitter && submitter.name === 'hb_job_action') return; // تیکت به مدیر استثنا است
      const closeBtn = form.querySelector('[data-admin-close-loader]') || btn;
      if (closeBtn) closeBtn.dataset.adminCloseLoader = '1';
    }
  });

  // ---- آپلود لوگوی/مستندات شغل به‌صورت AJAX + نمایش فوریِ همان‌جا ----
  // بلافاصله پس از انتخاب فایل در فرم شغل (اینپوتِ form='hb-job-doc-form')، فایل
  // به accounts:job_document_add فرستاده می‌شود و پاسخ JSON (آدرس فایل) برای
  // به‌روزرسانیِ پیش‌نمایش «همان‌جا» استفاده می‌شود — بدون رفرش صفحه.
  const jobDocForm = document.getElementById('hb-job-doc-form');
  const jobDocInput = document.querySelector('input[type="file"][name="job_doc"][form="hb-job-doc-form"]');
  const jobFormEl = document.getElementById('job-form');
  if (jobDocForm && jobDocInput) {
    const docPreview = document.getElementById('hb-job-doc-preview');
    const docEmpty = document.getElementById('hb-job-doc-empty');
    const docMeta = document.getElementById('hb-job-doc-meta');
    // حذفِ لوگوی فعلی در حالت ویرایش (اگر کاربر بعد از دیدن پیش‌نمایش، حذف را بخواهد)
    const docDeleteBtn = document.getElementById('hb-job-doc-delete');

    const showDoc = (url, name) => {
      if (docPreview) {
        docPreview.src = url;
        docPreview.style.display = '';
      }
      if (docEmpty) docEmpty.style.display = 'none';
      if (docMeta) {
        docMeta.textContent = 'فایل فعلی: ' + (name || 'لوگوی شغل');
        docMeta.hidden = false;
      }
    };      jobDocInput.addEventListener('change', function () {
      const file = jobDocInput.files && jobDocInput.files[0];
      if (!file) return;
      // شناسهٔ شغلِ هدف: در حالت ویرایش از خودِ فرم شغل؛ در حالت افزودن از فرم
      // پنهان (جدیدترین شغل کاربر — سرور هم کنترل می‌کند).
      const jobHidden = jobDocForm.querySelector('[name="job_id"]');
      if (jobHidden && (!jobHidden.value || jobHidden.value === 'None')) {
        jobHidden.value = '';
      }
      if (!jobDocForm.querySelector('[name="job_id"]').value && !(jobFormEl && jobFormEl.hasAttribute('data-job-edit'))) {
        showToast('برای آپلود لوگو، ابتدا شغل را ثبت کنید.', 'warning', 6000);
        jobDocInput.value = '';
        return;
      }
      const fd = new FormData(jobDocForm);
      fd.set('job_doc', file);
      const xhr = new XMLHttpRequest();
      xhr.open('POST', jobDocForm.action, true);
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
      xhr.onload = function () {
        jobDocInput.value = ''; // اجازهٔ انتخابِ دوبارهٔ همان فایل
        let data = null;
        try { data = JSON.parse(xhr.responseText); } catch (err) { data = null; }
        if (xhr.status >= 200 && xhr.status < 300 && data && data.ok) {
          showDoc(data.url, data.name);
          showToast(data.message || 'لوگوی/مستندات شغل ذخیره شد.', 'success');
        } else {
          showToast((data && data.error) || 'آپلود ناموفق بود؛ دوباره تلاش کنید.', 'error', 6000);
        }
      };
      xhr.onerror = function () {
        jobDocInput.value = '';
        showToast('خطا در ارتباط با سرور در حین آپلود. لطفاً دوباره تلاش کنید.', 'error', 6000);
      };
      showToast('در حال آپلود لوگوی/مستندات شغل…', 'info', 2500);
      xhr.send(fd);
    });

    if (docDeleteBtn) {
      docDeleteBtn.addEventListener('click', function () {
        if (docPreview) { docPreview.removeAttribute('src'); docPreview.style.display = 'none'; }
        if (docEmpty) docEmpty.style.display = '';
        if (docMeta) { docMeta.textContent = ''; docMeta.hidden = true; }
      });
    }
  }

  // ---- ۵) کپی شماره کارت/شبأ مقصد از جعبهٔ «حساب مقصد» ----
  document.querySelectorAll('[data-copy-text]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var text = btn.getAttribute('data-copy-text') || '';
      if (!text) return;
      var done = function () {
        var lbl = btn.querySelector('span');
        var old = lbl ? lbl.textContent : '';
        if (lbl) lbl.textContent = 'کپی شد!';
        setTimeout(function () { if (lbl) lbl.textContent = old; }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(function () {});
      } else {
        var ta = document.createElement('textarea');
        ta.value = text; document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); done(); } catch (err) {}
        ta.remove();
      }
    });
  });
}
