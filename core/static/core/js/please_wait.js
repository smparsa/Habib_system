/*
 * اورلی «واحد» و سراسریِ «لطفاً منتظر بمانید… / Please Wait» — مستقل از app.js.
 *
 * فقط همین یک اورلی در کل برنامه وجود دارد (لوگوی سکهٔ حبیب‌هاب: تصویر/GIF آپلودشدهٔ ادمین در
 * تنظیمات کیف پول یا تصویر پیش‌فرض static). پنل مدیریت و فضای ابری هم از همین استفاده می‌کنند
 * تا هرگز دو اورلی هم‌زمان نمایش داده نشود.
 *
 * دو راه فعال‌شدن:
 *  ۱) خودکار: ارسال هر فرم و کلیک روی پیوند داخلی (گذر به صفحهٔ بعد) — اگر بیش از ۲ ثانیه طول بکشد.
 *  ۲) برنامه‌نویسی (برای عملیات‌های fetch/AJAX): ``hbPleaseWait.begin(label?, delayMs?)`` در ابتدا و
 *     ``hbPleaseWait.end()`` در پایان. چند عملیات هم‌زمان شمرده می‌شوند و اورلی تا پایانِ آخرین باقی
 *     می‌ماند. ``hbPleaseWait.label(text)`` متن زیر عنوان را عوض می‌کند. ``window.hbWait`` همان
 *     ``{begin, end}`` است (سازگاری با کد قدیمی).
 *
 * این فایل باید در «همهٔ» صفحه‌ها بارگذاری شود؛ صفحه‌هایی که app.js دارند آن را از طریق app.js می‌گیرند و
 * بقیه با ``{% include "core/_please_wait.html" %}``. اجرای دوباره بی‌اثر است (``__hbPwBound``).
 *
 * تنظیمات:
 *  - ``data-no-please-wait`` روی فرم/لینک (یا والدشان): اورلی نمایش داده نمی‌شود (مثل دانلود فایل).
 *  - ``data-pw-delay="800"``: تأخیر اختصاصی پیش از نمایش (میلی‌ثانیه).
 *  - ``window.HB_PLEASE_WAIT_DELAY`` (پیش‌فرض ۲۰۰۰ms) پیش از بارگذاری این فایل.
 */
(function () {
  'use strict';
  if (window.__hbPwBound) return;
  window.__hbPwBound = true;

  var DELAY = typeof window.HB_PLEASE_WAIT_DELAY === 'number' ? window.HB_PLEASE_WAIT_DELAY : 2000;
  // اگر سرور هیچ‌وقت پاسخ ندهد/دانلود شود، قفل صفحه برای همیشه نماند.
  var FAILSAFE_MS = 120000;
  var DOWNLOAD_RE = /\.(csv|xlsx?|xlsm|pdf|zip|rar|7z|docx?|pptx?|json|txt|xml|sql|bak|apk|exe|dmg|mp3|mp4)$/i;

  var scriptSrc = (document.currentScript && document.currentScript.src) || '';
  var staticBase = scriptSrc ? scriptSrc.replace(/core\/js\/please_wait(?:_new)?\.js.*$/, '') : '/static/';

  var navTimer = null, holdTimer = null, failsafe = null;
  var active = false;          // اورلی در حال نمایش (یا در آستانهٔ نمایش پس از بارگذاری تصویر)
  var navBusy = false;         // گذر به صفحهٔ بعد (ارسال فرم/کلیک لینک) در جریان است
  var holds = 0;               // تعداد عملیات‌های برنامه‌نویسی‌شدهٔ در جریان (begin/end)
  var labelText = '';
  var coinUrl = '', coinTried = false, seq = 0;

  function build() {
    if (document.getElementById('hb-please-wait-overlay')) return;
    var style = document.createElement('style');
    style.id = 'hb-please-wait-style';
    style.textContent = [
      '#hb-please-wait-overlay{position:fixed;inset:0;z-index:99999;display:flex;align-items:center;justify-content:center;background:rgba(5,14,26,0.78);backdrop-filter:blur(2px);}',
      '#hb-please-wait-overlay[hidden]{display:none;}',
      '.hb-pw-box{display:flex;flex-direction:column;align-items:center;gap:0.85rem;padding:1.9rem 2.6rem;max-width:min(92vw,420px);text-align:center;background:var(--hb-navy-800,#101f33);border:1px solid rgba(212,175,55,0.45);border-radius:16px;box-shadow:0 14px 44px rgba(0,0,0,0.55);}',
      '.hb-pw-coin{width:96px;height:96px;object-fit:contain;border-radius:50%;}',
      '.hb-pw-coin.hb-pw-anim{animation:hbPwFlip 1.4s linear infinite;}',
      '@keyframes hbPwFlip{0%{transform:rotateY(0deg)}100%{transform:rotateY(360deg)}}',
      '.hb-pw-title{font-weight:800;font-size:1rem;color:var(--hb-gold-300,#d4af37);}',
      '.hb-pw-label{font-size:0.82rem;line-height:1.8;color:var(--hb-text-secondary,#c4d0de);}',
      '.hb-pw-sub{font-size:0.78rem;letter-spacing:0.2em;color:var(--hb-text-muted,#8aa0b8);direction:ltr;}',
      'body.hb-pw-lock{overflow:hidden;}',
      'body.hb-pw-lock *{pointer-events:none !important;}',
      'body.hb-pw-lock #hb-please-wait-overlay,body.hb-pw-lock #hb-please-wait-overlay *{pointer-events:auto !important;}'
    ].join('\n');
    document.head.appendChild(style);
    var ov = document.createElement('div');
    ov.id = 'hb-please-wait-overlay';
    ov.hidden = true;
    ov.setAttribute('role', 'status');
    ov.setAttribute('aria-live', 'polite');
    ov.setAttribute('aria-busy', 'true');
    ov.innerHTML = '<div class="hb-pw-box">' +
      '<img class="hb-pw-coin" alt="سکهٔ حبیب‌هاب" src="">' +
      '<div class="hb-pw-title">لطفاً منتظر بمانید…</div>' +
      '<div class="hb-pw-label" style="display:none"></div>' +
      '<div class="hb-pw-sub">Please Wait</div>' +
      '</div>';
    document.body.appendChild(ov);
  }

  function paintLabel() {
    var el = document.querySelector('#hb-please-wait-overlay .hb-pw-label');
    if (!el) return;
    el.textContent = labelText;
    el.style.display = labelText ? '' : 'none';
  }

  function setLabel(text) {
    labelText = text ? String(text) : '';
    paintLabel();
  }

  function coinSrc(ready) {
    // اولویت: متاتگ صفحه → تصویر آپلودشدهٔ ادمین (wallet:coin_image_url) → تصویر پیش‌فرض static
    var meta = document.querySelector('meta[name="hb-coin-image"]');
    if (meta && meta.content) { ready(meta.content); return; }
    if (coinUrl) { ready(coinUrl); return; }
    var fallback = staticBase + 'core/assets/coin.jpg';
    if (coinTried) { ready(fallback); return; }
    coinTried = true;
    fetch('/wallet/coin-image/', { headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var url = (data && data.url) || '';
        if (url) { coinUrl = url; ready(url); } else ready(fallback);
      })
      .catch(function () { ready(fallback); });
  }

  function show() {
    if (!(navBusy || holds > 0)) return;           // در فاصلهٔ تأخیر، همهٔ عملیات‌ها تمام شده باشد
    if (!document.body) return;
    build();
    var ov = document.getElementById('hb-please-wait-overlay');
    if (!ov || active) return;
    active = true;
    coinSrc(function (src) {
      if (!active) return;                          // در فاصلهٔ بارگذاری تصویر، عملیات لغو شده باشد
      var img = ov.querySelector('.hb-pw-coin');
      if (img && img.getAttribute('src') !== src) {
        img.src = src;
        // GIF خودش متحرک است؛ برای تصویر ثابت، چرخش سکه با CSS افزوده می‌شود
        img.classList.toggle('hb-pw-anim', !/\.gif(\?|$)/i.test(src));
      }
      paintLabel();
      ov.hidden = false;
      document.body.classList.add('hb-pw-lock');
      document.body.setAttribute('aria-busy', 'true');
      if (failsafe) clearTimeout(failsafe);
      failsafe = setTimeout(cancel, FAILSAFE_MS);
    });
  }

  function hideNow() {
    active = false;
    if (failsafe) { clearTimeout(failsafe); failsafe = null; }
    var ov = document.getElementById('hb-please-wait-overlay');
    if (ov) ov.hidden = true;
    if (document.body) {
      document.body.classList.remove('hb-pw-lock');
      document.body.removeAttribute('aria-busy');
    }
  }

  // اگر دیگر هیچ عملیاتی (نه گذر به صفحه، نه begin/end) در جریان نیست، اورلی برداشته می‌شود.
  function settle() {
    if (navBusy || holds > 0) return;
    if (navTimer) { clearTimeout(navTimer); navTimer = null; }
    if (holdTimer) { clearTimeout(holdTimer); holdTimer = null; }
    hideNow();
    setLabel('');
  }

  // بازنشانی کامل (بازگشت از کش مرورگر، یا قفل‌شکن ایمنی)
  function cancel() {
    if (navTimer) { clearTimeout(navTimer); navTimer = null; }
    if (holdTimer) { clearTimeout(holdTimer); holdTimer = null; }
    navBusy = false;
    holds = 0;
    hideNow();
    setLabel('');
  }

  function delayFor(el) {
    var host = el && el.closest ? el.closest('[data-pw-delay]') : null;
    var v = host ? parseInt(host.getAttribute('data-pw-delay'), 10) : NaN;
    return isNaN(v) || v < 0 ? DELAY : v;
  }

  // --- گذر به صفحهٔ بعد (ارسال فرم / کلیک پیوند) ---
  function arm(ms) {
    if (navTimer) clearTimeout(navTimer);
    var token = ++seq;
    navBusy = true;
    navTimer = setTimeout(function () { navTimer = null; show(); }, typeof ms === 'number' ? ms : DELAY);
    return token;
  }

  function cancelNav(token) {
    // اگر پس از این رویداد، مسلح‌سازیِ جدیدی انجام شده، تایمرِ آن نباید لغو شود.
    if (token !== undefined && token !== seq) return;
    if (navTimer) { clearTimeout(navTimer); navTimer = null; }
    navBusy = false;
    settle();
  }

  // --- عملیات برنامه‌نویسی‌شده (fetch/AJAX) ---
  function begin(label, ms) {
    holds += 1;
    if (label) setLabel(label);
    if (!active && !holdTimer) {
      holdTimer = setTimeout(function () { holdTimer = null; show(); }, typeof ms === 'number' ? ms : DELAY);
    }
  }

  function end() {
    if (holds > 0) holds -= 1;
    if (holds === 0) {
      if (holdTimer) { clearTimeout(holdTimer); holdTimer = null; }
      settle();
    }
  }

  window.hbPleaseWait = {
    arm: arm,
    begin: begin,
    end: end,
    label: setLabel,
    start: function (label) { begin(label, 0); },   // فوری (بدون تأخیر)
    cancel: cancel
  };
  if (!window.hbWait) window.hbWait = { begin: begin, end: end };   // سازگاری با فضای ابری

  // ۱) ارسال هر فرم
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (form && form.closest && form.closest('[data-no-please-wait]')) return;
    if (form && form.target && form.target !== '_self') return;     // تب/پنجرهٔ دیگر: این صفحه عوض نمی‌شود
    var token = arm(delayFor(form));
    // اگر هندلر دیگری submit را لغو کرد (مثل confirm یا تأیید دومرحله‌ای)، اورلی برداشته می‌شود
    setTimeout(function () { if (e.defaultPrevented) cancelNav(token); }, 0);
  }, true);

  // ۲) کلیک روی پیوندهای داخلی (گذر به صفحهٔ بعد)
  document.addEventListener('click', function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var a = e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    if (a.closest('[data-no-please-wait]')) return;
    var href = a.getAttribute('href') || '';
    if (!href || href.charAt(0) === '#' || href.slice(0, 11).toLowerCase() === 'javascript:') return;
    if (a.target === '_blank' || a.hasAttribute('download')) return;
    if (a.origin && a.origin !== window.location.origin) return;
    // دانلود فایل (CSV/PDF/…): صفحه عوض نمی‌شود، پس اورلی هرگز برداشته نمی‌شد
    if (DOWNLOAD_RE.test(a.pathname || '')) return;
    // پرش درون‌صفحه‌ای (#...) گذر به صفحهٔ بعد نیست
    var dest = (a.origin || '') + a.pathname + a.search;
    var here = window.location.origin + window.location.pathname + window.location.search;
    if (dest === here) return;
    var token = arm(delayFor(a));
    setTimeout(function () { if (e.defaultPrevented) cancelNav(token); }, 0);
  }, true);

  // ۳) بازگشت به صفحه از کش مرورگر (Back/Forward): قفل و اورلی حتماً برداشته شود
  window.addEventListener('pageshow', cancel);
})();
