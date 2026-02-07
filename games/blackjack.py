def get_js():
    return r"""
function initBlackjack(area) {
  var suits = ['S','H','D','C'];
  var ranks = ['A','2','3','4','5','6','7','8','9','10','J','Q','K'];
  var suitSymbols = { S: String.fromCodePoint(0x2660), H: String.fromCodePoint(0x2665), D: String.fromCodePoint(0x2666), C: String.fromCodePoint(0x2663) };
  var suitColors = { S: '#ccc', H: '#e74c3c', D: '#e74c3c', C: '#ccc' };

  var deck, playerHand, dealerHand, gameState;

  var status = document.createElement('div');
  status.className = 'game-status';
  status.setAttribute('data-testid', 'text-bj-status');
  area.appendChild(status);

  var tableEl = document.createElement('div');
  tableEl.className = 'bj-table';

  var dealerSection = document.createElement('div');
  dealerSection.className = 'bj-section';
  var dealerLabel = document.createElement('div');
  dealerLabel.className = 'bj-label';
  dealerLabel.textContent = 'Dealer';
  dealerSection.appendChild(dealerLabel);
  var dealerCards = document.createElement('div');
  dealerCards.className = 'bj-cards';
  dealerCards.setAttribute('data-testid', 'bj-dealer-cards');
  dealerSection.appendChild(dealerCards);
  var dealerScore = document.createElement('div');
  dealerScore.className = 'bj-score';
  dealerScore.setAttribute('data-testid', 'text-bj-dealer-score');
  dealerSection.appendChild(dealerScore);
  tableEl.appendChild(dealerSection);

  var divider = document.createElement('div');
  divider.className = 'bj-divider';
  tableEl.appendChild(divider);

  var playerSection = document.createElement('div');
  playerSection.className = 'bj-section';
  var playerLabel = document.createElement('div');
  playerLabel.className = 'bj-label';
  playerLabel.textContent = 'You';
  playerSection.appendChild(playerLabel);
  var playerCards = document.createElement('div');
  playerCards.className = 'bj-cards';
  playerCards.setAttribute('data-testid', 'bj-player-cards');
  playerSection.appendChild(playerCards);
  var playerScore = document.createElement('div');
  playerScore.className = 'bj-score';
  playerScore.setAttribute('data-testid', 'text-bj-player-score');
  playerSection.appendChild(playerScore);
  tableEl.appendChild(playerSection);

  area.appendChild(tableEl);

  var controls = document.createElement('div');
  controls.className = 'bj-controls';
  var hitBtn = document.createElement('button');
  hitBtn.className = 'game-reset-btn';
  hitBtn.textContent = 'Hit';
  hitBtn.setAttribute('data-testid', 'button-bj-hit');
  var standBtn = document.createElement('button');
  standBtn.className = 'game-reset-btn';
  standBtn.textContent = 'Stand';
  standBtn.setAttribute('data-testid', 'button-bj-stand');
  var newGameBtn = document.createElement('button');
  newGameBtn.className = 'game-reset-btn';
  newGameBtn.textContent = 'New Game';
  newGameBtn.setAttribute('data-testid', 'button-bj-new');
  controls.appendChild(hitBtn);
  controls.appendChild(standBtn);
  controls.appendChild(newGameBtn);
  area.appendChild(controls);

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

  function cardValue(hand) {
    var total = 0, aces = 0;
    for (var i = 0; i < hand.length; i++) {
      var r = hand[i].rank;
      if (r === 'A') { total += 11; aces++; }
      else if (r === 'J' || r === 'Q' || r === 'K') total += 10;
      else total += parseInt(r);
    }
    while (total > 21 && aces > 0) { total -= 10; aces--; }
    return total;
  }

  function renderCard(card, hidden) {
    var el = document.createElement('div');
    el.className = 'bj-card';
    if (hidden) {
      el.classList.add('bj-card-hidden');
      el.textContent = '?';
    } else {
      el.style.color = suitColors[card.suit];
      el.innerHTML = '<span class="bj-card-rank">' + card.rank + '</span><span class="bj-card-suit">' + suitSymbols[card.suit] + '</span>';
    }
    return el;
  }

  function renderHands(revealDealer) {
    dealerCards.innerHTML = '';
    playerCards.innerHTML = '';
    for (var i = 0; i < dealerHand.length; i++) {
      dealerCards.appendChild(renderCard(dealerHand[i], i === 1 && !revealDealer));
    }
    for (var i = 0; i < playerHand.length; i++) {
      playerCards.appendChild(renderCard(playerHand[i], false));
    }
    playerScore.textContent = cardValue(playerHand);
    if (revealDealer) {
      dealerScore.textContent = cardValue(dealerHand);
    } else {
      var firstVal = dealerHand[0].rank === 'A' ? 11 : (['J','Q','K'].indexOf(dealerHand[0].rank) >= 0 ? 10 : parseInt(dealerHand[0].rank));
      dealerScore.textContent = firstVal + ' + ?';
    }
  }

  function newGame() {
    deck = makeDeck();
    playerHand = [deck.pop(), deck.pop()];
    dealerHand = [deck.pop(), deck.pop()];
    gameState = 'playing';
    hitBtn.disabled = false;
    standBtn.disabled = false;
    status.textContent = 'Hit or Stand?';
    renderHands(false);
    if (cardValue(playerHand) === 21) {
      gameState = 'done';
      hitBtn.disabled = true;
      standBtn.disabled = true;
      renderHands(true);
      if (cardValue(dealerHand) === 21) {
        status.textContent = 'Push! Both have Blackjack.';
      } else {
        status.textContent = 'Blackjack! You win!';
      }
    }
  }

  hitBtn.addEventListener('click', function() {
    if (gameState !== 'playing') return;
    playerHand.push(deck.pop());
    var pv = cardValue(playerHand);
    renderHands(false);
    if (pv > 21) {
      gameState = 'done';
      hitBtn.disabled = true;
      standBtn.disabled = true;
      renderHands(true);
      status.textContent = 'Bust! You lose.';
    } else if (pv === 21) {
      dealerPlay();
    }
  });

  standBtn.addEventListener('click', function() {
    if (gameState !== 'playing') return;
    dealerPlay();
  });

  function dealerPlay() {
    gameState = 'done';
    hitBtn.disabled = true;
    standBtn.disabled = true;
    while (cardValue(dealerHand) < 17) {
      dealerHand.push(deck.pop());
    }
    renderHands(true);
    var pv = cardValue(playerHand);
    var dv = cardValue(dealerHand);
    if (dv > 21) status.textContent = 'Dealer busts! You win!';
    else if (dv > pv) status.textContent = 'Dealer wins. (' + dv + ' vs ' + pv + ')';
    else if (pv > dv) status.textContent = 'You win! (' + pv + ' vs ' + dv + ')';
    else status.textContent = 'Push! (' + pv + ' vs ' + dv + ')';
  }

  newGameBtn.addEventListener('click', newGame);
  newGame();
}
"""


def get_css():
    return """
.bj-table { display: flex; flex-direction: column; align-items: center; gap: 8px; margin: 12px 0; }
.bj-section { display: flex; flex-direction: column; align-items: center; gap: 6px; }
.bj-label { font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
.bj-cards { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
.bj-card {
  width: 60px; height: 84px; border-radius: 6px; background: #f0f0f0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  font-size: 18px; font-weight: 700; border: 2px solid #ddd; position: relative;
}
.bj-card-hidden { background: var(--accent); color: #fff; border-color: var(--accent-hover); font-size: 24px; }
.bj-card-rank { font-size: 16px; font-weight: 700; }
.bj-card-suit { font-size: 20px; }
.bj-score { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.bj-divider { width: 80%; height: 1px; background: var(--border); margin: 4px 0; }
.bj-controls { display: flex; gap: 8px; margin-top: 8px; }
"""
