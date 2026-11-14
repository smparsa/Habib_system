"""درج محتوای استاندارد فارسی صفحات اطلاعاتی حبیب‌هاب.

متن‌ها ترجمهٔ رسمی و بومی‌سازی‌شدهٔ فایل‌های HTML اولیه (about / privacy /
terms / support / Help Center / contact us) متناسب با اکوسیستم حبیب‌هاب است
(سکه، امتیاز، تیکت، پروفایل و …). اجرای مجدد فقط محتوای صفحات را به‌روز
می‌کند؛ تنظیمات ادمین (فعال/غیرفعال، نمایش در منو) دست‌نخورده می‌ماند.
"""

from django.core.management.base import BaseCommand
from django.conf import settings

from core.models import InfoPage

WALLET_FAQ_ITEMS = [
    ("چگونه سکه بخرم؟",
     "در بخش «کیف پول و سکه»، قسمت «خرید سکه» مبلغ دلخواه را انتخاب و به شبأ "
     "نمایش‌داده‌شده واریز کنید؛ سپس رسید پرداخت را بارگذاری و ثبت کنید. پس از "
     "تأیید ادمین، سکه‌ها به کیف پول شما اضافه می‌شود."),
    ("چگونه سکه‌هایم را بفروشم؟",
     "در قسمت «فروش سکه» تعداد سکه و شماره شبأ خود را وارد و درخواست را ثبت "
     "کنید. پس از تأیید دومرحله‌ای درخواست، وجه طی ساعات کاری به حساب شما "
     "واریز می‌شود."),
    ("چگونه سکه به دیگری منتقل کنم؟",
     "در قسمت «انتقال سکه به دیگران» کد ملی ۱۰ رقمی گیرنده را وارد کنید؛ فهرست "
     "نام‌های متناظر باز می‌شود و گیرنده را انتخاب می‌کنید. پس از تأیید نام و "
     "شماره موبایل و درج رمز انتقال (در صورت فعال بودن)، سکه فوراً منتقل می‌شود."),
    ("امتیاز من چگونه به سکه تبدیل می‌شود؟",
     "هر امتیازی که از طریق معرفی دوستان، تکمیل پروفایل یا فعالیت‌های برنامه "
     "کسب می‌کنید، بلافاصله بر اساس «تعرفه امتیازها» در پنل مدیریت به سکه تبدیل "
     "و به کیف پول شما تجمیع می‌شود. موجودی امتیاز شما در بالای کیف پول نمایش "
     "داده می‌شود."),
]

TICKET_FAQ_ITEMS = [
    ("تیکت چیست و چه زمانی استفاده کنم؟",
     "تیکت پیام رسمی شما به تیم پشتیبانی است. برای هر موضوع یک تیکت جدید "
     "بسازید؛ پاسخ‌ها در همان تیکت و با اعلان برای شما ثبت می‌شود."),
    ("چقدر طول می‌کشد تا پاسخ بگیرم؟",
     "بسته به اولویت تیکت: بحرانی نیم ساعت، فوری ۲ ساعت، بالا ۸ ساعت، عادی ۲۴ "
     "ساعت و کم ۴۸ ساعت (زمان اداری). تیکت‌های مالی با اولویت بالا بررسی می‌شوند."),
    ("امتیاز (رتبه‌بندی) پاسخ چیست؟",
     "پس از حل شدن تیکت می‌توانید کیفیت پشتیبانی را از ۱ تا ۵ ستاره امتیاز "
     "دهید تا کیفیت خدمت ما بهتر شود."),
]

PROFILE_FAQ_ITEMS = [
    ("چرا کد ملی را نمی‌توانم تغییر دهم؟",
     "برای جلوگیری از سواستفاده و حفظ یکتایی حساب‌ها، پس از تکمیل پروفایل، کد "
     "ملی قفل می‌شود. در صورت اشتباه بودن، از «مرکز تیکت» درخواست اصلاح ثبت کنید."),
    ("چرا باید مدارک آپلود کنم؟",
     "آپلود مدارک (تصویر پرسنلی، کارت ملی، گواهی و…) هویت شما را تأیید و سطح "
     "دسترسی حساب شما را کامل می‌کند. مدارک فقط برای کارشناسان مجاز قابل مشاهده است."),
    ("مشاهدهٔ پیش‌نمایش پروفایل چیست؟",
     "با دکمهٔ «پیش‌نمایش» می‌توانید پروفایل را همان‌گونه که مدیران می‌بینند "
     "بررسی و در صورت نیاز اصلاح کنید."),
]


def _faq_html(items, open_first=False):
    out = []
    for i, (q, a) in enumerate(items, start=1):
        open_attr = " open" if (open_first and i == 1) else ""
        out.append(
            '<div class="hb-info-faq" style="border:1px solid var(--hb-border);'
            'border-radius:10px;margin-bottom:0.6rem;background:var(--hb-navy-800);">'
            f'<details{open_attr}><summary style="cursor:pointer;padding:0.9rem 1.1rem;'
            'font-weight:600;color:var(--hb-text-primary);list-style:none;">'
            f'<i class="bi bi-question-circle" style="color:var(--hb-gold-300);margin-inline-end:0.5rem;"></i>{q}</summary>'
            f'<div style="padding:0 1.1rem 0.9rem;color:var(--hb-text-secondary);line-height:1.9;">{a}</div>'
            "</details></div>"
        )
    return "".join(out)


ABOUT_CONTENT = """
<p style="color:var(--hb-text-secondary);line-height:2;">
<strong>حبیب‌هاب (HabibHub)</strong> سامانهٔ یکپارچهٔ مدیریت اطلاعات و خدمات است؛ جایی که همهٔ
ابزارهای مورد نیاز شما — پروفایل هوشمند، کیف پول و سکه، حسابداری، تیکت، مجلهٔ دانستنی‌ها و
مرکز بازی — در یک هاب گرد هم آمده‌اند.</p>

<div class="hb-info-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem;margin:1.25rem 0;">
<div class="hb-card" style="margin:0;text-align:center;"><i class="bi bi-bullseye" style="font-size:2rem;color:var(--hb-gold-300);"></i><h4 style="margin:0.6rem 0 0.4rem;">مأموریت ما</h4><p style="font-size:0.9rem;">توانمندسازی کاربران با سامانه‌ای امن، ساده و یکپارچه برای مدیریت اطلاعات شخصی، مالی و ارتباطی.</p></div>
<div class="hb-card" style="margin:0;text-align:center;"><i class="bi bi-eye" style="font-size:2rem;color:var(--hb-gold-300);"></i><h4 style="margin:0.6rem 0 0.4rem;">چشم‌انداز ما</h4><p style="font-size:0.9rem;">تبدیل شدن به معتمدترین پلتفرم خدمات یکپارچه، جایی که فناوری به خدمت آسایش و پیشرفت کاربران درمی‌آید.</p></div>
</div>

<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-lightbulb" style="color:var(--hb-gold-300);"></i> ارزش‌های ما</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li><strong>امانت‌داری:</strong> اسناد، اطلاعات و امتیازهای شما نزد ما امانت است و با دقت حفظ می‌شود.</li>
<li><strong>شفافیت:</strong> همهٔ تراکنش‌های سکه، امتیازها و وضعیت درخواست‌ها در برنامه قابل مشاهده است.</li>
<li><strong>پاسخ‌گویی:</strong> با مرکز تیکت و تضمین زمان پاسخ، همیشه کنار شما هستیم.</li>
<li><strong>نوآوری:</strong> به‌روزرسانی مستمر ماژول‌ها بر اساس بازخورد کاربران.</li>
</ul>

<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-journal-check" style="color:var(--hb-gold-300);"></i> حبیب‌هاب در یک نگاه</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li>پروفایل کامل با بخش‌های شخصی، خانواده، تحصیلات، شغلی، مالی و مدارک</li>
<li>کیف پول با خرید، فروش، انتقال سکه و تبدیل خودکار امتیاز به سکه</li>
<li>مرکز تیکت با دسته‌بندی، اولویت و زمان پاسخ تضمین‌شده</li>
<li>مجلهٔ دانستنی‌ها و مرکز بازی برای اوقات فراغت</li>
</ul>
"""

PRIVACY_CONTENT = """
<p style="color:var(--hb-text-secondary);line-height:2;">حریم خصوصی شما برای ما مهم است. این سند توضیح می‌دهد حبیب‌هاب چه داده‌هایی جمع‌آوری می‌کند، چگونه از آن‌ها استفاده می‌شود و چه حقوقی دارید. با استفاده از برنامه، با همین شیوه‌ها موافقت می‌کنید.</p>

<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-database" style="color:var(--hb-gold-300);"></i> داده‌هایی که جمع‌آوری می‌کنیم</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li><strong>اطلاعات هویتی:</strong> نام، کد ملی، تاریخ تولد و اطلاعات تماس که در پروفایل ثبت می‌کنید.</li>
<li><strong>اطلاعات مالی:</strong> شماره شبا و حساب برای خرید، فروش و انتقال سکه، و رسیدهای پرداخت.</li>
<li><strong>مدارک:</strong> تصاویر پرسنلی، کارت ملی و گواهی‌هایی که برای تأیید هویت آپلود می‌کنید.</li>
<li><strong>داده‌های فنی:</strong> شماره موبایل برای ورود، موقعیت مکانی (فقط با اجازهٔ شما) و اطلاعات مرورگر.</li>
</ul>

<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-gear" style="color:var(--hb-gold-300);"></i> چگونه از داده‌ها استفاده می‌کنیم</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li>ارائهٔ خدمات اصلی برنامه: پروفایل، کیف پول، انتقال سکه و امتیازها</li>
<li>تأیید هویت و بررسی درخواست‌های خرید و فروش سکه</li>
<li>پاسخ به تیکت‌ها و اطلاع‌رسانی وضعیت درخواست‌ها</li>
<li>پیشگیری از تخلف و حفظ امنیت حساب‌ها</li>
</ul>

<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-shield-lock" style="color:var(--hb-gold-300);"></i> محافظت از داده‌ها</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li>دسترسی به اطلاعات شخصی و مدارک فقط برای کارشناسان مجاز و با ثبت ردپا.</li>
<li>ارتباطات برنامه رمزگذاری‌شده است و داده‌ها روی سرورهای امن نگهداری می‌شود.</li>
<li>مدارک شما هرگز با اشخاص ثالث به‌جز در مقررات قانونی به اشتراک گذاشته نمی‌شود.</li>
</ul>

<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-person-check" style="color:var(--hb-gold-300);"></i> حقوق شما</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li><strong>دسترسی:</strong> مشاهدهٔ و دریافت اطلاعات ثبت‌شدهٔ خود در پروفایل.</li>
<li><strong>اصلاح:</strong> ویرایش اطلاعات و ثبت درخواست اصلاح کد ملی از طریق تیکت.</li>
<li><strong>حذف:</strong> درخواست حذف حساب و داده‌های وابسته از طریق پشتیبانی.</li>
<li><strong>اعتراض:</strong> اعلام مخالفت با هر پردازش داده از طریق «تماس با ما».</li>
</ul>
"""

TERMS_CONTENT = """
<p style="color:var(--hb-text-secondary);line-height:2;">با ثبت‌نام و استفاده از حبیب‌هاب، این شرایط را می‌پذیرید. لطفاً پیش از استفاده، آن‌ها را با دقت بخوانید.</p>

<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-person-badge" style="color:var(--hb-gold-300);"></i> حساب کاربری</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li>اطلاعات پروفایل و کد ملی باید واقعی و متعلق به خودتان باشد؛ ثبت اطلاعات دیگران موجب تعلیق حساب می‌شود.</li>
<li>مسئولیت حفظ رمز انتقال و امنیت حساب با شماست؛ هر فعالیتی با حساب شما به نام شما ثبت می‌شود.</li>
<li>هر شخص فقط یک حساب کاربری دارد.</li>
</ul>

<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-coin" style="color:var(--hb-gold-300);"></i> سکه، امتیاز و تراکنش‌ها</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li>سکه پس از تأیید رسید پرداخت به کیف پول اضافه می‌شود؛ بازهٔ تأیید در ساعات اداری حداکثر یک روز کاری است.</li>
<li>نرخ خرید و فروش و سقف‌ها در «تنظیمات کیف پول» ادمین تعیین می‌شود و ممکن است به‌روزرسانی شود.</li>
<li>امتیازهای کسب‌شده به‌صورت خودکار و بر اساس «تعرفه امتیازها» به سکه تبدیل و تجمیع می‌شود؛ امتیاز قابل فروش مستقیم نیست.</li>
<li>انتقال سکه پس از تأیید دومرحله‌ای انجام می‌شود و قابل بازگشت نیست؛ در صورت خطا سریعاً به پشتیبانی اطلاع دهید.</li>
<li>درخواست فروش سکه پس از تأیید دومرحله‌ای، طی ساعات کاری به شبأ اعلامی واریز می‌شود.</li>
</ul>

<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-file-earmark-text" style="color:var(--hb-gold-300);"></i> محتوا و مدارک</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li>محتوای مجلهٔ دانستنی‌ها و پاسخ‌ها فقط برای اطلاع‌رسانی است و توصیهٔ تخصصی مالی یا حقوقی محسوب نمی‌شود.</li>
<li>آپلود مدارک جعلی یا محتوای مغایر قوانین، موجب توقف خدمات و در صورت لزوم معرفی به مراجع قانونی می‌شود.</li>
</ul>

<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-x-circle" style="color:var(--hb-gold-300);"></i> توقف یا خاتمهٔ حساب</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li>در صورت تخلف از شرایط، برنامه می‌تواند حساب را موقتاً متوقف یا خاتمه دهد؛ موجودی سکه تا پایان بررسی مسدود می‌شود.</li>
<li>شما هر زمان می‌توانید با اطلاع پشتیبانی، استفاده از برنامه را خاتمه دهید.</li>
</ul>

<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-shield-exclamation" style="color:var(--hb-gold-300);"></i> سلب مسئولیت</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li>سرویس «همان‌گونه که هست» ارائه می‌شود و برنامه مسئول وقفهٔ موقت، خرابی شبکهٔ کاربر یا خطای ورود اطلاعات توسط کاربر نیست.</li>
<li>مسئولیت صحت کد ملی، شبا و اطلاعات وارده به هنگام خرید، فروش و انتقال، با کاربر است.</li>
</ul>
"""

SUPPORT_CONTENT = """
<p style="color:var(--hb-text-secondary);line-height:2;">سؤالی دارید؟ تیم پشتیبانی حبیب‌هاب آمادهٔ پاسخ‌گویی است. سریع‌ترین راه، ثبت تیکت در «مرکز تیکت» است؛ پاسخ در همان تیکت ثبت و با اعلان به شما اعلام می‌شود.</p>

<div class="hb-info-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem;margin:1.25rem 0;">
<div class="hb-card" style="margin:0;text-align:center;"><i class="bi bi-chat-left-dots" style="font-size:2rem;color:var(--hb-gold-300);"></i><h4 style="margin:0.6rem 0 0.4rem;">مرکز تیکت</h4><p style="font-size:0.9rem;">ثبت درخواست، پیگیری و گفتگو با کارشناسان</p><a class="hb-btn hb-btn-primary hb-btn-sm" style="text-decoration:none;" href="/tickets/">ثبت تیکت</a></div>
<div class="hb-card" style="margin:0;text-align:center;"><i class="bi bi-book" style="font-size:2rem;color:var(--hb-gold-300);"></i><h4 style="margin:0.6rem 0 0.4rem;">مرکز راهنما</h4><p style="font-size:0.9rem;">راهنمای گام‌به‌گام ماژول‌ها و پرسش‌های متداول</p><a class="hb-btn hb-btn-outline hb-btn-sm" style="text-decoration:none;" href="/pages/help/">مشاهدهٔ راهنما</a></div>
</div>

<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-clock-history" style="color:var(--hb-gold-300);"></i> زمان پاسخ تضمین‌شده (SLA)</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li>بحرانی: حداکثر ۳۰ دقیقه &nbsp;|&nbsp; فوری: ۲ ساعت &nbsp;|&nbsp; بالا: ۸ ساعت</li>
<li>عادی: ۲۴ ساعت &nbsp;|&nbsp; کم: ۴۸ ساعت (زمان اداری)</li>
<li>تیکت‌های <strong>مالی</strong> (خرید، فروش و انتقال سکه) با اولویت بالا بررسی می‌شوند.</li>
</ul>

<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-list-check" style="color:var(--hb-gold-300);"></i> ثبت تیکت مؤثر</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li>موضوع و دستهٔ درست را انتخاب کنید (مثلاً «مالی» برای مسائل سکه).</li>
<li>کد پیگیری سفارش (مثل WAL-…) یا شماره تیکت مربوط را در توضیحات بنویسید.</li>
<li>برای مسائل پرداخت، تصویر رسید را در تیکت پیوست کنید.</li>
</ul>
"""

HELP_CONTENT = """
<p style="color:var(--hb-text-secondary);line-height:2;">راهنمای گام‌به‌گام ماژول‌های حبیب‌هاب و پاسخ پرسش‌های متداول.</p>

<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-person-vcard" style="color:var(--hb-gold-300);"></i> پروفایل من</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li>بخش‌ها به‌صورت کشویی بسته‌اند؛ روی عنوان هر بخش کلیک کنید تا باز شود.</li>
<li>نام و نام خانوادگی از فهرست استاندارد انتخاب می‌شود؛ کافی است چند حرف تایپ کنید.</li>
<li>مشاهدهٔ پیش‌نمایش پروفایل پیش از ذخیره، از دکمهٔ «پیش‌نمایش».</li>
</ul>
""" + _faq_html(PROFILE_FAQ_ITEMS) + """
<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-wallet2" style="color:var(--hb-gold-300);"></i> کیف پول و سکه</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li>«بانک مبادلات» بالای کیف پول، موجودی امتیاز شما و نرخ تبدیل آن به سکه را نشان می‌دهد؛ امتیازها خودکار به سکه اضافه می‌شود.</li>
<li>در «انتقال سکه به دیگران» کد ملی فقط عدد می‌پذیرد و فهرست گیرندگان به‌صورت آبشاری باز می‌شود.</li>
<li>در طول عملیات طولانی، تصویر سکه با پیام «لطفاً منتظر بمانید» نمایش داده می‌شود؛ صفحه را نبندید.</li>
</ul>
""" + _faq_html(WALLET_FAQ_ITEMS) + """
<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-chat-left-dots" style="color:var(--hb-gold-300);"></i> مرکز تیکت</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li>هر موضوع یک تیکت؛ می‌توانید فایل پیوست کنید و پاسخ‌ها را امتیاز دهید.</li>
</ul>
""" + _faq_html(TICKET_FAQ_ITEMS) + """
<h4 style="margin:1.25rem 0 0.75rem;"><i class="bi bi-people" style="color:var(--hb-gold-300);"></i> معرفی دوستان</h4>
<ul style="line-height:2.1;color:var(--hb-text-secondary);">
<li>در صفحهٔ ورود، دوست‌تان کد ملی شما را در «کد ملی معرف» وارد کند؛ پس از تکمیل ثبت‌نام، امتیاز معرفی به شما تعلق می‌گیرد.</li>
<li>سقف امتیاز معرفی در «تعرفه امتیازها» تعیین می‌شود و امتیازها خودکار به سکه تبدیل می‌شود.</li>
</ul>
"""

CONTACT_CONTENT = """
<p style="color:var(--hb-text-secondary);line-height:2;">برای ارتباط با تیم حبیب‌هاب از یکی از راه‌های زیر استفاده کنید. برای پیگیری سریع‌تر، کد پیگیری (تیکت یا سفارش) را ذکر کنید.</p>

<div class="hb-info-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem;margin:1.25rem 0;">
<div class="hb-card" style="margin:0;text-align:center;"><i class="bi bi-chat-left-dots" style="font-size:2rem;color:var(--hb-gold-300);"></i><h4 style="margin:0.6rem 0 0.4rem;">تیکت پشتیبانی</h4><p style="font-size:0.9rem;">سریع‌ترین راه دریافت پاسخ، با زمان پاسخ تضمین‌شده</p><a class="hb-btn hb-btn-primary hb-btn-sm" style="text-decoration:none;" href="/tickets/">ثبت تیکت</a></div>
</div>


"""

PAGES = [
    {
        "slug": "about",
        "title": "دربارهٔ حبیب‌هاب",
        "subtitle": "داستان، مأموریت و ارزش‌های ما",
        "icon": "bi-info-circle",
        "content": ABOUT_CONTENT.strip(),
        "sort_order": 10,
    },
    {
        "slug": "help",
        "title": "مرکز راهنما",
        "subtitle": "راهنمای ماژول‌ها و پرسش‌های متداول",
        "icon": "bi-life-preserver",
        "content": HELP_CONTENT.strip(),
        "sort_order": 20,
    },
    {
        "slug": "support",
        "title": "پشتیبانی",
        "subtitle": "هر سؤالی دارید، اینجا پاسخ می‌گیرید",
        "icon": "bi-headset",
        "content": SUPPORT_CONTENT.strip(),
        "sort_order": 30,
    },
    {
        "slug": "contact",
        "title": "تماس با ما",
        "subtitle": "راه‌های ارتباط با تیم حبیب‌هاب",
        "icon": "bi-envelope",
        "content": CONTACT_CONTENT.strip(),
        "sort_order": 40,
        "contact_phone": "۰۲۱-۹۱۰۰۹۹۱۴",
        "contact_email": "support@habibhub.ir",
        "contact_hours": "شنبه تا پنجشنبه، ۹ تا ۱۸",
        "contact_address": "تهران، ایران",
    },
    {
        "slug": "privacy",
        "title": "حریم خصوصی",
        "subtitle": "داده‌های شما چگونه محافظت می‌شود",
        "icon": "bi-shield-check",
        "content": PRIVACY_CONTENT.strip(),
        "show_in_sidebar": False,
        "sort_order": 50,
    },
    {
        "slug": "terms",
        "title": "قوانین و مقررات",
        "subtitle": "شرایط استفاده از حبیب‌هاب",
        "icon": "bi-file-earmark-text",
        "content": TERMS_CONTENT.strip(),
        "show_in_sidebar": False,
        "sort_order": 60,
    },
]

SUPPORT_TICKET_HOURS = "شنبه تا پنجشنبه ۹ تا ۱۸"


class Command(BaseCommand):
    help = "درج/به‌روزرسانی صفحات اطلاعاتی فارسی حبیب‌هاب"

    def handle(self, *args, **options):
        created_count = 0
        for spec in PAGES:
            obj, created = InfoPage.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "title": spec["title"],
                    "subtitle": spec["subtitle"],
                    "icon": spec["icon"],
                    "content": spec["content"],
                    "show_in_sidebar": spec.get("show_in_sidebar", True),
                    "show_in_footer": True,
                    "sort_order": spec["sort_order"],
                    "is_active": True,
                    "contact_phone": spec.get("contact_phone", ""),
                    "contact_email": spec.get("contact_email", ""),
                    "contact_hours": spec.get("contact_hours", ""),
                    "contact_address": spec.get("contact_address", ""),
                },
            )
            created_count += 1 if created else 0
        self.stdout.write(self.style.SUCCESS(
            f"صفحات اطلاعاتی همگام شد ({created_count} مورد جدید از {len(PAGES)} صفحه)."
        ))
