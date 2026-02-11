def get_js():
    return r"""
function initCrazyEights(container) {
  var suits = ['S','H','D','C'];
  var ranks = ['A','2','3','4','5','6','7','8','9','10','J','Q','K'];
  var suitSymbols = { S: String.fromCodePoint(0x2660), H: String.fromCodePoint(0x2665), D: String.fromCodePoint(0x2666), C: String.fromCodePoint(0x2663) };
  var suitColors = { S: '#333', H: '#e74c3c', D: '#e74c3c', C: '#333' };
  var suitNames = { S: 'Spades', H: 'Hearts', D: 'Diamonds', C: 'Clubs' };

  var deck, playerHand, computerHand, discardPile, currentSuit, currentRank;
  var playerTurn, drawCount, gameOver;
  var playerWins = 0, computerWins = 0;

  var status = document.createElement('div');
  status.className = 'game-status';
  status.setAttribute('data-testid', 'text-ce-status');
  container.appendChild(status);

  var scoreBoard = document.createElement('div');
  scoreBoard.setAttribute('data-testid', 'text-ce-score');
  scoreBoard.style.cssText = 'text-align:center;font-size:13px;font-weight:600;color:var(--text-secondary);margin-bottom:8px;';
  container.appendChild(scoreBoard);

  var tableEl = document.createElement('div');
  tableEl.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:10px;margin:8px 0;';

  var computerSection = document.createElement('div');
  computerSection.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:4px;';
  var computerLabel = document.createElement('div');
  computerLabel.style.cssText = 'font-size:12px;font-weight:600;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;';
  computerLabel.textContent = 'Computer';
  computerSection.appendChild(computerLabel);
  var computerCardsEl = document.createElement('div');
  computerCardsEl.setAttribute('data-testid', 'ce-computer-cards');
  computerCardsEl.style.cssText = 'display:flex;gap:4px;flex-wrap:wrap;justify-content:center;';
  computerSection.appendChild(computerCardsEl);
  var computerCountEl = document.createElement('div');
  computerCountEl.setAttribute('data-testid', 'text-ce-computer-count');
  computerCountEl.style.cssText = 'font-size:12px;color:var(--text-secondary);';
  computerSection.appendChild(computerCountEl);
  tableEl.appendChild(computerSection);

  var middleSection = document.createElement('div');
  middleSection.style.cssText = 'display:flex;align-items:center;gap:20px;margin:8px 0;';

  var drawPileEl = document.createElement('div');
  drawPileEl.setAttribute('data-testid', 'button-ce-draw');
  drawPileEl.style.cssText = 'width:60px;height:84px;border-radius:6px;background:var(--accent);display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;border:2px solid var(--accent-hover);cursor:pointer;user-select:none;';
  drawPileEl.textContent = 'Draw';
  var drawCountEl = document.createElement('div');
  drawCountEl.setAttribute('data-testid', 'text-ce-draw-count');
  drawCountEl.style.cssText = 'font-size:10px;margin-top:2px;';
  drawPileEl.appendChild(drawCountEl);
  middleSection.appendChild(drawPileEl);

  var discardEl = document.createElement('div');
  discardEl.setAttribute('data-testid', 'ce-discard-pile');
  discardEl.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:4px;';
  var discardCardEl = document.createElement('div');
  discardCardEl.style.cssText = 'width:60px;height:84px;border-radius:6px;background:#f0f0f0;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:18px;font-weight:700;border:2px solid #ddd;';
  discardEl.appendChild(discardCardEl);
  var currentSuitEl = document.createElement('div');
  currentSuitEl.setAttribute('data-testid', 'text-ce-current-suit');
  currentSuitEl.style.cssText = 'font-size:11px;font-weight:600;color:var(--text-secondary);';
  discardEl.appendChild(currentSuitEl);
  middleSection.appendChild(discardEl);

  tableEl.appendChild(middleSection);

  var divider = document.createElement('div');
  divider.style.cssText = 'width:80%;height:1px;background:var(--border);margin:4px 0;';
  tableEl.appendChild(divider);

  var playerSection = document.createElement('div');
  playerSection.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:4px;';
  var playerLabel = document.createElement('div');
  playerLabel.style.cssText = 'font-size:12px;font-weight:600;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;';
  playerLabel.textContent = 'Your Hand';
  playerSection.appendChild(playerLabel);
  var playerCardsEl = document.createElement('div');
  playerCardsEl.setAttribute('data-testid', 'ce-player-cards');
  playerCardsEl.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap;justify-content:center;';
  playerSection.appendChild(playerCardsEl);
  tableEl.appendChild(playerSection);

  container.appendChild(tableEl);

  var suitOverlay = document.createElement('div');
  suitOverlay.setAttribute('data-testid', 'ce-suit-selector');
  suitOverlay.style.cssText = 'display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:9999;align-items:center;justify-content:center;';
  var suitBox = document.createElement('div');
  suitBox.style.cssText = 'background:#fff;border-radius:10px;padding:20px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.3);';
  var suitTitle = document.createElement('div');
  suitTitle.style.cssText = 'font-size:16px;font-weight:700;margin-bottom:12px;color:#333;';
  suitTitle.textContent = 'Choose a suit';
  suitBox.appendChild(suitTitle);
  var suitBtns = document.createElement('div');
  suitBtns.style.cssText = 'display:flex;gap:10px;justify-content:center;';
  suits.forEach(function(s) {
    var btn = document.createElement('button');
    btn.setAttribute('data-testid', 'button-ce-suit-' + s);
    btn.style.cssText = 'width:50px;height:60px;border-radius:8px;border:2px solid #ddd;background:#f9f9f9;cursor:pointer;font-size:28px;display:flex;align-items:center;justify-content:center;color:' + suitColors[s] + ';';
    btn.textContent = suitSymbols[s];
    btn.addEventListener('click', function() {
      suitOverlay.style.display = 'none';
      chooseSuit(s);
    });
    suitBtns.appendChild(btn);
  });
  suitBox.appendChild(suitBtns);
  suitOverlay.appendChild(suitBox);
  container.appendChild(suitOverlay);

  var controls = document.createElement('div');
  controls.style.cssText = 'display:flex;gap:8px;margin-top:8px;justify-content:center;';
  var passBtn = document.createElement('button');
  passBtn.className = 'game-reset-btn';
  passBtn.textContent = 'Pass';
  passBtn.setAttribute('data-testid', 'button-ce-pass');
  var newGameBtn = document.createElement('button');
  newGameBtn.className = 'game-reset-btn';
  newGameBtn.textContent = 'New Round';
  newGameBtn.setAttribute('data-testid', 'button-ce-new');
  controls.appendChild(passBtn);
  controls.appendChild(newGameBtn);
  container.appendChild(controls);

  var pendingEightCard = null;

  function makeDeck() {
    var d = [];
    for (var s = 0; s < suits.length; s++) {
      for (var r = 0; r < ranks.length; r++) {
        d.push({ suit: suits[s], rank: ranks[r] });
      }
    }
    for (var i = d.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = d[i]; d[i] = d[j]; d[j] = tmp;
    }
    return d;
  }

  function renderCard(card, faceDown) {
    var el = document.createElement('div');
    el.style.cssText = 'width:60px;height:84px;border-radius:6px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:18px;font-weight:700;border:2px solid #ddd;user-select:none;flex-shrink:0;';
    if (faceDown) {
      el.style.background = 'var(--accent)';
      el.style.color = '#fff';
      el.style.borderColor = 'var(--accent-hover)';
      el.style.fontSize = '24px';
      el.textContent = '?';
    } else {
      el.style.background = '#f0f0f0';
      el.style.color = suitColors[card.suit];
      var rankSpan = document.createElement('span');
      rankSpan.style.cssText = 'font-size:16px;font-weight:700;';
      rankSpan.textContent = card.rank;
      var suitSpan = document.createElement('span');
      suitSpan.style.cssText = 'font-size:20px;';
      suitSpan.textContent = suitSymbols[card.suit];
      el.appendChild(rankSpan);
      el.appendChild(suitSpan);
    }
    return el;
  }

  function canPlay(card) {
    if (card.rank === '8') return true;
    if (card.suit === currentSuit) return true;
    if (card.rank === currentRank) return true;
    return false;
  }

  function hasPlayableCard(hand) {
    for (var i = 0; i < hand.length; i++) {
      if (canPlay(hand[i])) return true;
    }
    return false;
  }

  function render() {
    computerCardsEl.innerHTML = '';
    for (var i = 0; i < computerHand.length; i++) {
      computerCardsEl.appendChild(renderCard(computerHand[i], true));
    }
    computerCountEl.textContent = computerHand.length + ' card' + (computerHand.length !== 1 ? 's' : '');

    discardCardEl.innerHTML = '';
    var topCard = discardPile[discardPile.length - 1];
    discardCardEl.style.color = suitColors[topCard.suit];
    var rSpan = document.createElement('span');
    rSpan.style.cssText = 'font-size:16px;font-weight:700;';
    rSpan.textContent = topCard.rank;
    var sSpan = document.createElement('span');
    sSpan.style.cssText = 'font-size:20px;';
    sSpan.textContent = suitSymbols[topCard.suit];
    discardCardEl.appendChild(rSpan);
    discardCardEl.appendChild(sSpan);

    currentSuitEl.textContent = 'Suit: ' + suitNames[currentSuit];
    currentSuitEl.style.color = suitColors[currentSuit];

    drawCountEl.textContent = deck.length;

    playerCardsEl.innerHTML = '';
    for (var i = 0; i < playerHand.length; i++) {
      (function(idx) {
        var card = playerHand[idx];
        var el = renderCard(card, false);
        el.setAttribute('data-testid', 'button-ce-card-' + idx);
        if (playerTurn && !gameOver && canPlay(card)) {
          el.style.cursor = 'pointer';
          el.style.boxShadow = '0 0 6px rgba(46,204,113,0.5)';
          el.addEventListener('mouseenter', function() { el.style.transform = 'translateY(-6px)'; });
          el.addEventListener('mouseleave', function() { el.style.transform = 'translateY(0)'; });
          el.addEventListener('click', function() { playCard(idx); });
        } else if (playerTurn && !gameOver) {
          el.style.opacity = '0.5';
        }
        playerCardsEl.appendChild(el);
      })(i);
    }

    scoreBoard.textContent = 'You: ' + playerWins + ' | Computer: ' + computerWins;

    passBtn.disabled = !playerTurn || gameOver || drawCount < 3 || hasPlayableCard(playerHand);
    drawPileEl.style.opacity = (playerTurn && !gameOver && drawCount < 3 && !hasPlayableCard(playerHand) && deck.length > 0) ? '1' : '0.5';
    drawPileEl.style.cursor = (playerTurn && !gameOver && drawCount < 3 && !hasPlayableCard(playerHand) && deck.length > 0) ? 'pointer' : 'default';
  }

  function playCard(idx) {
    if (!playerTurn || gameOver) return;
    var card = playerHand[idx];
    if (!canPlay(card)) return;

    playerHand.splice(idx, 1);
    discardPile.push(card);
    currentRank = card.rank;

    if (card.rank === '8') {
      pendingEightCard = card;
      suitOverlay.style.display = 'flex';
      render();
      return;
    }

    currentSuit = card.suit;
    drawCount = 0;

    if (playerHand.length === 0) {
      gameOver = true;
      playerWins++;
      status.textContent = 'You win this round!';
      render();
      return;
    }

    playerTurn = false;
    status.textContent = 'Computer is thinking...';
    render();
    setTimeout(function() { computerPlay(); }, 800);
  }

  function chooseSuit(s) {
    currentSuit = s;
    drawCount = 0;
    pendingEightCard = null;

    if (playerHand.length === 0) {
      gameOver = true;
      playerWins++;
      status.textContent = 'You win this round!';
      render();
      return;
    }

    playerTurn = false;
    status.textContent = 'Computer is thinking...';
    render();
    setTimeout(function() { computerPlay(); }, 800);
  }

  function drawCard() {
    if (!playerTurn || gameOver || drawCount >= 3) return;
    if (hasPlayableCard(playerHand)) return;
    if (deck.length === 0) {
      reshuffleDeck();
      if (deck.length === 0) {
        drawCount = 3;
        status.textContent = 'No cards left to draw. Pass your turn.';
        render();
        return;
      }
    }
    playerHand.push(deck.pop());
    drawCount++;
    if (drawCount >= 3 && !hasPlayableCard(playerHand)) {
      status.textContent = 'No playable card. Pass your turn.';
    } else if (hasPlayableCard(playerHand)) {
      status.textContent = 'You drew a card. Play a card!';
    } else {
      status.textContent = 'Draw again (' + drawCount + '/3) or play a card.';
    }
    render();
  }

  function passTurn() {
    if (!playerTurn || gameOver) return;
    if (drawCount < 3 && deck.length > 0) return;
    if (hasPlayableCard(playerHand)) return;
    playerTurn = false;
    drawCount = 0;
    status.textContent = 'Computer is thinking...';
    render();
    setTimeout(function() { computerPlay(); }, 800);
  }

  function reshuffleDeck() {
    if (discardPile.length <= 1) return;
    var topCard = discardPile.pop();
    deck = discardPile.slice();
    discardPile = [topCard];
    for (var i = deck.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = deck[i]; deck[i] = deck[j]; deck[j] = tmp;
    }
  }

  function computerPlay() {
    if (gameOver) return;

    var playable = [];
    var eights = [];
    for (var i = 0; i < computerHand.length; i++) {
      if (canPlay(computerHand[i])) {
        if (computerHand[i].rank === '8') {
          eights.push(i);
        } else {
          playable.push(i);
        }
      }
    }

    if (playable.length > 0) {
      var idx = playable[0];
      var card = computerHand[idx];
      computerHand.splice(idx, 1);
      discardPile.push(card);
      currentSuit = card.suit;
      currentRank = card.rank;

      if (computerHand.length === 0) {
        gameOver = true;
        computerWins++;
        status.textContent = 'Computer wins this round!';
        render();
        return;
      }

      playerTurn = true;
      drawCount = 0;
      status.textContent = 'Your turn. Play a card!';
      render();
      return;
    }

    if (eights.length > 0) {
      var idx = eights[0];
      var card = computerHand[idx];
      computerHand.splice(idx, 1);
      discardPile.push(card);
      currentRank = '8';

      var suitCount = { S: 0, H: 0, D: 0, C: 0 };
      for (var i = 0; i < computerHand.length; i++) {
        suitCount[computerHand[i].suit]++;
      }
      var bestSuit = 'S', bestCount = -1;
      for (var s in suitCount) {
        if (suitCount[s] > bestCount) { bestCount = suitCount[s]; bestSuit = s; }
      }
      currentSuit = bestSuit;

      if (computerHand.length === 0) {
        gameOver = true;
        computerWins++;
        status.textContent = 'Computer wins this round!';
        render();
        return;
      }

      playerTurn = true;
      drawCount = 0;
      status.textContent = 'Computer played an 8, chose ' + suitNames[currentSuit] + '. Your turn!';
      render();
      return;
    }

    var compDraws = 0;
    while (compDraws < 3) {
      if (deck.length === 0) reshuffleDeck();
      if (deck.length === 0) break;
      computerHand.push(deck.pop());
      compDraws++;
      if (hasPlayableCard(computerHand)) break;
    }

    var afterPlayable = [];
    var afterEights = [];
    for (var i = 0; i < computerHand.length; i++) {
      if (canPlay(computerHand[i])) {
        if (computerHand[i].rank === '8') afterEights.push(i);
        else afterPlayable.push(i);
      }
    }

    if (afterPlayable.length > 0) {
      var idx = afterPlayable[0];
      var card = computerHand[idx];
      computerHand.splice(idx, 1);
      discardPile.push(card);
      currentSuit = card.suit;
      currentRank = card.rank;
      status.textContent = 'Computer drew ' + compDraws + ' and played. Your turn!';
    } else if (afterEights.length > 0) {
      var idx = afterEights[0];
      var card = computerHand[idx];
      computerHand.splice(idx, 1);
      discardPile.push(card);
      currentRank = '8';
      var suitCount = { S: 0, H: 0, D: 0, C: 0 };
      for (var i = 0; i < computerHand.length; i++) {
        suitCount[computerHand[i].suit]++;
      }
      var bestSuit = 'S', bestCount = -1;
      for (var s in suitCount) {
        if (suitCount[s] > bestCount) { bestCount = suitCount[s]; bestSuit = s; }
      }
      currentSuit = bestSuit;
      status.textContent = 'Computer drew ' + compDraws + ', played 8, chose ' + suitNames[currentSuit] + '. Your turn!';
    } else {
      status.textContent = 'Computer drew ' + compDraws + ' and passed. Your turn!';
    }

    if (computerHand.length === 0) {
      gameOver = true;
      computerWins++;
      status.textContent = 'Computer wins this round!';
      render();
      return;
    }

    playerTurn = true;
    drawCount = 0;
    render();
  }

  function newGame() {
    deck = makeDeck();
    playerHand = [];
    computerHand = [];
    discardPile = [];
    drawCount = 0;
    gameOver = false;
    playerTurn = true;
    pendingEightCard = null;

    for (var i = 0; i < 7; i++) {
      playerHand.push(deck.pop());
      computerHand.push(deck.pop());
    }

    var startCard = deck.pop();
    while (startCard.rank === '8') {
      deck.unshift(startCard);
      startCard = deck.pop();
    }
    discardPile.push(startCard);
    currentSuit = startCard.suit;
    currentRank = startCard.rank;

    status.textContent = 'Your turn. Play a card!';
    render();
  }

  drawPileEl.addEventListener('click', function() { drawCard(); });
  passBtn.addEventListener('click', function() { passTurn(); });
  newGameBtn.addEventListener('click', function() { newGame(); });

  newGame();
}
"""


def get_css():
    return ""
