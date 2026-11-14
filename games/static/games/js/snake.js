/* ==========================================================================
   بازی مار (Snake) — مرکز بازی HabibHub
   port از نسخهٔ React به JavaScript خالص
   ========================================================================== */
(function () {
  'use strict';

  var DIFFICULTIES = {
    easy:   { label: 'آسان',   speed: 200, grid: 16, points: 1 },
    medium: { label: 'متوسط', speed: 130, grid: 20, points: 2 },
    hard:   { label: 'سخت',   speed: 85,  grid: 24, points: 3 },
  };

  // DOM
  var canvas = document.getElementById('g-snake-canvas');
  var scoreEl = document.getElementById('g-snake-score');
  var bestEl = document.getElementById('g-snake-best');
  var lengthEl = document.getElementById('g-snake-length');
  var overlay = document.getElementById('g-snake-overlay');
  var overlayEmoji = document.getElementById('g-snake-overlay-emoji');
  var overlayTitle = document.getElementById('g-snake-overlay-title');
  var overlayBtn = document.getElementById('g-snake-overlay-btn');
  var overlayNote = document.getElementById('g-snake-overlay-note');
  var difficultySel = document.getElementById('g-snake-difficulty');
  var restartBtn = document.getElementById('g-snake-restart');
  var ctx = canvas.getContext('2d');

  // State
  var difficulty = 'medium';
  var state = 'idle'; // idle | playing | paused | gameover
  var snake, dir, nextDir, food, score, cell, cellCount;
  var lastTick = 0;
  var rafId = null;
  var touchStart = null;

  // ---------- storage ----------
  function getHighScores() {
    try {
      var raw = localStorage.getItem('snake-high-scores');
      if (raw) return JSON.parse(raw);
    } catch (e) { /* ignore */ }
    return { easy: 0, medium: 0, hard: 0 };
  }
  function saveHighScores(s) {
    try { localStorage.setItem('snake-high-scores', JSON.stringify(s)); } catch (e) { /* ignore */ }
  }

  // ---------- helpers ----------
  function config() { return DIFFICULTIES[difficulty]; }

  function randomFood() {
    var occupied = {};
    snake.forEach(function (s) { occupied[s.y * cellCount + s.x] = true; });
    var free = [];
    for (var i = 0; i < cellCount * cellCount; i++) {
      if (!occupied[i]) free.push(i);
    }
    var pick = free[Math.floor(Math.random() * free.length)];
    return { x: pick % cellCount, y: Math.floor(pick / cellCount) };
  }

  function reset() {
    cellCount = config().grid;
    var size = canvas.width / cellCount;
    cell = size;
    snake = [{ x: Math.floor(cellCount / 2), y: Math.floor(cellCount / 2) }];
    dir = { x: 1, y: 0 };
    nextDir = { x: 1, y: 0 };
    score = 0;
    food = randomFood();
    updateHud();
    draw();
  }

  function updateHud() {
    scoreEl.textContent = toPersianDigits(score);
    lengthEl.textContent = toPersianDigits(snake.length);
    bestEl.textContent = toPersianDigits(getHighScores()[difficulty]);
  }

  function toPersianDigits(n) {
    return String(n).replace(/\d/g, function (d) { return '۰۱۲۳۴۵۶۷۸۹'[+d]; });
  }

  // ---------- game step ----------
  function step() {
    dir = nextDir;
    var head = { x: snake[0].x + dir.x, y: snake[0].y + dir.y };

    // برخورد با دیوار یا بدن
    if (head.x < 0 || head.y < 0 || head.x >= cellCount || head.y >= cellCount ||
        snake.some(function (s) { return s.x === head.x && s.y === head.y; })) {
      gameOver();
      return;
    }

    snake.unshift(head);

    if (head.x === food.x && head.y === food.y) {
      score += config().points;
      food = randomFood();
    } else {
      snake.pop();
    }
    updateHud();
    draw();
  }

  function gameOver() {
    state = 'gameover';
    var hs = getHighScores();
    var isRecord = score > (hs[difficulty] || 0);
    if (isRecord) {
      hs[difficulty] = score;
      saveHighScores(hs);
    }
    overlayEmoji.textContent = isRecord && score > 0 ? '🏆' : '💀';
    overlayTitle.textContent = isRecord && score > 0 ? 'رکورد جدید! امتیاز: ' + toPersianDigits(score) : 'بازی تمام شد — امتیاز: ' + toPersianDigits(score);
    overlayBtn.textContent = 'بازی مجدد';
    overlayNote.textContent = 'یا Enter را بزنید';
    overlay.hidden = false;
    updateHud();
  }

  // ---------- render ----------
  function draw() {
    // پس‌زمینه
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // شبکه
    ctx.strokeStyle = 'rgba(51, 65, 85, 0.35)';
    ctx.lineWidth = 1;
    for (var i = 0; i <= cellCount; i++) {
      ctx.beginPath();
      ctx.moveTo(i * cell, 0); ctx.lineTo(i * cell, canvas.height);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, i * cell); ctx.lineTo(canvas.width, i * cell);
      ctx.stroke();
    }

    // غذا
    ctx.fillStyle = '#ef4444';
    ctx.shadowColor = 'rgba(239, 68, 68, 0.7)';
    ctx.shadowBlur = 12;
    ctx.beginPath();
    ctx.arc(food.x * cell + cell / 2, food.y * cell + cell / 2, cell * 0.32, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;

    // مار
    for (var j = snake.length - 1; j >= 0; j--) {
      var seg = snake[j];
      var t = j / Math.max(snake.length - 1, 1);
      var r = Math.round(74 + t * 10);
      var g = Math.round(222 - t * 60);
      var b = Math.round(128 + t * 20);
      ctx.fillStyle = j === 0 ? '#a7f3d0' : 'rgb(' + r + ',' + g + ',' + b + ')';
      ctx.shadowColor = 'rgba(74, 222, 128, 0.5)';
      ctx.shadowBlur = j === 0 ? 10 : 0;
      roundRect(seg.x * cell + 1, seg.y * cell + 1, cell - 2, cell - 2, j === 0 ? 6 : 4);
      ctx.shadowBlur = 0;
    }
  }

  function roundRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.fill();
  }

  // ---------- loop ----------
  function loop(timestamp) {
    if (state === 'playing') {
      var speed = config().speed;
      if (!lastTick) lastTick = timestamp;
      if (timestamp - lastTick >= speed) {
        step();
        lastTick = timestamp;
      }
    }
    if (state !== 'gameover') rafId = requestAnimationFrame(loop);
  }

  // ---------- controls ----------
  function startGame() {
    reset();
    state = 'playing';
    lastTick = 0;
    overlay.hidden = true;
    if (rafId) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(loop);
  }

  function togglePause() {
    if (state === 'playing') {
      state = 'paused';
      overlayEmoji.textContent = '⏸️';
      overlayTitle.textContent = 'متوقف';
      overlayBtn.textContent = 'ادامه';
      overlayNote.textContent = 'یا P / Esc را بزنید';
      overlay.hidden = false;
    } else if (state === 'paused') {
      state = 'playing';
      lastTick = 0;
      overlay.hidden = true;
    }
  }

  function setDir(x, y) {
    // جلوگیری از برگشت ۱۸۰ درجه
    if (dir.x + x === 0 && dir.y + y === 0) return;
    nextDir = { x: x, y: y };
  }

  document.addEventListener('keydown', function (e) {
    if (state === 'idle' || state === 'gameover') {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        startGame();
      }
      return;
    }
    if (e.key === 'p' || e.key === 'P' || e.key === 'Escape') {
      e.preventDefault();
      togglePause();
      return;
    }
    if (state !== 'playing') return;
    switch (e.key) {
      case 'ArrowLeft': case 'a': case 'A': e.preventDefault(); setDir(-1, 0); break;
      case 'ArrowRight': case 'd': case 'D': e.preventDefault(); setDir(1, 0); break;
      case 'ArrowUp': case 'w': case 'W': e.preventDefault(); setDir(0, -1); break;
      case 'ArrowDown': case 's': case 'S': e.preventDefault(); setDir(0, 1); break;
    }
  });

  // لمسی: swipe
  canvas.addEventListener('touchstart', function (e) {
    touchStart = { x: e.touches[0].clientX, y: e.touches[0].clientY };
  }, { passive: true });
  canvas.addEventListener('touchend', function (e) {
    if (!touchStart || state !== 'playing') return;
    var dx = e.changedTouches[0].clientX - touchStart.x;
    var dy = e.changedTouches[0].clientY - touchStart.y;
    if (Math.abs(dx) < 24 && Math.abs(dy) < 24) return;
    if (Math.abs(dx) > Math.abs(dy)) setDir(dx > 0 ? 1 : -1, 0);
    else setDir(0, dy > 0 ? 1 : -1);
    touchStart = null;
  }, { passive: true });

  // دکمه‌های لمسی
  document.querySelectorAll('[data-dir]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var d = btn.getAttribute('data-dir').split(',');
      setDir(+d[0], +d[1]);
    });
  });

  difficultySel.addEventListener('change', function () {
    difficulty = difficultySel.value;
    if (state === 'playing' || state === 'paused') {
      startGame();
    } else {
      reset();
    }
  });

  overlayBtn.addEventListener('click', function () {
    if (state === 'paused') togglePause();
    else startGame();
  });
  restartBtn.addEventListener('click', startGame);

  // شروع
  reset();
  overlayEmoji.textContent = '🐍';
  overlayTitle.textContent = 'آماده بازی؟';
  overlayBtn.textContent = 'شروع بازی';
  overlayNote.textContent = 'یا Enter را بزنید';
  rafId = requestAnimationFrame(loop);
})();
