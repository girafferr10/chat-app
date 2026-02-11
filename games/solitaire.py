def get_js():
    return r"""
function initSolitaire(container) {
  var suits = ['S','H','D','C'];
  var ranks = ['A','2','3','4','5','6','7','8','9','10','J','Q','K'];
  var suitSymbols = { S: String.fromCodePoint(0x2660), H: String.fromCodePoint(0x2665), D: String.fromCodePoint(0x2666), C: String.fromCodePoint(0x2663) };
  var suitColors = { S: '#333', H: '#e74c3c', D: '#e74c3c', C: '#333' };
  var suitNames = { S: 'Spades', H: 'Hearts', D: 'Diamonds', C: 'Clubs' };

  var stock = [];
  var waste = [];
  var foundations = [[], [], [], []];
  var tableau = [[], [], [], [], [], [], []];
  var selected = null;
  var moves = 0;
  var timerSeconds = 0;
  var timerInterval = null;
  var gameWon = false;

  var statusBar = document.createElement('div');
  statusBar.className = 'sol-status';
  statusBar.setAttribute('data-testid', 'text-sol-status');
  container.appendChild(statusBar);

  var topRow = document.createElement('div');
  topRow.className = 'sol-top-row';
  container.appendChild(topRow);

  var stockEl = document.createElement('div');
  stockEl.className = 'sol-pile sol-stock';
  stockEl.setAttribute('data-testid', 'sol-stock');
  stockEl.addEventListener('click', function() { drawFromStock(); });
  topRow.appendChild(stockEl);

  var wasteEl = document.createElement('div');
  wasteEl.className = 'sol-pile sol-waste';
  wasteEl.setAttribute('data-testid', 'sol-waste');
  wasteEl.addEventListener('click', function() { handlePileClick('waste', 0); });
  topRow.appendChild(wasteEl);

  var spacer = document.createElement('div');
  spacer.className = 'sol-spacer';
  topRow.appendChild(spacer);

  var foundationEls = [];
  for (var f = 0; f < 4; f++) {
    var fEl = document.createElement('div');
    fEl.className = 'sol-pile sol-foundation';
    fEl.setAttribute('data-testid', 'sol-foundation-' + f);
    (function(fi) {
      fEl.addEventListener('click', function() { handlePileClick('foundation', fi); });
    })(f);
    foundationEls.push(fEl);
    topRow.appendChild(fEl);
  }

  var tableauRow = document.createElement('div');
  tableauRow.className = 'sol-tableau-row';
  container.appendChild(tableauRow);

  var tableauEls = [];
  for (var t = 0; t < 7; t++) {
    var tCol = document.createElement('div');
    tCol.className = 'sol-tableau-col';
    tCol.setAttribute('data-testid', 'sol-tableau-' + t);
    (function(ti) {
      tCol.addEventListener('click', function(e) {
        var cardEl = e.target.closest('.sol-card');
        if (cardEl) {
          var cardIdx = parseInt(cardEl.getAttribute('data-card-idx'));
          handleCardClick('tableau', ti, cardIdx);
        } else {
          handlePileClick('tableau', ti);
        }
      });
    })(t);
    tableauEls.push(tCol);
    tableauRow.appendChild(tCol);
  }

  var controls = document.createElement('div');
  controls.className = 'sol-controls';
  var newGameBtn = document.createElement('button');
  newGameBtn.className = 'game-reset-btn';
  newGameBtn.textContent = 'New Game';
  newGameBtn.setAttribute('data-testid', 'button-sol-new');
  newGameBtn.addEventListener('click', function() { newGame(); });
  controls.appendChild(newGameBtn);
  var autoBtn = document.createElement('button');
  autoBtn.className = 'game-reset-btn';
  autoBtn.textContent = 'Auto Complete';
  autoBtn.setAttribute('data-testid', 'button-sol-auto');
  autoBtn.addEventListener('click', function() { autoComplete(); });
  controls.appendChild(autoBtn);
  container.appendChild(controls);

  function makeDeck() {
    var d = [];
    for (var s = 0; s < suits.length; s++) {
      for (var r = 0; r < ranks.length; r++) {
        d.push({ suit: suits[s], rank: ranks[r], faceUp: false });
      }
    }
    for (var i = d.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = d[i]; d[i] = d[j]; d[j] = tmp;
    }
    return d;
  }

  function rankIndex(rank) {
    return ranks.indexOf(rank);
  }

  function isRed(suit) {
    return suit === 'H' || suit === 'D';
  }

  function canPlaceOnTableau(card, targetCol) {
    if (tableau[targetCol].length === 0) {
      return card.rank === 'K';
    }
    var top = tableau[targetCol][tableau[targetCol].length - 1];
    if (!top.faceUp) return false;
    return isRed(card.suit) !== isRed(top.suit) && rankIndex(card.rank) === rankIndex(top.rank) - 1;
  }

  function canPlaceOnFoundation(card, fi) {
    if (foundations[fi].length === 0) {
      return card.rank === 'A';
    }
    var top = foundations[fi][foundations[fi].length - 1];
    return card.suit === top.suit && rankIndex(card.rank) === rankIndex(top.rank) + 1;
  }

  function drawFromStock() {
    clearSelection();
    if (stock.length === 0) {
      while (waste.length > 0) {
        var c = waste.pop();
        c.faceUp = false;
        stock.push(c);
      }
    } else {
      var card = stock.pop();
      card.faceUp = true;
      waste.push(card);
    }
    render();
  }

  function clearSelection() {
    selected = null;
  }

  function handleCardClick(source, pileIdx, cardIdx) {
    if (gameWon) return;
    if (source === 'tableau') {
      var card = tableau[pileIdx][cardIdx];
      if (!card.faceUp) return;

      if (selected) {
        if (selected.source === 'tableau' && selected.pileIdx === pileIdx) {
          clearSelection();
          render();
          return;
        }
        tryMove(pileIdx);
        return;
      }

      selected = { source: 'tableau', pileIdx: pileIdx, cardIdx: cardIdx };
      render();
    }
  }

  function handlePileClick(source, pileIdx) {
    if (gameWon) return;
    if (source === 'waste') {
      if (selected && selected.source === 'waste') {
        clearSelection();
        render();
        return;
      }
      if (waste.length > 0) {
        selected = { source: 'waste', pileIdx: 0, cardIdx: waste.length - 1 };
        render();
      }
      return;
    }
    if (source === 'foundation') {
      if (selected) {
        tryMoveToFoundation(pileIdx);
        return;
      }
      if (foundations[pileIdx].length > 0) {
        selected = { source: 'foundation', pileIdx: pileIdx, cardIdx: foundations[pileIdx].length - 1 };
        render();
      }
      return;
    }
    if (source === 'tableau') {
      if (selected) {
        tryMove(pileIdx);
      }
    }
  }

  function tryMove(targetCol) {
    if (!selected) return;
    var cards = getSelectedCards();
    if (!cards || cards.length === 0) { clearSelection(); render(); return; }

    if (canPlaceOnTableau(cards[0], targetCol)) {
      removeSelectedCards();
      for (var i = 0; i < cards.length; i++) {
        tableau[targetCol].push(cards[i]);
      }
      flipTopCards();
      moves++;
      clearSelection();
      render();
      checkWin();
      return;
    }

    if (cards.length === 1) {
      for (var f = 0; f < 4; f++) {
        if (canPlaceOnFoundation(cards[0], f)) {
          removeSelectedCards();
          foundations[f].push(cards[0]);
          flipTopCards();
          moves++;
          clearSelection();
          render();
          checkWin();
          return;
        }
      }
    }
    clearSelection();
    render();
  }

  function tryMoveToFoundation(fi) {
    if (!selected) return;
    var cards = getSelectedCards();
    if (!cards || cards.length !== 1) { clearSelection(); render(); return; }
    if (canPlaceOnFoundation(cards[0], fi)) {
      removeSelectedCards();
      foundations[fi].push(cards[0]);
      flipTopCards();
      moves++;
      clearSelection();
      render();
      checkWin();
    } else {
      clearSelection();
      render();
    }
  }

  function getSelectedCards() {
    if (!selected) return null;
    if (selected.source === 'waste') {
      return [waste[waste.length - 1]];
    }
    if (selected.source === 'foundation') {
      return [foundations[selected.pileIdx][foundations[selected.pileIdx].length - 1]];
    }
    if (selected.source === 'tableau') {
      return tableau[selected.pileIdx].slice(selected.cardIdx);
    }
    return null;
  }

  function removeSelectedCards() {
    if (!selected) return;
    if (selected.source === 'waste') {
      waste.pop();
    } else if (selected.source === 'foundation') {
      foundations[selected.pileIdx].pop();
    } else if (selected.source === 'tableau') {
      tableau[selected.pileIdx].splice(selected.cardIdx);
    }
  }

  function flipTopCards() {
    for (var t = 0; t < 7; t++) {
      if (tableau[t].length > 0) {
        tableau[t][tableau[t].length - 1].faceUp = true;
      }
    }
  }

  function checkWin() {
    var total = 0;
    for (var f = 0; f < 4; f++) total += foundations[f].length;
    if (total === 52) {
      gameWon = true;
      clearInterval(timerInterval);
      render();
    }
  }

  function canAutoComplete() {
    if (stock.length > 0 || waste.length > 0) return false;
    for (var t = 0; t < 7; t++) {
      for (var c = 0; c < tableau[t].length; c++) {
        if (!tableau[t][c].faceUp) return false;
      }
    }
    return true;
  }

  function autoComplete() {
    if (!canAutoComplete()) return;
    var moved = true;
    while (moved) {
      moved = false;
      for (var t = 0; t < 7; t++) {
        if (tableau[t].length === 0) continue;
        var card = tableau[t][tableau[t].length - 1];
        for (var f = 0; f < 4; f++) {
          if (canPlaceOnFoundation(card, f)) {
            tableau[t].pop();
            foundations[f].push(card);
            moves++;
            moved = true;
            break;
          }
        }
      }
    }
    render();
    checkWin();
  }

  function renderCard(card, idx, isSelected) {
    var el = document.createElement('div');
    el.className = 'sol-card';
    el.setAttribute('data-card-idx', idx);
    if (!card.faceUp) {
      el.classList.add('sol-card-back');
      el.textContent = '';
    } else {
      el.style.color = suitColors[card.suit];
      var rankSpan = document.createElement('span');
      rankSpan.className = 'sol-card-rank';
      rankSpan.textContent = card.rank;
      var suitSpan = document.createElement('span');
      suitSpan.className = 'sol-card-suit';
      suitSpan.textContent = suitSymbols[card.suit];
      el.appendChild(rankSpan);
      el.appendChild(suitSpan);
      if (isSelected) {
        el.classList.add('sol-card-selected');
      }
    }
    return el;
  }

  function render() {
    var mins = Math.floor(timerSeconds / 60);
    var secs = timerSeconds % 60;
    var timeStr = mins + ':' + (secs < 10 ? '0' : '') + secs;
    if (gameWon) {
      statusBar.textContent = 'You Win! Moves: ' + moves + ' | Time: ' + timeStr;
    } else {
      statusBar.textContent = 'Moves: ' + moves + ' | Time: ' + timeStr;
    }

    stockEl.innerHTML = '';
    if (stock.length > 0) {
      var backEl = document.createElement('div');
      backEl.className = 'sol-card sol-card-back sol-card-stock';
      var countEl = document.createElement('span');
      countEl.className = 'sol-stock-count';
      countEl.textContent = stock.length;
      backEl.appendChild(countEl);
      stockEl.appendChild(backEl);
    } else {
      var emptyEl = document.createElement('div');
      emptyEl.className = 'sol-card sol-card-empty';
      emptyEl.textContent = String.fromCodePoint(0x21BB);
      stockEl.appendChild(emptyEl);
    }

    wasteEl.innerHTML = '';
    if (waste.length > 0) {
      var wCard = waste[waste.length - 1];
      var isSel = selected && selected.source === 'waste';
      wasteEl.appendChild(renderCard(wCard, waste.length - 1, isSel));
    }

    for (var f = 0; f < 4; f++) {
      foundationEls[f].innerHTML = '';
      if (foundations[f].length > 0) {
        var fCard = foundations[f][foundations[f].length - 1];
        var isSel = selected && selected.source === 'foundation' && selected.pileIdx === f;
        foundationEls[f].appendChild(renderCard(fCard, foundations[f].length - 1, isSel));
      } else {
        var emptyF = document.createElement('div');
        emptyF.className = 'sol-card sol-card-empty';
        emptyF.textContent = suitSymbols[suits[f]];
        emptyF.style.color = suitColors[suits[f]];
        emptyF.style.opacity = '0.3';
        foundationEls[f].appendChild(emptyF);
      }
    }

    for (var t = 0; t < 7; t++) {
      tableauEls[t].innerHTML = '';
      if (tableau[t].length === 0) {
        var emptyT = document.createElement('div');
        emptyT.className = 'sol-card sol-card-empty';
        tableauEls[t].appendChild(emptyT);
      } else {
        for (var c = 0; c < tableau[t].length; c++) {
          var isSel = selected && selected.source === 'tableau' && selected.pileIdx === t && c >= selected.cardIdx;
          var cardEl = renderCard(tableau[t][c], c, isSel);
          cardEl.style.marginTop = c > 0 ? (tableau[t][c - 1].faceUp ? '-60px' : '-72px') : '0';
          cardEl.style.position = 'relative';
          cardEl.style.zIndex = c;
          tableauEls[t].appendChild(cardEl);
        }
      }
    }

    if (canAutoComplete()) {
      autoBtn.style.display = 'inline-block';
    } else {
      autoBtn.style.display = 'none';
    }
  }

  function newGame() {
    gameWon = false;
    moves = 0;
    timerSeconds = 0;
    clearInterval(timerInterval);
    timerInterval = setInterval(function() {
      if (!gameWon) { timerSeconds++; render(); }
    }, 1000);

    var deck = makeDeck();
    stock = [];
    waste = [];
    foundations = [[], [], [], []];
    tableau = [[], [], [], [], [], [], []];
    selected = null;

    for (var t = 0; t < 7; t++) {
      for (var c = 0; c <= t; c++) {
        var card = deck.pop();
        card.faceUp = (c === t);
        tableau[t].push(card);
      }
    }
    stock = deck;
    render();
  }

  newGame();
}
"""


def get_css():
    return """
.sol-status { font-size: 13px; font-weight: 600; color: var(--text-primary); text-align: center; padding: 6px 0; }
.sol-top-row { display: flex; gap: 6px; justify-content: flex-start; align-items: flex-start; margin-bottom: 10px; flex-wrap: wrap; }
.sol-spacer { flex: 1; min-width: 10px; }
.sol-pile { min-width: 56px; min-height: 78px; }
.sol-tableau-row { display: flex; gap: 6px; justify-content: flex-start; flex-wrap: wrap; }
.sol-tableau-col { min-width: 56px; display: flex; flex-direction: column; align-items: center; }
.sol-card {
  width: 56px; height: 78px; border-radius: 5px; background: #f5f5f0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; border: 1.5px solid #ccc; cursor: pointer;
  user-select: none; box-sizing: border-box;
}
.sol-card-back { background: linear-gradient(135deg, #2980b9, #3498db); border-color: #2471a3; }
.sol-card-stock { position: relative; }
.sol-stock-count { font-size: 11px; color: #fff; font-weight: 700; }
.sol-card-empty { background: transparent; border: 1.5px dashed #999; color: #999; font-size: 20px; }
.sol-card-selected { outline: 2px solid #f39c12; outline-offset: -2px; background: #fef9e7; }
.sol-card-rank { font-size: 13px; font-weight: 700; line-height: 1; }
.sol-card-suit { font-size: 18px; line-height: 1; }
.sol-controls { display: flex; gap: 8px; margin-top: 10px; justify-content: center; }
"""
