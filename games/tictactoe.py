def get_js():
    return r"""
function initTicTacToe(area) {
  var board = [0,0,0,0,0,0,0,0,0];
  var xTurn = true;
  var gameOver = false;

  var status = document.createElement('div');
  status.className = 'game-status';
  status.textContent = 'Your turn (X)';
  area.appendChild(status);

  var boardEl = document.createElement('div');
  boardEl.className = 'ttt-board';
  var cells = [];
  for (var i = 0; i < 9; i++) {
    var cell = document.createElement('button');
    cell.className = 'ttt-cell';
    cell.setAttribute('data-testid', 'ttt-cell-' + i);
    (function(idx) {
      cell.addEventListener('click', function() {
        if (gameOver || board[idx] !== 0 || !xTurn) return;
        board[idx] = 1;
        this.textContent = 'X';
        this.classList.add('x');
        var w = checkWin(board);
        if (w) { status.textContent = 'You win!'; gameOver = true; return; }
        if (board.indexOf(0) === -1) { status.textContent = "It's a draw!"; gameOver = true; return; }
        xTurn = false;
        status.textContent = 'Computer thinking...';
        setTimeout(function() { aiMove(); }, 300);
      });
    })(i);
    cells.push(cell);
    boardEl.appendChild(cell);
  }
  area.appendChild(boardEl);

  var resetBtn = document.createElement('button');
  resetBtn.className = 'game-reset-btn';
  resetBtn.textContent = 'Reset';
  resetBtn.setAttribute('data-testid', 'button-reset-ttt');
  resetBtn.addEventListener('click', function() {
    board = [0,0,0,0,0,0,0,0,0];
    xTurn = true;
    gameOver = false;
    status.textContent = 'Your turn (X)';
    cells.forEach(function(c) { c.textContent = ''; c.className = 'ttt-cell'; });
  });
  area.appendChild(resetBtn);

  function aiMove() {
    var best = -1, bestScore = -Infinity;
    for (var i = 0; i < 9; i++) {
      if (board[i] === 0) {
        board[i] = 2;
        var score = minimax(board, false);
        board[i] = 0;
        if (score > bestScore) { bestScore = score; best = i; }
      }
    }
    if (best !== -1) {
      board[best] = 2;
      cells[best].textContent = 'O';
      cells[best].classList.add('o');
      var w = checkWin(board);
      if (w) { status.textContent = 'Computer wins!'; gameOver = true; return; }
      if (board.indexOf(0) === -1) { status.textContent = "It's a draw!"; gameOver = true; return; }
    }
    xTurn = true;
    status.textContent = 'Your turn (X)';
  }

  function minimax(b, isMax) {
    var w = checkWinner(b);
    if (w === 2) return 1;
    if (w === 1) return -1;
    if (b.indexOf(0) === -1) return 0;
    if (isMax) {
      var best = -Infinity;
      for (var i = 0; i < 9; i++) {
        if (b[i] === 0) { b[i] = 2; best = Math.max(best, minimax(b, false)); b[i] = 0; }
      }
      return best;
    } else {
      var best = Infinity;
      for (var i = 0; i < 9; i++) {
        if (b[i] === 0) { b[i] = 1; best = Math.min(best, minimax(b, true)); b[i] = 0; }
      }
      return best;
    }
  }

  function checkWinner(b) {
    var lines = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
    for (var i = 0; i < lines.length; i++) {
      var a = lines[i][0], bb = lines[i][1], c = lines[i][2];
      if (b[a] && b[a] === b[bb] && b[a] === b[c]) return b[a];
    }
    return 0;
  }

  function checkWin(b) { return checkWinner(b) !== 0; }
}
"""


def get_css():
    return ""

