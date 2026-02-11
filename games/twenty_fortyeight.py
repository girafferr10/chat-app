def get_js():
    return r"""
function init2048(container) {
  var size = 4;
  var grid = [];
  var score = 0;
  var highScore = 0;
  var gameOver = false;
  var won = false;
  var keepPlaying = false;

  var tileColors = {
    0: '#cdc1b4',
    2: '#eee4da',
    4: '#ede0c8',
    8: '#f2b179',
    16: '#f59563',
    32: '#f67c5f',
    64: '#f65e3b',
    128: '#edcf72',
    256: '#edcc61',
    512: '#edc850',
    1024: '#edc53f',
    2048: '#edc22e'
  };

  var tileTextColors = {
    0: 'transparent',
    2: '#776e65',
    4: '#776e65',
    8: '#f9f6f2',
    16: '#f9f6f2',
    32: '#f9f6f2',
    64: '#f9f6f2',
    128: '#f9f6f2',
    256: '#f9f6f2',
    512: '#f9f6f2',
    1024: '#f9f6f2',
    2048: '#f9f6f2'
  };

  function getTileColor(val) {
    return tileColors[val] || '#3c3a32';
  }
  function getTileTextColor(val) {
    return tileTextColors[val] || '#f9f6f2';
  }
  function getTileFontSize(val) {
    if (val < 100) return '32px';
    if (val < 1000) return '26px';
    if (val < 10000) return '20px';
    return '16px';
  }

  var header = document.createElement('div');
  header.style.cssText = 'display:flex;justify-content:space-between;align-items:center;width:100%;max-width:340px;margin-bottom:8px;gap:8px;flex-wrap:wrap;';

  var titleEl = document.createElement('div');
  titleEl.style.cssText = 'font-size:28px;font-weight:800;color:#776e65;';
  titleEl.textContent = '2048';
  titleEl.setAttribute('data-testid', 'text-2048-title');
  header.appendChild(titleEl);

  var scoresWrap = document.createElement('div');
  scoresWrap.style.cssText = 'display:flex;gap:6px;';

  var scoreBox = document.createElement('div');
  scoreBox.style.cssText = 'background:#bbada0;border-radius:4px;padding:4px 12px;text-align:center;min-width:60px;';
  var scoreLabel = document.createElement('div');
  scoreLabel.style.cssText = 'font-size:10px;font-weight:600;color:#eee4da;text-transform:uppercase;';
  scoreLabel.textContent = 'Score';
  var scoreVal = document.createElement('div');
  scoreVal.style.cssText = 'font-size:18px;font-weight:700;color:#fff;';
  scoreVal.textContent = '0';
  scoreVal.setAttribute('data-testid', 'text-2048-score');
  scoreBox.appendChild(scoreLabel);
  scoreBox.appendChild(scoreVal);

  var highBox = document.createElement('div');
  highBox.style.cssText = 'background:#bbada0;border-radius:4px;padding:4px 12px;text-align:center;min-width:60px;';
  var highLabel = document.createElement('div');
  highLabel.style.cssText = 'font-size:10px;font-weight:600;color:#eee4da;text-transform:uppercase;';
  highLabel.textContent = 'Best';
  var highVal = document.createElement('div');
  highVal.style.cssText = 'font-size:18px;font-weight:700;color:#fff;';
  highVal.textContent = '0';
  highVal.setAttribute('data-testid', 'text-2048-highscore');
  highBox.appendChild(highLabel);
  highBox.appendChild(highVal);

  scoresWrap.appendChild(scoreBox);
  scoresWrap.appendChild(highBox);
  header.appendChild(scoresWrap);
  container.appendChild(header);

  var newGameBtn = document.createElement('button');
  newGameBtn.className = 'game-reset-btn';
  newGameBtn.textContent = 'New Game';
  newGameBtn.setAttribute('data-testid', 'button-2048-new');
  newGameBtn.style.cssText = 'margin-bottom:8px;';
  container.appendChild(newGameBtn);

  var statusEl = document.createElement('div');
  statusEl.className = 'game-status';
  statusEl.setAttribute('data-testid', 'text-2048-status');
  statusEl.style.cssText = 'min-height:24px;margin-bottom:6px;font-weight:600;';
  container.appendChild(statusEl);

  var boardWrap = document.createElement('div');
  boardWrap.style.cssText = 'background:#bbada0;border-radius:6px;padding:8px;display:inline-block;position:relative;';
  boardWrap.setAttribute('data-testid', 'board-2048');

  var cellEls = [];
  var tileEls = [];

  var boardGrid = document.createElement('div');
  boardGrid.style.cssText = 'display:grid;grid-template-columns:repeat(4,1fr);grid-template-rows:repeat(4,1fr);gap:8px;';

  for (var r = 0; r < size; r++) {
    cellEls[r] = [];
    tileEls[r] = [];
    for (var c = 0; c < size; c++) {
      var cell = document.createElement('div');
      cell.style.cssText = 'width:72px;height:72px;border-radius:4px;background:#cdc1b4;display:flex;align-items:center;justify-content:center;position:relative;';
      var tile = document.createElement('div');
      tile.style.cssText = 'width:100%;height:100%;border-radius:4px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:32px;transition:all 0.12s ease;position:absolute;top:0;left:0;';
      cell.appendChild(tile);
      boardGrid.appendChild(cell);
      cellEls[r][c] = cell;
      tileEls[r][c] = tile;
    }
  }
  boardWrap.appendChild(boardGrid);
  container.appendChild(boardWrap);

  var dpadWrap = document.createElement('div');
  dpadWrap.style.cssText = 'margin-top:12px;display:flex;flex-direction:column;align-items:center;gap:4px;';
  dpadWrap.setAttribute('data-testid', 'controls-2048-dpad');

  var upBtn = document.createElement('button');
  upBtn.className = 'game-reset-btn';
  upBtn.innerHTML = '&#9650;';
  upBtn.setAttribute('data-testid', 'button-2048-up');
  upBtn.style.cssText = 'width:52px;height:40px;font-size:18px;';

  var midRow = document.createElement('div');
  midRow.style.cssText = 'display:flex;gap:4px;';

  var leftBtn = document.createElement('button');
  leftBtn.className = 'game-reset-btn';
  leftBtn.innerHTML = '&#9664;';
  leftBtn.setAttribute('data-testid', 'button-2048-left');
  leftBtn.style.cssText = 'width:52px;height:40px;font-size:18px;';

  var rightBtn = document.createElement('button');
  rightBtn.className = 'game-reset-btn';
  rightBtn.innerHTML = '&#9654;';
  rightBtn.setAttribute('data-testid', 'button-2048-right');
  rightBtn.style.cssText = 'width:52px;height:40px;font-size:18px;';

  midRow.appendChild(leftBtn);
  midRow.appendChild(rightBtn);

  var downBtn = document.createElement('button');
  downBtn.className = 'game-reset-btn';
  downBtn.innerHTML = '&#9660;';
  downBtn.setAttribute('data-testid', 'button-2048-down');
  downBtn.style.cssText = 'width:52px;height:40px;font-size:18px;';

  dpadWrap.appendChild(upBtn);
  dpadWrap.appendChild(midRow);
  dpadWrap.appendChild(downBtn);
  container.appendChild(dpadWrap);

  function initGrid() {
    grid = [];
    for (var r = 0; r < size; r++) {
      grid[r] = [];
      for (var c = 0; c < size; c++) {
        grid[r][c] = 0;
      }
    }
  }

  function emptyCells() {
    var cells = [];
    for (var r = 0; r < size; r++) {
      for (var c = 0; c < size; c++) {
        if (grid[r][c] === 0) cells.push({r: r, c: c});
      }
    }
    return cells;
  }

  function addRandomTile() {
    var empty = emptyCells();
    if (empty.length === 0) return;
    var cell = empty[Math.floor(Math.random() * empty.length)];
    grid[cell.r][cell.c] = Math.random() < 0.9 ? 2 : 4;
  }

  function render() {
    for (var r = 0; r < size; r++) {
      for (var c = 0; c < size; c++) {
        var val = grid[r][c];
        var tile = tileEls[r][c];
        tile.textContent = val === 0 ? '' : val;
        tile.style.background = getTileColor(val);
        tile.style.color = getTileTextColor(val);
        tile.style.fontSize = getTileFontSize(val);
        if (val > 0) {
          tile.style.transform = 'scale(1)';
        } else {
          tile.style.transform = 'scale(0)';
        }
      }
    }
    scoreVal.textContent = score;
    highVal.textContent = highScore;
  }

  function slideRow(row) {
    var filtered = row.filter(function(v) { return v !== 0; });
    var merged = [];
    var pts = 0;
    for (var i = 0; i < filtered.length; i++) {
      if (i + 1 < filtered.length && filtered[i] === filtered[i + 1]) {
        var newVal = filtered[i] * 2;
        merged.push(newVal);
        pts += newVal;
        i++;
      } else {
        merged.push(filtered[i]);
      }
    }
    while (merged.length < size) merged.push(0);
    return {row: merged, points: pts};
  }

  function move(direction) {
    if (gameOver && !keepPlaying) return false;
    var moved = false;
    var totalPts = 0;

    if (direction === 'left') {
      for (var r = 0; r < size; r++) {
        var result = slideRow(grid[r].slice());
        for (var c = 0; c < size; c++) {
          if (grid[r][c] !== result.row[c]) moved = true;
          grid[r][c] = result.row[c];
        }
        totalPts += result.points;
      }
    } else if (direction === 'right') {
      for (var r = 0; r < size; r++) {
        var reversed = grid[r].slice().reverse();
        var result = slideRow(reversed);
        var newRow = result.row.reverse();
        for (var c = 0; c < size; c++) {
          if (grid[r][c] !== newRow[c]) moved = true;
          grid[r][c] = newRow[c];
        }
        totalPts += result.points;
      }
    } else if (direction === 'up') {
      for (var c = 0; c < size; c++) {
        var col = [];
        for (var r = 0; r < size; r++) col.push(grid[r][c]);
        var result = slideRow(col);
        for (var r = 0; r < size; r++) {
          if (grid[r][c] !== result.row[r]) moved = true;
          grid[r][c] = result.row[r];
        }
        totalPts += result.points;
      }
    } else if (direction === 'down') {
      for (var c = 0; c < size; c++) {
        var col = [];
        for (var r = 0; r < size; r++) col.push(grid[r][c]);
        col.reverse();
        var result = slideRow(col);
        var newCol = result.row.reverse();
        for (var r = 0; r < size; r++) {
          if (grid[r][c] !== newCol[r]) moved = true;
          grid[r][c] = newCol[r];
        }
        totalPts += result.points;
      }
    }

    if (moved) {
      score += totalPts;
      if (score > highScore) highScore = score;
      addRandomTile();
      render();
      checkGameState();
    }
    return moved;
  }

  function hasMovesLeft() {
    for (var r = 0; r < size; r++) {
      for (var c = 0; c < size; c++) {
        if (grid[r][c] === 0) return true;
        if (c + 1 < size && grid[r][c] === grid[r][c + 1]) return true;
        if (r + 1 < size && grid[r][c] === grid[r + 1][c]) return true;
      }
    }
    return false;
  }

  function has2048() {
    for (var r = 0; r < size; r++) {
      for (var c = 0; c < size; c++) {
        if (grid[r][c] >= 2048) return true;
      }
    }
    return false;
  }

  function checkGameState() {
    if (!won && !keepPlaying && has2048()) {
      won = true;
      statusEl.textContent = 'You reached 2048! Keep going or start a new game.';
      keepPlaying = true;
      return;
    }
    if (!hasMovesLeft()) {
      gameOver = true;
      statusEl.textContent = 'Game Over! No moves left.';
    }
  }

  function newGame() {
    score = 0;
    gameOver = false;
    won = false;
    keepPlaying = false;
    statusEl.textContent = '';
    initGrid();
    addRandomTile();
    addRandomTile();
    render();
  }

  document.addEventListener('keydown', function(e) {
    var key = e.key;
    var dir = null;
    if (key === 'ArrowLeft') dir = 'left';
    else if (key === 'ArrowRight') dir = 'right';
    else if (key === 'ArrowUp') dir = 'up';
    else if (key === 'ArrowDown') dir = 'down';
    if (dir) {
      e.preventDefault();
      move(dir);
    }
  });

  var touchStartX = 0, touchStartY = 0;
  boardWrap.addEventListener('touchstart', function(e) {
    var t = e.touches[0];
    touchStartX = t.clientX;
    touchStartY = t.clientY;
  }, {passive: true});
  boardWrap.addEventListener('touchend', function(e) {
    var t = e.changedTouches[0];
    var dx = t.clientX - touchStartX;
    var dy = t.clientY - touchStartY;
    var absDx = Math.abs(dx);
    var absDy = Math.abs(dy);
    if (Math.max(absDx, absDy) < 20) return;
    if (absDx > absDy) {
      move(dx > 0 ? 'right' : 'left');
    } else {
      move(dy > 0 ? 'down' : 'up');
    }
  }, {passive: true});

  upBtn.addEventListener('click', function() { move('up'); });
  downBtn.addEventListener('click', function() { move('down'); });
  leftBtn.addEventListener('click', function() { move('left'); });
  rightBtn.addEventListener('click', function() { move('right'); });
  newGameBtn.addEventListener('click', newGame);

  newGame();
}
"""


def get_css():
    return """
.game-2048-board { display: inline-block; }
"""
