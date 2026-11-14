/* ==========================================================================
   بازی مگنت (Magnet) — مرکز بازی HabibHub
   port از نسخهٔ React شامل هوش مصنوعی minimax با هرس آلفا-بتا
   ========================================================================== */
(function () {
  'use strict';

  var GRID_SIZE = 10;
  var INITIAL_MAGNETS_PER_SIDE = 6;

  // ---------- مدل ----------
  function createInitialMagnets() {
    var magnets = [];
    var offset = Math.floor((GRID_SIZE - INITIAL_MAGNETS_PER_SIDE) / 2);
    for (var i = 0; i < INITIAL_MAGNETS_PER_SIDE; i++) {
      magnets.push({ id: 'ai-' + i, owner: 'ai', pole: i % 2 === 0 ? 'N' : 'S', x: offset + i, y: 1 });
    }
    for (var j = 0; j < INITIAL_MAGNETS_PER_SIDE; j++) {
      magnets.push({ id: 'player-' + j, owner: 'player', pole: j % 2 === 0 ? 'S' : 'N', x: offset + j, y: GRID_SIZE - 2 });
    }
    return magnets;
  }

  function isValidPosition(x, y) {
    return x >= 0 && x < GRID_SIZE && y >= 0 && y < GRID_SIZE;
  }

  function isValidMove(magnet, tx, ty, all) {
    if (!isValidPosition(tx, ty)) return false;
    var occupant = null;
    for (var i = 0; i < all.length; i++) {
      if (all[i].x === tx && all[i].y === ty) { occupant = all[i]; break; }
    }
    if (occupant) {
      if (occupant.owner !== magnet.owner && occupant.pole !== magnet.pole) {
        var ddx = Math.abs(tx - magnet.x), ddy = Math.abs(ty - magnet.y);
        if (ddx <= 1 && ddy <= 1) return true;
      }
      return false;
    }
    var dx = Math.abs(tx - magnet.x), dy = Math.abs(ty - magnet.y);
    return dx <= 1 && dy <= 1 && (dx + dy > 0);
  }

  function getValidMoves(magnet, all) {
    var moves = [];
    for (var dx = -1; dx <= 1; dx++) {
      for (var dy = -1; dy <= 1; dy++) {
        if (dx === 0 && dy === 0) continue;
        var nx = magnet.x + dx, ny = magnet.y + dy;
        if (isValidMove(magnet, nx, ny, all)) moves.push({ x: nx, y: ny });
      }
    }
    return moves;
  }

  // ---------- AI ----------
  function evaluateBoard(magnets) {
    var ai = [], player = [];
    magnets.forEach(function (m) { (m.owner === 'ai' ? ai : player).push(m); });

    if (player.length === 0) return 10000;
    if (ai.length === 0) return -10000;

    var score = (ai.length - player.length) * 50;
    var center = GRID_SIZE / 2;

    ai.forEach(function (m) {
      score += (GRID_SIZE - (Math.abs(m.x - center) + Math.abs(m.y - center))) * 2;
    });
    player.forEach(function (m) {
      score -= (GRID_SIZE - (Math.abs(m.x - center) + Math.abs(m.y - center))) * 2;
    });

    ai.forEach(function (a) {
      player.forEach(function (p) {
        var dx = Math.abs(a.x - p.x), dy = Math.abs(a.y - p.y);
        if (dx <= 1 && dy <= 1) {
          score += a.pole !== p.pole ? 80 : -30;
        } else if (dx <= 2 && dy <= 2) {
          if (a.pole !== p.pole) score += 15;
        }
      });
    });

    ai.forEach(function (a) {
      var threatened = player.some(function (p) {
        return Math.abs(a.x - p.x) <= 1 && Math.abs(a.y - p.y) <= 1;
      });
      if (!threatened) score += 10;
    });

    return score;
  }

  function minimax(magnets, depth, alpha, beta, isMaximizing) {
    var ai = [], player = [];
    magnets.forEach(function (m) { (m.owner === 'ai' ? ai : player).push(m); });

    if (player.length === 0) return 10000 + depth;
    if (ai.length === 0) return -10000 - depth;
    if (depth === 0) return evaluateBoard(magnets);

    var current = isMaximizing ? ai : player;

    if (isMaximizing) {
      var maxEval = -Infinity;
      for (var i = 0; i < current.length; i++) {
        var magnet = current[i];
        // گزینه ۱: تغییر قطب
        var flipped = magnets.map(function (m) {
          return m.id === magnet.id ? { id: m.id, owner: m.owner, pole: m.pole === 'N' ? 'S' : 'N', x: m.x, y: m.y } : m;
        });
        var e1 = minimax(flipped, depth - 1, alpha, beta, false);
        if (e1 > maxEval) maxEval = e1;
        if (e1 > alpha) alpha = e1;
        if (beta <= alpha) return maxEval;

        // گزینه ۲: حرکت
        var moves = getValidMoves(magnet, magnets);
        for (var k = 0; k < moves.length; k++) {
          var move = moves[k];
          var captured = magnets.find(function (m) {
            return m.x === move.x && m.y === move.y && m.owner === 'player';
          });
          var next;
          if (captured) {
            next = magnets.filter(function (m) { return m.id !== captured.id; }).map(function (m) {
              return m.id === magnet.id ? { id: m.id, owner: m.owner, pole: m.pole, x: move.x, y: move.y } : m;
            });
          } else {
            next = magnets.map(function (m) {
              return m.id === magnet.id ? { id: m.id, owner: m.owner, pole: m.pole, x: move.x, y: move.y } : m;
            });
          }
          var e2 = minimax(next, depth - 1, alpha, beta, false);
          if (e2 > maxEval) maxEval = e2;
          if (e2 > alpha) alpha = e2;
          if (beta <= alpha) return maxEval;
        }
      }
      return maxEval;
    } else {
      var minEval = Infinity;
      for (var j = 0; j < current.length; j++) {
        var magnet2 = current[j];
        var flipped2 = magnets.map(function (m) {
          return m.id === magnet2.id ? { id: m.id, owner: m.owner, pole: m.pole === 'N' ? 'S' : 'N', x: m.x, y: m.y } : m;
        });
        var f1 = minimax(flipped2, depth - 1, alpha, beta, true);
        if (f1 < minEval) minEval = f1;
        if (f1 < beta) beta = f1;
        if (alpha <= beta) return minEval;

        var moves2 = getValidMoves(magnet2, magnets);
        for (var k2 = 0; k2 < moves2.length; k2++) {
          var move2 = moves2[k2];
          var captured2 = magnets.find(function (m) {
            return m.x === move2.x && m.y === move2.y && m.owner === 'ai';
          });
          var next2;
          if (captured2) {
            next2 = magnets.filter(function (m) { return m.id !== captured2.id; }).map(function (m) {
              return m.id === magnet2.id ? { id: m.id, owner: m.owner, pole: m.pole, x: move2.x, y: move2.y } : m;
            });
          } else {
            next2 = magnets.map(function (m) {
              return m.id === magnet2.id ? { id: m.id, owner: m.owner, pole: m.pole, x: move2.x, y: move2.y } : m;
            });
          }
          var f2 = minimax(next2, depth - 1, alpha, beta, true);
          if (f2 < minEval) minEval = f2;
          if (f2 < beta) beta = f2;
          if (alpha <= beta) return minEval;
        }
      }
      return minEval;
    }
  }

  function getBestMove(magnets, difficulty) {
    var aiMagnets = magnets.filter(function (m) { return m.owner === 'ai'; });
    if (aiMagnets.length === 0) return null;
    var depth = difficulty === 'easy' ? 1 : difficulty === 'medium' ? 2 : 3;

    if (difficulty === 'easy' && Math.random() < 0.3) {
      var rm = aiMagnets[Math.floor(Math.random() * aiMagnets.length)];
      var rmoves = getValidMoves(rm, magnets);
      if (rmoves.length > 0) {
        return { magnetId: rm.id, action: 'move', target: rmoves[Math.floor(Math.random() * rmoves.length)] };
      }
      return { magnetId: rm.id, action: 'flip' };
    }

    var bestMove = null;
    var bestScore = -Infinity;

    for (var i = 0; i < aiMagnets.length; i++) {
      var magnet = aiMagnets[i];

      // گزینه ۱: تغییر قطب
      var flipped = magnets.map(function (m) {
        return m.id === magnet.id ? { id: m.id, owner: m.owner, pole: m.pole === 'N' ? 'S' : 'N', x: m.x, y: m.y } : m;
      });
      var s1 = minimax(flipped, depth - 1, -Infinity, Infinity, false);
      if (s1 > bestScore) { bestScore = s1; bestMove = { magnetId: magnet.id, action: 'flip' }; }

      // گزینه ۲: حرکت
      var moves = getValidMoves(magnet, magnets);
      for (var k = 0; k < moves.length; k++) {
        var move = moves[k];
        var captured = magnets.find(function (m) {
          return m.x === move.x && m.y === move.y && m.owner === 'player';
        });
        var next;
        if (captured) {
          next = magnets.filter(function (m) { return m.id !== captured.id; }).map(function (m) {
            return m.id === magnet.id ? { id: m.id, owner: m.owner, pole: m.pole, x: move.x, y: move.y } : m;
          });
        } else {
          next = magnets.map(function (m) {
            return m.id === magnet.id ? { id: m.id, owner: m.owner, pole: m.pole, x: move.x, y: move.y } : m;
          });
        }
        var s2 = minimax(next, depth - 1, -Infinity, Infinity, false);
        if (s2 > bestScore) { bestScore = s2; bestMove = { magnetId: magnet.id, action: 'move', target: move }; }
      }
    }
    return bestMove;
  }

  // ---------- UI ----------
  var boardEl = document.getElementById('g-magnet-board');
  var playerEl = document.getElementById('g-magnet-player');
  var aiEl = document.getElementById('g-magnet-ai');
  var turnEl = document.getElementById('g-magnet-turn');
  var bestEl = document.getElementById('g-magnet-best');
  var difficultySel = document.getElementById('g-magnet-difficulty');
  var startBtn = document.getElementById('g-magnet-start');
  var flipBtn = document.getElementById('g-magnet-flip');
  var overlay = document.getElementById('g-magnet-overlay');
  var overlayTitle = document.getElementById('g-magnet-overlay-title');
  var overlayResult = document.getElementById('g-magnet-overlay-result');

  var magnets = createInitialMagnets();
  var gameState = 'idle'; // idle | playerTurn | aiTurn | gameover
  var selectedId = null;
  var validMoves = [];
  var difficulty = 'medium';
  var playerCaptures = 0, aiCaptures = 0;
  var aiTimer = null;

  function getHighScores() {
    try {
      var raw = localStorage.getItem('magnet-high-scores');
      if (raw) return JSON.parse(raw);
    } catch (e) { /* ignore */ }
    return { easy: 0, medium: 0, hard: 0 };
  }
  function saveHighScores(s) {
    try { localStorage.setItem('magnet-high-scores', JSON.stringify(s)); } catch (e) { /* ignore */ }
  }
  function toPersianDigits(n) {
    return String(n).replace(/\d/g, function (d) { return '۰۱۲۳۴۵۶۷۸۹'[+d]; });
  }

  function checkGameEnd(mags) {
    var p = mags.filter(function (m) { return m.owner === 'player'; }).length;
    var a = mags.filter(function (m) { return m.owner === 'ai'; }).length;
    if (p === 0) return { winner: 'ai', reason: 'همه مگنت‌های شما گرفته شدند!' };
    if (a === 0) return { winner: 'player', reason: 'شما همه مگنت‌های حریف را گرفتید!' };
    return null;
  }

  function updateHud() {
    playerEl.textContent = toPersianDigits(playerCaptures);
    aiEl.textContent = toPersianDigits(aiCaptures);
    bestEl.textContent = toPersianDigits(getHighScores()[difficulty] || 0);
    if (gameState === 'idle') turnEl.textContent = 'برای شروع دکمهٔ شروع را بزنید';
    else if (gameState === 'playerTurn') turnEl.textContent = 'نوبت شما';
    else if (gameState === 'aiTurn') turnEl.textContent = 'هوش مصنوعی در حال فکر کردن…';
    else turnEl.textContent = 'بازی پایان یافت';
  }

  function buildBoard() {
    boardEl.innerHTML = '';
    for (var y = 0; y < GRID_SIZE; y++) {
      for (var x = 0; x < GRID_SIZE; x++) {
        var cellEl = document.createElement('div');
        cellEl.className = 'm-cell' + ((x + y) % 2 === 0 ? ' m-cell-alt' : '');
        cellEl.dataset.x = x;
        cellEl.dataset.y = y;
        boardEl.appendChild(cellEl);
      }
    }
  }

  function render() {
    var magnetMap = {};
    magnets.forEach(function (m) { magnetMap[m.y * GRID_SIZE + m.x] = m; });
    var moveSet = {};
    validMoves.forEach(function (mv) { moveSet[mv.y * GRID_SIZE + mv.x] = true; });

    boardEl.querySelectorAll('.m-cell').forEach(function (cellEl) {
      var x = +cellEl.dataset.x, y = +cellEl.dataset.y;
      var m = magnetMap[y * GRID_SIZE + x];
      var isTarget = !!moveSet[y * GRID_SIZE + x];
      var isSelected = m && m.id === selectedId;

      cellEl.className = 'm-cell' + ((x + y) % 2 === 0 ? ' m-cell-alt' : '');
      if (isTarget) cellEl.classList.add(m ? 'm-cell-capture' : 'm-cell-move');
      cellEl.innerHTML = '';

      if (m) {
        var mag = document.createElement('div');
        mag.className = 'm-magnet ' + (m.owner === 'player' ? 'm-magnet-player' : 'm-magnet-ai') + (isSelected ? ' m-magnet-selected' : '');
        mag.innerHTML = '<span class="m-pole">' + m.pole + '</span><span class="m-pole-bar ' + (m.pole === 'N' ? 'm-bar-n' : 'm-bar-s') + '"></span>';
        cellEl.appendChild(mag);
      } else if (isTarget) {
        var dot = document.createElement('div');
        dot.className = 'm-move-dot';
        cellEl.appendChild(dot);
      }
    });
  }

  function handleCellClick(cellEl) {
    if (gameState !== 'playerTurn') return;
    var x = +cellEl.dataset.x, y = +cellEl.dataset.y;
    var magnet = magnets.find(function (m) { return m.x === x && m.y === y; });

    if (validMoves.some(function (mv) { return mv.x === x && mv.y === y; })) {
      moveMagnet(magnet ? magnet : null, x, y);
      return;
    }
    if (magnet && magnet.owner === 'player') {
      if (selectedId === magnet.id) {
        selectedId = null; validMoves = [];
      } else {
        selectedId = magnet.id;
        validMoves = getValidMoves(magnet, magnets);
      }
    } else {
      selectedId = null; validMoves = [];
    }
    render();
  }

  function moveMagnet(captured, tx, ty) {
    var magnet = magnets.find(function (m) { return m.id === selectedId; });
    if (!magnet) return;
    if (!isValidMove(magnet, tx, ty, magnets)) return;

    var next;
    if (captured) {
      next = magnets.filter(function (m) { return m.id !== captured.id; }).map(function (m) {
        return m.id === selectedId ? { id: m.id, owner: m.owner, pole: m.pole, x: tx, y: ty } : m;
      });
      playerCaptures++;
    } else {
      next = magnets.map(function (m) {
        return m.id === selectedId ? { id: m.id, owner: m.owner, pole: m.pole, x: tx, y: ty } : m;
      });
    }
    magnets = next;
    selectedId = null; validMoves = [];
    endTurn(checkGameEnd(magnets));
  }

  function flipPole() {
    if (gameState !== 'playerTurn' || !selectedId) return;
    magnets = magnets.map(function (m) {
      return m.id === selectedId ? { id: m.id, owner: m.owner, pole: m.pole === 'N' ? 'S' : 'N', x: m.x, y: m.y } : m;
    });
    selectedId = null; validMoves = [];
    endTurn(null);
  }

  function endTurn(gameEnd) {
    render();
    if (gameEnd) {
      finishGame(gameEnd);
      return;
    }
    gameState = 'aiTurn';
    updateHud();
    aiTimer = setTimeout(aiMove, 600);
  }

  function aiMove() {
    if (gameState !== 'aiTurn') return;
    var move = getBestMove(magnets, difficulty);
    if (!move) {
      gameState = 'playerTurn'; updateHud(); return;
    }
    var magnet = magnets.find(function (m) { return m.id === move.magnetId; });
    if (!magnet) {
      gameState = 'playerTurn'; updateHud(); return;
    }

    var next;
    if (move.action === 'flip') {
      next = magnets.map(function (m) {
        return m.id === move.magnetId ? { id: m.id, owner: m.owner, pole: m.pole === 'N' ? 'S' : 'N', x: m.x, y: m.y } : m;
      });
    } else if (move.target) {
      var captured = magnets.find(function (m) {
        return m.x === move.target.x && m.y === move.target.y && m.owner === 'player';
      });
      if (captured) {
        next = magnets.filter(function (m) { return m.id !== captured.id; }).map(function (m) {
          return m.id === move.magnetId ? { id: m.id, owner: m.owner, pole: m.pole, x: move.target.x, y: move.target.y } : m;
        });
        aiCaptures++;
      } else {
        next = magnets.map(function (m) {
          return m.id === move.magnetId ? { id: m.id, owner: m.owner, pole: m.pole, x: move.target.x, y: move.target.y } : m;
        });
      }
    } else {
      gameState = 'playerTurn'; updateHud(); return;
    }

    magnets = next;
    render();
    var gameEnd = checkGameEnd(magnets);
    if (gameEnd) { finishGame(gameEnd); return; }
    gameState = 'playerTurn';
    updateHud();
  }

  function finishGame(result) {
    gameState = 'gameover';
    if (result.winner === 'player') {
      if (playerCaptures > (getHighScores()[difficulty] || 0)) {
        var hs = getHighScores();
        hs[difficulty] = playerCaptures;
        saveHighScores(hs);
      }
      overlayTitle.textContent = '🎉 شما بردید!';
    } else {
      overlayTitle.textContent = '😔 هوش مصنوعی برد';
    }
    overlayResult.textContent = result.reason + ' — امتیاز شما: ' + toPersianDigits(playerCaptures);
    overlay.hidden = false;
    updateHud();
  }

  function startGame() {
    clearTimeout(aiTimer);
    magnets = createInitialMagnets();
    gameState = 'playerTurn';
    selectedId = null; validMoves = [];
    playerCaptures = 0; aiCaptures = 0;
    overlay.hidden = true;
    render();
    updateHud();
  }

  boardEl.addEventListener('click', function (e) {
    var cellEl = e.target.closest('.m-cell');
    if (cellEl) handleCellClick(cellEl);
  });
  flipBtn.addEventListener('click', flipPole);
  startBtn.addEventListener('click', startGame);
  difficultySel.addEventListener('change', function () {
    difficulty = difficultySel.value;
    updateHud();
  });

  buildBoard();
  render();
  updateHud();
})();
