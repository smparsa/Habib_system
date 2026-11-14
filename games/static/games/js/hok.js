/* ==========================================================================
   Honor of Kings — مینی‌موبای سه‌لِین (وانیلا JS، بدون وابستگی)
   ▸ ۳ لِین (بالا/میانی/پایین)، ۴ برج برای هر تیم (۳ بیرونی + پایگاه)
   ▸ موج‌های مینیون، طلای منفعل، XP و سطح، ارتقای تجهیزات
   ▸ ۶ هیرو با قدرت ویژه، ۲ هم‌تیمی و ۳ دشمن هوش مصنوعی
   ▸ کنترل: کیبورد WASD/جهت‌ها + جوی‌استیک لمسی + کلیک برای حرکت
   ========================================================================== */
(function () {
  'use strict';

  /* ---------- ابزارها ---------- */
  const $ = (id) => document.getElementById(id);
  const fa = (n) => Number(Math.round(n)).toLocaleString('fa-IR');
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
  const norm = (x, y) => {
    const d = Math.hypot(x, y) || 1;
    return { x: x / d, y: y / d };
  };
  const fmtTime = (s) => {
    const m = Math.floor(s / 60), r = Math.floor(s % 60);
    return fa(m) + ':' + (r < 10 ? '۰' : '') + fa(r);
  };

  /* ---------- ثابت‌ها ---------- */
  const W = 640, H = 480;
  const LANES = ['top', 'mid', 'bot'];
  const laneY = (l) => H * { top: 0.16, mid: 0.5, bot: 0.84 }[l];
  const spawnX = (side) => (side === 'blue' ? 46 : W - 46);
  const HERO_CD = 0.8;

  const HEROES = [
    { id: 'arthur', name: 'آرتور', emoji: '🛡️', color: '#60a5fa', hp: 1350, mp: 420, atk: 44, rng: 17, spd: 1.9, arm: 0.30, power: 'shield', powerIcon: '🛡️', powerFa: 'سپر مقدس', powerMp: 60, powerCd: 12, powerDesc: 'سپر ۳۵٪ + سرعت ۴ ثانیه' },
    { id: 'zhao', name: 'ژائو یون', emoji: '⚔️', color: '#4ade80', hp: 1150, mp: 380, atk: 54, rng: 17, spd: 2.1, arm: 0.22, power: 'leap', powerIcon: '💥', powerFa: 'جهش اژدها', powerMp: 70, powerCd: 12, powerDesc: 'جهش ۹۰px + ضربهٔ محیطی' },
    { id: 'houyi', name: 'هویی', emoji: '🏹', color: '#fbbf24', hp: 920, mp: 400, atk: 64, rng: 34, spd: 1.9, arm: 0.12, power: 'volley', powerIcon: '🌟', powerFa: 'تیرباران خورشید', powerMp: 65, powerCd: 10, powerDesc: '۵ تیر متوالی پرقدرت' },
    { id: 'daji', name: 'داجی', emoji: '🌸', color: '#f472b6', hp: 840, mp: 520, atk: 72, rng: 30, spd: 1.8, arm: 0.10, power: 'blink', powerIcon: '✨', powerFa: 'جانشین ناپدید', powerMp: 75, powerCd: 11, powerDesc: 'پرش + انفجار و کندی' },
    { id: 'atlas', name: 'اطلس', emoji: '🐙', color: '#38bdf8', hp: 1200, mp: 480, atk: 46, rng: 18, spd: 1.85, arm: 0.25, power: 'heal', powerIcon: '💚', powerFa: 'مهر حیات', powerMp: 60, powerCd: 12, powerDesc: 'مداوای خود و مینیون‌ها' },
    { id: 'lunata', name: 'لونا', emoji: '🌙', color: '#c084fc', hp: 950, mp: 420, atk: 60, rng: 15, spd: 2.3, arm: 0.14, power: 'dash', powerIcon: '🗡️', powerFa: 'ضرب هلال', powerMp: 70, powerCd: 10, powerDesc: 'یورش به نزدیک‌ترین دشمن' },
  ];

  const DIFFS = {
    easy: { aim: 0.5, aggro: 0.55, strike: 0.5, atk: 0.85 },
    medium: { aim: 0.75, aggro: 0.8, strike: 0.75, atk: 1.0 },
    hard: { aim: 0.95, aggro: 1.0, strike: 0.95, atk: 1.15 },
  };

  /* ---------- عناصر DOM ---------- */
  const canvas = $('g-hok-canvas');
  const ctx = canvas.getContext('2d');
  const el = {
    timer: $('hok-timer'), kb: $('hok-kills-blue'), kr: $('hok-kills-red'),
    gold: $('hok-gold'), lvl: $('hok-lvl'),
    hp: $('hok-hp'), hpL: $('hok-hp-label'), mp: $('hok-mp'), mpL: $('hok-mp-label'), xp: $('hok-xp'),
    abB: $('hok-ab-b'), abBCd: $('hok-ab-b-cd'), abBIc: $('hok-ab-b-icon'),
    abU: $('hok-ab-u'), abUCost: $('hok-ab-u-cost'),
    abH: $('hok-ab-h'), abHCd: $('hok-ab-h-cd'),
    overlay: $('g-hok-overlay'), ovEmoji: $('g-hok-overlay-emoji'), ovTitle: $('g-hok-overlay-title'),
    ovBtn: $('g-hok-overlay-btn'), ovNote: $('g-hok-overlay-note'),
    events: $('hok-events'), diff: $('hok-diff'),
    heroInfo: $('hok-hero-info'),
    heroCards: document.querySelectorAll('.h-hero-card'),
  };

  /* ---------- وضعیت بازی ---------- */
  const G = {
    running: false, paused: false, over: false, won: null,
    time: 0, waveT: 0, waveN: 0, diff: 'medium',
    heroes: [], towers: [], minions: [], projs: [], fx: [], texts: [],
    kills: { blue: 0, red: 0 },
    order: 'push',
    player: null, heroId: 'arthur',
    bestWins: Number(localStorage.getItem('hok-wins') || 0),
    bestKills: Number(localStorage.getItem('hok-kills') || 0),
  };

  const keys = {};
  const joy = { active: false, x: 0, y: 0 };
  const clickMove = { x: null, y: null };
  let last = 0, raf = 0;

  /* ---------- ساخت موجودیت‌ها ---------- */
  function makeHero(def, side, idx) {
    const baseX = spawnX(side);
    return {
      type: 'hero', def, side, idx, lane: idx === 0 ? 'mid' : (idx === 1 ? 'top' : 'bot'),
      x: baseX + (side === 'blue' ? 26 : -26), y: H / 2 + (idx - 1) * 34,
      hp: def.hp, maxhp: def.hp, mp: def.mp, maxmp: def.mp,
      atk: def.atk, arm: def.arm, rng: def.rng, spd: def.spd,
      lvl: 1, xp: 0, gold: 200, upgrades: 0,
      cd: 0, pcd: 0, ucd: 0, alive: true, respawnT: 0, hitFlash: 0,
      shield: 0, shieldT: 0, hasteT: 0, slowT: 0, stunT: 0,
      burst: null, recallT: 0, aiT: Math.random() * 2, strikeT: 6 + Math.random() * 5,
      state: 'lane', isPlayer: idx === 0 && side === 'blue',
    };
  }

  function makeTowers() {
    const arr = [];
    for (const side of ['blue', 'red']) {
      const s = side === 'blue' ? 1 : -1;
      for (const l of LANES) {
        arr.push({ type: 'tower', side, lane: l, base: false, x: W / 2 + s * W * 0.22, y: laneY(l), hp: 1200, maxhp: 1200, rng: 62, atk: 60, cd: 0, alive: true, hitFlash: 0 });
      }
      arr.push({ type: 'tower', side, lane: 'mid', base: true, x: W / 2 + s * W * 0.43, y: H / 2, hp: 2400, maxhp: 2400, rng: 72, atk: 70, cd: 0, alive: true, hitFlash: 0 });
    }
    return arr;
  }

  function baseOf(side) { return G.towers.find((t) => t.side === side && t.base); }
  function outerTowers(side) { return G.towers.filter((t) => t.side === side && !t.base); }
  function baseLocked(side) { return outerTowers(side).filter((t) => t.alive).length >= 2; }

  function spawnWave() {
    G.waveN++;
    const scale = 1 + G.waveN * 0.05;
    for (const side of ['blue', 'red']) {
      const s = side === 'blue' ? 1 : -1;
      for (const l of LANES) {
        const y0 = laneY(l);
        for (let i = 0; i < 3; i++) {
          G.minions.push({ type: 'minion', side, lane: l, kind: 'melee', x: spawnX(side) + s * (8 + i * 13), y: y0 + (i - 1) * 11, hp: 260 * scale, maxhp: 260 * scale, atk: 22 * scale, rng: 14, spd: 34, cd: 1 + i * 0.3, alive: true, hitFlash: 0, idle: false });
        }
        G.minions.push({ type: 'minion', side, lane: l, kind: 'mage', x: spawnX(side) + s * 60, y: y0 + 13, hp: 180 * scale, maxhp: 180 * scale, atk: 34 * scale, rng: 26, spd: 32, cd: 1.6, alive: true, hitFlash: 0, idle: false });
      }
    }
    if (G.waveN > 1) pushEvent('♟️ موج مینیون ' + fa(G.waveN), 'h-event-info');
  }

  /* ---------- رویدادها و افکت‌ها ---------- */
  function pushEvent(txt, cls) {
    const d = document.createElement('div');
    d.className = 'h-event ' + (cls || 'h-event-info');
    d.textContent = txt;
    el.events.prepend(d);
    while (el.events.children.length > 4) el.events.lastChild.remove();
    setTimeout(() => d.remove(), 3100);
  }
  function addFx(x, y, color, r0, r1, life) {
    G.fx.push({ x, y, color, r0, r1, life, max: life });
  }
  function addText(x, y, txt, color) {
    G.texts.push({ x, y, txt, color, life: 1.1, max: 1.1 });
  }

  /* ---------- هدف‌یابی ---------- */
  function enemiesOf(side) {
    const out = [];
    for (const h of G.heroes) if (h.side !== side && h.alive) out.push(h);
    for (const m of G.minions) if (m.side !== side && m.alive) out.push(m);
    for (const t of G.towers) if (t.side !== side && t.alive && !(t.base && baseLocked(t.side))) out.push(t);
    return out;
  }
  function nearest(from, list, maxD) {
    let best = null, bd = maxD == null ? Infinity : maxD;
    for (const e of list) {
      const d = dist(from, e);
      if (d < bd) { bd = d; best = e; }
    }
    return best;
  }

  /* ---------- آسیب و مرگ ---------- */
  function applyDamage(src, target, amount) {
    if (!target.alive || amount <= 0) return;
    let dmg = amount * (1 - (target.arm || 0));
    if (target.shield > 0) {
      const abs = Math.min(target.shield, dmg);
      target.shield -= abs; dmg -= abs;
    }
    target.hp -= dmg;
    target.hitFlash = 0.15;
    if (target.recallT > 0) target.recallT = 0; // قطع بازگشت با آسیب
    if (target.type === 'hero' && src && src.type === 'hero' && target.isPlayer) {
      addText(target.x, target.y - 26, '-' + fa(dmg), '#f87171');
    }
    if (target.hp <= 0) killEntity(src, target);
  }

  function grantKillRewards(src, victim, goldVal, xpVal) {
    if (src && src.type === 'hero' && src.side !== victim.side) {
      src.gold += goldVal;
      if (src.isPlayer) addText(victim.x, victim.y - 18, '+' + fa(goldVal) + ' 🪙', '#fde047');
    }
    // XP به قهرمان‌های نزدیکِ قاتل
    for (const h of G.heroes) {
      if (h.alive && h.side === (src ? src.side : 'blue') && h.type === 'hero' && dist(h, victim) < 140) {
        gainXp(h, xpVal);
      }
    }
  }

  function killEntity(src, target) {
    target.alive = false;
    addFx(target.x, target.y, target.side === 'blue' ? '#60a5fa' : '#f87171', 4, 26, 0.5);
    if (target.type === 'minion') {
      grantKillRewards(src, target, 12, 40);
    } else if (target.type === 'tower') {
      grantKillRewards(src, target, 150, 80);
      pushEvent((target.side === 'red' ? '🏹 برج دشمن ' : '⚠️ برج ما ') + (target.base ? 'پایگاه' : 'بیرونی') + (target.side === 'red' ? ' نابود شد!' : ' از دست رفت!'), target.side === 'red' ? 'h-event-gold' : 'h-event-kill');
      addFx(target.x, target.y, '#fbbf24', 6, 70, 0.8);
      if (target.base) { endMatch(target.side !== 'blue'); return; }
      if (!baseLocked(target.side)) pushEvent('🔓 سپر پایگاه ' + (target.side === 'blue' ? 'ما' : 'دشمن') + ' شکست!', 'h-event-info');
      syncTowerDots();
    } else if (target.type === 'hero') {
      const bounty = 180 + target.lvl * 20;
      grantKillRewards(src, target, bounty, 120);
      G.kills[target.side === 'blue' ? 'red' : 'blue']++;
      pushEvent('💀 ' + target.def.name + (target.side === 'blue' ? ' (ما) ' : ' (دشمن) ') + 'حذف شد!', target.side === 'blue' ? 'h-event-kill' : 'h-event-gold');
      target.respawnT = Math.min(4 + target.lvl, 15);
      target.shield = 0; target.shieldT = 0; target.burst = null; target.recallT = 0;
      if (target.isPlayer) pushEvent('⏳ بازگشت به میدان: ' + fa(target.respawnT) + ' ثانیه', 'h-event-info');
      syncTowerDots();
    }
  }

  function gainXp(h, amount) {
    if (!h.alive || h.lvl >= 15) return;
    h.xp += amount;
    let need = 80 + (h.lvl - 1) * 60;
    while (h.xp >= need && h.lvl < 15) {
      h.xp -= need;
      h.lvl++;
      h.maxhp += 110; h.maxmp += 25; h.atk += 7;
      h.hp = Math.min(h.maxhp, h.hp + h.maxhp * 0.3);
      if (h.isPlayer) { addFx(h.x, h.y, '#c084fc', 8, 40, 0.7); addText(h.x, h.y - 30, 'سطح ' + fa(h.lvl) + '!', '#c084fc'); }
      need = 80 + (h.lvl - 1) * 60;
    }
  }

  /* ---------- حمله ---------- */
  function fireProjectile(src, target, dmg, color, speed, size) {
    G.projs.push({ x: src.x, y: src.y, target, dmg, color, speed: speed || 320, size: size || 4, side: src.side, src, life: 2.2 });
  }
  function tryAttack(u, dt, cdTime) {
    u.cd -= dt;
    if (u.cd > 0) return;
    const tg = nearest(u, enemiesOf(u.side), u.rng);
    if (!tg) return;
    u.cd = cdTime;
    if (u.rng > 20) {
      fireProjectile(u, tg, u.atk, u.side === 'blue' ? '#7dd3fc' : '#fda4af', u.type === 'tower' ? 380 : 330, u.type === 'tower' ? 5 : 4);
    } else {
      applyDamage(u, tg, u.atk);
      addFx(tg.x, tg.y, '#fef08a', 2, 10, 0.18);
    }
  }

  /* ---------- حرکت ---------- */
  function moveToward(u, tx, ty, dt, mul) {
    const d = norm(tx - u.x, ty - u.y);
    let sp = u.spd * 62 * (mul == null ? 1 : mul);
    if (u.hasteT > 0) sp *= 1.35;
    if (u.slowT > 0) sp *= 0.65;
    u.x = clamp(u.x + d.x * sp * dt, 14, W - 14);
    u.y = clamp(u.y + d.y * sp * dt, 14, H - 14);
  }

  /* ---------- قابلیت‌های ویژه بازیکن ---------- */
  function usePower(h) {
    if (!G.running || G.paused || G.over || !h.alive || h.pcd > 0) return;
    if (h.mp < h.def.powerMp) { addText(h.x, h.y - 28, 'مانا کافی نیست', '#93c5fd'); return; }
    h.mp -= h.def.powerMp;
    h.pcd = h.def.powerCd;
    el.abB.classList.add('casting');
    setTimeout(() => el.abB.classList.remove('casting'), 350);
    const p = h.def.power;
    if (p === 'shield') {
      h.shield = h.maxhp * 0.35; h.shieldT = 4; h.hasteT = 4;
      addFx(h.x, h.y, '#fde047', 8, 34, 0.6);
      addText(h.x, h.y - 30, h.def.powerFa, '#fde047');
    } else if (p === 'leap') {
      const t = nearest(h, enemiesOf(h.side), 140);
      const dir = t ? norm(t.x - h.x, t.y - h.y) : lastMoveDir(h);
      h.x = clamp(h.x + dir.x * 90, 14, W - 14);
      h.y = clamp(h.y + dir.y * 90, 14, H - 14);
      addFx(h.x, h.y, '#4ade80', 6, 52, 0.45);
      for (const e of enemiesOf(h.side)) {
        if (dist(h, e) < 62) { applyDamage(h, e, h.atk * 1.4); if (e.type === 'hero') e.stunT = 1; }
      }
    } else if (p === 'volley') {
      h.burst = { n: 5, t: 0 };
      addText(h.x, h.y - 30, h.def.powerFa, '#fde047');
    } else if (p === 'blink') {
      const dir = lastMoveDir(h);
      addFx(h.x, h.y, '#f472b6', 4, 22, 0.35);
      h.x = clamp(h.x + dir.x * 110, 14, W - 14);
      h.y = clamp(h.y + dir.y * 110, 14, H - 14);
      addFx(h.x, h.y, '#f472b6', 6, 56, 0.5);
      for (const e of enemiesOf(h.side)) {
        if (dist(h, e) < 70) {
          applyDamage(h, e, 100 + h.atk * 0.8);
          if (e.type === 'hero') { e.slowT = 2; }
        }
      }
    } else if (p === 'heal') {
      h.hp = Math.min(h.maxhp, h.hp + 140);
      addFx(h.x, h.y, '#4ade80', 6, 44, 0.6);
      for (const m of G.minions) {
        if (m.side === h.side && m.alive && dist(m, h) < 90) { m.hp = Math.min(m.maxhp, m.hp + 80); addFx(m.x, m.y, '#4ade80', 2, 12, 0.3); }
      }
      addText(h.x, h.y - 30, '+' + fa(140), '#4ade80');
    } else if (p === 'dash') {
      const t = nearest(h, enemiesOf(h.side), 160) || null;
      const dir = t ? norm(t.x - h.x, t.y - h.y) : lastMoveDir(h);
      addFx(h.x, h.y, '#c084fc', 4, 20, 0.3);
      h.x = clamp(h.x + dir.x * 110, 14, W - 14);
      h.y = clamp(h.y + dir.y * 110, 14, H - 14);
      addFx(h.x, h.y, '#c084fc', 6, 48, 0.45);
      if (t && dist(h, t) < 60) applyDamage(h, t, h.atk * 1.3);
    }
  }

  function lastMoveDir(h) {
    const d = h.lastDir || { x: h.side === 'blue' ? 1 : -1, y: 0 };
    return d;
  }

  function buyUpgrade(h) {
    if (!G.running || G.paused || G.over || !h.alive) return;
    const cost = 500 + h.upgrades * 250;
    if (h.gold < cost) { addText(h.x, h.y - 28, 'طلا کافی نیست', '#fde047'); return; }
    h.gold -= cost;
    h.upgrades++;
    h.atk += 12; h.maxhp += 110; h.maxmp += 30; h.arm = Math.min(0.6, h.arm + 0.03);
    h.hp = Math.min(h.maxhp, h.hp + 80);
    addFx(h.x, h.y, '#fbbf24', 6, 38, 0.5);
    addText(h.x, h.y - 30, '⬆ ارتقا!', '#fbbf24');
  }

  function startRecall(h) {
    if (!G.running || G.paused || G.over || !h.alive || h.recallT > 0) return;
    h.recallT = 2.5;
    addText(h.x, h.y - 28, 'بازگشت...', '#93c5fd');
  }

  /* ---------- هوش مصنوعی قهرمان‌ها ---------- */
  function laneFront(lane, side) {
    let best = null, bd = -1;
    const own = spawnX(side);
    for (const m of G.minions) {
      if (m.side === side && m.lane === lane && m.alive) {
        const d = Math.abs(m.x - own);
        if (d > bd) { bd = d; best = m; }
      }
    }
    if (best) return best;
    const outer = outerTowers(side).find((t) => t.lane === lane && t.alive);
    return outer || baseOf(side);
  }

  function aiHero(h, dt) {
    const base = baseOf(h.side);
    if (h.stunT > 0) { h.stunT -= dt; return; }
    if (h.hp < h.maxhp * 0.28) h.state = 'retreat';
    else if (h.state === 'retreat' && (h.hp > h.maxhp * 0.62 || dist(h, base) < 60)) h.state = 'lane';

    if (h.state === 'retreat') {
      moveToward(h, base.x, base.y, dt);
      return;
    }
    const diff = DIFFS[G.diff];
    const front = laneFront(h.lane, h.side);
    let tx = front.x, ty = front.y;
    // درگیری با قهرمان دشمن
    const foe = nearest(h, G.heroes.filter((o) => o.side !== h.side && o.alive), 130);
    if (foe && h.hp / h.maxhp > 0.45 && Math.random() < diff.aggro * dt * 3) {
      tx = foe.x; ty = foe.y;
      h.engageT = 1.2;
    } else if (h.engageT > 0 && foe) {
      h.engageT -= dt;
      tx = foe.x; ty = foe.y;
    }
    if (dist(h, { x: tx, y: ty }) > 12) moveToward(h, tx, ty, dt);
    tryAttack(h, dt, HERO_CD);
    // ضربهٔ ویژهٔ دوره‌ای AI
    h.strikeT -= dt;
    if (h.strikeT <= 0) {
      h.strikeT = 8 + Math.random() * 4;
      const v = nearest(h, G.heroes.filter((o) => o.side !== h.side && o.alive), h.rng + 34);
      if (v && Math.random() < diff.strike) {
        applyDamage(h, v, h.atk * 1.3 * (h.side === 'red' ? diff.atk : 1));
        addFx(v.x, v.y, h.side === 'blue' ? '#7dd3fc' : '#f87171', 4, 30, 0.4);
        if (v.isPlayer) addText(v.x, v.y - 30, 'ضربهٔ دشمن!', '#f87171');
      }
    }
  }

  /* ---------- به‌روزرسانی مینیون‌ها ---------- */
  function updMinion(m, dt) {
    if (m.stunT > 0) { m.stunT -= dt; return; }
    const dir = m.side === 'blue' ? 1 : -1;
    const b = baseOf(m.side === 'blue' ? 'red' : 'blue');
    const tg = nearest(m, enemiesOf(m.side), 85);
    if (tg) {
      const d = dist(m, tg);
      if (d > m.rng) moveToward(m, tg.x, tg.y, dt);
      else {
        m.cd -= dt;
        if (m.cd <= 0) {
          m.cd = m.kind === 'mage' ? 1.6 : 1.0;
          if (m.kind === 'mage') fireProjectile(m, tg, m.atk, m.side === 'blue' ? '#7dd3fc' : '#fda4af', 300, 3);
          else { applyDamage(m, tg, m.atk); addFx(tg.x, tg.y, '#fef08a', 2, 8, 0.15); }
        }
      }
    } else if (Math.abs(m.x - b.x) < 30) {
      m.idle = true; // محاصرهٔ جلوی پایگاه قفل
    } else {
      m.idle = false;
      // دستور فرمانده (فقط تیم آبی): حمله / دفاع / عقب‌نشینی
      const bHalf = W * 0.5;
      if (m.side === 'blue' && G.order === 'retreat' && !tg) {
        moveToward(m, spawnX('blue'), laneY(m.lane), dt);
        return;
      }
      if (m.side === 'blue' && G.order === 'hold' && !tg) {
        // پشت خط میانی بمان
        if (m.x > bHalf) { moveToward(m, bHalf - 20, laneY(m.lane), dt); return; }
        m.idle = true;
        return;
      }
      m.x += dir * m.spd * dt;
      m.y += (laneY(m.lane) - m.y) * dt * 1.2;
    }
  }

  /* ---------- به‌روزرسانی برج‌ها ---------- */
  function updTower(t, dt) {
    t.cd -= dt;
    if (t.cd > 0) return;
    const list = enemiesOf(t.side).filter((e) => e.type !== 'tower');
    let tg = nearest(t, list.filter((e) => e.type === 'minion'), t.rng);
    if (!tg) tg = nearest(t, list.filter((e) => e.type === 'hero'), t.rng);
    if (!tg) return;
    t.cd = 1.1;
    fireProjectile(t, tg, t.atk, t.side === 'blue' ? '#93c5fd' : '#fca5a5', 400, 5);
  }

  /* ---------- به‌روزرسانی قهرمان بازیکن ---------- */
  function updPlayer(h, dt) {
    if (!h.alive) return;
    if (h.stunT > 0) { h.stunT -= dt; return; }
    // اولویت: جوی‌استیک > کیبورد > کلیک
    let dx = 0, dy = 0;
    if (joy.active && (joy.x || joy.y)) { dx = joy.x; dy = joy.y; }
    else if (keys['arrowup'] || keys['w']) dy -= 1;
    if (keys['arrowdown'] || keys['s']) dy += 1;
    if (keys['arrowleft'] || keys['a']) dx -= 1;
    if (keys['arrowright'] || keys['d']) dx += 1;
    if (dx || dy) {
      clickMove.x = null;
      const d = norm(dx, dy);
      h.lastDir = d;
      moveToward(h, h.x + d.x * 40, h.y + d.y * 40, dt);
      h.recallT = 0;
    } else if (clickMove.x != null) {
      if (dist(h, clickMove) > 6) {
        h.lastDir = norm(clickMove.x - h.x, clickMove.y - h.y);
        moveToward(h, clickMove.x, clickMove.y, dt);
      } else clickMove.x = null;
    } else if (h.recallT > 0) {
      h.recallT -= dt;
      if (h.recallT <= 0) {
        const b = baseOf(h.side);
        h.x = b.x + 24; h.y = b.y + 24;
        h.hp = Math.min(h.maxhp, h.hp + h.maxhp * 0.35);
        h.mp = Math.min(h.maxmp, h.mp + h.maxmp * 0.35);
        addFx(h.x, h.y, '#93c5fd', 6, 40, 0.6);
        pushEvent('🏠 به پایگاه بازگشتید', 'h-event-info');
      }
    }
    // حملهٔ خودکار
    tryAttack(h, dt, HERO_CD);
    // رگبار تیر
    if (h.burst) {
      h.burst.t -= dt;
      if (h.burst.t <= 0) {
        const tg = nearest(h, enemiesOf(h.side), h.rng + 8);
        if (tg && h.burst.n > 0) {
          fireProjectile(h, tg, h.atk * 0.55, '#fde047', 420, 4);
          addFx(h.x, h.y, '#fde047', 3, 12, 0.15);
          h.burst.n--; h.burst.t = 0.16;
        } else h.burst = null;
      }
    }
    // طلای منفعل
    h.gold += 2 * dt;
  }

  /* ---------- به‌روزرسانی اصلی ---------- */
  function update(dt) {
    G.time += dt;
    G.waveT -= dt;
    if (G.waveT <= 0) { G.waveT = 25; spawnWave(); }

    // قهرمان‌ها
    for (const h of G.heroes) {
      h.hitFlash = Math.max(0, h.hitFlash - dt);
      if (h.pcd > 0) h.pcd -= dt;
      if (h.ucd > 0) h.ucd -= dt;
      if (h.shieldT > 0) { h.shieldT -= dt; if (h.shieldT <= 0) h.shield = 0; }
      if (h.hasteT > 0) h.hasteT -= dt;
      if (h.slowT > 0) h.slowT -= dt;
      if (!h.alive) {
        h.respawnT -= dt;
        if (h.respawnT <= 0) {
          const b = baseOf(h.side);
          h.alive = true; h.hp = h.maxhp; h.mp = h.maxmp;
          h.x = b.x + (h.side === 'blue' ? 26 : -26); h.y = b.y + 20;
          addFx(h.x, h.y, '#a5f3fc', 6, 36, 0.5);
        }
        continue;
      }
      // بازیابی
      const b = baseOf(h.side);
      const nearBase = dist(h, b) < 95;
      h.hp = Math.min(h.maxhp, h.hp + h.maxhp * (nearBase ? 0.045 : 0.004) * dt);
      h.mp = Math.min(h.maxmp, h.mp + h.maxmp * (nearBase ? 0.05 : 0.008) * dt);
      if (h.isPlayer) updPlayer(h, dt);
      else aiHero(h, dt);
    }

    // برج‌ها
    for (const t of G.towers) {
      t.hitFlash = Math.max(0, t.hitFlash - dt);
      if (t.alive) updTower(t, dt);
    }
    // مینیون‌ها
    for (const m of G.minions) {
      m.hitFlash = Math.max(0, m.hitFlash - dt);
      if (m.alive) updMinion(m, dt);
    }
    G.minions = G.minions.filter((m) => m.alive);

    // پرتابه‌ها
    for (const p of G.projs) {
      p.life -= dt;
      if (p.target && p.target.alive) {
        const d = norm(p.target.x - p.x, p.target.y - p.y);
        p.x += d.x * p.speed * dt;
        p.y += d.y * p.speed * dt;
        if (dist(p, p.target) < 12) {
          const mult = p.src && p.src.type === 'hero' && p.src.side === 'red' ? DIFFS[G.diff].atk : 1;
          applyDamage(p.src, p.target, p.dmg * mult);
          addFx(p.x, p.y, p.color, 2, 9, 0.18);
          p.life = 0;
        }
      } else p.life = 0;
    }
    G.projs = G.projs.filter((p) => p.life > 0);

    // افکت‌ها و متن‌ها
    for (const f of G.fx) f.life -= dt;
    G.fx = G.fx.filter((f) => f.life > 0);
    for (const t of G.texts) { t.life -= dt; t.y -= 22 * dt; }
    G.texts = G.texts.filter((t) => t.life > 0);
  }

  /* ---------- ترسیم ---------- */
  const bushes = [];
  (function seedBushes() {
    let s = 42;
    const rnd = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
    for (let i = 0; i < 26; i++) {
      const x = 40 + rnd() * (W - 80);
      const laneDists = LANES.map((l) => Math.abs(laneY(l) - (40 + rnd() * (H - 80))));
      const y = 40 + rnd() * (H - 80);
      if (laneDists.some((d) => false)) continue;
      if (Math.abs(y - laneY('top')) < 40 || Math.abs(y - laneY('mid')) < 40 || Math.abs(y - laneY('bot')) < 40) continue;
      bushes.push({ x, y, r: 8 + rnd() * 10 });
    }
  })();

  function drawArena() {
    // پس‌زمینه
    const bg = ctx.createLinearGradient(0, 0, W, H);
    bg.addColorStop(0, '#0b1a12');
    bg.addColorStop(0.5, '#0d2130');
    bg.addColorStop(1, '#0b1a12');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, W, H);
    // مسیر لِین‌ها
    for (const l of LANES) {
      const y = laneY(l);
      ctx.fillStyle = 'rgba(148,163,184,0.09)';
      ctx.fillRect(46, y - 22, W - 92, 44);
      ctx.strokeStyle = 'rgba(148,163,184,0.14)';
      ctx.setLineDash([8, 10]);
      ctx.beginPath();
      ctx.moveTo(60, y);
      ctx.lineTo(W - 60, y);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    // رودخانهٔ میانی
    const rv = ctx.createLinearGradient(W / 2 - 14, 0, W / 2 + 14, 0);
    rv.addColorStop(0, 'rgba(56,189,248,0)');
    rv.addColorStop(0.5, 'rgba(56,189,248,0.18)');
    rv.addColorStop(1, 'rgba(56,189,248,0)');
    ctx.fillStyle = rv;
    ctx.fillRect(W / 2 - 14, 0, 28, H);
    // بوته‌ها
    ctx.fillStyle = 'rgba(74,222,128,0.10)';
    for (const b of bushes) {
      ctx.beginPath();
      ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2);
      ctx.fill();
    }
    // دیوار مرزی
    ctx.strokeStyle = 'rgba(250,204,21,0.22)';
    ctx.lineWidth = 2;
    ctx.strokeRect(6, 6, W - 12, H - 12);
    ctx.lineWidth = 1;
  }

  function hpBar(x, y, w, pct, color) {
    ctx.fillStyle = 'rgba(2,6,23,0.8)';
    ctx.fillRect(x - w / 2 - 1, y - 1, w + 2, 5);
    ctx.fillStyle = color;
    ctx.fillRect(x - w / 2, y, w * clamp(pct, 0, 1), 3);
  }

  function drawTower(t) {
    const c = t.side === 'blue' ? '#60a5fa' : '#f87171';
    const locked = t.base && baseLocked(t.side);
    ctx.save();
    if (t.base) {
      // کریستال پایگاه
      ctx.translate(t.x, t.y);
      ctx.rotate(Math.PI / 4);
      ctx.fillStyle = t.hitFlash > 0 ? '#fff' : c;
      ctx.globalAlpha = locked ? 0.55 : 1;
      ctx.fillRect(-16, -16, 32, 32);
      ctx.globalAlpha = 1;
      ctx.rotate(-Math.PI / 4);
      ctx.fillStyle = '#e2e8f0';
      ctx.font = '14px serif';
      ctx.textAlign = 'center';
      ctx.fillText(locked ? '🔒' : '💎', 0, 5);
      if (locked) {
        ctx.strokeStyle = 'rgba(250,204,21,0.5)';
        ctx.beginPath();
        ctx.arc(0, 0, 30 + Math.sin(G.time * 3) * 3, 0, Math.PI * 2);
        ctx.stroke();
      }
    } else {
      ctx.fillStyle = t.hitFlash > 0 ? '#fff' : c;
      ctx.globalAlpha = 0.9;
      ctx.fillRect(t.x - 13, t.y - 13, 26, 26);
      ctx.globalAlpha = 1;
      ctx.fillStyle = 'rgba(2,6,23,0.55)';
      ctx.fillRect(t.x - 13, t.y - 13, 26, 8);
      ctx.fillStyle = '#fde047';
      ctx.beginPath();
      ctx.arc(t.x, t.y + 2, 4, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
    hpBar(t.x, t.y - (t.base ? 28 : 21), t.base ? 44 : 32, t.hp / t.maxhp, c);
  }

  function drawMinion(m) {
    const c = m.side === 'blue' ? '#7dd3fc' : '#fda4af';
    ctx.fillStyle = m.hitFlash > 0 ? '#fff' : c;
    if (m.kind === 'mage') {
      ctx.beginPath();
      ctx.moveTo(m.x, m.y - 6);
      ctx.lineTo(m.x + 5, m.y + 5);
      ctx.lineTo(m.x - 5, m.y + 5);
      ctx.closePath();
      ctx.fill();
    } else {
      ctx.beginPath();
      ctx.arc(m.x, m.y, 5, 0, Math.PI * 2);
      ctx.fill();
    }
    if (m.hp < m.maxhp) hpBar(m.x, m.y - 10, 12, m.hp / m.maxhp, c);
  }

  function drawHero(h) {
    const c = h.def.color;
    if (!h.alive) return;
    ctx.save();
    // دایرهٔ برد حمله برای بازیکن
    if (h.isPlayer && G.running) {
      ctx.strokeStyle = 'rgba(250,204,21,0.14)';
      ctx.beginPath();
      ctx.arc(h.x, h.y, h.rng, 0, Math.PI * 2);
      ctx.stroke();
    }
    // سایه
    ctx.fillStyle = 'rgba(2,6,23,0.5)';
    ctx.beginPath();
    ctx.ellipse(h.x, h.y + 12, 10, 4, 0, 0, Math.PI * 2);
    ctx.fill();
    // حلقهٔ تیم
    ctx.strokeStyle = h.isPlayer ? '#facc15' : c;
    ctx.lineWidth = h.isPlayer ? 2.5 : 1.5;
    ctx.beginPath();
    ctx.arc(h.x, h.y, 13, 0, Math.PI * 2);
    ctx.stroke();
    ctx.lineWidth = 1;
    // بدنه
    ctx.fillStyle = h.hitFlash > 0 ? '#fff' : 'rgba(15,23,42,0.9)';
    ctx.beginPath();
    ctx.arc(h.x, h.y, 12, 0, Math.PI * 2);
    ctx.fill();
    ctx.font = '14px serif';
    ctx.textAlign = 'center';
    ctx.fillText(h.def.emoji, h.x, h.y + 5);
    // سپر
    if (h.shield > 0) {
      ctx.strokeStyle = 'rgba(250,204,21,0.85)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(h.x, h.y, 17, G.time * 2, G.time * 2 + Math.PI * 1.4);
      ctx.stroke();
      ctx.lineWidth = 1;
    }
    // گیج‌شدگی
    if (h.stunT > 0) {
      ctx.fillStyle = '#fde047';
      ctx.font = '10px serif';
      ctx.fillText('✦', h.x, h.y - 20);
    }
    ctx.restore();
    hpBar(h.x, h.y - 20, 28, h.hp / h.maxhp, h.side === 'blue' ? '#4ade80' : '#f87171');
    hpBar(h.x, h.y - 15, 28, h.mp / h.maxmp, '#60a5fa');
    // نشان سطح
    ctx.fillStyle = '#1e293b';
    ctx.beginPath();
    ctx.arc(h.x + 13, h.y - 13, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#fde047';
    ctx.font = 'bold 7px Tahoma';
    ctx.textAlign = 'center';
    ctx.fillText(h.lvl, h.x + 13, h.y - 10.5);
    // نوار بازگشت به پایگاه
    if (h.recallT > 0) {
      ctx.strokeStyle = '#93c5fd';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(h.x, h.y, 20, -Math.PI / 2, -Math.PI / 2 + (1 - h.recallT / 2.5) * Math.PI * 2);
      ctx.stroke();
      ctx.lineWidth = 1;
    }
  }

  function render() {
    drawArena();
    for (const t of G.towers) if (t.alive) drawTower(t);
    for (const m of G.minions) drawMinion(m);
    for (const h of G.heroes) drawHero(h);
    for (const p of G.projs) {
      ctx.fillStyle = p.color;
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 6;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    }
    for (const f of G.fx) {
      const k = 1 - f.life / f.max;
      ctx.strokeStyle = f.color;
      ctx.globalAlpha = f.life / f.max;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(f.x, f.y, f.r0 + (f.r1 - f.r0) * k, 0, Math.PI * 2);
      ctx.stroke();
      ctx.globalAlpha = 1;
      ctx.lineWidth = 1;
    }
    ctx.font = 'bold 12px Tahoma';
    ctx.textAlign = 'center';
    for (const t of G.texts) {
      ctx.fillStyle = t.color;
      ctx.globalAlpha = clamp(t.life / t.max, 0, 1);
      ctx.fillText(t.txt, t.x, t.y);
      ctx.globalAlpha = 1;
    }
    // متن ریسپاون بازیکن
    const pl = G.player;
    if (pl && !pl.alive && G.running && !G.over) {
      ctx.fillStyle = 'rgba(2,6,23,0.65)';
      ctx.fillRect(0, H / 2 - 34, W, 52);
      ctx.fillStyle = '#f87171';
      ctx.font = 'bold 15px Tahoma';
      ctx.fillText('💀 بازگشت به میدان: ' + fa(Math.max(0, pl.respawnT)) + ' ثانیه', W / 2, H / 2);
    }
  }

  /* ---------- HUD ---------- */
  function syncTowerDots() {
    const blueOut = outerTowers('blue'), redOut = outerTowers('red');
    ['hok-tb-0', 'hok-tb-1', 'hok-tb-2'].forEach((id, i) => {
      const n = $(id);
      if (n) n.classList.toggle('alive', blueOut[i] ? blueOut[i].alive : false);
    });
    ['hok-tr-0', 'hok-tr-1', 'hok-tr-2'].forEach((id, i) => {
      const n = $(id);
      if (n) n.classList.toggle('alive', redOut[i] ? redOut[i].alive : false);
    });
    const bb = $('hok-tb-base'), rb = $('hok-tr-base');
    if (bb) bb.classList.toggle('alive', baseOf('blue').alive);
    if (rb) rb.classList.toggle('alive', baseOf('red').alive);
  }

  function syncHud() {
    const pl = G.player;
    el.timer.textContent = fmtTime(G.time);
    el.kb.textContent = fa(G.kills.blue);
    el.kr.textContent = fa(G.kills.red);
    if (!pl) return;
    el.gold.textContent = fa(pl.gold);
    el.lvl.textContent = fa(pl.lvl);
    el.hp.style.width = (pl.hp / pl.maxhp) * 100 + '%';
    el.hpL.textContent = fa(Math.max(0, pl.hp)) + ' / ' + fa(pl.maxhp);
    el.mp.style.width = (pl.mp / pl.maxmp) * 100 + '%';
    el.mpL.textContent = fa(Math.max(0, pl.mp)) + ' / ' + fa(pl.maxmp);
    const need = 80 + (pl.lvl - 1) * 60;
    el.xp.style.width = (pl.lvl >= 15 ? 100 : (pl.xp / need) * 100) + '%';
    el.abBCd.style.display = pl.pcd > 0 ? 'flex' : 'none';
    el.abBCd.textContent = fa(Math.ceil(pl.pcd));
    el.abB.classList.toggle('ready', pl.pcd <= 0);
    const cost = 500 + pl.upgrades * 250;
    el.abUCost.textContent = fa(cost);
    el.abHCd.style.display = pl.recallT > 0 ? 'flex' : 'none';
    el.abHCd.textContent = fa(Math.ceil(pl.recallT));
    document.querySelectorAll('.h-order-btn').forEach((b) => {
      b.classList.toggle('active', b.dataset.order === G.order);
    });
  }

  /* ---------- شروع / پایان ---------- */
  function resetMatch() {
    G.heroes = [
      makeHero(HEROES.find((h) => h.id === G.heroId), 'blue', 0),
      makeHero(HEROES[1], 'blue', 1),
      makeHero(HEROES[4], 'blue', 2),
      makeHero(HEROES[0], 'red', 0),
      makeHero(HEROES[3], 'red', 1),
      makeHero(HEROES[5], 'red', 2),
    ];
    G.player = G.heroes[0];
    G.towers = makeTowers();
    G.minions = []; G.projs = []; G.fx = []; G.texts = [];
    G.kills = { blue: 0, red: 0 };
    G.time = 0; G.waveT = 2.5; G.waveN = 0;
    G.over = false; G.won = null; G.paused = false;
    G.order = 'push';
    el.heroInfo.textContent = G.player.def.name + ' • ' + G.player.def.powerFa + ': ' + G.player.def.powerDesc;
    syncTowerDots();
  }

  function startMatch() {
    resetMatch();
    G.running = true;
    el.overlay.style.display = 'none';
    pushEvent('👑 نبرد آغاز شد!', 'h-event-gold');
    pushEvent('♟️ اولین موج مینیون به‌زودی...', 'h-event-info');
  }

  function endMatch(won) {
    G.over = true;
    G.running = false;
    G.won = won;
    if (won) {
      G.bestWins++;
      localStorage.setItem('hok-wins', G.bestWins);
    }
    if (G.kills.blue > G.bestKills) {
      G.bestKills = G.kills.blue;
      localStorage.setItem('hok-kills', G.bestKills);
    }
    el.ovEmoji.textContent = won ? '🏆' : '💀';
    el.ovTitle.textContent = won ? 'پیروزی! پایگاه دشمن نابود شد' : 'شکست! پایگاه ما سقوط کرد';
    el.ovTitle.className = 'g-overlay-title ' + (won ? 't-green' : 't-red');
    el.ovBtn.textContent = 'بازی مجدد 👑';
    el.ovNote.textContent = 'کشتار ' + fa(G.kills.blue) + ' - ' + fa(G.kills.red) + ' • زمان ' + fmtTime(G.time) + ' • رکورد برد: ' + fa(G.bestWins);
    el.overlay.style.display = 'flex';
  }

  /* ---------- حلقهٔ بازی ---------- */
  function loop(now) {
    raf = requestAnimationFrame(loop);
    const dt = Math.min(0.05, (now - last) / 1000 || 0);
    last = now;
    if (G.running && !G.paused && !G.over) update(dt);
    render();
    if (G.player) syncHud();
  }

  /* ---------- ورودی‌ها ---------- */
  document.addEventListener('keydown', (e) => {
    const k = e.key.toLowerCase();
    keys[k] = true;
    if (['arrowup', 'arrowdown', 'arrowleft', 'arrowright', ' '].includes(k)) e.preventDefault();
    if (k === 'b') usePower(G.player);
    if (k === 'u') buyUpgrade(G.player);
    if (k === 'h') startRecall(G.player);
    if (k === 'p' && G.running && !G.over) {
      G.paused = !G.paused;
      if (G.paused) {
        el.ovEmoji.textContent = '⏸️';
        el.ovTitle.textContent = 'بازی متوقف شد';
        el.ovTitle.className = 'g-overlay-title t-yellow';
        el.ovBtn.textContent = 'ادامه بازی';
        el.ovNote.textContent = 'P برای ادامه';
        el.overlay.style.display = 'flex';
      } else el.overlay.style.display = 'none';
    }
    if (k === 'enter' && (!G.running || G.over)) startMatch();
  });
  document.addEventListener('keyup', (e) => { keys[e.key.toLowerCase()] = false; });

  // جوی‌استیک لمسی
  const joyEl = document.querySelector('.h-joystick');
  const knob = document.querySelector('.h-joystick-knob');
  function joyUpdate(e) {
    const r = joyEl.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    let dx = e.clientX - cx, dy = e.clientY - cy;
    const d = Math.hypot(dx, dy), max = r.width / 2;
    if (d > max) { dx = (dx / d) * max; dy = (dy / d) * max; }
    knob.style.transform = 'translate(calc(-50% + ' + dx + 'px), calc(-50% + ' + dy + 'px))';
    joy.x = dx / max;
    joy.y = dy / max;
  }
  joyEl.addEventListener('pointerdown', (e) => {
    joy.active = true;
    joyEl.classList.add('active');
    joyEl.setPointerCapture(e.pointerId);
    joyUpdate(e);
    e.preventDefault();
  });
  joyEl.addEventListener('pointermove', (e) => { if (joy.active) joyUpdate(e); });
  const joyEnd = () => {
    joy.active = false;
    joy.x = 0; joy.y = 0;
    joyEl.classList.remove('active');
    knob.style.transform = 'translate(-50%, -50%)';
  };
  joyEl.addEventListener('pointerup', joyEnd);
  joyEl.addEventListener('pointercancel', joyEnd);

  // کلیک روی بوم برای حرکت
  canvas.addEventListener('pointerdown', (e) => {
    if (!G.running || G.paused || G.over) return;
    const r = canvas.getBoundingClientRect();
    clickMove.x = (e.clientX - r.left) * (W / r.width);
    clickMove.y = (e.clientY - r.top) * (H / r.height);
  });

  // دکمه‌های قابلیت
  el.abB.addEventListener('click', () => usePower(G.player));
  el.abU.addEventListener('click', () => buyUpgrade(G.player));
  el.abH.addEventListener('click', () => startRecall(G.player));

  // دستور مینیون‌ها
  document.querySelectorAll('.h-order-btn').forEach((b) => {
    b.addEventListener('click', () => {
      G.order = b.dataset.order;
      pushEvent('♟️ دستور: ' + b.textContent.trim(), 'h-event-info');
    });
  });

  // انتخاب هیرو
  function applyHeroInfo(def) {
    el.heroInfo.textContent = def.name + ' • ' + def.powerFa + ': ' + def.powerDesc;
    el.abBIc.textContent = def.powerIcon;
    document.getElementById('hok-ab-b').title = def.powerFa + ' (B)';
  }

  el.heroCards.forEach((card) => {
    card.addEventListener('click', () => {
      if (G.running && !G.over) return; // وسط مبارزه قابل تغییر نیست
      G.heroId = card.dataset.hero;
      el.heroCards.forEach((c) => c.classList.toggle('selected', c === card));
      const def = HEROES.find((h) => h.id === G.heroId);
      applyHeroInfo(def);
    });
  });

  el.diff.addEventListener('change', () => { G.diff = el.diff.value; });
  el.ovBtn.addEventListener('click', () => {
    if (G.paused) { G.paused = false; el.overlay.style.display = 'none'; }
    else startMatch();
  });

  /* ---------- راه‌اندازی ---------- */
  resetMatch();
  G.running = false;
  el.ovEmoji.textContent = '👑';
  el.ovTitle.textContent = 'Honor of Kings';
  el.ovTitle.className = 'g-overlay-title t-yellow';
  el.ovBtn.textContent = 'شروع نبرد 👑';
  el.ovNote.textContent = 'هیرو را انتخاب کنید • Enter برای شروع';
  el.overlay.style.display = 'flex';
  applyHeroInfo(G.player.def);
  syncHud();
  raf = requestAnimationFrame(loop);
})();
