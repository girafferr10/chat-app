def get_js():
    return r"""
function initHangman(container) {
  var words = [
    'apple','banana','cherry','dragon','eagle','forest','garden','heaven','island','jungle',
    'kitten','lemon','monkey','nature','ocean','planet','queen','rabbit','silver','tiger',
    'umbrella','violin','window','yellow','zebra','anchor','bridge','castle','desert','engine',
    'falcon','guitar','harbor','insect','jacket','knight','ladder','marble','needle','orange',
    'pencil','quartz','rocket','shadow','temple','under','valley','winter','crystal','dolphin',
    'empire','flower','glacier','hammer','ivory','jester','kettle','lizard','mirror','nectar',
    'oyster','palace','riddle','salmon','throne','unity','vessel','walrus','mystic','zombie',
    'basket','candle','dinner','eclipse','fridge','gravel','helmet','invent','jumble','kernel',
    'lantern','magnet','nugget','option','pirate','quicksand','ransom','socket','tablet','update',
    'vacuum','waffle','export','yogurt','zipper','artist','butter','copper','donkey','elbow',
    'fabric','goblin','hockey','iguana','jigsaw','kimono','lumber','muffin','noodle','paddle',
    'quiver','rattle','saddle','tumble','utmost','velvet','wobble','expire','yonder','zenith'
  ];

  var categories = {
    'apple':'Fruit','banana':'Fruit','cherry':'Fruit','lemon':'Fruit','orange':'Fruit',
    'eagle':'Animal','kitten':'Animal','monkey':'Animal','tiger':'Animal','rabbit':'Animal',
    'falcon':'Animal','dolphin':'Animal','lizard':'Animal','walrus':'Animal','donkey':'Animal',
    'iguana':'Animal','salmon':'Animal','zebra':'Animal','oyster':'Animal','insect':'Animal',
    'forest':'Nature','ocean':'Nature','island':'Nature','desert':'Nature','glacier':'Nature',
    'garden':'Nature','nature':'Nature','flower':'Nature','jungle':'Nature','valley':'Nature',
    'guitar':'Object','mirror':'Object','pencil':'Object','candle':'Object','helmet':'Object',
    'basket':'Object','hammer':'Object','ladder':'Object','needle':'Object','lantern':'Object',
    'castle':'Place','palace':'Place','temple':'Place','harbor':'Place','bridge':'Place',
    'planet':'Science','crystal':'Science','marble':'Science','quartz':'Science','copper':'Science'
  };

  var currentWord = '';
  var guessedLetters = [];
  var wrongGuesses = 0;
  var maxWrong = 6;
  var wins = 0;
  var losses = 0;
  var streak = 0;
  var gameActive = false;

  var statusEl = document.createElement('div');
  statusEl.className = 'game-status';
  statusEl.setAttribute('data-testid', 'text-hm-status');
  container.appendChild(statusEl);

  var scoreEl = document.createElement('div');
  scoreEl.className = 'hm-score';
  scoreEl.setAttribute('data-testid', 'text-hm-score');
  container.appendChild(scoreEl);

  var hangmanCanvas = document.createElement('div');
  hangmanCanvas.className = 'hm-canvas';
  hangmanCanvas.setAttribute('data-testid', 'hm-canvas');
  container.appendChild(hangmanCanvas);

  var hintEl = document.createElement('div');
  hintEl.className = 'hm-hint';
  hintEl.setAttribute('data-testid', 'text-hm-hint');
  container.appendChild(hintEl);

  var wordDisplay = document.createElement('div');
  wordDisplay.className = 'hm-word';
  wordDisplay.setAttribute('data-testid', 'text-hm-word');
  container.appendChild(wordDisplay);

  var keyboardEl = document.createElement('div');
  keyboardEl.className = 'hm-keyboard';
  container.appendChild(keyboardEl);

  var letterBtns = {};
  var letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  for (var i = 0; i < letters.length; i++) {
    var btn = document.createElement('button');
    btn.className = 'hm-key';
    btn.textContent = letters[i];
    btn.setAttribute('data-testid', 'button-hm-key-' + letters[i]);
    (function(letter) {
      btn.addEventListener('click', function() { guessLetter(letter); });
    })(letters[i]);
    letterBtns[letters[i]] = btn;
    keyboardEl.appendChild(btn);
  }

  var controlsEl = document.createElement('div');
  controlsEl.className = 'hm-controls';
  var newWordBtn = document.createElement('button');
  newWordBtn.className = 'game-reset-btn';
  newWordBtn.textContent = 'New Word';
  newWordBtn.setAttribute('data-testid', 'button-hm-new');
  newWordBtn.addEventListener('click', function() { newGame(); });
  controlsEl.appendChild(newWordBtn);
  container.appendChild(controlsEl);

  function drawHangman() {
    hangmanCanvas.innerHTML = '';
    var parts = [
      '<div class="hm-head"></div>',
      '<div class="hm-body"></div>',
      '<div class="hm-arm-left"></div>',
      '<div class="hm-arm-right"></div>',
      '<div class="hm-leg-left"></div>',
      '<div class="hm-leg-right"></div>'
    ];
    var gallowsHtml = '<div class="hm-gallows">';
    gallowsHtml += '<div class="hm-gallow-base"></div>';
    gallowsHtml += '<div class="hm-gallow-pole"></div>';
    gallowsHtml += '<div class="hm-gallow-top"></div>';
    gallowsHtml += '<div class="hm-gallow-rope"></div>';
    for (var p = 0; p < wrongGuesses && p < parts.length; p++) {
      gallowsHtml += parts[p];
    }
    gallowsHtml += '</div>';
    hangmanCanvas.innerHTML = gallowsHtml;
  }

  function updateWordDisplay() {
    var display = '';
    for (var i = 0; i < currentWord.length; i++) {
      var letter = currentWord[i].toUpperCase();
      if (guessedLetters.indexOf(letter) >= 0) {
        display += '<span class="hm-letter-revealed">' + letter + '</span>';
      } else {
        display += '<span class="hm-letter-blank">_</span>';
      }
    }
    wordDisplay.innerHTML = display;
  }

  function checkWin() {
    for (var i = 0; i < currentWord.length; i++) {
      if (guessedLetters.indexOf(currentWord[i].toUpperCase()) < 0) return false;
    }
    return true;
  }

  function guessLetter(letter) {
    if (!gameActive) return;
    if (guessedLetters.indexOf(letter) >= 0) return;
    guessedLetters.push(letter);
    var btn = letterBtns[letter];
    btn.disabled = true;

    if (currentWord.toUpperCase().indexOf(letter) >= 0) {
      btn.classList.add('hm-key-correct');
      updateWordDisplay();
      if (checkWin()) {
        gameActive = false;
        wins++;
        streak++;
        statusEl.textContent = 'You win! The word was "' + currentWord + '"';
        updateScore();
      }
    } else {
      btn.classList.add('hm-key-wrong');
      wrongGuesses++;
      drawHangman();
      if (wrongGuesses >= maxWrong) {
        gameActive = false;
        losses++;
        streak = 0;
        statusEl.textContent = 'Game over! The word was "' + currentWord + '"';
        updateWordDisplay();
        var revealWord = '';
        for (var i = 0; i < currentWord.length; i++) {
          revealWord += '<span class="hm-letter-revealed">' + currentWord[i].toUpperCase() + '</span>';
        }
        wordDisplay.innerHTML = revealWord;
        updateScore();
      }
    }
  }

  function updateScore() {
    scoreEl.textContent = 'Wins: ' + wins + ' | Losses: ' + losses + ' | Streak: ' + streak;
  }

  function newGame() {
    currentWord = words[Math.floor(Math.random() * words.length)];
    guessedLetters = [];
    wrongGuesses = 0;
    gameActive = true;
    statusEl.textContent = 'Guess the word!';
    var cat = categories[currentWord];
    if (cat) {
      hintEl.textContent = 'Hint: ' + cat;
      hintEl.style.display = 'block';
    } else {
      hintEl.textContent = '';
      hintEl.style.display = 'none';
    }
    for (var key in letterBtns) {
      letterBtns[key].disabled = false;
      letterBtns[key].className = 'hm-key';
    }
    drawHangman();
    updateWordDisplay();
    updateScore();
  }

  newGame();
}
"""


def get_css():
    return """
.hm-score { font-size: 12px; font-weight: 600; color: var(--text-secondary); text-align: center; margin-bottom: 6px; }
.hm-canvas { display: flex; justify-content: center; margin: 8px 0; }
.hm-gallows { position: relative; width: 120px; height: 130px; }
.hm-gallow-base { position: absolute; bottom: 0; left: 10px; width: 100px; height: 4px; background: #555; border-radius: 2px; }
.hm-gallow-pole { position: absolute; bottom: 0; left: 30px; width: 4px; height: 120px; background: #555; }
.hm-gallow-top { position: absolute; top: 0; left: 30px; width: 50px; height: 4px; background: #555; }
.hm-gallow-rope { position: absolute; top: 4px; left: 76px; width: 3px; height: 18px; background: #888; }
.hm-head { position: absolute; top: 22px; left: 65px; width: 24px; height: 24px; border: 3px solid #e74c3c; border-radius: 50%; box-sizing: border-box; }
.hm-body { position: absolute; top: 46px; left: 75px; width: 3px; height: 30px; background: #e74c3c; }
.hm-arm-left { position: absolute; top: 52px; left: 56px; width: 20px; height: 3px; background: #e74c3c; transform: rotate(30deg); transform-origin: right; }
.hm-arm-right { position: absolute; top: 52px; left: 77px; width: 20px; height: 3px; background: #e74c3c; transform: rotate(-30deg); transform-origin: left; }
.hm-leg-left { position: absolute; top: 73px; left: 60px; width: 20px; height: 3px; background: #e74c3c; transform: rotate(40deg); transform-origin: right; }
.hm-leg-right { position: absolute; top: 73px; left: 77px; width: 20px; height: 3px; background: #e74c3c; transform: rotate(-40deg); transform-origin: left; }
.hm-hint { font-size: 12px; color: var(--text-secondary); text-align: center; margin-bottom: 4px; font-style: italic; }
.hm-word { display: flex; gap: 6px; justify-content: center; margin: 10px 0; flex-wrap: wrap; }
.hm-letter-blank { font-size: 22px; font-weight: 700; color: var(--text-primary); width: 24px; text-align: center; border-bottom: 2px solid var(--text-secondary); display: inline-block; }
.hm-letter-revealed { font-size: 22px; font-weight: 700; color: var(--text-primary); width: 24px; text-align: center; display: inline-block; }
.hm-keyboard { display: flex; flex-wrap: wrap; gap: 4px; justify-content: center; max-width: 320px; margin: 0 auto; }
.hm-key { width: 30px; height: 32px; border: 1px solid #bbb; border-radius: 4px; background: #f0f0f0; font-size: 13px; font-weight: 600; cursor: pointer; color: #333; display: flex; align-items: center; justify-content: center; }
.hm-key:hover:not(:disabled) { background: #e0e0e0; }
.hm-key:disabled { cursor: default; opacity: 0.7; }
.hm-key-correct { background: #27ae60 !important; color: #fff !important; border-color: #1e8449 !important; }
.hm-key-wrong { background: #e74c3c !important; color: #fff !important; border-color: #c0392b !important; }
.hm-controls { display: flex; gap: 8px; margin-top: 10px; justify-content: center; }
"""
