def get_js():
    return r"""
function initWar(container) {
  var suits = ['S','H','D','C'];
  var ranks = ['2','3','4','5','6','7','8','9','10','J','Q','K','A'];
  var suitSymbols = { S: String.fromCodePoint(0x2660), H: String.fromCodePoint(0x2665), D: String.fromCodePoint(0x2666), C: String.fromCodePoint(0x2663) };
  var suitColors = { S: '#222', H: '#e74c3c', D: '#e74c3c', C: '#222' };
  var rankValues = {};
  for (var i = 0; i < ranks.length; i++) { rankValues[ranks[i]] = i + 2; }

  var playerDeck = [];
  var computerDeck = [];
  var playerWins = 0;
  var computerWins = 0;
  var isAnimating = false;

  var status = document.createElement('div');
  status.className = 'game-status';
  status.setAttribute('data-testid', 'text-war-status');
  container.appendChild(status);

  var scoreBoard = document.createElement('div');
  scoreBoard.className = 'war-scoreboard';
  var scoreText = document.createElement('div');
  scoreText.className = 'war-score-text';
  scoreText.setAttribute('data-testid', 'text-war-score');
  scoreBoard.appendChild(scoreText);
  container.appendChild(scoreBoard);

  var tableEl = document.createElement('div');
  tableEl.className = 'war-table';

  var computerSection = document.createElement('div');
  computerSection.className = 'war-section';
  var computerLabel = document.createElement('div');
  computerLabel.className = 'war-label';
  computerLabel.textContent = 'Computer';
  computerSection.appendChild(computerLabel);
  var computerCount = document.createElement('div');
  computerCount.className = 'war-count';
  computerCount.setAttribute('data-testid', 'text-war-computer-count');
  computerSection.appendChild(computerCount);
  var computerCardArea = document.createElement('div');
  computerCardArea.className = 'war-card-area';
  computerCardArea.setAttribute('data-testid', 'war-computer-cards');
  computerSection.appendChild(computerCardArea);
  tableEl.appendChild(computerSection);

  var vsLabel = document.createElement('div');
  vsLabel.className = 'war-vs';
  vsLabel.textContent = 'VS';
  tableEl.appendChild(vsLabel);

  var playerSection = document.createElement('div');
  playerSection.className = 'war-section';
  var playerLabel = document.createElement('div');
  playerLabel.className = 'war-label';
  playerLabel.textContent = 'You';
  playerSection.appendChild(playerLabel);
  var playerCount = document.createElement('div');
  playerCount.className = 'war-count';
  playerCount.setAttribute('data-testid', 'text-war-player-count');
  playerSection.appendChild(playerCount);
  var playerCardArea = document.createElement('div');
  playerCardArea.className = 'war-card-area';
  playerCardArea.setAttribute('data-testid', 'war-player-cards');
  playerSection.appendChild(playerCardArea);
  tableEl.appendChild(playerSection);

  container.appendChild(tableEl);

  var warPile = document.createElement('div');
  warPile.className = 'war-pile';
  warPile.setAttribute('data-testid', 'war-pile');
  container.appendChild(warPile);

  var controls = document.createElement('div');
  controls.className = 'war-controls';
  var drawBtn = document.createElement('button');
  drawBtn.className = 'game-reset-btn';
  drawBtn.textContent = 'Draw';
  drawBtn.setAttribute('data-testid', 'button-war-draw');
  var newGameBtn = document.createElement('button');
  newGameBtn.className = 'game-reset-btn';
  newGameBtn.textContent = 'New Game';
  newGameBtn.setAttribute('data-testid', 'button-war-new');
  controls.appendChild(drawBtn);
  controls.appendChild(newGameBtn);
  container.appendChild(controls);

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
    el.className = 'war-card';
    if (faceDown) {
      el.classList.add('war-card-hidden');
      el.textContent = '?';
    } else {
      el.style.color = suitColors[card.suit];
      var rankSpan = document.createElement('span');
      rankSpan.className = 'war-card-rank';
      rankSpan.textContent = card.rank;
      var suitSpan = document.createElement('span');
      suitSpan.className = 'war-card-suit';
      suitSpan.textContent = suitSymbols[card.suit];
      el.appendChild(rankSpan);
      el.appendChild(suitSpan);
    }
    return el;
  }

  function updateCounts() {
    playerCount.textContent = playerDeck.length + ' cards';
    computerCount.textContent = computerDeck.length + ' cards';
    scoreText.textContent = 'Wins - You: ' + playerWins + ' | Computer: ' + computerWins;
  }

  function clearCardAreas() {
    playerCardArea.innerHTML = '';
    computerCardArea.innerHTML = '';
    warPile.innerHTML = '';
  }

  function checkGameOver() {
    if (playerDeck.length === 0) {
      status.textContent = 'Computer wins the game!';
      computerWins++;
      drawBtn.disabled = true;
      updateCounts();
      return true;
    }
    if (computerDeck.length === 0) {
      status.textContent = 'You win the game!';
      playerWins++;
      drawBtn.disabled = true;
      updateCounts();
      return true;
    }
    return false;
  }

  function playRound() {
    if (isAnimating) return;
    if (playerDeck.length === 0 || computerDeck.length === 0) return;

    isAnimating = true;
    clearCardAreas();

    var pCard = playerDeck.shift();
    var cCard = computerDeck.shift();
    var pot = [pCard, cCard];

    playerCardArea.appendChild(renderCard(pCard, false));
    computerCardArea.appendChild(renderCard(cCard, false));

    var pVal = rankValues[pCard.rank];
    var cVal = rankValues[cCard.rank];

    if (pVal > cVal) {
      status.textContent = pCard.rank + suitSymbols[pCard.suit] + ' beats ' + cCard.rank + suitSymbols[cCard.suit] + ' - You win this round!';
      shuffleInto(playerDeck, pot);
      updateCounts();
      isAnimating = false;
    } else if (cVal > pVal) {
      status.textContent = cCard.rank + suitSymbols[cCard.suit] + ' beats ' + pCard.rank + suitSymbols[pCard.suit] + ' - Computer wins this round!';
      shuffleInto(computerDeck, pot);
      updateCounts();
      isAnimating = false;
    } else {
      status.textContent = 'Tie! ' + pCard.rank + ' vs ' + cCard.rank + ' - WAR!';
      resolveWar(pot, 1);
    }

    if (!isAnimating) checkGameOver();
  }

  function resolveWar(pot, warNum) {
    var warLabel = document.createElement('div');
    warLabel.className = 'war-label war-announce';
    warLabel.textContent = 'WAR' + (warNum > 1 ? ' x' + warNum : '') + '!';
    warPile.appendChild(warLabel);

    var faceDownCount = Math.min(3, playerDeck.length, computerDeck.length);

    if (faceDownCount === 0 || playerDeck.length < 1 || computerDeck.length < 1) {
      if (playerDeck.length === 0 && computerDeck.length === 0) {
        status.textContent = 'Both ran out during war - Draw!';
        isAnimating = false;
        return;
      } else if (playerDeck.length === 0) {
        shuffleInto(computerDeck, pot);
        updateCounts();
        isAnimating = false;
        checkGameOver();
        return;
      } else {
        shuffleInto(playerDeck, pot);
        updateCounts();
        isAnimating = false;
        checkGameOver();
        return;
      }
    }

    var pileRow = document.createElement('div');
    pileRow.className = 'war-pile-row';

    for (var i = 0; i < faceDownCount; i++) {
      var pc = playerDeck.shift();
      var cc = computerDeck.shift();
      pot.push(pc, cc);
      pileRow.appendChild(renderCard(pc, true));
      pileRow.appendChild(renderCard(cc, true));
    }
    warPile.appendChild(pileRow);

    if (playerDeck.length === 0 || computerDeck.length === 0) {
      if (playerDeck.length === 0 && computerDeck.length === 0) {
        status.textContent = 'Both ran out during war - Draw!';
        isAnimating = false;
        return;
      } else if (playerDeck.length === 0) {
        shuffleInto(computerDeck, pot);
        updateCounts();
        isAnimating = false;
        checkGameOver();
        return;
      } else {
        shuffleInto(playerDeck, pot);
        updateCounts();
        isAnimating = false;
        checkGameOver();
        return;
      }
    }

    setTimeout(function() {
      var pFlip = playerDeck.shift();
      var cFlip = computerDeck.shift();
      pot.push(pFlip, cFlip);

      var flipRow = document.createElement('div');
      flipRow.className = 'war-pile-row war-flip-row';
      var pEl = renderCard(pFlip, false);
      var cEl = renderCard(cFlip, false);
      pEl.classList.add('war-card-flip');
      cEl.classList.add('war-card-flip');

      var pWrap = document.createElement('div');
      pWrap.className = 'war-flip-label';
      var pLbl = document.createElement('div');
      pLbl.className = 'war-tiny-label';
      pLbl.textContent = 'You';
      pWrap.appendChild(pLbl);
      pWrap.appendChild(pEl);

      var cWrap = document.createElement('div');
      cWrap.className = 'war-flip-label';
      var cLbl = document.createElement('div');
      cLbl.className = 'war-tiny-label';
      cLbl.textContent = 'CPU';
      cWrap.appendChild(cLbl);
      cWrap.appendChild(cEl);

      flipRow.appendChild(pWrap);
      flipRow.appendChild(cWrap);
      warPile.appendChild(flipRow);

      var pv = rankValues[pFlip.rank];
      var cv = rankValues[cFlip.rank];

      if (pv > cv) {
        status.textContent = 'War won! ' + pFlip.rank + suitSymbols[pFlip.suit] + ' beats ' + cFlip.rank + suitSymbols[cFlip.suit] + ' - You take ' + pot.length + ' cards!';
        shuffleInto(playerDeck, pot);
        updateCounts();
        isAnimating = false;
        checkGameOver();
      } else if (cv > pv) {
        status.textContent = 'War lost! ' + cFlip.rank + suitSymbols[cFlip.suit] + ' beats ' + pFlip.rank + suitSymbols[pFlip.suit] + ' - Computer takes ' + pot.length + ' cards!';
        shuffleInto(computerDeck, pot);
        updateCounts();
        isAnimating = false;
        checkGameOver();
      } else {
        status.textContent = 'Another tie! ' + pFlip.rank + ' vs ' + cFlip.rank + ' - DOUBLE WAR!';
        setTimeout(function() {
          resolveWar(pot, warNum + 1);
        }, 600);
      }
    }, 800);
  }

  function shuffleInto(deck, cards) {
    for (var i = cards.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = cards[i]; cards[i] = cards[j]; cards[j] = tmp;
    }
    for (var i = 0; i < cards.length; i++) {
      deck.push(cards[i]);
    }
  }

  function newGame() {
    var full = makeDeck();
    playerDeck = full.slice(0, 26);
    computerDeck = full.slice(26);
    isAnimating = false;
    drawBtn.disabled = false;
    clearCardAreas();
    status.textContent = 'Click Draw to play a round!';
    updateCounts();
  }

  drawBtn.addEventListener('click', playRound);
  newGameBtn.addEventListener('click', newGame);
  newGame();
}
"""


def get_css():
    return """
.war-scoreboard { text-align: center; margin: 4px 0; }
.war-score-text { font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.war-table { display: flex; flex-direction: row; align-items: flex-start; justify-content: center; gap: 24px; margin: 12px 0; }
.war-section { display: flex; flex-direction: column; align-items: center; gap: 6px; min-width: 90px; }
.war-label { font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
.war-count { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.war-card-area { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; min-height: 88px; align-items: center; }
.war-vs { font-size: 16px; font-weight: 800; color: var(--text-secondary); align-self: center; margin-top: 40px; }
.war-card {
  width: 60px; height: 84px; border-radius: 6px; background: #f8f8f8;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  font-size: 18px; font-weight: 700; border: 2px solid #ddd; position: relative;
  transition: transform 0.3s ease;
}
.war-card-hidden { background: var(--accent); color: #fff; border-color: var(--accent-hover); font-size: 24px; }
.war-card-rank { font-size: 16px; font-weight: 700; }
.war-card-suit { font-size: 20px; }
.war-card-flip { animation: warFlipIn 0.4s ease-out; }
@keyframes warFlipIn {
  0% { transform: rotateY(90deg) scale(0.8); opacity: 0; }
  100% { transform: rotateY(0deg) scale(1); opacity: 1; }
}
.war-pile { display: flex; flex-direction: column; align-items: center; gap: 8px; margin: 8px 0; min-height: 20px; }
.war-pile-row { display: flex; gap: 4px; flex-wrap: wrap; justify-content: center; }
.war-flip-row { gap: 16px; }
.war-flip-label { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.war-tiny-label { font-size: 10px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; }
.war-announce { font-size: 16px; font-weight: 800; color: #e74c3c; animation: warPulse 0.5s ease-in-out; }
@keyframes warPulse {
  0% { transform: scale(0.5); opacity: 0; }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); opacity: 1; }
}
.war-controls { display: flex; gap: 8px; margin-top: 8px; }
"""
