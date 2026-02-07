def get_js():
    return r"""
function initMemory(area) {
  var symbols = ['A','B','C','D','E','F','G','H'];
  var cards = symbols.concat(symbols);
  var statsEl = document.createElement('div');
  statsEl.className = 'memory-stats';
  statsEl.setAttribute('data-testid', 'text-memory-stats');
  area.appendChild(statsEl);

  var boardEl = document.createElement('div');
  boardEl.className = 'memory-board';
  area.appendChild(boardEl);

  var resetBtn = document.createElement('button');
  resetBtn.className = 'game-reset-btn';
  resetBtn.textContent = 'New Game';
  resetBtn.setAttribute('data-testid', 'button-reset-memory');
  area.appendChild(resetBtn);

  var flipped = [];
  var matched = 0;
  var moves = 0;
  var lockBoard = false;
  var cardEls = [];
  var shuffled = [];

  function shuffle(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  }

  var symbolDisplay = {
    'A': String.fromCodePoint(0x2660), 'B': String.fromCodePoint(0x2665),
    'C': String.fromCodePoint(0x2666), 'D': String.fromCodePoint(0x2663),
    'E': String.fromCodePoint(0x2605), 'F': String.fromCodePoint(0x25CF),
    'G': String.fromCodePoint(0x25B2), 'H': String.fromCodePoint(0x25A0)
  };

  function reset() {
    shuffled = shuffle(cards);
    matched = 0;
    moves = 0;
    flipped = [];
    lockBoard = false;
    boardEl.innerHTML = '';
    cardEls = [];
    statsEl.textContent = 'Moves: 0 | Pairs: 0/8';
    shuffled.forEach(function(sym, idx) {
      var card = document.createElement('button');
      card.className = 'memory-card';
      card.setAttribute('data-testid', 'memory-card-' + idx);
      card.textContent = symbolDisplay[sym] || sym;
      card.addEventListener('click', function() {
        if (lockBoard || card.classList.contains('flipped') || card.classList.contains('matched')) return;
        card.classList.add('flipped');
        flipped.push({idx: idx, sym: sym, el: card});
        if (flipped.length === 2) {
          moves++;
          statsEl.textContent = 'Moves: ' + moves + ' | Pairs: ' + matched + '/8';
          if (flipped[0].sym === flipped[1].sym) {
            flipped[0].el.classList.add('matched');
            flipped[1].el.classList.add('matched');
            flipped[0].el.classList.remove('flipped');
            flipped[1].el.classList.remove('flipped');
            matched++;
            statsEl.textContent = 'Moves: ' + moves + ' | Pairs: ' + matched + '/8';
            flipped = [];
            if (matched === 8) {
              statsEl.textContent = 'You won in ' + moves + ' moves!';
            }
          } else {
            lockBoard = true;
            setTimeout(function() {
              flipped[0].el.classList.remove('flipped');
              flipped[1].el.classList.remove('flipped');
              flipped = [];
              lockBoard = false;
            }, 800);
          }
        }
      });
      cardEls.push(card);
      boardEl.appendChild(card);
    });
  }

  resetBtn.addEventListener('click', reset);
  reset();
}
"""


def get_css():
    return ""

