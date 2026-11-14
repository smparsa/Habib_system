/* ==========================================================================
   بازی تتریس (Tetris) — مرکز بازی HabibHub
   port از نسخهٔ React: bag تصادفی، ghost، hold، wall-kick و امتیازدهی استاندارد
   ========================================================================== */
(function () {
  'use strict';

  var BOARD_WIDTH = 10;
  var BOARD_HEIGHT = 20;
  var CELL = 30;
  var POINTS = { SINGLE: 100, DOUBLE: 300, TRIPLE: 500, TETRIS: 800, SOFT_DROP: 1, HARD_DROP: 2 };
  var LEVEL_SPEEDS = {
    easy: function (level) { return Math.max(800 - level * 50, 200); },
    normal: function (level) { return Math.max(600 - level * 50, 100); },
    hard: function (level) { return Math.max(400 - level * 40, 50); },
  };

  var TETROMINOES = {
    I: {
      shapes: [
        [[0,0,0,0],[1,1,1,1],[0,0,0,0],[0,0,0,0]],
        [[0,0,1,0],[0,0,1,0],[0,0,1,0],[0,0,1,0]],
        [[0,0,0,0],[0,0,0,0],[1,1,1,1],[0,0,0,0]],
        [[0,1,0,0],[0,1,0,0],[0,1,0,0],[0,1,0,0]],
      ],
      color: '#06b6d4', glow: 'rgba(6,182,212,0.5)', gradient: ['#22d3ee', '#0891b2'],
    },
    O: {
      shapes: [
        [[0,1,1,0],[0,1,1,0],[0,0,0,0],[0,0,0,0]],
        [[0,1,1,0],[0,1,1,0],[0,0,0,0],[0,0,0,0]],
        [[0,1,1,0],[0,1,1,0],[0,0,0,0],[0,0,0,0]],
        [[0,1,1,0],[0,1,1,0],[0,0,0,0],[0,0,0,0]],
      ],
      color: '#eab308', glow: 'rgba(234,179,8,0.5)', gradient: ['#fde047', '#ca8a04'],
    },
    T: {
      shapes: [
        [[0,1,0,0],[1,1,1,0],[0,0,0,0],[0,0,0,0]],
        [[0,1,0,0],[0,1,1,0],[0,1,0,0],[0,0,0,0]],
        [[0,0,0,0],[1,1,1,0],[0,1,0,0],[0,0,0,0]],
        [[0,1,0,0],[1,1,0,0],[0,1,0,0],[0,0,0,0]],
      ],
      color: '#a855f7', glow: 'rgba(168,85,247,0.5)', gradient: ['#c084fc', '#7e22ce'],
    },
    S: {
      shapes: [
        [[0,1,1,0],[1,1,0,0],[0,0,0,0],[0,0,0,0]],
        [[0,1,0,0],[0,1,1,0],[0,0,1,0],[0,0,0,0]],
        [[0,0,0,0],[0,1,1,0],[1,1,0,0],[0,0,0,0]],
        [[1,0,0,0],[1,1,0,0],[0,1,0,0],[0,0,0,0]],
      ],
      color: '#22c55e', glow: 'rgba(34,197,94,0.5)', gradient: ['#4ade80', '#15803d'],
    },
    Z: {
      shapes: [
        [[1,1,0,0],[0,1,1,0],[0,0,0,0],[0,0,0,0]],
        [[0,0,1,0],[0,1,1,0],[0,1,0,0],[0,0,0,0]],
        [[0,0,0,0],[0,1,1,0],[1,1,0,0],[0,0,0,0]],
        [[0,1,0,0],[1,1,0,0],[1,0,0,0],[0,0,0,0]],
      ],
      color: '#ef4444', glow: 'rgba(239,68,68,0.5)', gradient: ['#f87171', '#b91c1c'],
    },
    J: {
      shapes: [
        [[1,0,0,0],[1,1,1,0],[0,0,0,0],[0,0,0,0]],
        [[0,1,1,0],[0,1,0,0],[0,1,0,0],[0,0,0,0]],
        [[0,0,0,0],[1,1,1,0],[0,0,1,0],[0,0,0,0]],
        [[0,1,0,0],[0,1,0,0],[1,1,0,0],[0,0,0,0]],
      ],
      color: '#3b82f6', glow: 'rgba(59,130,246,0.5)', gradient: ['#60a5fa', '#1d4ed8'],
    },
    L: {
      shapes: [
        [[0,0,1,0],[1,1,1,0],[0,0,0,0],[0,0,0,0]],
        [[0,1,0,0],[0,1,0,0],[0,1,1,0],[0,0,0,0]],
        [[0,0,0,0],[1,1,1,0],[1,0,0,0],[0,0,0,0]],
        [[1,1,0,0],[0,1,0,0],[0,1,0,0],[0,0,0,0]],
      ],
      color: '#f97316', glow: 'rgba(249,115,22,0.5)', gradient: ['#fb923c', '#c2410c'],
    },
  };

  // ---------- bag randomizer (7-bag) ----------
  function createBag() {
    var types = ['I', 'O', 'T', 'S', 'Z', 'J', 'L'];
    for (var i = types.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = types[i]; types[i] = types[j]; types[j] = tmp;
    }
    return types;
  }

  // ---------- helpers ----------
  function toPersianDigits(n) {
    return String(n).replace(/\d/g, function (d) { return '۰۱۲۳۴۵۶۷۸۹'[+d]; });
  }
  function createEmptyBoard() {
    var b = [];
    for (var y = 0; y < BOARD_HEIGHT; y++) b.push(new Array(BOARD_WIDTH).fill(0));
    return b;
  }
  function createTetromino(type) {
    return {
      type: type,
      shape: TETROMINOES[type].shapes[0],
      color: TETROMINOES[type].color,
      position: { x: Math.floor(BOARD_WIDTH / 2) - 2, y: 0 },
      rotation: 0,
    };
  }
  function checkCollision(b, piece, offsetX, offsetY, newShape) {
    offsetX = offsetX || 0; offsetY = offsetY || 0;
    var shape = newShape || piece.shape;
    for (var y = 0; y < shape.length; y++) {
      for (var x = 0; x < shape[y].length; x++) {
        if (shape[y][x]) {
          var nx = piece.position.x + x + offsetX;
          var ny = piece.position.y + y + offsetY;
          if (nx < 0 || nx >= BOARD_WIDTH || ny >= BOARD_HEIGHT) return true;
          if (ny >= 0 && b[ny][nx] !== 0) return true;
        }
      }
    }
    return false;
  }
  function mergePiece(b, piece) {
    var nb = b.map(function (row) { return row.slice(); });
    for (var y = 0; y < piece.shape.length; y++) {
      for (var x = 0; x < piece.shape[y].length; x++) {
        if (piece.shape[y][x]) {
          var by = piece.position.y + y, bx = piece.position.x + x;
          if (by >= 0 && by < BOARD_HEIGHT && bx >= 0 && bx < BOARD_WIDTH) {
            nb[by][bx] = piece.color;
          }
        }
      }
    }
    return nb;
  }
  function clearLines(b) {
    var cleared = [];
    var nb = b.filter(function (row, idx) {
      var full = row.every(function (c) { return c !== 0; });
      if (full) { cleared.push(idx); return false; }
      return true;
    });
    while (nb.length < BOARD_HEIGHT) nb.unshift(new Array(BOARD_WIDTH).fill(0));
    return { board: nb, count: cleared.length, rows: cleared };
  }
  function getGhostY(b, piece) {
    var offsetY = 0;
    while (!checkCollision(b, piece, 0, offsetY + 1)) offsetY++;
    return piece.position.y + offsetY;
  }

  // ---------- state ----------
  var canvas = document.getElementById('g-tetris-canvas');
  var ctx = canvas.getContext('2d');
  var scoreEl = document.getElementById('g-tetris-score');
  var linesEl = document.getElementById('g-tetris-lines');
  var levelEl = document.getElementById('g-tetris-level');
  var bestEl = document.getElementById('g-tetris-best');
  var holdCanvas = document.getElementById('g-tetris-hold');
  var holdCtx = holdCanvas ? holdCanvas.getContext('2d') : null;
  var nextCanvas = document.getElementById('g-tetris-next');
  var nextCtx = nextCanvas ? nextCanvas.getContext('2d') : null;
  var difficultySel = document.getElementById('g-tetris-difficulty');
  var restartBtn = document.getElementById('g-tetris-restart');
  var overlay = document.getElementById('g-tetris-overlay');
  var overlayEmoji = document.getElementById('g-tetris-overlay-emoji');
  var overlayTitle = document.getElementById('g-tetris-overlay-title');
  var overlayBtn = document.getElementById('g-tetris-overlay-btn');
  var overlayNote = document.getElementById('g-tetris-overlay-note');

  var board, currentPiece, nextPieces, holdPiece, canHold;
  var gameState = 'idle'; // idle | playing | paused | gameover
  var score, lines, level, difficulty = 'normal';
  var bag = [], lastDrop = 0, rafId = null;
  var clearedRows = [];

  function getHighScores() {
    try {
      var raw = localStorage.getItem('tetris-high-scores');
      if (raw) return JSON.parse(raw);
    } catch (e) { /* ignore */ }
    return { easy: 0, normal: 0, hard: 0 };
  }
  function saveHighScores(s) {
    try { localStorage.setItem('tetris-high-scores', JSON.stringify(s)); } catch (e) { /* ignore */ }
  }

  function updateHud() {
    scoreEl.textContent = toPersianDigits(score || 0);
    linesEl.textContent = toPersianDigits(lines || 0);
    levelEl.textContent = toPersianDigits(level || 1);
    bestEl.textContent = toPersianDigits(getHighScores()[difficulty] || 0);
  }

  function getNextPiece() {
    if (bag.length === 0) bag = createBag();
    return bag.shift();
  }

  function spawnPiece(type) {
    var pieceType = type || getNextPiece();
    var newPiece = createTetromino(pieceType);
    if (checkCollision(board, newPiece)) {
      currentPiece = newPiece;
      render();
      gameOver();
      return;
    }
    currentPiece = newPiece;
    canHold = true;
    while (nextPieces.length < 3) nextPieces.push(getNextPiece());
    renderNext();
    render();
  }

  function lockPiece() {
    var merged = mergePiece(board, currentPiece);
    var res = clearLines(merged);
    if (res.count > 0) {
      clearedRows = res.rows;
      setTimeout(function () { clearedRows = []; render(); }, 250);
      var pts = 0;
      switch (res.count) {
        case 1: pts = POINTS.SINGLE; break;
        case 2: pts = POINTS.DOUBLE; break;
        case 3: pts = POINTS.TRIPLE; break;
        case 4: pts = POINTS.TETRIS; break;
      }
      score += pts * level;
      lines += res.count;
      var newLevel = Math.floor(lines / 10) + 1;
      if (newLevel !== level) level = newLevel;
    }
    board = res.board;
    spawnPiece();
  }

  function moveLeft() {
    if (gameState !== 'playing' || !currentPiece) return;
    if (!checkCollision(board, currentPiece, -1, 0)) {
      currentPiece.position.x--;
      render();
    }
  }
  function moveRight() {
    if (gameState !== 'playing' || !currentPiece) return;
    if (!checkCollision(board, currentPiece, 1, 0)) {
      currentPiece.position.x++;
      render();
    }
  }
  function moveDown() {
    if (gameState !== 'playing' || !currentPiece) return false;
    if (!checkCollision(board, currentPiece, 0, 1)) {
      currentPiece.position.y++;
      return true;
    }
    lockPiece();
    return false;
  }
  function softDrop() {
    if (moveDown()) { score += POINTS.SOFT_DROP; updateHud(); render(); }
  }
  function hardDrop() {
    if (gameState !== 'playing' || !currentPiece) return;
    var dropDistance = 0;
    while (!checkCollision(board, currentPiece, 0, dropDistance + 1)) dropDistance++;
    currentPiece.position.y += dropDistance;
    score += dropDistance * POINTS.HARD_DROP;
    lockPiece();
  }
  function rotate(direction) {
    if (gameState !== 'playing' || !currentPiece) return;
    direction = direction || 1;
    var piece = currentPiece;
    var newRotation = ((piece.rotation + direction) % 4 + 4) % 4;
    var newShape = TETROMINOES[piece.type].shapes[newRotation];

    if (!checkCollision(board, piece, 0, 0, newShape)) {
      piece.shape = newShape; piece.rotation = newRotation;
      render();
      return;
    }
    var kicks = [
      { x: -1, y: 0 }, { x: 1, y: 0 }, { x: -2, y: 0 }, { x: 2, y: 0 },
      { x: 0, y: -1 }, { x: -1, y: -1 }, { x: 1, y: -1 },
    ];
    for (var i = 0; i < kicks.length; i++) {
      if (!checkCollision(board, piece, kicks[i].x, kicks[i].y, newShape)) {
        piece.shape = newShape;
        piece.rotation = newRotation;
        piece.position.x += kicks[i].x;
        piece.position.y += kicks[i].y;
        render();
        return;
      }
    }
  }
  function hold() {
    if (!currentPiece || !canHold || gameState !== 'playing') return;
    var currentType = currentPiece.type;
    if (holdPiece) {
      var swap = holdPiece;
      holdPiece = currentType;
      spawnPiece(swap);
    } else {
      holdPiece = currentType;
      spawnPiece();
    }
    canHold = false;
    renderMini(holdCtx, holdPiece, holdCanvas);
  }

  function gameOver() {
    gameState = 'gameover';
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

  function startGame() {
    bag = [];
    board = createEmptyBoard();
    score = 0; lines = 0; level = 1;
    holdPiece = null; canHold = true;
    nextPieces = [];
    lastDrop = 0;
    clearedRows = [];
    gameState = 'playing';
    overlay.hidden = true;
    renderMini(holdCtx, null, holdCanvas);
    spawnPiece();
    updateHud();
    if (rafId) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(loop);
  }

  function togglePause() {
    if (gameState === 'playing') {
      gameState = 'paused';
      overlayEmoji.textContent = '⏸️';
      overlayTitle.textContent = 'متوقف';
      overlayBtn.textContent = 'ادامه';
      overlayNote.textContent = 'یا P / Esc را بزنید';
      overlay.hidden = false;
    } else if (gameState === 'paused') {
      gameState = 'playing';
      lastDrop = 0;
      overlay.hidden = true;
    }
  }

  // ---------- loop ----------
  function loop(timestamp) {
    if (gameState === 'playing') {
      var speed = LEVEL_SPEEDS[difficulty](level);
      if (!lastDrop) lastDrop = timestamp;
      if (timestamp - lastDrop >= speed) {
        moveDown();
        lastDrop = timestamp;
      }
      render();
    }
    if (gameState !== 'gameover') rafId = requestAnimationFrame(loop);
  }

  // ---------- render ----------
  function drawCell(c, px, py, size, color, gradient, glow) {
    if (gradient) {
      var grd = c.createLinearGradient(px, py, px + size, py + size);
      grd.addColorStop(0, gradient[0]);
      grd.addColorStop(1, gradient[1]);
      c.fillStyle = grd;
    } else {
      c.fillStyle = color;
    }
    c.shadowColor = glow || 'transparent';
    c.shadowBlur = 6;
    c.fillRect(px + 1, py + 1, size - 2, size - 2);
    c.shadowBlur = 0;
    c.strokeStyle = 'rgba(15, 23, 42, 0.4)';
    c.strokeRect(px + 1, py + 1, size - 2, size - 2);
  }

  function findTypeByColor(color) {
    for (var t in TETROMINOES) {
      if (TETROMINOES[t].color === color) return t;
    }
    return null;
  }

  function render() {
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // شبکه
    ctx.strokeStyle = 'rgba(51, 65, 85, 0.4)';
    ctx.lineWidth = 1;
    for (var x = 0; x <= BOARD_WIDTH; x++) {
      ctx.beginPath(); ctx.moveTo(x * CELL, 0); ctx.lineTo(x * CELL, canvas.height); ctx.stroke();
    }
    for (var y = 0; y <= BOARD_HEIGHT; y++) {
      ctx.beginPath(); ctx.moveTo(0, y * CELL); ctx.lineTo(canvas.width, y * CELL); ctx.stroke();
    }

    // قطعه‌های قفل‌شده
    for (var ry = 0; ry < BOARD_HEIGHT; ry++) {
      for (var rx = 0; rx < BOARD_WIDTH; rx++) {
        var v = board[ry][rx];
        if (v) {
          var isCleared = clearedRows.indexOf(ry) !== -1;
          ctx.globalAlpha = isCleared ? 0.3 : 1;
          var t = findTypeByColor(v);
          drawCell(ctx, rx * CELL, ry * CELL, CELL, v, t ? TETROMINOES[t].gradient : null, null);
          ctx.globalAlpha = 1;
        }
      }
    }

    if (currentPiece) {
      var tet = TETROMINOES[currentPiece.type];
      // ghost
      var gy = getGhostY(board, currentPiece);
      for (var sy = 0; sy < currentPiece.shape.length; sy++) {
        for (var sx = 0; sx < currentPiece.shape[sy].length; sx++) {
          if (currentPiece.shape[sy][sx]) {
            var px = (currentPiece.position.x + sx) * CELL;
            var py = gy + sy >= 0 ? (gy + sy) * CELL : (gy + sy) * CELL;
            ctx.strokeStyle = tet.glow;
            ctx.lineWidth = 2;
            ctx.strokeRect(px + 3, py + 3, CELL - 6, CELL - 6);
          }
        }
      }
      // قطعهٔ فعلی
      for (var cy = 0; cy < currentPiece.shape.length; cy++) {
        for (var cx = 0; cx < currentPiece.shape[cy].length; cx++) {
          if (currentPiece.shape[cy][cx]) {
            var by = currentPiece.position.y + cy;
            if (by >= 0) {
              drawCell(ctx, (currentPiece.position.x + cx) * CELL, by * CELL, CELL,
                currentPiece.color, tet.gradient, tet.glow);
            }
          }
        }
      }
    }
    updateHud();
  }

  function renderMini(c, type, cv) {
    if (!c) return;
    c.clearRect(0, 0, cv.width, cv.height);
    if (!type) return;
    var tet = TETROMINOES[type];
    var shape = tet.shapes[0];
    var size = cv.width / 4.5;
    var offset = (cv.width - 4 * size) / 2;
    for (var y = 0; y < shape.length; y++) {
      for (var x = 0; x < shape[y].length; x++) {
        if (shape[y][x]) {
          var grd = c.createLinearGradient(offset + x * size, offset + y * size, offset + (x + 1) * size, offset + (y + 1) * size);
          grd.addColorStop(0, tet.gradient[0]);
          grd.addColorStop(1, tet.gradient[1]);
          c.fillStyle = grd;
          c.fillRect(offset + x * size + 1, offset + y * size + 1, size - 2, size - 2);
        }
      }
    }
  }

  function renderNext() {
    if (!nextCtx) return;
    nextCtx.clearRect(0, 0, nextCanvas.width, nextCanvas.height);
    (nextPieces || []).forEach(function (type, idx) {
      var tet = TETROMINOES[type];
      var shape = tet.shapes[0];
      var size = nextCanvas.width / 6;
      var slotH = nextCanvas.height / 3;
      var ox = (nextCanvas.width - 4 * size) / 2;
      var oy = idx * slotH + (slotH - 2 * size) / 2;
      for (var y = 0; y < shape.length; y++) {
        for (var x = 0; x < shape[y].length; x++) {
          if (shape[y][x] && oy + y * size >= 0) {
            var grd = nextCtx.createLinearGradient(ox + x * size, oy + y * size, ox + (x + 1) * size, oy + (y + 1) * size);
            grd.addColorStop(0, tet.gradient[0]);
            grd.addColorStop(1, tet.gradient[1]);
            nextCtx.fillStyle = grd;
            nextCtx.fillRect(ox + x * size + 1, oy + y * size + 1, size - 2, size - 2);
          }
        }
      }
    });
  }

  // ---------- controls ----------
  document.addEventListener('keydown', function (e) {
    if (gameState === 'gameover' || gameState === 'idle') {
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
    if (gameState !== 'playing') return;
    switch (e.key) {
      case 'ArrowLeft': case 'a': case 'A': e.preventDefault(); moveLeft(); break;
      case 'ArrowRight': case 'd': case 'D': e.preventDefault(); moveRight(); break;
      case 'ArrowDown': case 's': case 'S': e.preventDefault(); softDrop(); break;
      case 'ArrowUp': case 'w': case 'W': e.preventDefault(); rotate(1); break;
      case 'z': case 'Z': e.preventDefault(); rotate(-1); break;
      case ' ': e.preventDefault(); hardDrop(); break;
      case 'c': case 'C': case 'Shift': e.preventDefault(); hold(); break;
    }
  });

  // دکمه‌های لمسی
  document.querySelectorAll('[data-tetris-action]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var action = btn.getAttribute('data-tetris-action');
      if (action === 'left') moveLeft();
      else if (action === 'right') moveRight();
      else if (action === 'down') softDrop();
      else if (action === 'rotate') rotate(1);
      else if (action === 'drop') hardDrop();
      else if (action === 'hold') hold();
    });
  });

  overlayBtn.addEventListener('click', function () {
    if (gameState === 'paused') togglePause();
    else startGame();
  });
  restartBtn.addEventListener('click', startGame);
  difficultySel.addEventListener('change', function () {
    difficulty = difficultySel.value;
    updateHud();
    if (gameState === 'playing' || gameState === 'paused') startGame();
  });

  // ---------- init ----------
  board = createEmptyBoard();
  nextPieces = [];
  score = 0; lines = 0; level = 1;
  updateHud();
  render();
  renderNext();
  renderMini(holdCtx, null, holdCanvas);
  rafId = requestAnimationFrame(loop);
})();
