def get_js():
    return r"""
function initBlackjackMulti(area) {
  var suitSymbols = { S: String.fromCodePoint(0x2660), H: String.fromCodePoint(0x2665), D: String.fromCodePoint(0x2666), C: String.fromCodePoint(0x2663) };
  var suitColors = { S: '#ccc', H: '#e74c3c', D: '#e74c3c', C: '#ccc' };
  var myId = null;
  var roomId = null;

  var lobbyDiv = document.createElement('div');
  lobbyDiv.className = 'bj-lobby';

  var lobbyStatus = document.createElement('div');
  lobbyStatus.className = 'game-status';
  lobbyStatus.textContent = 'Multiplayer Blackjack';
  lobbyDiv.appendChild(lobbyStatus);

  var lobbyInfo = document.createElement('div');
  lobbyInfo.className = 'bj-lobby-info';
  lobbyInfo.textContent = 'Play blackjack against other players. The dealer is automatic.';
  lobbyDiv.appendChild(lobbyInfo);

  var createBtn = document.createElement('button');
  createBtn.className = 'game-reset-btn';
  createBtn.textContent = 'Create Room';
  createBtn.setAttribute('data-testid', 'button-bj-create');
  lobbyDiv.appendChild(createBtn);

  var joinDiv = document.createElement('div');
  joinDiv.className = 'bj-join-row';
  var joinInput = document.createElement('input');
  joinInput.type = 'text';
  joinInput.placeholder = 'Room code...';
  joinInput.className = 'bj-join-input';
  joinInput.setAttribute('data-testid', 'input-bj-room');
  joinDiv.appendChild(joinInput);
  var joinBtn = document.createElement('button');
  joinBtn.className = 'game-reset-btn';
  joinBtn.textContent = 'Join Room';
  joinBtn.setAttribute('data-testid', 'button-bj-join');
  joinDiv.appendChild(joinBtn);
  lobbyDiv.appendChild(joinDiv);

  area.appendChild(lobbyDiv);

  var gameDiv = document.createElement('div');
  gameDiv.className = 'bj-game-area';
  gameDiv.style.display = 'none';
  area.appendChild(gameDiv);

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

  function renderGameState(state) {
    gameDiv.innerHTML = '';
    gameDiv.style.display = 'block';
    lobbyDiv.style.display = 'none';

    var roomInfo = document.createElement('div');
    roomInfo.className = 'bj-room-info';
    roomInfo.textContent = 'Room: ' + state.room_id + ' | Players: ' + state.players.length;
    gameDiv.appendChild(roomInfo);

    var statusEl = document.createElement('div');
    statusEl.className = 'game-status';
    if (state.phase === 'waiting') {
      statusEl.textContent = 'Waiting for players... (' + state.players.length + '/4)';
    } else if (state.phase === 'playing') {
      if (state.current_turn === myId) {
        statusEl.textContent = 'Your turn! Hit or Stand?';
      } else {
        var turnName = state.current_turn || '...';
        statusEl.textContent = turnName + "'s turn...";
      }
    } else if (state.phase === 'dealer') {
      statusEl.textContent = 'Dealer is playing...';
    } else if (state.phase === 'done') {
      statusEl.textContent = 'Round over!';
    }
    gameDiv.appendChild(statusEl);

    var dealerSection = document.createElement('div');
    dealerSection.className = 'bj-section';
    var dLabel = document.createElement('div');
    dLabel.className = 'bj-label';
    dLabel.textContent = 'Dealer' + (state.dealer_value ? ' (' + state.dealer_value + ')' : '');
    dealerSection.appendChild(dLabel);
    var dCards = document.createElement('div');
    dCards.className = 'bj-cards';
    if (state.dealer_hand) {
      for (var i = 0; i < state.dealer_hand.length; i++) {
        var c = state.dealer_hand[i];
        dCards.appendChild(renderCard(c, c.hidden));
      }
    }
    dealerSection.appendChild(dCards);
    gameDiv.appendChild(dealerSection);

    var divider = document.createElement('div');
    divider.className = 'bj-divider';
    gameDiv.appendChild(divider);

    for (var p = 0; p < state.players.length; p++) {
      var pl = state.players[p];
      var pSection = document.createElement('div');
      pSection.className = 'bj-section' + (pl.id === myId ? ' bj-section-me' : '');
      var pLabel = document.createElement('div');
      pLabel.className = 'bj-label';
      pLabel.textContent = pl.name + (pl.id === myId ? ' (You)' : '') + (pl.value ? ' - ' + pl.value : '') + (pl.result ? ' | ' + pl.result : '');
      pSection.appendChild(pLabel);
      var pCards = document.createElement('div');
      pCards.className = 'bj-cards';
      if (pl.hand) {
        for (var ci = 0; ci < pl.hand.length; ci++) {
          pCards.appendChild(renderCard(pl.hand[ci], false));
        }
      }
      pSection.appendChild(pCards);
      gameDiv.appendChild(pSection);
    }

    var controls = document.createElement('div');
    controls.className = 'bj-controls';

    if (state.phase === 'waiting' && state.host === myId) {
      var startBtn = document.createElement('button');
      startBtn.className = 'game-reset-btn';
      startBtn.textContent = 'Start Game';
      startBtn.setAttribute('data-testid', 'button-bj-start');
      startBtn.addEventListener('click', function() {
        ws.send(JSON.stringify({ type: 'bj_action', action: 'start', room_id: roomId }));
      });
      controls.appendChild(startBtn);
    }

    if (state.phase === 'playing' && state.current_turn === myId) {
      var hitBtn = document.createElement('button');
      hitBtn.className = 'game-reset-btn';
      hitBtn.textContent = 'Hit';
      hitBtn.setAttribute('data-testid', 'button-bjm-hit');
      hitBtn.addEventListener('click', function() {
        ws.send(JSON.stringify({ type: 'bj_action', action: 'hit', room_id: roomId }));
      });
      controls.appendChild(hitBtn);
      var standBtn = document.createElement('button');
      standBtn.className = 'game-reset-btn';
      standBtn.textContent = 'Stand';
      standBtn.setAttribute('data-testid', 'button-bjm-stand');
      standBtn.addEventListener('click', function() {
        ws.send(JSON.stringify({ type: 'bj_action', action: 'stand', room_id: roomId }));
      });
      controls.appendChild(standBtn);
    }

    if (state.phase === 'done') {
      var newRoundBtn = document.createElement('button');
      newRoundBtn.className = 'game-reset-btn';
      newRoundBtn.textContent = 'New Round';
      newRoundBtn.setAttribute('data-testid', 'button-bjm-newround');
      newRoundBtn.addEventListener('click', function() {
        ws.send(JSON.stringify({ type: 'bj_action', action: 'start', room_id: roomId }));
      });
      controls.appendChild(newRoundBtn);
    }

    var leaveBtn = document.createElement('button');
    leaveBtn.className = 'game-reset-btn';
    leaveBtn.textContent = 'Leave';
    leaveBtn.setAttribute('data-testid', 'button-bjm-leave');
    leaveBtn.addEventListener('click', function() {
      ws.send(JSON.stringify({ type: 'bj_action', action: 'leave', room_id: roomId }));
      roomId = null;
      gameDiv.style.display = 'none';
      gameDiv.innerHTML = '';
      lobbyDiv.style.display = 'block';
    });
    controls.appendChild(leaveBtn);
    gameDiv.appendChild(controls);
  }

  createBtn.addEventListener('click', function() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: 'bj_action', action: 'create' }));
  });

  joinBtn.addEventListener('click', function() {
    var code = joinInput.value.trim().toUpperCase();
    if (!code || !ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: 'bj_action', action: 'join', room_id: code }));
  });

  window._bjMultiHandler = function(data) {
    if (data.type === 'bj_room_created') {
      roomId = data.room_id;
      myId = data.player_id;
      renderGameState(data.state);
    } else if (data.type === 'bj_joined') {
      roomId = data.room_id;
      myId = data.player_id;
      renderGameState(data.state);
    } else if (data.type === 'bj_state') {
      renderGameState(data.state);
    } else if (data.type === 'bj_error') {
      lobbyStatus.textContent = data.text || 'Error';
    }
  };
}
"""


def get_css():
    return """
.bj-lobby { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 20px; }
.bj-lobby-info { font-size: 13px; color: var(--text-secondary); text-align: center; max-width: 300px; }
.bj-join-row { display: flex; gap: 8px; align-items: center; }
.bj-join-input {
  padding: 6px 10px; border-radius: 4px; border: 1px solid var(--border);
  background: var(--input-bg); color: var(--text-primary); font-size: 13px;
  width: 140px; outline: none;
}
.bj-join-input:focus { border-color: var(--accent); }
.bj-room-info { font-size: 12px; color: var(--text-muted); text-align: center; margin-bottom: 4px; }
.bj-game-area { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 12px; overflow-y: auto; }
.bj-section-me { background: var(--bg-secondary); border-radius: 8px; padding: 8px 12px; }
"""
