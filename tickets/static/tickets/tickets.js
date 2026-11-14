/* مرکز تیکت — رفتارهای سمت کلاینت (بدون وابستگی به app.js) */
(function () {
  'use strict';

  function $(s, r) { return (r || document).querySelector(s); }
  function $all(s, r) { return Array.from((r || document).querySelectorAll(s)); }

  /* تأیید عملیات مخرب/گروهی */
  $all('[data-confirm]').forEach(function (b) {
    b.addEventListener('click', function (e) {
      if (!window.confirm('این عملیات گروهی انجام شود؟')) e.preventDefault();
    });
  });

  /* انتخاب همه در جدول مدیریت */
  var checkAll = $('[data-checkall]');
  if (checkAll) {
    checkAll.addEventListener('change', function () {
      $all('input[name="ids"]').forEach(function (c) { c.checked = checkAll.checked; });
    });
  }

  /* ---------- جادوگر ساخت تیکت ---------- */
  var form = $('#tkt-create-form');
  if (form) {
    var audience = $('#tkt-audience');
    var blocks = $all('[data-aud]');

    var audNote = $('#tkt-aud-note');
    // چند نوع مخاطب یک بلوکِ ورودی مشترک دارند (کشور/استان/شهر ← انتخاب‌گر مرجع)
    var AUD_BLOCK = {
      job: 'job',
      country: 'geo',
      province: 'geo',
      city: 'geo',
      radius: 'radius',
      mobile_prefix: 'mobile_prefix',
      age: 'age',
      group: 'group',
      level: 'level',
      score: 'score',
      specific_users: 'specific_users'
    };
    function showAudience() {
      var val = audience ? audience.value : '';
      var key = AUD_BLOCK[val];
      blocks.forEach(function (b) {
        b.hidden = !(b.getAttribute('data-aud') === key);
      });
      // نوع جغرافیایی → سطح انتخاب‌گر مرجع (کشور/استان/شهرستان) و پاک‌کردن انتخاب قبلی
      if (key === 'geo' && val && window.HbGeoPick) {
        var wrap = form.querySelector('[data-hb-geo-pick]');
        if (wrap) window.HbGeoPick.setKind(wrap, val);
      }
      if (audNote) {
        if (val.indexOf('saved:') === 0 && audience) {
          var opt = audience.options[audience.selectedIndex];
          audNote.hidden = false;
          audNote.innerHTML = '<i class="bi bi-megaphone"></i> ارسال انبوه به جامعهٔ هدفِ تعریف‌شده توسط ادمین: <b>' +
            (opt ? opt.textContent.trim() : '') + '</b>';
        } else {
          audNote.hidden = true;
        }
      }
    }
    if (audience) audience.addEventListener('change', showAudience);
    showAudience();

    /* برآورد گیرندگان (سمت سرور؛ بدون افشای نام) */
    var est = $('#tkt-estimate');
    var estOut = $('#tkt-est');
    if (est && estOut) {
      est.addEventListener('click', function () {
        var params = new URLSearchParams();
        params.set('audience', audience.value);
        var visible = blocks.filter(function (b) { return !b.hidden; })[0];
        if (visible) {
          $all('input, select, textarea', visible).forEach(function (el) {
            if (el.name && el.value && !params.has(el.name)) params.set(el.name, el.value);
          });
        }
        estOut.textContent = 'در حال محاسبه…';
        fetch('/tickets/estimate/?' + params.toString(), { headers: { 'Accept': 'application/json' } })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            estOut.textContent = (d.status === 'ok') ? String(d.count) : (d.message || 'خطا');
          })
          .catch(function () { estOut.textContent = 'خطا در محاسبه'; });
      });
    }

    /* نمایش خلاصهٔ انتخاب در مرحلهٔ بازبینی */
    var sel = $('#tkt-sel');
    if (sel) {
      function refreshSummary() {
        var cat = form.querySelector('input[name="category"]:checked');
        var prio = form.querySelector('select[name="priority"]');
        sel.textContent = (cat ? cat.nextElementSibling.nextElementSibling.textContent.trim() : '—') +
          ' / ' + (prio ? prio.options[prio.selectedIndex].textContent.trim().replace('اولویت: ', '') : '—');
      }
      form.addEventListener('change', refreshSummary);
      refreshSummary();
    }
  }
})();
