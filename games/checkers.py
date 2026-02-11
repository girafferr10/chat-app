def get_js():
    return r"""
function initCheckers(container) {
  var EMPTY = 0, RED = 1, BLACK = 2, RED_KING = 3, BLACK_KING = 4;
  var board = [];
  var selectedPiece = null;
  var validMoves = [];
  var playerTurn = true;
  var redScore = 0;
  var blackScore = 0;
  var gamesPlayed = 0;

  var statusEl = document.createElement('div');
  statusEl.className = 'game-status';
  statusEl.setAttribute('data-testid', 'text-checkers-status');
  container.appendChild(statusEl);

  var scoreEl = document.createElement('div');
  scoreEl.className = 'ck-score';
  scoreEl.setAttribute('data-testid', 'text-checkers-score');
  container.appendChild(scoreEl);

  var boardEl = document.createElement('div');
  boardEl.className = 'ck-board';
  boardEl.setAttribute('data-testid', 'ck-board');
  container.appendChild(boardEl);

  var controls = document.createElement('div');
  controls.className = 'ck-controls';
  var newGameBtn = document.createElement('button');
  newGameBtn.className = 'game-reset-btn';
  newGameBtn.textContent = 'New Game';
  newGameBtn.setAttribute('data-testid', 'button-checkers-new');
  newGameBtn.addEventListener('click', function() { newGame(); });
  controls.appendChild(newGameBtn);
  container.appendChild(controls);

  function initBoard() {
    board = [];
    for (var r = 0; r < 8; r++) {
      board[r] = [];
      for (var c = 0; c < 8; c++) {
        board[r][c] = EMPTY;
        if ((r + c) % 2 === 1) {
          if (r < 3) board[r][c] = BLACK;
          else if (r > 4) board[r][c] = RED;
        }
      }
    }
  }

  function isRed(piece) { return piece === RED || piece === RED_KING; }
  function isBlack(piece) { return piece === BLACK || piece === BLACK_KING; }
  function isKing(piece) { return piece === RED_KING || piece === BLACK_KING; }
  function isPlayer(piece) { return isRed(piece); }
  function isAI(piece) { return isBlack(piece); }

  function getMovesForPiece(r, c) {
    var piece = board[r][c];
    if (piece === EMPTY) return { jumps: [], simple: [] };
    var dirs = [];
    if (piece === RED || piece === RED_KING) dirs.push([-1, -1], [-1, 1]);
    if (piece === BLACK || piece === BLACK_KING) dirs.push([1, -1], [1, 1]);
    if (isKing(piece)) {
      if (isRed(piece)) { dirs = [[-1,-1],[-1,1],[1,-1],[1,1]]; }
      else { dirs = [[-1,-1],[-1,1],[1,-1],[1,1]]; }
    }
    var jumps = [];
    var simple = [];
    for (var d = 0; d < dirs.length; d++) {
      var dr = dirs[d][0], dc = dirs[d][1];
      var nr = r + dr, nc = c + dc;
      if (nr >= 0 && nr < 8 && nc >= 0 && nc < 8) {
        if (board[nr][nc] === EMPTY) {
          simple.push({ fr: r, fc: c, tr: nr, tc: nc });
        } else if ((isRed(piece) && isBlack(board[nr][nc])) || (isBlack(piece) && isRed(board[nr][nc]))) {
          var jr = nr + dr, jc = nc + dc;
          if (jr >= 0 && jr < 8 && jc >= 0 && jc < 8 && board[jr][jc] === EMPTY) {
            jumps.push({ fr: r, fc: c, tr: jr, tc: jc, cr: nr, cc: nc });
          }
        }
      }
    }
    return { jumps: jumps, simple: simple };
  }

  function getAllMoves(isPlayerSide) {
    var allJumps = [];
    var allSimple = [];
    for (var r = 0; r < 8; r++) {
      for (var c = 0; c < 8; c++) {
        var piece = board[r][c];
        if ((isPlayerSide && isPlayer(piece)) || (!isPlayerSide && isAI(piece))) {
          var m = getMovesForPiece(r, c);
          allJumps = allJumps.concat(m.jumps);
          allSimple = allSimple.concat(m.simple);
        }
      }
    }
    if (allJumps.length > 0) return allJumps;
    return allSimple;
  }

  function makeMove(move) {
    var piece = board[move.fr][move.fc];
    board[move.fr][move.fc] = EMPTY;
    board[move.tr][move.tc] = piece;
    if (move.cr !== undefined) {
      board[move.cr][move.cc] = EMPTY;
    }
    if (piece === RED && move.tr === 0) board[move.tr][move.tc] = RED_KING;
    if (piece === BLACK && move.tr === 7) board[move.tr][move.tc] = BLACK_KING;
  }

  function getJumpsFrom(r, c) {
    return getMovesForPiece(r, c).jumps;
  }

  function handleCellClick(r, c) {
    if (!playerTurn) return;
    var piece = board[r][c];

    if (selectedPiece) {
      var move = null;
      for (var i = 0; i < validMoves.length; i++) {
        if (validMoves[i].tr === r && validMoves[i].tc === c) {
          move = validMoves[i];
          break;
        }
      }
      if (move) {
        makeMove(move);
        if (move.cr !== undefined) {
          var moreJumps = getJumpsFrom(move.tr, move.tc);
          if (moreJumps.length > 0) {
            selectedPiece = { r: move.tr, c: move.tc };
            validMoves = moreJumps;
            render();
            return;
          }
        }
        selectedPiece = null;
        validMoves = [];
        render();
        var result = checkGameOver();
        if (result) { endGame(result); return; }
        playerTurn = false;
        statusEl.textContent = 'AI thinking...';
        setTimeout(function() { aiTurn(); }, 400);
        return;
      }
    }

    if (isPlayer(piece)) {
      var allMoves = getAllMoves(true);
      var hasJumps = allMoves.length > 0 && allMoves[0].cr !== undefined;
      var pieceMoves = [];
      for (var i = 0; i < allMoves.length; i++) {
        if (allMoves[i].fr === r && allMoves[i].fc === c) {
          pieceMoves.push(allMoves[i]);
        }
      }
      if (hasJumps) {
        var pieceJumps = pieceMoves.filter(function(m) { return m.cr !== undefined; });
        if (pieceJumps.length > 0) {
          selectedPiece = { r: r, c: c };
          validMoves = pieceJumps;
        } else {
          selectedPiece = null;
          validMoves = [];
        }
      } else if (pieceMoves.length > 0) {
        selectedPiece = { r: r, c: c };
        validMoves = pieceMoves;
      } else {
        selectedPiece = null;
        validMoves = [];
      }
      render();
    }
  }

  function aiTurn() {
    var moves = getAllMoves(false);
    if (moves.length === 0) {
      endGame('player');
      return;
    }
    var jumps = moves.filter(function(m) { return m.cr !== undefined; });
    var chosen;
    if (jumps.length > 0) {
      chosen = jumps[Math.floor(Math.random() * jumps.length)];
    } else {
      chosen = moves[Math.floor(Math.random() * moves.length)];
    }
    makeMove(chosen);
    if (chosen.cr !== undefined) {
      var moreJumps = getJumpsFrom(chosen.tr, chosen.tc);
      while (moreJumps.length > 0) {
        var next = moreJumps[Math.floor(Math.random() * moreJumps.length)];
        makeMove(next);
        moreJumps = getJumpsFrom(next.tr, next.tc);
      }
    }
    playerTurn = true;
    render();
    var result = checkGameOver();
    if (result) { endGame(result); return; }
    statusEl.textContent = 'Your turn (Red)';
    var playerMoves = getAllMoves(true);
    if (playerMoves.length === 0) {
      endGame('ai');
    }
  }

  function checkGameOver() {
    var hasRed = false, hasBlack = false;
    for (var r = 0; r < 8; r++) {
      for (var c = 0; c < 8; c++) {
        if (isRed(board[r][c])) hasRed = true;
        if (isBlack(board[r][c])) hasBlack = true;
      }
    }
    if (!hasRed) return 'ai';
    if (!hasBlack) return 'player';
    return null;
  }

  function endGame(winner) {
    playerTurn = false;
    gamesPlayed++;
    if (winner === 'player') {
      redScore++;
      statusEl.textContent = 'You win!';
    } else if (winner === 'ai') {
      blackScore++;
      statusEl.textContent = 'AI wins!';
    } else {
      statusEl.textContent = 'Draw!';
    }
    updateScore();
  }

  function updateScore() {
    scoreEl.textContent = 'You: ' + redScore + ' | AI: ' + blackScore + ' | Games: ' + gamesPlayed;
  }

  function render() {
    boardEl.innerHTML = '';
    var validTargets = {};
    for (var v = 0; v < validMoves.length; v++) {
      validTargets[validMoves[v].tr + ',' + validMoves[v].tc] = true;
    }
    for (var r = 0; r < 8; r++) {
      for (var c = 0; c < 8; c++) {
        var cell = document.createElement('div');
        cell.className = 'ck-cell';
        cell.setAttribute('data-testid', 'ck-cell-' + r + '-' + c);
        if ((r + c) % 2 === 1) {
          cell.classList.add('ck-cell-dark');
        } else {
          cell.classList.add('ck-cell-light');
        }
        if (selectedPiece && selectedPiece.r === r && selectedPiece.c === c) {
          cell.classList.add('ck-cell-selected');
        }
        if (validTargets[r + ',' + c]) {
          cell.classList.add('ck-cell-valid');
        }
        var piece = board[r][c];
        if (piece !== EMPTY) {
          var pieceEl = document.createElement('div');
          pieceEl.className = 'ck-piece';
          if (isRed(piece)) pieceEl.classList.add('ck-piece-red');
          else pieceEl.classList.add('ck-piece-black');
          if (isKing(piece)) {
            pieceEl.classList.add('ck-piece-king');
            var crownEl = document.createElement('span');
            crownEl.className = 'ck-crown';
            crownEl.textContent = String.fromCodePoint(0x265A);
            pieceEl.appendChild(crownEl);
          }
          cell.appendChild(pieceEl);
        }
        (function(row, col) {
          cell.addEventListener('click', function() { handleCellClick(row, col); });
        })(r, c);
        boardEl.appendChild(cell);
      }
    }
  }

  function newGame() {
    initBoard();
    selectedPiece = null;
    validMoves = [];
    playerTurn = true;
    statusEl.textContent = 'Your turn (Red)';
    updateScore();
    render();
  }

  newGame();
}
"""


def get_css():
    return """
.ck-score { font-size: 12px; font-weight: 600; color: var(--text-secondary); text-align: center; margin-bottom: 8px; }
.ck-board { display: grid; grid-template-columns: repeat(8, 36px); grid-template-rows: repeat(8, 36px); gap: 0; border: 2px solid #555; margin: 0 auto; width: fit-content; }
.ck-cell { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; cursor: pointer; position: relative; }
.ck-cell-light { background: #f0d9b5; }
.ck-cell-dark { background: #b58863; }
.ck-cell-selected { background: #f6e58d !important; }
.ck-cell-valid { position: relative; }
.ck-cell-valid::after { content: ''; position: absolute; width: 14px; height: 14px; border-radius: 50%; background: rgba(46, 204, 113, 0.6); z-index: 1; }
.ck-piece { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; z-index: 2; border: 2px solid rgba(0,0,0,0.3); box-shadow: 0 2px 4px rgba(0,0,0,0.3); }
.ck-piece-red { background: #e74c3c; }
.ck-piece-black { background: #2c3e50; }
.ck-piece-king { border-color: #f1c40f; }
.ck-crown { font-size: 14px; color: #f1c40f; line-height: 1; }
.ck-controls { display: flex; gap: 8px; margin-top: 10px; justify-content: center; }
"""
