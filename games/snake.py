def get_js():
    return r"""
function initSnake(area) {
  var gridSize = 20;
  var cellSize = 18;
  var canvasSize = gridSize * cellSize;

  var scoreEl = document.createElement('div');
  scoreEl.className = 'snake-score';
  scoreEl.setAttribute('data-testid', 'text-snake-score');
  scoreEl.textContent = 'Score: 0';
  area.appendChild(scoreEl);

  var canvas = document.createElement('canvas');
  canvas.className = 'snake-canvas';
  canvas.width = canvasSize;
  canvas.height = canvasSize;
  canvas.setAttribute('data-testid', 'canvas-snake');
  area.appendChild(canvas);

  var hint = document.createElement('div');
  hint.className = 'snake-hint';
  hint.textContent = 'Arrow keys or WASD to move.';
  area.appendChild(hint);

  var resetBtn = document.createElement('button');
  resetBtn.className = 'game-reset-btn';
  resetBtn.textContent = 'Restart';
  resetBtn.setAttribute('data-testid', 'button-reset-snake');
  area.appendChild(resetBtn);

  var ctx = canvas.getContext('2d');
  var snake, food, dir, score, running, interval;
  var rootStyle = getComputedStyle(document.documentElement);

  function reset() {
    snake = [{x:10,y:10},{x:9,y:10},{x:8,y:10}];
    dir = {x:1,y:0};
    score = 0;
    scoreEl.textContent = 'Score: 0';
    placeFood();
    running = true;
    if (interval) clearInterval(interval);
    interval = setInterval(tick, 120);
  }

  function placeFood() {
    do {
      food = {x: Math.floor(Math.random()*gridSize), y: Math.floor(Math.random()*gridSize)};
    } while (snake.some(function(s) { return s.x === food.x && s.y === food.y; }));
  }

  function tick() {
    if (!running) return;
    var head = {x: snake[0].x + dir.x, y: snake[0].y + dir.y};
    if (head.x < 0 || head.x >= gridSize || head.y < 0 || head.y >= gridSize) { endGame(); return; }
    for (var i = 0; i < snake.length; i++) {
      if (snake[i].x === head.x && snake[i].y === head.y) { endGame(); return; }
    }
    snake.unshift(head);
    if (head.x === food.x && head.y === food.y) {
      score++;
      scoreEl.textContent = 'Score: ' + score;
      placeFood();
    } else {
      snake.pop();
    }
    draw();
  }

  function endGame() {
    running = false;
    clearInterval(interval);
    scoreEl.textContent = 'Game Over! Score: ' + score;
  }

  function draw() {
    var bgColor = rootStyle.getPropertyValue('--bg-secondary').trim() || '#2b2d31';
    var accentColor = rootStyle.getPropertyValue('--accent').trim() || '#5865f2';
    var greenColor = rootStyle.getPropertyValue('--green').trim() || '#23a559';
    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, canvasSize, canvasSize);
    ctx.fillStyle = greenColor;
    ctx.fillRect(food.x*cellSize+1, food.y*cellSize+1, cellSize-2, cellSize-2);
    snake.forEach(function(s, i) {
      ctx.fillStyle = i === 0 ? accentColor : accentColor + 'cc';
      ctx.fillRect(s.x*cellSize+1, s.y*cellSize+1, cellSize-2, cellSize-2);
    });
  }

  function keyHandler(e) {
    var key = e.key.toLowerCase();
    if ((key === 'arrowup' || key === 'w') && dir.y !== 1) { dir = {x:0,y:-1}; e.preventDefault(); }
    else if ((key === 'arrowdown' || key === 's') && dir.y !== -1) { dir = {x:0,y:1}; e.preventDefault(); }
    else if ((key === 'arrowleft' || key === 'a') && dir.x !== 1) { dir = {x:-1,y:0}; e.preventDefault(); }
    else if ((key === 'arrowright' || key === 'd') && dir.x !== -1) { dir = {x:1,y:0}; e.preventDefault(); }
  }
  document.addEventListener('keydown', keyHandler);

  resetBtn.addEventListener('click', reset);

  window._gameCleanup = function() {
    running = false;
    if (interval) clearInterval(interval);
    document.removeEventListener('keydown', keyHandler);
  };

  reset();
}
"""


def get_css():
    return ""
