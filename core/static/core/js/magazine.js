/* ============================================
   HABIBHUB - مجله دانستنی‌ها (Magazine)
   واکنش با ۱۰ ایموجی، انتشار مطلب توسط ادمین (تا ۵۰MB)،
   و تایمر ۳۰ دقیقه‌ای «ماندن در صفحه → ۱ سکه».
   وابسته به app.js (showToast / toFa) که پیش از این فایل لود می‌شود.
   ============================================ */
(function () {
  const page = document.querySelector('[data-magazine-page]');
  const inboxPage = document.querySelector('[data-inbox-page]');
  if (!page && !inboxPage) return;

  const csrfMatch = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
  const csrfToken = csrfMatch ? decodeURIComponent(csrfMatch[1]) : '';

  function api(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': csrfToken,
      },
      body: body ? new URLSearchParams(body).toString() : '',
    }).then((r) => r.json());
  }

  const toFa = (window.toFa || ((s) => String(s)));
  const showToast = (window.showToast || function () {});
  const WATCH_SECONDS = 1800;

  // شمارندهٔ اولیهٔ واکنش‌ها (رندر سمت سرور) را به ارقام فارسی تبدیل کن
  document.querySelectorAll('.mag-react-count').forEach((el) => {
    if (el.textContent && /[0-9]/.test(el.textContent)) el.textContent = toFa(el.textContent);
  });

  /* ---------- زمان نسبی (پیش از این) ---------- */
  document.querySelectorAll('[data-mag-time]').forEach((el) => {
    const iso = el.getAttribute('data-mag-time');
    if (!iso) return;
    const then = new Date(iso);
    const diff = Math.max(0, Date.now() - then.getTime());
    const min = Math.floor(diff / 60000);
    let label;
    if (min < 1) label = 'همین الان';
    else if (min < 60) label = toFa(min) + ' دقیقه پیش';
    else if (min < 1440) label = toFa(Math.floor(min / 60)) + ' ساعت پیش';
    else label = toFa(Math.floor(min / 1440)) + ' روز پیش';
    el.textContent = label;
  });

  /* ---------- واکنش‌ها (مثل تلگرام) ---------- */
  document.querySelectorAll('[data-reactions]').forEach((bar) => {
    const postId = bar.getAttribute('data-post-id');
    const buttons = bar.querySelectorAll('[data-react]');
    buttons.forEach((btn) => {
      btn.addEventListener('click', async () => {
        if (btn.classList.contains('busy')) return;
        btn.classList.add('busy');
        const emoji = btn.getAttribute('data-emoji');
        let data = null;
        try {
          data = await api('/magazine/react/', { post_id: postId, emoji: emoji });
        } catch (e) { /* شبکه */ }
        btn.classList.remove('busy');
        if (!data || data.status !== 'ok') {
          showToast('خطا در ثبت واکنش؛ دوباره تلاش کنید.', 'error');
          return;
        }
        const mine = data.my || [];
        buttons.forEach((b) => {
          const e = b.getAttribute('data-emoji');
          const count = (data.counts && data.counts[e]) || 0;
          b.classList.toggle('active', mine.indexOf(e) !== -1);
          const cnt = b.querySelector('.mag-react-count');
          if (cnt) cnt.textContent = count ? toFa(count) : '';
          b.classList.toggle('has-count', count > 0);
        });
      });
    });
  });

  /* ---------- انتشار مطلب توسط ادمین (پیش‌بررسی حجم < ۵۰MB) ---------- */
  const composer = document.querySelector('[data-mag-composer]');
  if (composer) {
    const fileInput = composer.querySelector('[data-mag-files]');
    const fileHint = composer.querySelector('[data-mag-file-hint]');
    const textInput = composer.querySelector('[data-mag-text]');
    const submitBtn = composer.querySelector('[data-mag-publish]');
    const errBox = composer.querySelector('[data-mag-composer-error]');
    const MAX_BYTES = 50 * 1024 * 1024;

    const fmtBytes = (b) => {
      const mb = b / (1024 * 1024);
      return (mb >= 10 ? mb.toFixed(0) : mb.toFixed(1)) + ' مگابایت';
    };
    const setError = (msg) => {
      if (!errBox) return;
      errBox.textContent = msg || '';
      errBox.hidden = !msg;
    };
    const updateHint = () => {
      if (!fileHint) return;
      const files = Array.from(fileInput.files || []);
      if (!files.length) {
        fileHint.textContent = '';
        fileHint.hidden = true;
        return;
      }
      const total = files.reduce((s, f) => s + f.size, 0);
      fileHint.hidden = false;
      fileHint.innerHTML = files.map((f) => f.name).join('، ') +
        ' — مجموع: ' + fmtBytes(total);
      fileHint.style.color = total < MAX_BYTES ? 'var(--hb-text-muted)' : '#ff8a80';
    };
    fileInput.addEventListener('change', updateHint);
    composer.addEventListener('submit', (e) => {
      const files = Array.from(fileInput.files || []);
      const total = files.reduce((s, f) => s + f.size, 0);
      const text = (textInput ? textInput.value : '').trim();
      if (!text && !files.length) {
        e.preventDefault();
        setError('مطلب خالی است؛ متن بنویسید یا فایل پیوست کنید.');
        if (textInput) textInput.focus();
        return;
      }
      if (total >= MAX_BYTES) {
        e.preventDefault();
        setError('حجم کل فایل‌ها باید زیر ۵۰ مگابایت باشد. (' + fmtBytes(total) + ' انتخاب شده)');
        return;
      }
      setError('');
      if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'در حال انتشار…'; }
    });
  }

  /* ---------- ضدکپی محتوا + لینک مطلب + فوروارد + فوکوس به مطلب (فقط مجله) ---------- */
  if (page) {
    const insideProtected = (node) => {
      if (!node) return false;
      const el = node.nodeType === 1 ? node : node.parentElement;
      return !!(el && el.closest && el.closest('.mag-protected'));
    };

    // هیچ کاربری نمی‌تواند متن/تصویر/کلیپ/آهنگ مطلب را انتخاب، کپی یا ذخیره کند
    document.addEventListener('selectstart', (e) => {
      if (insideProtected(e.target)) e.preventDefault();
    });
    document.addEventListener('copy', (e) => {
      const sel = window.getSelection();
      let hit = false;
      if (sel && sel.rangeCount) {
        const r = sel.getRangeAt(0);
        hit = insideProtected(r.startContainer) || insideProtected(r.endContainer);
      } else {
        hit = insideProtected(e.target);
      }
      if (hit) {
        e.preventDefault();
        showToast('کپی محتوای مطلب مجاز نیست؛ فقط دکمهٔ «کپی لینک مطلب» را می‌توانید بفرستید.', 'warning');
      }
    });
    document.addEventListener('cut', (e) => {
      if (insideProtected(e.target)) e.preventDefault();
    });
    document.addEventListener('contextmenu', (e) => {
      if (insideProtected(e.target)) e.preventDefault();
    });
    document.addEventListener('dragstart', (e) => {
      if (insideProtected(e.target)) e.preventDefault();
    });

    // لینک مطلب از زیر هر مطلب: بعد از انتشار، برای همه در دسترس است
    document.querySelectorAll('[data-copy-link]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const article = btn.closest('.mag-post');
        const link = (article && article.getAttribute('data-permalink')) || '';
        let ok = false;
        try {
          await navigator.clipboard.writeText(link);
          ok = true;
        } catch (e) { /* بدون مجوز کلیپ‌بورد */ }
        if (!ok && link) {
          const ta = document.createElement('textarea');
          ta.value = link;
          ta.style.position = 'fixed';
          ta.style.opacity = '0';
          document.body.appendChild(ta);
          ta.focus();
          ta.select();
          try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
          document.body.removeChild(ta);
        }
        showToast(
          ok ? 'لینک مطلب کپی شد؛ برای دیگران بفرستید.' : 'لینکی برای کپی یافت نشد.',
          ok ? 'success' : 'error'
        );
      });
    });

    // فوروارد مطلب برای عضو دیگر با کد ملی او → تیکت برای گیرنده
    const fwdOverlay = document.querySelector('[data-fwd-overlay]');
    if (fwdOverlay) {
      const nidInput = fwdOverlay.querySelector('[data-fwd-nid]');
      const errBox = fwdOverlay.querySelector('[data-fwd-error]');
      const sendBtn = fwdOverlay.querySelector('[data-fwd-send]');
      const selTarget = fwdOverlay.querySelector('[data-fwd-select]');
      let fwdPostId = null;

      // انتخاب آبشاری عضو از فهرست (در کنار تایپ دستی کد ملی)
      if (selTarget && nidInput) {
        selTarget.addEventListener('change', () => {
          if (!selTarget.value) return;
          nidInput.value = selTarget.value;
          if (errBox) errBox.textContent = '';
        });
        nidInput.addEventListener('input', () => {
          if (selTarget.value) selTarget.value = '';
        });
      }

      const toLatin = (s) => String(s || '')
        .replace(/[۰-۹]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d))
        .replace(/[٠-٩]/g, (d) => '٠١٢٣٤٥٦٧٨٩'.indexOf(d));
      const closeFwd = () => fwdOverlay.classList.remove('open');

      document.querySelectorAll('[data-forward-post]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const article = btn.closest('.mag-post');
          fwdPostId = article ? article.id.replace('mag-post-', '') : '';
          if (errBox) errBox.textContent = '';
          if (nidInput) nidInput.value = '';
          fwdOverlay.classList.add('open');
          setTimeout(() => { if (nidInput) nidInput.focus(); }, 160);
        });
      });
      document.querySelectorAll('[data-fwd-cancel]').forEach((b) => b.addEventListener('click', closeFwd));
      fwdOverlay.addEventListener('click', (e) => { if (e.target === fwdOverlay) closeFwd(); });
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && fwdOverlay.classList.contains('open')) closeFwd();
      });

      if (sendBtn) {
        const origHtml = sendBtn.innerHTML;
        sendBtn.addEventListener('click', async () => {
          if (!fwdPostId || !nidInput) return;
          const nid = toLatin(nidInput.value.trim());
          if (!/^\d{10}$/.test(nid)) {
            if (errBox) errBox.textContent = 'کد ملی گیرنده باید دقیقاً ۱۰ رقم باشد.';
            nidInput.focus();
            return;
          }
          sendBtn.disabled = true;
          sendBtn.textContent = 'در حال ارسال…';
          let data = null;
          try {
            data = await api('/magazine/forward/', { post_id: fwdPostId, national_id: nid });
          } catch (e) { /* شبکه */ }
          sendBtn.disabled = false;
          sendBtn.innerHTML = origHtml;
          if (!data || data.status !== 'ok') {
            if (errBox) errBox.textContent = (data && data.message) || 'ارسال نشد؛ دوباره تلاش کنید.';
            return;
          }
          closeFwd();
          showToast(data.message || 'تیکت برای عضو ارسال شد.', 'success');
        });
      }
    }

    // فوکوس به همان مطلب: ?focus=<id> یا #mag-post-<id>
    const focusId = new URLSearchParams(window.location.search).get('focus') ||
      ((window.location.hash.match(/^#mag-post-(\d+)$/) || [])[1] || '');
    if (focusId) {
      const jump = (smooth) => {
        const el = document.getElementById('mag-post-' + focusId);
        if (!el) return;
        el.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'center' });
        el.classList.add('mag-focus');
        setTimeout(() => el.classList.remove('mag-focus'), 2600);
      };
      setTimeout(() => jump(false), 250);
      setTimeout(() => jump(true), 950);
      window.addEventListener('load', () => setTimeout(() => jump(true), 250));
      // پارامتر فوکوس را از نوار آدرس پاک کن تا با رفرش مجدد باز هم فوکوس نکند
      if (window.location.hash) {
        history.replaceState(null, '', window.location.pathname + window.location.search);
      }
    }
  }

  /* ---------- تایمر سکه: ماندن ۳۰ دقیقه در صفحه = ۱ سکه ---------- */
  const coinEl = document.querySelector('[data-mag-coins-num]');
  const timerEl = document.querySelector('[data-mag-timer]');
  if (!coinEl || !timerEl) return;

  let coins = parseFloat(coinEl.getAttribute('data-coins') || '0');
  let remaining = parseInt(coinEl.getAttribute('data-watch-remaining') || '1800', 10);
  let tick = null;
  let hiddenSince = 0;

  const fmt = (sec) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return toFa(m) + ':' + toFa(s < 10 ? '0' + s : s);
  };
  const render = () => {
    coinEl.textContent = toFa(coins);
    timerEl.textContent = fmt(Math.max(0, remaining));
  };
  const stop = () => { if (tick) { clearInterval(tick); tick = null; } };
  const start = () => {
    if (tick) return;
    tick = setInterval(() => {
      // اگر تب مخفی باشد زمان شمرده نمی‌شود (ماندن واقعی در صفحه)
      if (document.visibilityState === 'hidden') return;
      remaining -= 1;
      if (remaining <= 0) { stop(); claim(); return; }
      render();
    }, 1000);
  };

  async function claim() {
    // پایان چرخه: درخواست سکه؛ سرور صحت گذشت ۳۰ دقیقه را کنترل می‌کند
    let data = null;
    try { data = await api('/magazine/watch/award/', null); } catch (e) { /* شبکه */ }
    if (!data) { remaining = WATCH_SECONDS; render(); start(); return; }
    if (data.status === 'ok') {
      coins = parseFloat(data.coins != null ? data.coins : coins);
      remaining = data.remaining || WATCH_SECONDS;
      const got = parseInt(data.awarded || 0, 10);
      showToast(
        got > 0
          ? 'هدیه گرفتی: ' + toFa(got) + ' سکه 🪙 — چرخهٔ بعدی ۳۰ دقیقهٔ دیگر!'
          : 'چرخهٔ بعدی از همین لحظه شروع شد ⏳',
        'success'
      );
    } else {
      remaining = data.remaining || WATCH_SECONDS;
    }
    render();
    start(); // چرخهٔ بعدی (در صورت ok) یا ادامهٔ انتظار
  }

  // همگام‌سازی اولیه با سرور (مثلاً چرخه از تب دیگر ادامه یافته باشد)
  api('/magazine/watch/start/', null)
    .then((d) => {
      if (d && d.status === 'ok' && typeof d.remaining === 'number') {
        remaining = Math.min(remaining, d.remaining);
        render();
      }
      start();
    })
    .catch(() => start());

  // مدت مخفی‌ماندن تب را حساب کن؛ هنگام برگشت، اگر طولانی بود با سرور همگام شو
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') { hiddenSince = Date.now(); return; }
    const away = hiddenSince ? Date.now() - hiddenSince : 0;
    hiddenSince = 0;
    if (away > 30000) {
      // بیش از نیم دقیقه از صفحه دور بوده → زمان مخفی به حساب نیاید
      stop();
      remaining = WATCH_SECONDS;
      render();
      api('/magazine/watch/start/', null)
        .then((d) => {
          if (d && typeof d.remaining === 'number') { remaining = d.remaining; render(); }
          start();
        })
        .catch(() => start());
    } else if (!tick) {
      start();
    }
  });

  render();
})();
