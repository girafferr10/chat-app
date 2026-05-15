def get_js():
    return r"""
function initGarlicPhone(container) {
  var roomId = null;
  var isHost = false;
  var gamePhase = 'lobby'; // lobby, waiting, text-input, drawing, reveal
  var currentRound = 0;
  var totalRounds = 0;
  var promptData = null;
  var promptWasType = null;
  var players = [];

  // Drawing state
  var drawing = false;
  var drawCtx = null;
  var drawCanvas = null;
  var currentColor = '#000000';
  var currentSize = 4;
  var lastX = 0, lastY = 0;

  function send(obj) {
    if (window.ws && window.ws.readyState === 1) {
      window.ws.send(JSON.stringify(obj));
    }
  }

  function setPhase(phase) {
    gamePhase = phase;
    render();
  }

  // ───── Message handler ─────
  function onMsg(d) {
    if (d.type === 'garlic_state') {
      roomId = d.room_id;
      isHost = d.is_host;
      players = d.players || [];
      if (d.status === 'lobby') setPhase('lobby');
      else if (d.status === 'playing') setPhase('waiting');
      else if (d.status === 'done') { /* handled by garlic_reveal */ }
    } else if (d.type === 'garlic_prompt') {
      roomId = d.room_id;
      currentRound = d.round;
      totalRounds = d.round_of;
      promptData = d.prompt;
      promptWasType = d.prompt_was_type || 'text';
      if (d.prompt_type === 'text') setPhase('text-input');
      else setPhase('drawing');
    } else if (d.type === 'garlic_submitted') {
      setPhase('waiting');
    } else if (d.type === 'garlic_reveal') {
      roomId = d.room_id;
      gamePhase = 'reveal';
      renderReveal(d.chains, d.players);
    } else if (d.type === 'garlic_error') {
      showError(d.text);
    }
  }

  window._garlicMessageHandler = onMsg;
  window._gameCleanup = function() {
    window._garlicMessageHandler = null;
  };

  // ───── Helpers ─────
  var errorEl = document.createElement('div');
  errorEl.style.cssText = 'color:var(--red);font-size:13px;margin:8px 0;min-height:20px;text-align:center;';
  function showError(msg) { errorEl.textContent = msg; setTimeout(function() { errorEl.textContent = ''; }, 4000); }

  function makeBtn(label, accent) {
    var b = document.createElement('button');
    b.className = 'game-reset-btn';
    b.textContent = label;
    if (!accent) b.style.cssText = 'background:var(--bg-tertiary);color:var(--text-secondary);margin-top:0;';
    return b;
  }

  function section(title) {
    var el = document.createElement('div');
    el.style.cssText = 'font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-muted);margin-bottom:6px;';
    el.textContent = title;
    return el;
  }

  // ───── Render dispatcher ─────
  function render() {
    container.innerHTML = '';
    container.appendChild(errorEl);
    if (gamePhase === 'lobby') renderLobby();
    else if (gamePhase === 'waiting') renderWaiting();
    else if (gamePhase === 'text-input') renderTextInput();
    else if (gamePhase === 'drawing') renderDrawing();
  }

  // ───── Lobby ─────
  function renderLobby() {
    if (roomId) {
      renderRoom();
      return;
    }
    var wrap = document.createElement('div');
    wrap.style.cssText = 'max-width:400px;margin:0 auto;display:flex;flex-direction:column;gap:16px;';

    var title = document.createElement('div');
    title.style.cssText = 'text-align:center;';
    title.innerHTML = '<div style="font-size:32px;">&#x1F9C4;</div><div style="font-size:22px;font-weight:800;color:var(--text-primary);margin:4px 0;">Garlic Phone</div><div style="font-size:13px;color:var(--text-muted);">Telephone game with drawing! 2-8 players.</div>';
    wrap.appendChild(title);

    // Create room
    var createBox = document.createElement('div');
    createBox.style.cssText = 'background:var(--bg-secondary);border-radius:8px;padding:16px;';
    createBox.appendChild(section('Create Room'));
    var createBtn = makeBtn('Create New Room', true);
    createBtn.style.cssText = 'width:100%;padding:10px;';
    createBtn.addEventListener('click', function() {
      send({ type: 'garlic_action', action: 'create' });
    });
    createBox.appendChild(createBtn);
    wrap.appendChild(createBox);

    // Join room
    var joinBox = document.createElement('div');
    joinBox.style.cssText = 'background:var(--bg-secondary);border-radius:8px;padding:16px;';
    joinBox.appendChild(section('Join Room'));
    var codeInput = document.createElement('input');
    codeInput.type = 'text';
    codeInput.placeholder = 'Enter room code (e.g. ABC12)';
    codeInput.maxLength = 5;
    codeInput.style.cssText = 'width:100%;padding:10px 12px;border:1px solid var(--border);border-radius:6px;background:var(--bg-tertiary);color:var(--text-primary);font-size:14px;outline:none;box-sizing:border-box;margin-bottom:8px;text-transform:uppercase;';
    codeInput.addEventListener('input', function() { codeInput.value = codeInput.value.toUpperCase(); });
    codeInput.addEventListener('keydown', function(e) { if (e.key === 'Enter') joinBtn.click(); });
    var joinBtn = makeBtn('Join Room', true);
    joinBtn.style.cssText = 'width:100%;padding:10px;';
    joinBtn.addEventListener('click', function() {
      var code = codeInput.value.trim().toUpperCase();
      if (code.length < 2) { showError('Enter a room code.'); return; }
      send({ type: 'garlic_action', action: 'join', room_id: code });
    });
    joinBox.appendChild(codeInput);
    joinBox.appendChild(joinBtn);
    wrap.appendChild(joinBox);

    container.appendChild(wrap);
  }

  function renderRoom() {
    var wrap = document.createElement('div');
    wrap.style.cssText = 'max-width:480px;margin:0 auto;display:flex;flex-direction:column;gap:14px;';

    var header = document.createElement('div');
    header.style.cssText = 'text-align:center;';
    header.innerHTML = '<div style="font-size:28px;">&#x1F9C4;</div><div style="font-size:20px;font-weight:700;color:var(--text-primary);">Garlic Phone</div>';
    wrap.appendChild(header);

    var roomInfo = document.createElement('div');
    roomInfo.style.cssText = 'background:var(--bg-secondary);border-radius:8px;padding:14px;text-align:center;';
    roomInfo.innerHTML = '<div style="font-size:11px;font-weight:700;text-transform:uppercase;color:var(--text-muted);margin-bottom:4px;">Room Code</div><div style="font-size:32px;font-weight:900;color:var(--accent);letter-spacing:8px;">' + (roomId||'') + '</div><div style="font-size:12px;color:var(--text-muted);margin-top:4px;">Share this code with friends</div>';
    wrap.appendChild(roomInfo);

    var playerList = document.createElement('div');
    playerList.style.cssText = 'background:var(--bg-secondary);border-radius:8px;padding:14px;';
    playerList.appendChild(section('Players (' + players.length + ')'));
    players.forEach(function(p) {
      var pEl = document.createElement('div');
      pEl.style.cssText = 'display:flex;align-items:center;gap:8px;padding:4px 0;font-size:14px;color:var(--text-primary);';
      pEl.innerHTML = '<span style="font-size:16px;">&#x1F464;</span>' + escHtml(p.display_name || p.username);
      playerList.appendChild(pEl);
    });
    if (players.length < 2) {
      var waiting = document.createElement('div');
      waiting.style.cssText = 'font-size:12px;color:var(--text-muted);margin-top:8px;text-align:center;';
      waiting.textContent = 'Waiting for more players... (need 2+)';
      playerList.appendChild(waiting);
    }
    wrap.appendChild(playerList);

    if (isHost) {
      var startBtn = makeBtn('Start Game', true);
      startBtn.style.cssText = 'width:100%;padding:12px;font-size:15px;';
      startBtn.disabled = players.length < 2;
      if (players.length < 2) startBtn.style.opacity = '0.5';
      startBtn.addEventListener('click', function() {
        send({ type: 'garlic_action', action: 'start', room_id: roomId });
      });
      wrap.appendChild(startBtn);
    } else {
      var hostWaiting = document.createElement('div');
      hostWaiting.style.cssText = 'text-align:center;color:var(--text-muted);font-size:13px;padding:8px;';
      hostWaiting.textContent = 'Waiting for the host to start the game...';
      wrap.appendChild(hostWaiting);
    }

    var leaveBtn = makeBtn('Leave Room');
    leaveBtn.style.cssText = 'width:100%;padding:8px;background:transparent;color:var(--red);border:1px solid var(--red);border-radius:6px;cursor:pointer;font-size:13px;';
    leaveBtn.addEventListener('click', function() {
      send({ type: 'garlic_action', action: 'leave', room_id: roomId });
      roomId = null; isHost = false; players = [];
      setPhase('lobby');
    });
    wrap.appendChild(leaveBtn);
    container.appendChild(wrap);
  }

  // ───── Waiting ─────
  function renderWaiting() {
    var wrap = document.createElement('div');
    wrap.style.cssText = 'max-width:400px;margin:0 auto;text-align:center;display:flex;flex-direction:column;align-items:center;gap:16px;padding:20px;';

    var icon = document.createElement('div');
    icon.style.cssText = 'font-size:48px;animation:spin 2s linear infinite;';
    icon.textContent = '⏳';
    wrap.appendChild(icon);

    var msg = document.createElement('div');
    msg.style.cssText = 'font-size:18px;font-weight:600;color:var(--text-primary);';
    msg.textContent = 'Waiting for other players...';
    wrap.appendChild(msg);

    var sub = document.createElement('div');
    sub.style.cssText = 'font-size:13px;color:var(--text-muted);';
    sub.textContent = 'Once everyone has submitted, the next round will begin.';
    wrap.appendChild(sub);

    container.appendChild(wrap);
  }

  // ───── Text Input ─────
  function renderTextInput() {
    var wrap = document.createElement('div');
    wrap.style.cssText = 'max-width:500px;margin:0 auto;display:flex;flex-direction:column;gap:14px;';

    var header = document.createElement('div');
    header.style.cssText = 'text-align:center;padding:8px;';
    header.innerHTML = '<div style="font-size:13px;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Round ' + (currentRound+1) + ' of ' + totalRounds + ' &mdash; Write a phrase</div>';
    if (currentRound === 0) {
      header.innerHTML += '<div style="font-size:15px;color:var(--text-primary);margin-top:6px;">Write any phrase or idea to start your chain!</div>';
    } else {
      header.innerHTML += '<div style="font-size:13px;color:var(--text-muted);margin-top:4px;">What do you see in this drawing?</div>';
    }
    wrap.appendChild(header);

    if (currentRound > 0 && promptData) {
      var imgBox = document.createElement('div');
      imgBox.style.cssText = 'background:var(--bg-secondary);border-radius:8px;padding:8px;text-align:center;';
      var img = document.createElement('img');
      img.src = promptData;
      img.style.cssText = 'max-width:100%;max-height:260px;border-radius:6px;border:1px solid var(--border);';
      imgBox.appendChild(img);
      imgBox.innerHTML = '<div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;text-transform:uppercase;font-weight:600;">Drawing to describe:</div>' + imgBox.innerHTML;
      wrap.appendChild(imgBox);
    }

    var inputBox = document.createElement('div');
    inputBox.style.cssText = 'background:var(--bg-secondary);border-radius:8px;padding:14px;';
    var textArea = document.createElement('textarea');
    textArea.placeholder = currentRound === 0 ? 'Write your starting phrase...' : 'What do you see in the drawing?';
    textArea.maxLength = 120;
    textArea.rows = 3;
    textArea.style.cssText = 'width:100%;padding:10px 12px;border:1px solid var(--border);border-radius:6px;background:var(--bg-tertiary);color:var(--text-primary);font-size:15px;resize:none;outline:none;box-sizing:border-box;font-family:inherit;';
    inputBox.appendChild(textArea);
    wrap.appendChild(inputBox);

    var charCount = document.createElement('div');
    charCount.style.cssText = 'font-size:11px;color:var(--text-muted);text-align:right;margin-top:-8px;';
    charCount.textContent = '0 / 120';
    textArea.addEventListener('input', function() { charCount.textContent = textArea.value.length + ' / 120'; });
    wrap.appendChild(charCount);

    var submitBtn = makeBtn('Submit', true);
    submitBtn.style.cssText = 'width:100%;padding:12px;font-size:15px;';
    submitBtn.addEventListener('click', function() {
      var text = textArea.value.trim();
      if (!text) { showError('Please write something!'); return; }
      send({ type: 'garlic_action', action: 'submit', room_id: roomId, content: text });
      setPhase('waiting');
    });
    wrap.appendChild(submitBtn);

    setTimeout(function() { textArea.focus(); }, 50);
    container.appendChild(wrap);
  }

  // ───── Drawing Canvas ─────
  function renderDrawing() {
    var wrap = document.createElement('div');
    wrap.style.cssText = 'max-width:600px;margin:0 auto;display:flex;flex-direction:column;gap:10px;';

    var header = document.createElement('div');
    header.style.cssText = 'text-align:center;';
    header.innerHTML = '<div style="font-size:13px;color:var(--text-muted);font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Round ' + (currentRound+1) + ' of ' + totalRounds + ' &mdash; Draw this!</div>';
    wrap.appendChild(header);

    if (promptData) {
      var phraseBox = document.createElement('div');
      phraseBox.style.cssText = 'background:var(--bg-secondary);border-radius:8px;padding:12px 16px;text-align:center;border:2px solid var(--accent);';
      phraseBox.innerHTML = '<div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;text-transform:uppercase;font-weight:600;">Draw this phrase:</div><div style="font-size:20px;font-weight:700;color:var(--text-primary);">' + escHtml(promptData) + '</div>';
      wrap.appendChild(phraseBox);
    }

    // Toolbar
    var toolbar = document.createElement('div');
    toolbar.style.cssText = 'display:flex;gap:8px;align-items:center;flex-wrap:wrap;background:var(--bg-secondary);border-radius:8px;padding:8px 12px;';

    // Colors
    var colors = ['#000000','#ffffff','#e74c3c','#e67e22','#f1c40f','#2ecc71','#3498db','#9b59b6','#1abc9c','#e91e63','#795548','#607d8b'];
    var colorBtns = document.createElement('div');
    colorBtns.style.cssText = 'display:flex;gap:4px;flex-wrap:wrap;';
    colors.forEach(function(c) {
      var cb = document.createElement('button');
      cb.style.cssText = 'width:22px;height:22px;border-radius:50%;background:' + c + ';border:2px solid ' + (c === currentColor ? 'var(--text-primary)' : 'transparent') + ';cursor:pointer;padding:0;flex-shrink:0;';
      cb.addEventListener('click', function() {
        currentColor = c;
        colorBtns.querySelectorAll('button').forEach(function(b) { b.style.border = '2px solid transparent'; });
        cb.style.border = '2px solid var(--text-primary)';
        if (drawCtx) drawCtx.strokeStyle = currentColor;
      });
      colorBtns.appendChild(cb);
    });
    toolbar.appendChild(colorBtns);

    // Size
    var sizeWrap = document.createElement('div');
    sizeWrap.style.cssText = 'display:flex;align-items:center;gap:6px;';
    var sizeLabel = document.createElement('span');
    sizeLabel.style.cssText = 'font-size:12px;color:var(--text-muted);';
    sizeLabel.textContent = 'Size:';
    var sizeInput = document.createElement('input');
    sizeInput.type = 'range'; sizeInput.min = '2'; sizeInput.max = '24'; sizeInput.value = String(currentSize);
    sizeInput.style.cssText = 'width:60px;';
    sizeInput.addEventListener('input', function() {
      currentSize = parseInt(sizeInput.value);
      if (drawCtx) drawCtx.lineWidth = currentSize;
    });
    sizeWrap.appendChild(sizeLabel);
    sizeWrap.appendChild(sizeInput);
    toolbar.appendChild(sizeWrap);

    // Eraser
    var eraserBtn = makeBtn('Eraser');
    eraserBtn.style.cssText = 'padding:4px 10px;font-size:12px;margin-top:0;';
    eraserBtn.addEventListener('click', function() {
      currentColor = '#ffffff';
      if (drawCtx) drawCtx.strokeStyle = '#ffffff';
    });
    toolbar.appendChild(eraserBtn);

    // Clear
    var clearBtn = makeBtn('Clear');
    clearBtn.style.cssText = 'padding:4px 10px;font-size:12px;margin-top:0;background:var(--bg-tertiary);color:var(--red);';
    clearBtn.addEventListener('click', function() {
      if (drawCtx && drawCanvas) {
        drawCtx.fillStyle = '#ffffff';
        drawCtx.fillRect(0, 0, drawCanvas.width, drawCanvas.height);
      }
    });
    toolbar.appendChild(clearBtn);
    wrap.appendChild(toolbar);

    // Canvas
    var cSize = Math.min(container.clientWidth - 32, 560);
    drawCanvas = document.createElement('canvas');
    drawCanvas.width = cSize;
    drawCanvas.height = Math.round(cSize * 0.6);
    drawCanvas.style.cssText = 'border:2px solid var(--border);border-radius:8px;background:#ffffff;cursor:crosshair;touch-action:none;display:block;';
    drawCtx = drawCanvas.getContext('2d');
    drawCtx.strokeStyle = currentColor;
    drawCtx.lineWidth = currentSize;
    drawCtx.lineCap = 'round';
    drawCtx.lineJoin = 'round';
    drawCtx.fillStyle = '#ffffff';
    drawCtx.fillRect(0, 0, drawCanvas.width, drawCanvas.height);

    function getPos(e) {
      var rect = drawCanvas.getBoundingClientRect();
      var scaleX = drawCanvas.width / rect.width;
      var scaleY = drawCanvas.height / rect.height;
      if (e.touches) {
        return { x: (e.touches[0].clientX - rect.left) * scaleX, y: (e.touches[0].clientY - rect.top) * scaleY };
      }
      return { x: (e.clientX - rect.left) * scaleX, y: (e.clientY - rect.top) * scaleY };
    }

    drawCanvas.addEventListener('mousedown', function(e) {
      drawing = true;
      var p = getPos(e);
      drawCtx.beginPath();
      drawCtx.moveTo(p.x, p.y);
      lastX = p.x; lastY = p.y;
    });
    drawCanvas.addEventListener('mousemove', function(e) {
      if (!drawing) return;
      var p = getPos(e);
      drawCtx.lineTo(p.x, p.y);
      drawCtx.stroke();
      lastX = p.x; lastY = p.y;
    });
    drawCanvas.addEventListener('mouseup', function() { drawing = false; drawCtx.closePath(); });
    drawCanvas.addEventListener('mouseleave', function() { drawing = false; drawCtx.closePath(); });
    drawCanvas.addEventListener('touchstart', function(e) {
      e.preventDefault();
      drawing = true;
      var p = getPos(e);
      drawCtx.beginPath();
      drawCtx.moveTo(p.x, p.y);
    }, {passive: false});
    drawCanvas.addEventListener('touchmove', function(e) {
      e.preventDefault();
      if (!drawing) return;
      var p = getPos(e);
      drawCtx.lineTo(p.x, p.y);
      drawCtx.stroke();
    }, {passive: false});
    drawCanvas.addEventListener('touchend', function() { drawing = false; drawCtx.closePath(); });
    wrap.appendChild(drawCanvas);

    var submitBtn = makeBtn('Submit Drawing', true);
    submitBtn.style.cssText = 'width:100%;padding:12px;font-size:15px;';
    submitBtn.addEventListener('click', function() {
      var dataUrl = drawCanvas.toDataURL('image/png');
      // Compress to JPEG for smaller size
      var img = new Image();
      img.onload = function() {
        var c2 = document.createElement('canvas');
        c2.width = Math.min(400, drawCanvas.width);
        c2.height = Math.round(c2.width * drawCanvas.height / drawCanvas.width);
        var c2ctx = c2.getContext('2d');
        c2ctx.fillStyle = '#ffffff';
        c2ctx.fillRect(0, 0, c2.width, c2.height);
        c2ctx.drawImage(img, 0, 0, c2.width, c2.height);
        var compressed = c2.toDataURL('image/jpeg', 0.6);
        send({ type: 'garlic_action', action: 'submit', room_id: roomId, content: compressed });
        setPhase('waiting');
      };
      img.src = dataUrl;
    });
    wrap.appendChild(submitBtn);
    container.appendChild(wrap);
  }

  // ───── Reveal ─────
  function renderReveal(chains, playerNames) {
    container.innerHTML = '';
    var wrap = document.createElement('div');
    wrap.style.cssText = 'max-width:600px;margin:0 auto;display:flex;flex-direction:column;gap:20px;';

    var title = document.createElement('div');
    title.style.cssText = 'text-align:center;font-size:24px;font-weight:800;color:var(--text-primary);padding:8px 0;';
    title.innerHTML = '&#x1F9C4; Garlic Phone Results';
    wrap.appendChild(title);

    chains.forEach(function(chain, ci) {
      var chainBox = document.createElement('div');
      chainBox.style.cssText = 'background:var(--bg-secondary);border-radius:10px;overflow:hidden;border:1px solid var(--border);';

      var chainHeader = document.createElement('div');
      chainHeader.style.cssText = 'background:var(--bg-tertiary);padding:8px 16px;font-size:13px;font-weight:700;color:var(--accent);border-bottom:1px solid var(--border);';
      chainHeader.textContent = "Chain " + (ci + 1) + (playerNames && playerNames[ci] ? " — started by " + playerNames[ci] : "");
      chainBox.appendChild(chainHeader);

      chain.forEach(function(entry, ei) {
        var entryEl = document.createElement('div');
        entryEl.style.cssText = 'padding:12px 16px;' + (ei > 0 ? 'border-top:1px solid var(--border);' : '');

        var authorEl = document.createElement('div');
        authorEl.style.cssText = 'font-size:11px;font-weight:700;text-transform:uppercase;color:var(--text-muted);margin-bottom:6px;';
        authorEl.textContent = (entry.author || 'Player') + ' — ' + (entry.type === 'draw' ? 'Drew:' : 'Wrote:');
        entryEl.appendChild(authorEl);

        if (entry.type === 'text') {
          var textEl = document.createElement('div');
          textEl.style.cssText = 'font-size:16px;font-weight:600;color:var(--text-primary);padding:8px 12px;background:var(--bg-tertiary);border-radius:6px;';
          textEl.textContent = entry.content || '(empty)';
          entryEl.appendChild(textEl);
        } else {
          var imgEl = document.createElement('img');
          imgEl.src = entry.content;
          imgEl.style.cssText = 'max-width:100%;max-height:200px;border-radius:6px;border:1px solid var(--border);display:block;';
          entryEl.appendChild(imgEl);
        }
        chainBox.appendChild(entryEl);
      });
      wrap.appendChild(chainBox);
    });

    var playAgainBtn = makeBtn('Play Again', true);
    playAgainBtn.style.cssText = 'width:100%;padding:12px;font-size:15px;';
    playAgainBtn.addEventListener('click', function() {
      roomId = null; isHost = false; players = [];
      setPhase('lobby');
    });
    wrap.appendChild(playAgainBtn);

    container.appendChild(wrap);
  }

  function escHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  render();
}
"""


def get_css():
    return ""
