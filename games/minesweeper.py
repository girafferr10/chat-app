def get_js():
    return r"""
function initMinesweeper(area) {
  var rows = 10, cols = 10, mineCount = 15;
  var grid, revealed, flagged, mines, gameOver, firstClick, flagMode;

  var status = document.createElement('div');
  status.className = 'game-status';
  status.setAttribute('data-testid', 'text-ms-status');
  area.appendChild(status);

  var infoBar = document.createElement('div');
  infoBar.className = 'ms-info';
  var mineCounter = document.createElement('span');
  mineCounter.setAttribute('data-testid', 'text-ms-mines');
  infoBar.appendChild(mineCounter);
  var flagBtn = document.createElement('button');
  flagBtn.className = 'game-reset-btn ms-flag-btn';
  flagBtn.setAttribute('data-testid', 'button-ms-flag');
  infoBar.appendChild(flagBtn);
  area.appendChild(infoBar);

  var boardEl = document.createElement('div');
  boardEl.className = 'ms-board';
  boardEl.setAttribute('data-testid', 'ms-board');
  area.appendChild(boardEl);

  var resetBtn = document.createElement('button');
  resetBtn.className = 'game-reset-btn';
  resetBtn.textContent = 'New Game';
  resetBtn.setAttribute('data-testid', 'button-reset-ms');
  area.appendChild(resetBtn);

  function reset() {
    grid = [];
    revealed = [];
    flagged = [];
    mines = [];
    gameOver = false;
    firstClick = true;
    flagMode = false;
    flagBtn.textContent = 'Flag: OFF';
    flagBtn.classList.remove('ms-flag-active');
    status.textContent = 'Click a cell to start';
    mineCounter.textContent = 'Mines: ' + mineCount;
    boardEl.innerHTML = '';
    boardEl.style.gridTemplateColumns = 'repeat(' + cols + ', 32px)';
    for (var r = 0; r < rows; r++) {
      grid[r] = [];
      revealed[r] = [];
      flagged[r] = [];
      for (var c = 0; c < cols; c++) {
        grid[r][c] = 0;
        revealed[r][c] = false;
        flagged[r][c] = false;
        var cell = document.createElement('button');
        cell.className = 'ms-cell';
        cell.setAttribute('data-testid', 'ms-cell-' + r + '-' + c);
        (function(rr, cc) {
          cell.addEventListener('click', function() { handleClick(rr, cc); });
          cell.addEventListener('contextmenu', function(e) { e.preventDefault(); toggleFlag(rr, cc); });
        })(r, c);
        boardEl.appendChild(cell);
      }
    }
  }

  function placeMines(safeR, safeC) {
    mines = [];
    var placed = 0;
    while (placed < mineCount) {
      var r = Math.floor(Math.random() * rows);
      var c = Math.floor(Math.random() * cols);
      if (Math.abs(r - safeR) <= 1 && Math.abs(c - safeC) <= 1) continue;
      if (grid[r][c] === -1) continue;
      grid[r][c] = -1;
      mines.push([r, c]);
      placed++;
    }
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        if (grid[r][c] === -1) continue;
        var count = 0;
        for (var dr = -1; dr <= 1; dr++) {
          for (var dc = -1; dc <= 1; dc++) {
            var nr = r + dr, nc = c + dc;
            if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && grid[nr][nc] === -1) count++;
          }
        }
        grid[r][c] = count;
      }
    }
  }

  function handleClick(r, c) {
    if (gameOver) return;
    if (flagMode) { toggleFlag(r, c); return; }
    if (flagged[r][c]) return;
    if (firstClick) {
      firstClick = false;
      placeMines(r, c);
      status.textContent = 'Playing...';
    }
    if (grid[r][c] === -1) {
      gameOver = true;
      revealAll();
      status.textContent = 'Game Over! You hit a mine.';
      return;
    }
    reveal(r, c);
    checkWin();
  }

  function toggleFlag(r, c) {
    if (gameOver || revealed[r][c]) return;
    flagged[r][c] = !flagged[r][c];
    renderCell(r, c);
    var fCount = 0;
    for (var rr = 0; rr < rows; rr++) for (var cc = 0; cc < cols; cc++) if (flagged[rr][cc]) fCount++;
    mineCounter.textContent = 'Mines: ' + (mineCount - fCount);
  }

  function reveal(r, c) {
    if (r < 0 || r >= rows || c < 0 || c >= cols) return;
    if (revealed[r][c] || flagged[r][c]) return;
    revealed[r][c] = true;
    renderCell(r, c);
    if (grid[r][c] === 0) {
      for (var dr = -1; dr <= 1; dr++) {
        for (var dc = -1; dc <= 1; dc++) {
          reveal(r + dr, c + dc);
        }
      }
    }
  }

  function revealAll() {
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        revealed[r][c] = true;
        renderCell(r, c);
      }
    }
  }

  function checkWin() {
    var unrevealed = 0;
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        if (!revealed[r][c]) unrevealed++;
      }
    }
    if (unrevealed === mineCount) {
      gameOver = true;
      status.textContent = 'You win! All mines cleared!';
      revealAll();
    }
  }

  var numColors = ['', '#5865f2', '#23a559', '#ed4245', '#9b59b6', '#f0b232', '#1abc9c', '#e91e63', '#95a5a6'];

  function renderCell(r, c) {
    var idx = r * cols + c;
    var cell = boardEl.children[idx];
    if (!cell) return;
    cell.className = 'ms-cell';
    if (flagged[r][c] && !revealed[r][c]) {
      cell.classList.add('ms-flagged');
      cell.textContent = String.fromCodePoint(0x2691);
    } else if (revealed[r][c]) {
      cell.classList.add('ms-revealed');
      if (grid[r][c] === -1) {
        cell.classList.add('ms-mine');
        cell.textContent = String.fromCodePoint(0x2739);
      } else if (grid[r][c] > 0) {
        cell.textContent = grid[r][c];
        cell.style.color = numColors[grid[r][c]] || '';
      } else {
        cell.textContent = '';
      }
    } else {
      cell.textContent = '';
    }
  }

  flagBtn.addEventListener('click', function() {
    flagMode = !flagMode;
    flagBtn.textContent = 'Flag: ' + (flagMode ? 'ON' : 'OFF');
    if (flagMode) flagBtn.classList.add('ms-flag-active');
    else flagBtn.classList.remove('ms-flag-active');
  });

  resetBtn.addEventListener('click', reset);
  reset();
}
"""


def get_css():
    return """
.ms-info { display: flex; align-items: center; gap: 12px; margin: 8px 0; }
.ms-flag-btn { font-size: 12px; }
.ms-flag-active { background: var(--accent) !important; color: #fff !important; }
.ms-board {
  display: grid; gap: 1px; background: var(--border); border: 2px solid var(--border);
  border-radius: 4px;
}
.ms-cell {
  width: 32px; height: 32px; border: none; background: var(--bg-secondary);
  color: var(--text-primary); font-size: 14px; font-weight: 700;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  padding: 0;
}
.ms-cell:hover:not(.ms-revealed) { background: var(--bg-message-hover); }
.ms-revealed { background: var(--bg-primary); cursor: default; }
.ms-mine { background: var(--red); color: #fff; }
.ms-flagged { color: var(--orange); font-size: 16px; }
"""
