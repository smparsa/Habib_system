/* انتخاب‌گر چندمقداری «کشور/استان/شهرستان» از جدول مرجع اطلاعات مکانی.
 *
 * برای هدف‌گیری تیکت‌ها (جادوگر تیکت و جوامع هدفِ پنل مدیریت) به‌جای جعبهٔ
 * متنِ آزاد: کاربر با تایپ، فهرستِ رکوردهای مرجع (accounts:location_search)
 * را با Query واقعی جستجو می‌کند و نام رسمی فارسی را به‌صورت «چیپ» اضافه
 * می‌کند؛ مقدارِ انتخاب‌شده (با «،» جدا شده) داخل همان فیلدِ ارسالیِ قبلی
 * نوشته می‌شود تا منطق سمت سرور تغییری نکند و گیرنده‌ها با متنِ نامرتبط
 * (مثلاً نام انگلیسی یا املای آزاد) به خطا نروند.
 *
 * استفاده: هر عنصر با ویژگی data-hb-geo-pick؛ نوع سطح از
 * data-hb-geo-kind (country|province|city) خوانده می‌شود. فیلدِ مقدار، اولین
 * عنصرِ [name=aud_geo] یا [name=location] یا [data-hb-geo-value] داخل همان
 * عنصر است.
 */
(function () {
  'use strict';

  var URL = '/accounts/locations/search/';
  var KIND_LABELS = {
    country: 'کشور',
    province: 'استان',
    city: 'شهرستان',
  };

  function qsa(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function qs(sel, root) { return (root || document).querySelector(sel); }

  function parseValues(text) {
    return String(text || '').split(/[،,]/).map(function (s) { return s.trim(); }).filter(Boolean);
  }

  var State = function (wrap, kind) {
    this.wrap = wrap;
    this.kind = kind || 'country';
    this.values = [];
    this.target = null;
    this.ui = null;      // کانتینر چیپ‌ها/جعبهٔ تایپ
    this.input = null;
    this.list = null;
    this.timer = null;
    this.controller = null;
    this.active = -1;
  };

  function destroyState(st) {
    if (!st) return;
    if (st.timer) clearTimeout(st.timer);
    if (st.controller) st.controller.abort();
    if (st.ui && st.ui.parentNode) st.ui.parentNode.removeChild(st.ui);
    if (st.list && st.list.parentNode) st.list.parentNode.removeChild(st.list);
    // فیلدِ ارسالی به حالت اولیه برنمی‌گردد؛ مقدار در اختیار فراخواننده است.
    st.wrap._hbGeoState = null;
  }

  function findTarget(wrap) {
    return qs('[name="aud_geo"],[name="geo_values"],[name="location"],[data-hb-geo-value]', wrap);
  }

  function setTargetValue(st) {
    if (st.target) st.target.value = st.values.join('، ');
  }

  function renderChips(st) {
    if (!st.ui) return;
    var chipsEl = st.ui.querySelector('.hb-geo-chips');
    if (!chipsEl) return;
    chipsEl.innerHTML = '';
    st.values.forEach(function (v) {
      var chip = document.createElement('span');
      chip.className = 'hb-geo-chip';
      chip.appendChild(document.createTextNode(v));
      var x = document.createElement('button');
      x.type = 'button';
      x.className = 'hb-geo-chip-x';
      x.setAttribute('aria-label', 'حذف ' + v);
      x.innerHTML = '&times;';
      x.addEventListener('click', function (e) {
        e.preventDefault();
        st.values = st.values.filter(function (it) { return it !== v; });
        setTargetValue(st);
        renderChips(st);
        if (st.input) { st.input.focus(); }
      });
      chip.appendChild(x);
      chipsEl.appendChild(chip);
    });
  }

  function renderList(st, items) {
    if (!st.list) return;
    st.list.innerHTML = '';
    if (!items.length) {
      var empty = document.createElement('div');
      empty.className = 'hb-autocomplete-empty';
      empty.textContent = 'موردی یافت نشد — نام را با دقت بیشتری بنویسید یا از ادمین بخواهید آن را به فهرست اضافه کند';
      st.list.appendChild(empty);
    } else {
      items.forEach(function (item, i) {
        var row = document.createElement('div');
        row.className = 'hb-autocomplete-item';
        row.setAttribute('role', 'option');
        var main = document.createElement('span');
        main.textContent = item.fa;
        row.appendChild(main);
        var extra = String(item.hint || item.en || '').trim();
        if (extra) {
          var sm = document.createElement('small');
          sm.textContent = extra;
          sm.style.direction = 'ltr';
          row.appendChild(sm);
        }
        row.addEventListener('mousedown', function (e) {
          e.preventDefault();
          addValue(st, item.fa);
        });
        row.addEventListener('mouseenter', function () { setActive(st, i); });
        st.list.appendChild(row);
      });
      setActive(st, 0);
    }
    st.list.hidden = false;
  }

  function setActive(st, i) {
    st.active = i;
    var rows = qsa('.hb-autocomplete-item', st.list);
    rows.forEach(function (r, idx) { r.classList.toggle('active', idx === i); });
    if (rows[i]) rows[i].scrollIntoView({ block: 'nearest' });
  }

  function addValue(st, fa) {
    if (!fa) return;
    if (st.values.indexOf(fa) === -1) st.values.push(fa);
    setTargetValue(st);
    renderChips(st);
    if (st.list) { st.list.hidden = true; st.list.innerHTML = ''; }
    if (st.input) {
      st.input.value = '';
      st.input.focus();
    }
  }

  function closeList(st) {
    if (st.list) { st.list.hidden = true; st.list.innerHTML = ''; }
    st.active = -1;
  }

  function doSearch(st) {
    var q = st.input ? st.input.value.trim() : '';
    if (st.timer) { clearTimeout(st.timer); st.timer = null; }
    if (st.controller) st.controller.abort();
    if (!q) { closeList(st); return; }
    var params = 'q=' + encodeURIComponent(q) + '&kind=' + encodeURIComponent(st.kind) + '&limit=30';
    st.list.innerHTML = '';
    var loading = document.createElement('div');
    loading.className = 'hb-autocomplete-empty';
    loading.textContent = 'در حال جستجو…';
    st.list.appendChild(loading);
    st.list.hidden = false;
    st.controller = new AbortController();
    fetch(URL + '?' + params, { signal: st.controller.signal })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (st.input && st.input.value.trim() !== q) return; // کاربر بیشتر تایپ کرده
        renderList(st, data.results || []);
      })
      .catch(function (err) {
        if (err && err.name !== 'AbortError' && st.list) {
          st.list.innerHTML = '';
          var empty = document.createElement('div');
          empty.className = 'hb-autocomplete-empty';
          empty.textContent = 'خطا در جستجو — دوباره تلاش کنید';
          st.list.appendChild(empty);
          st.list.hidden = false;
        }
      });
  }

  function buildUi(st) {
    var host = st.target ? st.target.parentNode : st.wrap;
    var ui = document.createElement('div');
    ui.className = 'hb-geo-pick';
    var chips = document.createElement('div');
    chips.className = 'hb-geo-chips';
    ui.appendChild(chips);

    var field = document.createElement('div');
    field.className = 'hb-autocomplete';
    var input = document.createElement('input');
    input.type = 'text';
    input.className = 'hb-form-control hb-autocomplete-input';
    input.autocomplete = 'off';
    input.placeholder = 'تایپ کنید و از فهرست انتخاب کنید… (' + (KIND_LABELS[st.kind] || '') + ')';
    var list = document.createElement('div');
    list.className = 'hb-autocomplete-list';
    list.hidden = true;
    list.setAttribute('role', 'listbox');
    field.appendChild(input);
    field.appendChild(list);
    ui.appendChild(field);
    host.appendChild(ui);

    st.ui = ui;
    st.input = input;
    st.list = list;

    input.addEventListener('input', function () {
      if (st.timer) clearTimeout(st.timer);
      st.timer = setTimeout(function () { doSearch(st); }, 220);
    });
    input.addEventListener('keydown', function (e) {
      var rows = function () { return qsa('.hb-autocomplete-item', st.list); };
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        var r1 = rows();
        if (!st.list.hidden && r1.length) setActive(st, (st.active + 1) % r1.length);
        else doSearch(st);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        var r2 = rows();
        if (!st.list.hidden && r2.length) setActive(st, (st.active - 1 + r2.length) % r2.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        var r3 = rows();
        if (!st.list.hidden && r3[st.active]) {
          addValue(st, r3[st.active].textContent.replace(/\s*$/g, ''));
        } else {
          doSearch(st);
        }
      } else if (e.key === 'Escape') {
        closeList(st);
      }
    });
    input.addEventListener('blur', function () {
      setTimeout(function () { closeList(st); }, 160);
    });
    renderChips(st);
  }

  function initWrapper(wrap) {
    var existing = wrap._hbGeoState;
    if (existing) return existing;
    var target = findTarget(wrap);
    if (target && target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA' && target.tagName !== 'SELECT') {
      target = null;
    }
    if (!target) return null;
    // فیلد ارسالی دیگر به کاربر نمایش داده نمی‌شود (مقدارش را JS نگه می‌دارد)
    if (target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') {
      target.style.display = 'none';
    }
    var kind = wrap.getAttribute('data-hb-geo-kind') || 'country';
    var st = new State(wrap, kind);
    st.target = target;
    // مقدارِ از پیش ذخیره‌شده (مثلاً هنگام ویرایش جامعهٔ هدف) → چیپ
    parseValues(target.value).forEach(function (v) {
      if (st.values.indexOf(v) === -1) st.values.push(v);
    });
    buildUi(st);
    wrap._hbGeoState = st;
    return st;
  }

  function setKind(wrap, kind) {
    if (!wrap) return;
    wrap.setAttribute('data-hb-geo-kind', kind || 'country');
    var st = wrap._hbGeoState;
    if (st && st.kind !== kind) {
      st.kind = kind;
      st.values = [];
      setTargetValue(st);
      renderChips(st);
      if (st.input) st.input.placeholder = 'تایپ کنید و از فهرست انتخاب کنید… (' + (KIND_LABELS[kind] || '') + ')';
      closeList(st);
    }
  }

  function initAll(rootEl) {
    qsa('[data-hb-geo-pick]', rootEl || document).forEach(function (wrap) {
      try { initWrapper(wrap); } catch (e) { /* یک ویجت خراب بقیه را نمی‌شکند */ }
    });
  }

  window.HbGeoPick = {
    initAll: initAll,
    setKind: setKind,
    reset: function (wrap) {
      if (wrap && wrap._hbGeoState) destroyState(wrap._hbGeoState);
      else qsa('[data-hb-geo-pick]').forEach(function (w) {
        if (w._hbGeoState) destroyState(w._hbGeoState);
      });
    },
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { initAll(document); });
  } else {
    initAll(document);
  }
})();
