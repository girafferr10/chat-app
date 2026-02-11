import asyncio
import hashlib
import json
import os
import secrets
import re
import random
import string
import aiohttp
from aiohttp import web
import time as _time
from datetime import datetime, timedelta

from games import tictactoe, snake, memory, blackjack, blackjack_multi, minesweeper, solitaire, checkers, hangman, war, crazy_eights, twenty_fortyeight

connected = {}       # ws -> {"username": str, "ws": ws}
banned_users = set() # set of banned usernames
owner_ws = None      # owner websocket connection
admin_connections = {}  # ws -> {"name": str, "key": str}
dm_store = {}        # (sorted_user_a, sorted_user_b) -> [{"sender":..., "recipient":..., "text":..., "ts":...}]

bj_rooms = {}
gc_store = {}
gc_counter = 0

admin_accounts = {}  # key -> {"name": str, "created": str}
suggestions = []     # [{"id": int, "from": str, "text": str, "timestamp": str, "read": bool}]
suggestion_counter = [0]
owner_mailbox = []   # [{"id": int, "type": str, "text": str, "timestamp": str, "read": bool}]
owner_mailbox_counter = 0

LOG_FILE = "chat_logs.json"
chat_logs = []
log_id_counter = 0

try:
    from zoneinfo import ZoneInfo
    MTN_TZ = ZoneInfo("America/Denver")
except ImportError:
    import pytz
    MTN_TZ = pytz.timezone("America/Denver")


def mtn_now():
    return datetime.now(MTN_TZ)


def load_logs():
    global chat_logs, log_id_counter
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                chat_logs = json.load(f)
                for entry in chat_logs:
                    if "id" not in entry:
                        log_id_counter += 1
                        entry["id"] = log_id_counter
                if chat_logs:
                    log_id_counter = max(e.get("id", 0) for e in chat_logs)
    except Exception:
        chat_logs = []


def save_logs():
    try:
        with open(LOG_FILE, "w") as f:
            json.dump(chat_logs, f)
    except Exception as e:
        print(f"[LOG] Error saving logs: {e}")


def add_log(log_type, **kwargs):
    global log_id_counter
    log_id_counter += 1
    entry = {
        "id": log_id_counter,
        "type": log_type,
        "timestamp": mtn_now().strftime("%Y-%m-%d %H:%M:%S MT"),
        **kwargs
    }
    chat_logs.append(entry)
    save_logs()


def delete_log(log_id):
    global chat_logs
    chat_logs = [e for e in chat_logs if e.get("id") != log_id]
    save_logs()


def dm_key(a, b):
    return tuple(sorted([a, b]))

_raw_secret = os.environ.get("SESSION_SECRET", secrets.token_urlsafe(16))
OWNER_TOKEN = hashlib.sha256(_raw_secret.encode()).hexdigest()[:24]

USERNAME_RE = re.compile(r'^[a-zA-Z0-9_-]{1,20}$')
RESERVED_RE = re.compile(r'admin|mod|owner', re.IGNORECASE)


def get_admin_html(token):
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chat Server - Owner Panel</title>
<style>
:root {
  --bg-primary: #313338;
  --bg-secondary: #2b2d31;
  --bg-tertiary: #1e1f22;
  --bg-message-hover: #2e3035;
  --text-primary: #f2f3f5;
  --text-secondary: #b5bac1;
  --text-tertiary: #949ba4;
  --text-muted: #6d6f78;
  --border: #3f4147;
  --accent: #5865f2;
  --accent-hover: #4752c4;
  --green: #23a559;
  --red: #ed4245;
  --yellow: #fee75c;
  --orange: #f0b232;
  --admin-color: #e03e3e;
  --input-bg: #383a40;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'gg sans', 'Noto Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  background: var(--bg-primary); color: var(--text-primary);
  height: 100vh; display: flex; flex-direction: column;
}
header {
  background: var(--bg-primary); border-bottom: 1px solid var(--bg-tertiary);
  padding: 12px 20px; display: flex; align-items: center;
  justify-content: space-between; gap: 8px; flex-wrap: wrap;
}
header h1 { font-size: 16px; font-weight: 600; }
.header-right { display: flex; align-items: center; gap: 12px; }
.status { font-size: 12px; color: var(--text-secondary); display: flex; align-items: center; gap: 6px; }
.status .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); }
.status.offline .dot { background: var(--red); }
.theme-btn {
  background: var(--input-bg); color: var(--text-secondary); border: none;
  padding: 6px 10px; border-radius: 4px; font-size: 12px; cursor: pointer;
}
.theme-btn:hover { background: var(--border); color: var(--text-primary); }

.container { flex: 1; display: flex; overflow: hidden; }

.sidebar {
  width: 240px; background: var(--bg-secondary);
  display: flex; flex-direction: column; flex-shrink: 0;
}
.sidebar-header {
  padding: 12px 16px; font-size: 11px; font-weight: 700; color: var(--text-tertiary);
  text-transform: uppercase; letter-spacing: 0.5px;
  display: flex; justify-content: space-between; align-items: center;
}
.sidebar-header .count {
  background: var(--bg-tertiary); color: var(--text-secondary);
  padding: 1px 6px; border-radius: 8px; font-size: 11px;
}
.user-list { flex: 1; overflow-y: auto; padding: 0 8px; }
.user-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 8px; border-radius: 4px; margin-bottom: 1px;
}
.user-item:hover { background: var(--bg-message-hover); }
.user-info { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }
.user-avatar {
  width: 32px; height: 32px; border-radius: 50%; background: var(--accent);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600; color: #fff; flex-shrink: 0;
}
.user-name {
  font-size: 14px; font-weight: 500; color: var(--text-secondary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.user-actions { display: flex; gap: 4px; visibility: hidden; }
.user-item:hover .user-actions { visibility: visible; }
.btn {
  padding: 4px 8px; border: none; border-radius: 4px;
  font-size: 11px; font-weight: 600; cursor: pointer;
  background: var(--bg-tertiary); color: var(--text-secondary);
}
.btn:hover { background: var(--border); color: var(--text-primary); }
.btn-danger { color: var(--red); }
.btn-danger:hover { background: rgba(237,66,69,0.15); color: var(--red); }
.btn-warn { color: var(--orange); }
.btn-warn:hover { background: rgba(240,178,50,0.15); color: var(--orange); }

.chat-area { flex: 1; display: flex; flex-direction: column; background: var(--bg-primary); }
.messages { flex: 1; overflow-y: auto; padding: 16px 16px; }
.msg { padding: 2px 8px; margin-bottom: 0; border-radius: 4px; line-height: 1.4; }
.msg:hover { background: var(--bg-message-hover); }
.msg-inline { padding: 4px 8px; display: flex; align-items: baseline; gap: 0; flex-wrap: wrap; }
.msg-sender { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.msg-sender.is-admin { color: var(--admin-color); }
.msg-badge { font-size: 10px; font-weight: 700; color: #fff; background: var(--admin-color);
  padding: 1px 4px; border-radius: 3px; margin-left: 4px; vertical-align: middle; }
.msg-colon { color: var(--text-tertiary); margin-right: 6px; }
.msg-time { font-size: 11px; color: var(--text-muted); margin-left: 6px; }
.msg-text { font-size: 14px; color: var(--text-secondary); word-break: break-word; }
.msg-system { text-align: center; padding: 4px 8px; margin-bottom: 2px; }
.msg-system span {
  font-size: 12px; color: var(--text-muted); background: var(--bg-secondary);
  padding: 2px 10px; border-radius: 10px;
}

.admin-input {
  padding: 12px 16px; display: flex; gap: 8px; flex-wrap: wrap;
}
.admin-input .name-input {
  width: 140px; padding: 10px 12px; border: none; border-radius: 8px;
  font-size: 14px; outline: none; background: var(--input-bg);
  color: var(--text-primary); flex-shrink: 0;
}
.admin-input .name-input:focus { outline: 2px solid var(--accent); }
.admin-input .msg-field {
  flex: 1; padding: 10px 14px; border: none; border-radius: 8px;
  font-size: 14px; outline: none; background: var(--input-bg);
  color: var(--text-primary); min-width: 200px;
}
.admin-input .msg-field:focus { outline: 2px solid var(--accent); }
.admin-input button {
  padding: 10px 20px; background: var(--accent); color: #fff;
  border: none; border-radius: 8px; font-size: 14px;
  font-weight: 500; cursor: pointer;
}
.admin-input button:hover { background: var(--accent-hover); }

.banned-section {
  border-top: 1px solid var(--bg-tertiary); padding: 10px 16px;
  max-height: 120px; overflow-y: auto;
}
.banned-header {
  font-size: 11px; font-weight: 700; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;
}
.banned-item {
  display: flex; align-items: center; justify-content: space-between; padding: 4px 0;
}
.banned-name { font-size: 13px; color: var(--text-muted); text-decoration: line-through; }
.btn-unban { color: var(--green); }
.btn-unban:hover { background: rgba(35,165,89,0.15); color: var(--green); }

.empty { display: flex; align-items: center; justify-content: center;
  height: 100%; color: var(--text-muted); font-size: 14px; }

body.theme-light {
  --bg-primary: #ffffff;
  --bg-secondary: #f2f3f5;
  --bg-tertiary: #e3e5e8;
  --bg-message-hover: #f2f3f5;
  --text-primary: #060607;
  --text-secondary: #4e5058;
  --text-tertiary: #6d6f78;
  --text-muted: #80848e;
  --border: #e3e5e8;
  --accent: #5865f2;
  --accent-hover: #4752c4;
  --input-bg: #e3e5e8;
  --admin-color: #c0392b;
}
body.theme-midnight {
  --bg-primary: #0a0a0f;
  --bg-secondary: #111118;
  --bg-tertiary: #06060a;
  --bg-message-hover: #14141c;
  --text-primary: #e0e0e8;
  --text-secondary: #9a9ab0;
  --text-tertiary: #6a6a80;
  --text-muted: #4a4a5a;
  --border: #1a1a24;
  --input-bg: #14141c;
  --admin-color: #ff5555;
}
body.theme-ocean {
  --bg-primary: #0d1b2a; --bg-secondary: #1b2838; --bg-tertiary: #0a1520;
  --bg-message-hover: #1f3044; --text-primary: #e0f0ff; --text-secondary: #8ab4d6;
  --text-tertiary: #5a8aaa; --text-muted: #3a6080; --border: #1a3050;
  --accent: #1e90ff; --accent-hover: #1570cc; --input-bg: #162636; --admin-color: #ff6b6b;
}
body.theme-forest {
  --bg-primary: #1a2618; --bg-secondary: #222e20; --bg-tertiary: #141e12;
  --bg-message-hover: #283628; --text-primary: #e0f0e0; --text-secondary: #8ab88a;
  --text-tertiary: #5a8a5a; --text-muted: #3a6a3a; --border: #2a3e2a;
  --accent: #2ecc71; --accent-hover: #27ae60; --input-bg: #1e2e1c; --admin-color: #e74c3c;
}
body.theme-sunset {
  --bg-primary: #2a1a1e; --bg-secondary: #381e24; --bg-tertiary: #1e1214;
  --bg-message-hover: #3e242a; --text-primary: #ffe8e0; --text-secondary: #d4a090;
  --text-tertiary: #a07060; --text-muted: #705040; --border: #4a2a30;
  --accent: #ff6b35; --accent-hover: #e55a2b; --input-bg: #321a20; --admin-color: #ff4444;
}
body.theme-neon {
  --bg-primary: #0a0a14; --bg-secondary: #10101e; --bg-tertiary: #06060c;
  --bg-message-hover: #161628; --text-primary: #e0e0ff; --text-secondary: #a0a0d0;
  --text-tertiary: #7070a0; --text-muted: #404070; --border: #1e1e3a;
  --accent: #ff00ff; --accent-hover: #cc00cc; --input-bg: #12121e; --admin-color: #ff3366;
}
body.theme-rose {
  --bg-primary: #201418; --bg-secondary: #2a1a20; --bg-tertiary: #180e12;
  --bg-message-hover: #301e26; --text-primary: #ffe8f0; --text-secondary: #d4a0b8;
  --text-tertiary: #a07088; --text-muted: #705060; --border: #3a1e2a;
  --accent: #e91e63; --accent-hover: #c2185b; --input-bg: #261620; --admin-color: #ff5252;
}
</style>
</head>
<body>
<header>
  <h1>Chat Server</h1>
  <div class="header-right">
    <div class="status" id="status">
      <span class="dot"></span>
      <span id="status-text">Connecting...</span>
    </div>
    <button class="theme-btn" id="themeBtn" data-testid="button-theme">Dark</button>
  </div>
</header>
<div class="container">
  <div class="sidebar">
    <div class="sidebar-header">
      Online <span class="count" id="user-count" data-testid="text-user-count">0</span>
    </div>
    <div class="user-list" id="user-list" data-testid="list-users"></div>
    <div class="banned-section" id="banned-section" style="display:none;">
      <div class="banned-header">Banned</div>
      <div id="banned-list"></div>
    </div>
  </div>
  <div class="chat-area">
    <div class="messages" id="messages" data-testid="list-messages">
      <div class="empty" id="empty-state">No messages yet</div>
    </div>
    <div class="admin-input">
      <input type="text" class="name-input" id="name-input" data-testid="input-admin-name" placeholder="Your name" value="Admin" />
      <input type="text" class="msg-field" id="msg-input" data-testid="input-message" placeholder="Type a message..." />
      <button id="send-btn" data-testid="button-send">Send</button>
    </div>
  </div>
</div>
<script>
const OWNER_TOKEN = '__TOKEN__';
history.replaceState({}, '', '/admin');
const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = protocol + '//' + location.host + '/owner-ws?token=' + OWNER_TOKEN;
let ws;
const themes = ['theme-dark', 'theme-light', 'theme-midnight', 'theme-ocean', 'theme-forest', 'theme-sunset', 'theme-neon', 'theme-rose'];
const themeLabels = ['Dark', 'Light', 'Midnight', 'Ocean', 'Forest', 'Sunset', 'Neon', 'Rose'];
let themeIdx = parseInt(localStorage.getItem('admin-theme') || '0');

function applyTheme() {
  document.body.className = themes[themeIdx] || '';
  document.getElementById('themeBtn').textContent = themeLabels[themeIdx];
  localStorage.setItem('admin-theme', themeIdx);
}
applyTheme();

document.getElementById('themeBtn').addEventListener('click', function() {
  themeIdx = (themeIdx + 1) % themes.length;
  applyTheme();
});

function connectWS() {
  ws = new WebSocket(wsUrl);
  ws.onopen = () => {
    document.getElementById('status').className = 'status';
    document.getElementById('status-text').textContent = 'Server Running';
  };
  ws.onclose = () => {
    document.getElementById('status').className = 'status offline';
    document.getElementById('status-text').textContent = 'Disconnected';
    setTimeout(connectWS, 2000);
  };
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    switch (data.type) {
      case 'users': renderUsers(data.list); break;
      case 'chat': addMessage(data.sender, data.text, data.admin || false); break;
      case 'system': addSystemMessage(data.text); break;
      case 'banned_list': renderBanned(data.list); break;
    }
  };
}

function renderUsers(users) {
  const el = document.getElementById('user-list');
  document.getElementById('user-count').textContent = users.length;
  if (users.length === 0) {
    el.innerHTML = '<div class="empty" style="height:80px;">No users online</div>';
    return;
  }
  el.innerHTML = '';
  users.forEach(userObj => {
    const u = typeof userObj === 'string' ? userObj : userObj.name;
    const item = document.createElement('div');
    item.className = 'user-item';
    const info = document.createElement('div');
    info.className = 'user-info';
    const avatar = document.createElement('div');
    avatar.className = 'user-avatar';
    avatar.textContent = u.substring(0,2).toUpperCase();
    const name = document.createElement('div');
    name.className = 'user-name';
    name.textContent = u;
    info.appendChild(avatar);
    info.appendChild(name);
    const actions = document.createElement('div');
    actions.className = 'user-actions';
    const kickBtn = document.createElement('button');
    kickBtn.className = 'btn btn-warn';
    kickBtn.textContent = 'Kick';
    kickBtn.addEventListener('click', () => { ws.send(JSON.stringify({type:'kick',username:u})); });
    const banBtn = document.createElement('button');
    banBtn.className = 'btn btn-danger';
    banBtn.textContent = 'Ban';
    banBtn.addEventListener('click', () => { ws.send(JSON.stringify({type:'ban',username:u})); });
    actions.appendChild(kickBtn);
    actions.appendChild(banBtn);
    item.appendChild(info);
    item.appendChild(actions);
    el.appendChild(item);
  });
}

function renderBanned(list) {
  const section = document.getElementById('banned-section');
  const el = document.getElementById('banned-list');
  if (list.length === 0) { section.style.display = 'none'; return; }
  section.style.display = 'block';
  el.innerHTML = '';
  list.forEach(u => {
    const item = document.createElement('div');
    item.className = 'banned-item';
    const name = document.createElement('span');
    name.className = 'banned-name';
    name.textContent = u;
    const unbanBtn = document.createElement('button');
    unbanBtn.className = 'btn btn-unban';
    unbanBtn.textContent = 'Unban';
    unbanBtn.addEventListener('click', () => { ws.send(JSON.stringify({type:'unban',username:u})); });
    item.appendChild(name);
    item.appendChild(unbanBtn);
    el.appendChild(item);
  });
}

function addMessage(sender, text, isAdmin) {
  document.getElementById('empty-state')?.remove();
  const el = document.getElementById('messages');
  const time = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  const div = document.createElement('div');
  div.className = 'msg msg-inline';

  const senderEl = document.createElement('span');
  senderEl.className = 'msg-sender' + (isAdmin ? ' is-admin' : '');
  senderEl.textContent = sender;
  div.appendChild(senderEl);

  if (isAdmin) {
    const badge = document.createElement('span');
    badge.className = 'msg-badge';
    badge.textContent = 'ADMIN';
    div.appendChild(badge);
  }

  const colon = document.createElement('span');
  colon.className = 'msg-colon';
  colon.textContent = ': ';
  div.appendChild(colon);

  const textEl = document.createElement('span');
  textEl.className = 'msg-text';
  textEl.textContent = text;
  div.appendChild(textEl);

  const timeEl = document.createElement('span');
  timeEl.className = 'msg-time';
  timeEl.textContent = time;
  div.appendChild(timeEl);

  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

function addSystemMessage(text) {
  document.getElementById('empty-state')?.remove();
  const el = document.getElementById('messages');
  const wrapper = document.createElement('div');
  wrapper.className = 'msg-system';
  const span = document.createElement('span');
  span.textContent = text;
  wrapper.appendChild(span);
  el.appendChild(wrapper);
  el.scrollTop = el.scrollHeight;
}

function sendMsg() {
  const nameInput = document.getElementById('name-input');
  const input = document.getElementById('msg-input');
  const text = input.value.trim();
  const name = nameInput.value.trim() || 'Admin';
  if (!text) return;
  ws.send(JSON.stringify({type: 'chat', text: text, name: name}));
  input.value = '';
  input.focus();
}

document.getElementById('send-btn').addEventListener('click', sendMsg);
document.getElementById('msg-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendMsg();
});
connectWS();
</script>
</body>
</html>""".replace('__TOKEN__', token)


def get_client_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chat</title>
<style>
:root {
  --bg-primary: #313338;
  --bg-secondary: #2b2d31;
  --bg-tertiary: #1e1f22;
  --bg-message-hover: #2e3035;
  --text-primary: #f2f3f5;
  --text-secondary: #b5bac1;
  --text-tertiary: #949ba4;
  --text-muted: #6d6f78;
  --border: #3f4147;
  --accent: #5865f2;
  --accent-hover: #4752c4;
  --green: #23a559;
  --red: #ed4245;
  --orange: #f0b232;
  --admin-color: #e03e3e;
  --input-bg: #383a40;
  --dm-color: #9b59b6;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'gg sans', 'Noto Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  background: var(--bg-primary); color: var(--text-primary);
  height: 100vh; display: flex; flex-direction: column;
}

.join-screen {
  display: flex; align-items: center; justify-content: center;
  min-height: 100vh; background: var(--bg-tertiary);
}
.join-box {
  background: var(--bg-primary); border-radius: 8px;
  padding: 32px; max-width: 400px; width: 90%;
}
.join-box h2 { margin-bottom: 8px; font-size: 22px; font-weight: 700; color: var(--text-primary); }
.join-box p { color: var(--text-secondary); margin-bottom: 20px; font-size: 14px; }
.join-box label { display: block; font-size: 12px; font-weight: 700; margin-bottom: 6px;
  color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
.join-box input {
  width: 100%; padding: 10px 12px; border: none; border-radius: 4px;
  font-size: 14px; margin-bottom: 16px; background: var(--bg-tertiary);
  color: var(--text-primary); outline: none;
}
.join-box input:focus { outline: 2px solid var(--accent); }
.join-box button {
  width: 100%; padding: 10px; background: var(--accent); color: #fff; border: none;
  border-radius: 4px; font-size: 14px; font-weight: 600; cursor: pointer;
}
.join-box button:hover { background: var(--accent-hover); }
.join-error { color: var(--red); font-size: 13px; margin-bottom: 10px; display: none; }

header {
  background: var(--bg-primary); border-bottom: 1px solid var(--bg-tertiary);
  padding: 12px 20px; display: flex; align-items: center;
  justify-content: space-between; gap: 8px; flex-wrap: wrap;
}
header h1 { font-size: 16px; font-weight: 600; }
.header-right { display: flex; align-items: center; gap: 12px; }
.status { font-size: 12px; color: var(--text-secondary); display: flex; align-items: center; gap: 6px; }
.status .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); }
.theme-btn {
  background: var(--input-bg); color: var(--text-secondary); border: none;
  padding: 6px 10px; border-radius: 4px; font-size: 12px; cursor: pointer;
}
.theme-btn:hover { background: var(--border); color: var(--text-primary); }

.container { display: flex; flex: 1; overflow: hidden; }

.sidebar {
  width: 240px; background: var(--bg-secondary);
  display: flex; flex-direction: column; flex-shrink: 0;
}
.sidebar-section {
  padding: 10px 10px 0 10px;
}
.sidebar-label {
  padding: 4px 6px; font-size: 11px; font-weight: 700;
  color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.5px;
  display: flex; align-items: center; gap: 6px;
}
.sidebar-label .count {
  background: var(--bg-tertiary); color: var(--text-secondary);
  padding: 1px 6px; border-radius: 8px; font-size: 11px;
}
.channel-item {
  padding: 7px 10px; font-size: 14px; color: var(--text-secondary);
  border-radius: 4px; margin-bottom: 1px; display: flex; align-items: center; gap: 8px;
  cursor: pointer;
}
.channel-item:hover { background: var(--bg-message-hover); }
.channel-item.active { background: var(--bg-message-hover); color: var(--text-primary); font-weight: 600; }
.channel-icon { font-size: 16px; opacity: 0.6; }
.dm-badge {
  margin-left: auto; background: var(--red); color: #fff;
  font-size: 10px; font-weight: 700; padding: 1px 5px; border-radius: 8px;
  min-width: 16px; text-align: center;
}
.user-list-area { flex: 1; overflow-y: auto; padding: 0 10px 10px 10px; }
.user-item {
  padding: 6px 10px; font-size: 14px; color: var(--text-secondary);
  border-radius: 4px; margin-bottom: 1px; display: flex; align-items: center; gap: 8px;
  cursor: pointer; position: relative;
}
.user-item:hover { background: var(--bg-message-hover); }
.user-avatar {
  width: 28px; height: 28px; border-radius: 50%; background: var(--accent);
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600; color: #fff; flex-shrink: 0;
}
.user-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.user-actions { display: flex; gap: 4px; visibility: hidden; }
.user-item:hover .user-actions { visibility: visible; }

.chat-area { flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }

.main-panel { flex: 1; display: flex; flex-direction: column; min-width: 0; min-height: 0; }
.tab-bar {
  display: flex; align-items: center; background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border); height: 36px; flex-shrink: 0;
  overflow-x: auto; overflow-y: hidden;
}
.tab-bar::-webkit-scrollbar { height: 0; }
.tab-items { display: flex; flex: 1; min-width: 0; overflow-x: auto; }
.tab-items::-webkit-scrollbar { height: 0; }
.tab-item {
  display: flex; align-items: center; gap: 6px;
  padding: 0 12px; height: 36px; font-size: 13px; font-weight: 500;
  color: var(--text-secondary); cursor: pointer; white-space: nowrap;
  border-right: 1px solid var(--border); background: var(--bg-tertiary);
  flex-shrink: 0; min-width: 0;
}
.tab-item:hover { background: var(--bg-secondary); }
.tab-item.active { background: var(--bg-primary); color: var(--text-primary); }
.tab-item .tab-icon { font-size: 14px; opacity: 0.7; }
.tab-item .tab-close {
  font-size: 14px; opacity: 0; width: 18px; height: 18px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 3px; color: var(--text-muted); margin-left: 2px;
  background: none; border: none; cursor: pointer; padding: 0;
}
.tab-item:hover .tab-close { visibility: visible; opacity: 1; }
.tab-item .tab-close:hover { background: var(--bg-message-hover); color: var(--text-primary); }
.new-tab-btn {
  width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
  background: none; border: none; color: var(--text-muted); font-size: 18px;
  cursor: pointer; flex-shrink: 0;
}
.new-tab-btn:hover { background: var(--bg-secondary); color: var(--text-primary); }
#tabContents { flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
.tab-content { flex: 1; display: none; flex-direction: column; min-height: 0; overflow: hidden; }
.tab-content.active { display: flex; }

.newtab-page {
  flex: 1; display: flex; flex-direction: column; background: var(--bg-primary); overflow-y: auto;
}
.newtab-search {
  padding: 12px 16px 0; flex-shrink: 0;
}
.newtab-search input {
  width: 100%; padding: 8px 12px; border-radius: 4px; border: 1px solid var(--border);
  background: var(--input-bg); color: var(--text-primary); font-size: 13px; outline: none;
}
.newtab-search input:focus { border-color: var(--accent); }
.newtab-search input::placeholder { color: var(--text-muted); }
.newtab-list {
  flex: 1; overflow-y: auto; padding: 8px 0;
}
.newtab-item {
  display: flex; align-items: center; padding: 10px 16px; cursor: pointer;
  gap: 12px; transition: background 0.1s;
}
.newtab-item:hover { background: var(--bg-message-hover); }
.newtab-item-info { flex: 1; min-width: 0; }
.newtab-item-name { font-size: 14px; font-weight: 500; color: var(--text-primary); }
.newtab-item-desc { font-size: 12px; color: var(--text-muted); margin-top: 1px; }
.newtab-item-badge {
  font-size: 10px; padding: 2px 6px; border-radius: 3px;
  background: var(--bg-tertiary); color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.3px; font-weight: 600; flex-shrink: 0;
}
.newtab-section-label {
  font-size: 11px; font-weight: 700; color: var(--text-tertiary);
  text-transform: uppercase; letter-spacing: 0.5px;
  padding: 12px 16px 4px;
}
.newtab-empty {
  padding: 20px 16px; text-align: center; color: var(--text-muted); font-size: 13px;
}

.games-hub {
  flex: 1; display: flex; flex-direction: column; background: var(--bg-primary); overflow: hidden;
}
.games-header {
  padding: 10px 16px; border-bottom: 1px solid var(--bg-tertiary);
  font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 8px;
}
.games-header .back-btn {
  background: var(--input-bg); border: none; color: var(--text-secondary);
  padding: 4px 10px; border-radius: 4px; font-size: 12px; cursor: pointer;
}
.games-header .back-btn:hover { background: var(--border); color: var(--text-primary); }
.games-search {
  padding: 8px 16px; flex-shrink: 0;
}
.games-search input {
  width: 100%; padding: 7px 10px; border-radius: 4px; border: 1px solid var(--border);
  background: var(--input-bg); color: var(--text-primary); font-size: 13px; outline: none;
}
.games-search input:focus { border-color: var(--accent); }
.games-search input::placeholder { color: var(--text-muted); }
.games-list {
  flex: 1; overflow-y: auto; padding: 0;
}
.game-item {
  display: flex; align-items: center; padding: 10px 16px; cursor: pointer;
  gap: 12px; transition: background 0.1s;
}
.game-item:hover { background: var(--bg-message-hover); }
.game-item-info { flex: 1; min-width: 0; }
.game-item-name { font-size: 14px; font-weight: 500; color: var(--text-primary); }
.game-item-desc { font-size: 12px; color: var(--text-muted); margin-top: 1px; }
.game-item-badge {
  font-size: 10px; padding: 2px 6px; border-radius: 3px;
  background: var(--bg-tertiary); color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.3px; font-weight: 600; flex-shrink: 0;
}
.game-play-area {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 16px; overflow-y: auto;
}

.ttt-board {
  display: grid; grid-template-columns: repeat(3, 80px); grid-template-rows: repeat(3, 80px); gap: 4px;
}
.ttt-cell {
  width: 80px; height: 80px; background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: 4px; font-size: 32px; font-weight: 700; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  color: var(--text-primary);
}
.ttt-cell:hover { background: var(--bg-message-hover); }
.ttt-cell.x { color: var(--accent); }
.ttt-cell.o { color: var(--red); }
.game-status {
  font-size: 15px; font-weight: 600; margin-bottom: 12px; color: var(--text-primary);
  min-height: 24px;
}
.game-reset-btn {
  margin-top: 12px; padding: 8px 20px; background: var(--accent); color: #fff;
  border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer;
}
.game-reset-btn:hover { background: var(--accent-hover); }

.snake-canvas {
  border: 2px solid var(--border); border-radius: 4px; background: var(--bg-secondary);
}
.snake-score { font-size: 14px; color: var(--text-secondary); margin-bottom: 8px; }
.snake-hint { font-size: 12px; color: var(--text-muted); margin-top: 8px; }

.memory-board {
  display: grid; grid-template-columns: repeat(4, 70px); gap: 6px;
}
.memory-card {
  width: 70px; height: 70px; background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: 6px; font-size: 24px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  color: transparent; user-select: none;
}
.memory-card:hover { background: var(--bg-message-hover); }
.memory-card.flipped, .memory-card.matched {
  color: var(--text-primary); background: var(--bg-message-hover);
  border-color: var(--accent);
}
.memory-card.matched { border-color: var(--green); cursor: default; }
.memory-stats { font-size: 13px; color: var(--text-secondary); margin-bottom: 10px; }

.channel-header {
  padding: 10px 16px; border-bottom: 1px solid var(--bg-tertiary);
  font-size: 15px; font-weight: 600; display: flex; align-items: center; gap: 8px;
}
.channel-header .dm-label { color: var(--dm-color); }

#messages { flex: 1; overflow-y: auto; padding: 16px 16px; min-height: 0; }
.msg { padding: var(--msg-padding, 2px 8px); border-radius: 4px; line-height: 1.4; }
.msg:hover { background: var(--bg-message-hover); }
.msg-inline { padding: 4px 8px; display: flex; align-items: baseline; gap: 0; flex-wrap: wrap; }
.msg-sender { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.msg-sender.is-admin { color: var(--admin-color); }
.msg-badge { font-size: 10px; font-weight: 700; color: #fff; background: var(--admin-color);
  padding: 1px 4px; border-radius: 3px; margin-left: 4px; vertical-align: middle; }
.msg-badge.dm-badge-inline { background: var(--dm-color); }
.msg-colon { color: var(--text-tertiary); margin-right: 6px; }
.msg-time { font-size: 11px; color: var(--text-muted); margin-left: 6px; }
.msg-text { font-size: 14px; color: var(--text-secondary); word-break: break-word; }
.msg-text a { color: var(--accent); text-decoration: none; }
.msg-text a:hover { text-decoration: underline; }
.msg-text .inline-img {
  display: block; max-width: 400px; max-height: 300px;
  border-radius: 8px; margin-top: 4px; cursor: pointer;
}
.msg-text .inline-img:hover { opacity: 0.9; }
.msg-system { text-align: center; padding: 4px 8px; margin-bottom: 2px; }
.msg-system span { font-size: 12px; color: var(--text-muted); background: var(--bg-secondary);
  padding: 2px 10px; border-radius: 10px; }
.msg-error { padding: 4px 8px; color: var(--red); font-size: 13px; font-weight: 500; }

.emoji-picker-btn {
  background: var(--input-bg); color: var(--text-secondary); border: none;
  padding: 10px 12px; border-radius: 8px; font-size: 18px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.emoji-picker-btn:hover { background: var(--border); color: var(--text-primary); }
.emoji-picker-container {
  position: relative;
}
.emoji-panel {
  position: absolute; bottom: 100%; right: 0; margin-bottom: 8px;
  background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: 8px; padding: 8px; width: 320px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.3); display: none; z-index: 100;
}
.emoji-panel.open { display: block; }
.emoji-panel-header {
  display: flex; gap: 4px; margin-bottom: 6px; flex-wrap: wrap;
}
.emoji-cat-btn {
  background: none; border: none; color: var(--text-muted);
  font-size: 16px; cursor: pointer; padding: 4px 6px; border-radius: 4px;
  width: auto;
}
.emoji-cat-btn:hover { background: var(--bg-message-hover); }
.emoji-cat-btn.active { background: var(--bg-tertiary); color: var(--text-primary); }
.emoji-search {
  width: 100%; padding: 6px 8px; border: none; border-radius: 4px;
  font-size: 13px; background: var(--bg-tertiary); color: var(--text-primary);
  outline: none; margin-bottom: 6px;
}
.emoji-search:focus { outline: 1px solid var(--accent); }
.emoji-grid {
  display: grid; grid-template-columns: repeat(8, 1fr); gap: 2px;
  max-height: 200px; overflow-y: auto;
}
.emoji-grid::-webkit-scrollbar { width: 6px; }
.emoji-grid::-webkit-scrollbar-thumb { background: var(--bg-tertiary); border-radius: 3px; }
.emoji-item {
  font-size: 20px; padding: 4px; text-align: center; cursor: pointer;
  border-radius: 4px; border: none; background: none; width: auto;
}
.emoji-item:hover { background: var(--bg-message-hover); }

.input-bar {
  padding: 12px 16px; display: flex; gap: 8px; flex-shrink: 0;
}
.input-bar input {
  flex: 1; padding: 10px 14px; border: none; border-radius: 8px;
  font-size: 14px; outline: none; background: var(--input-bg);
  color: var(--text-primary);
}
.input-bar input:focus { outline: 2px solid var(--accent); }
.input-bar button {
  padding: 10px 20px; background: var(--accent); color: #fff; border: none;
  border-radius: 8px; font-size: 14px; cursor: pointer; font-weight: 500;
}
.input-bar button:hover { background: var(--accent-hover); }
.input-bar button:disabled { background: var(--bg-tertiary); color: var(--text-muted); cursor: not-allowed; }

.empty { color: var(--text-muted); text-align: center; margin-top: 60px; font-size: 14px; }

.chat-screen { display: none; height: 100vh; flex-direction: column; }

.banned-section {
  border-top: 1px solid var(--bg-tertiary); padding: 10px 16px;
  max-height: 120px; overflow-y: auto;
}
.banned-header {
  font-size: 11px; font-weight: 700; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;
}

.dm-spy-section {
  border-top: 1px solid var(--bg-tertiary); padding: 10px;
}
.dm-spy-label {
  padding: 4px 6px; font-size: 11px; font-weight: 700;
  color: var(--dm-color); text-transform: uppercase; letter-spacing: 0.5px;
  margin-bottom: 4px;
}
.dm-spy-item {
  padding: 5px 10px; font-size: 13px; color: var(--text-secondary);
  border-radius: 4px; cursor: pointer; margin-bottom: 1px;
  display: flex; align-items: center; gap: 6px;
}
.dm-spy-item:hover { background: var(--bg-message-hover); }
.dm-spy-item.active { background: var(--bg-message-hover); color: var(--text-primary); }
.dm-spy-icon { color: var(--dm-color); font-size: 14px; }

.gc-create-btn {
  background: var(--accent); color: #fff; border: none; border-radius: 4px;
  width: 20px; height: 20px; font-size: 14px; font-weight: 700; cursor: pointer;
  display: flex; align-items: center; justify-content: center; line-height: 1;
}
.gc-create-btn:hover { opacity: 0.8; }
.gc-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.6); z-index: 1000;
  display: flex; align-items: center; justify-content: center;
}
.gc-modal {
  background: var(--bg-secondary); border-radius: 8px; padding: 20px;
  width: 320px; max-height: 80vh; overflow-y: auto; box-shadow: 0 4px 24px rgba(0,0,0,0.3);
}
.gc-modal-title { font-size: 16px; font-weight: 700; color: var(--text-primary); margin-bottom: 12px; }
.gc-modal-input {
  width: 100%; padding: 8px 10px; border-radius: 4px; border: 1px solid var(--border);
  background: var(--input-bg); color: var(--text-primary); font-size: 13px;
  outline: none; margin-bottom: 10px; box-sizing: border-box;
}
.gc-modal-input:focus { border-color: var(--accent); }
.gc-member-list { max-height: 200px; overflow-y: auto; margin-bottom: 12px; }
.gc-member-item {
  display: flex; align-items: center; gap: 8px; padding: 6px 8px;
  border-radius: 4px; cursor: pointer; font-size: 13px; color: var(--text-secondary);
}
.gc-member-item:hover { background: var(--bg-message-hover); }
.gc-member-item.selected { background: var(--accent); color: #fff; }
.gc-member-item .gc-check {
  width: 16px; height: 16px; border: 2px solid var(--border); border-radius: 3px;
  display: flex; align-items: center; justify-content: center; font-size: 11px;
  flex-shrink: 0;
}
.gc-member-item.selected .gc-check { background: #fff; border-color: #fff; color: var(--accent); }
.gc-modal-btns { display: flex; gap: 8px; justify-content: flex-end; }
.gc-modal-btns button {
  padding: 6px 16px; border-radius: 4px; border: none; font-size: 13px;
  font-weight: 600; cursor: pointer;
}
.gc-modal-btns .gc-cancel { background: var(--bg-tertiary); color: var(--text-secondary); }
.gc-modal-btns .gc-confirm { background: var(--accent); color: #fff; }
.gc-modal-btns .gc-confirm:disabled { opacity: 0.5; cursor: not-allowed; }
.gc-badge { font-size: 10px; font-weight: 600; color: var(--green); margin-left: auto; }

.settings-row {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px; gap: 8px;
}
.settings-label { font-size: 13px; color: var(--text-secondary); flex-shrink: 0; }
.settings-row input[type="text"] {
  flex: 1; padding: 6px 8px; border-radius: 4px; border: 1px solid var(--border);
  background: var(--input-bg); color: var(--text-primary); font-size: 12px; outline: none;
}
.settings-row input[type="text"]:focus { border-color: var(--accent); }
.settings-row input[type="color"] {
  width: 36px; height: 28px; border: 1px solid var(--border); border-radius: 4px;
  padding: 0; cursor: pointer; background: transparent;
}

body.theme-light {
  --bg-primary: #ffffff;
  --bg-secondary: #f2f3f5;
  --bg-tertiary: #e3e5e8;
  --bg-message-hover: #f2f3f5;
  --text-primary: #060607;
  --text-secondary: #4e5058;
  --text-tertiary: #6d6f78;
  --text-muted: #80848e;
  --border: #e3e5e8;
  --input-bg: #e3e5e8;
  --admin-color: #c0392b;
  --dm-color: #8e44ad;
}
body.theme-midnight {
  --bg-primary: #0a0a0f;
  --bg-secondary: #111118;
  --bg-tertiary: #06060a;
  --bg-message-hover: #14141c;
  --text-primary: #e0e0e8;
  --text-secondary: #9a9ab0;
  --text-tertiary: #6a6a80;
  --text-muted: #4a4a5a;
  --border: #1a1a24;
  --input-bg: #14141c;
  --admin-color: #ff5555;
  --dm-color: #bb86fc;
}
body.theme-ocean {
  --bg-primary: #0d1b2a;
  --bg-secondary: #1b2838;
  --bg-tertiary: #0a1520;
  --bg-message-hover: #1f3044;
  --text-primary: #e0f0ff;
  --text-secondary: #8ab4d6;
  --text-tertiary: #5a8aaa;
  --text-muted: #3a6080;
  --border: #1a3050;
  --accent: #1e90ff;
  --accent-hover: #1570cc;
  --input-bg: #162636;
  --admin-color: #ff6b6b;
  --dm-color: #64b5f6;
}
body.theme-forest {
  --bg-primary: #1a2618;
  --bg-secondary: #222e20;
  --bg-tertiary: #141e12;
  --bg-message-hover: #283628;
  --text-primary: #e0f0e0;
  --text-secondary: #8ab88a;
  --text-tertiary: #5a8a5a;
  --text-muted: #3a6a3a;
  --border: #2a3e2a;
  --accent: #2ecc71;
  --accent-hover: #27ae60;
  --input-bg: #1e2e1c;
  --admin-color: #e74c3c;
  --dm-color: #a0d468;
}
body.theme-sunset {
  --bg-primary: #2a1a1e;
  --bg-secondary: #381e24;
  --bg-tertiary: #1e1214;
  --bg-message-hover: #3e242a;
  --text-primary: #ffe8e0;
  --text-secondary: #d4a090;
  --text-tertiary: #a07060;
  --text-muted: #705040;
  --border: #4a2a30;
  --accent: #ff6b35;
  --accent-hover: #e55a2b;
  --input-bg: #321a20;
  --admin-color: #ff4444;
  --dm-color: #ffb380;
}
body.theme-neon {
  --bg-primary: #0a0a14;
  --bg-secondary: #10101e;
  --bg-tertiary: #06060c;
  --bg-message-hover: #161628;
  --text-primary: #e0e0ff;
  --text-secondary: #a0a0d0;
  --text-tertiary: #7070a0;
  --text-muted: #404070;
  --border: #1e1e3a;
  --accent: #ff00ff;
  --accent-hover: #cc00cc;
  --input-bg: #12121e;
  --admin-color: #ff3366;
  --dm-color: #00ffcc;
}
body.theme-rose {
  --bg-primary: #201418;
  --bg-secondary: #2a1a20;
  --bg-tertiary: #180e12;
  --bg-message-hover: #301e26;
  --text-primary: #ffe8f0;
  --text-secondary: #d4a0b8;
  --text-tertiary: #a07088;
  --text-muted: #705060;
  --border: #3a1e2a;
  --accent: #e91e63;
  --accent-hover: #c2185b;
  --input-bg: #261620;
  --admin-color: #ff5252;
  --dm-color: #f48fb1;
}

@media (max-width: 600px) {
  .sidebar { display: none; }
}
""" + tictactoe.get_css() + snake.get_css() + memory.get_css() + blackjack.get_css() + blackjack_multi.get_css() + minesweeper.get_css() + solitaire.get_css() + checkers.get_css() + hangman.get_css() + war.get_css() + crazy_eights.get_css() + twenty_fortyeight.get_css() + """
</style>
</head>
<body>
<div class="join-screen" id="joinScreen">
  <div class="join-box" id="roleBox">
    <h2>Join Chat</h2>
    <p>How would you like to join?</p>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <button id="guestBtn" data-testid="button-guest" style="flex:1;">Guest</button>
      <button id="staffAdminBtn" data-testid="button-staff-admin" style="flex:1;background:var(--accent);">Admin</button>
      <button id="ownerBtn" data-testid="button-owner" style="flex:1;background:var(--admin-color);">Owner</button>
    </div>
  </div>
  <div class="join-box" id="guestBox" style="display:none;">
    <h2>Join as Guest</h2>
    <p>Pick a username to start chatting.</p>
    <div class="join-error" id="joinError"></div>
    <label for="usernameInput">Username</label>
    <input type="text" id="usernameInput" data-testid="input-username" placeholder="Enter username..." maxlength="20" />
    <button id="joinBtn" data-testid="button-join">Join</button>
    <button id="backBtn1" data-testid="button-back-guest" style="margin-top:8px;background:var(--input-bg);color:var(--text-secondary);">Back</button>
  </div>
  <div class="join-box" id="staffAdminBox" style="display:none;">
    <h2>Join as Admin</h2>
    <p>Enter your admin key to continue.</p>
    <div class="join-error" id="staffAdminError"></div>
    <label for="staffAdminKeyInput">Admin Key</label>
    <input type="password" id="staffAdminKeyInput" data-testid="input-admin-key" placeholder="Paste admin key here..." />
    <button id="staffAdminLoginBtn" data-testid="button-staff-admin-login">Login</button>
    <button id="backBtn3" data-testid="button-back-staff-admin" style="margin-top:8px;background:var(--input-bg);color:var(--text-secondary);">Back</button>
  </div>
  <div class="join-box" id="adminBox" style="display:none;">
    <h2>Join as Owner</h2>
    <p>Enter the owner key to continue.</p>
    <div class="join-error" id="adminError"></div>
    <label for="adminTokenInput">Owner Key</label>
    <input type="password" id="adminTokenInput" data-testid="input-token" placeholder="Paste owner key here..." />
    <button id="adminLoginBtn" data-testid="button-admin-login">Login</button>
    <button id="backBtn2" data-testid="button-back-admin" style="margin-top:8px;background:var(--input-bg);color:var(--text-secondary);">Back</button>
  </div>
</div>

<div class="chat-screen" id="chatScreen">
  <header>
    <h1 data-testid="text-header">Chat</h1>
    <div class="header-right">
      <div class="status"><div class="dot"></div> Connected</div>
      <button class="theme-btn" id="settingsBtn" data-testid="button-settings" title="Settings" style="font-size:16px;padding:4px 8px;">&#x2699;</button>
      <button class="theme-btn" id="themeBtn" data-testid="button-theme">Dark</button>
    </div>
  </header>
  <div class="container">
    <div class="sidebar">
      <div class="sidebar-section">
        <div class="sidebar-label">Channels</div>
        <div class="channel-item active" id="channelGeneral" data-testid="channel-general">
          <span class="channel-icon">#</span> General
        </div>
      </div>
      <div class="sidebar-section" id="dmChannelsSection" style="display:none;">
        <div class="sidebar-label">Direct Messages</div>
        <div id="dmChannelsList"></div>
      </div>
      <div class="sidebar-section" id="gcChannelsSection" style="display:none;">
        <div class="sidebar-label" style="display:flex;align-items:center;justify-content:space-between;">Group Chats <button class="gc-create-btn" id="gcCreateBtn" data-testid="button-gc-create" title="Create Group Chat">+</button></div>
        <div id="gcChannelsList"></div>
      </div>
      <div class="sidebar-section">
        <div class="sidebar-label">Online <span class="count" id="userCount" data-testid="text-user-count">0</span></div>
      </div>
      <div class="user-list-area" id="userList" data-testid="list-users"></div>
      <div id="dmSpySection" class="dm-spy-section" style="display:none;">
        <div class="dm-spy-label">DM Spy</div>
        <div id="dmSpyList"></div>
      </div>
      <div id="bannedSection" class="banned-section" style="display:none;">
        <div class="banned-header">Banned</div>
        <div id="bannedList"></div>
      </div>
      <div id="logsSection" class="dm-spy-section" style="display:none;">
        <div class="dm-spy-label" style="display:flex;align-items:center;justify-content:space-between;">Logs <button class="gc-create-btn" id="viewLogsBtn" data-testid="button-view-logs" title="View Logs" style="font-size:11px;width:auto;padding:0 6px;">View</button></div>
      </div>
      <div id="mailboxSection" class="dm-spy-section" style="display:none;">
        <div class="dm-spy-label" style="display:flex;align-items:center;justify-content:space-between;color:var(--orange);">Mailbox <span class="dm-badge" id="mailboxBadge" style="display:none;">0</span></div>
        <div class="dm-spy-item" id="suggestionsBtn" data-testid="button-suggestions" style="cursor:pointer;"><span class="dm-spy-icon" style="color:var(--orange);">IN</span><span>Suggestions</span></div>
        <div class="dm-spy-item" id="adminCreatorBtn" data-testid="button-admin-creator" style="cursor:pointer;display:none;"><span class="dm-spy-icon" style="color:var(--green);">+</span><span>Create Admin</span></div>
        <div class="dm-spy-item" id="manageAdminsBtn" data-testid="button-manage-admins" style="cursor:pointer;display:none;"><span class="dm-spy-icon" style="color:var(--accent);">A</span><span>Manage Admins</span></div>
      </div>
      <div id="suggestBoxSection" class="dm-spy-section" style="display:none;">
        <div class="dm-spy-label" style="color:var(--green);">Send Suggestion</div>
        <div style="padding:4px 0;">
          <input type="text" id="suggestInput" data-testid="input-suggestion" placeholder="Type a suggestion..." style="width:100%;padding:6px 8px;border-radius:4px;border:1px solid var(--border);background:var(--input-bg);color:var(--text-primary);font-size:12px;outline:none;box-sizing:border-box;" />
          <button id="suggestSendBtn" data-testid="button-send-suggestion" style="margin-top:4px;width:100%;padding:4px;background:var(--accent);color:#fff;border:none;border-radius:4px;font-size:12px;cursor:pointer;">Send</button>
        </div>
      </div>
    </div>
    <div class="main-panel">
      <div class="tab-bar">
        <div class="tab-items" id="tabItems" data-testid="tab-bar"></div>
        <button class="new-tab-btn" id="newTabBtn" data-testid="button-new-tab" title="New Tab">+</button>
      </div>
      <div id="tabContents">
        <div class="tab-content active" id="tabContent-chat">
          <div class="chat-area">
            <div class="channel-header" id="channelHeaderBar">
              <span class="channel-icon">#</span> <span id="channelName" data-testid="text-channel-name">General</span>
            </div>
            <div id="messages" data-testid="list-messages">
              <div class="empty" id="emptyState">No messages yet</div>
            </div>
            <div class="input-bar">
              <input type="text" id="nameInput" data-testid="input-admin-name" placeholder="Your name" value="Admin" style="display:none;width:140px;flex:unset;" />
              <input type="text" id="msgInput" data-testid="input-message" placeholder="Type a message..." />
              <div class="emoji-picker-container">
                <button class="emoji-picker-btn" id="emojiBtn" data-testid="button-emoji" type="button" title="Emoji picker">&#x1F600;</button>
                <div class="emoji-panel" id="emojiPanel">
                  <input type="text" class="emoji-search" id="emojiSearch" data-testid="input-emoji-search" placeholder="Search emojis..." />
                  <div class="emoji-panel-header" id="emojiCatBar"></div>
                  <div class="emoji-grid" id="emojiGrid" data-testid="grid-emoji"></div>
                </div>
              </div>
              <button id="sendBtn" data-testid="button-send">Send</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
var ws = null;
var myUsername = '';
var isAdmin = false;
var isOwner = false;
var isStaffAdmin = false;
var myRole = 'guest';
var currentChannel = 'general';
var generalMessages = [];
var dmMessages = {};
var dmUnread = {};
var onlineUsers = [];
var activeDmPairs = [];
var gcList = {};
var gcMessages = {};
var gcUnread = {};
var themes = ['theme-dark', 'theme-light', 'theme-midnight', 'theme-ocean', 'theme-forest', 'theme-sunset', 'theme-neon', 'theme-rose'];
var themeLabels = ['Dark', 'Light', 'Midnight', 'Ocean', 'Forest', 'Sunset', 'Neon', 'Rose'];
var themeIdx = parseInt(localStorage.getItem('chat-theme') || '0');

function applyTheme() {
  document.body.className = themes[themeIdx] || '';
  document.getElementById('themeBtn').textContent = themeLabels[themeIdx];
  localStorage.setItem('chat-theme', themeIdx);
}
applyTheme();

document.getElementById('themeBtn').addEventListener('click', function() {
  themeIdx = (themeIdx + 1) % themes.length;
  applyTheme();
});

document.getElementById('guestBtn').addEventListener('click', function() {
  document.getElementById('roleBox').style.display = 'none';
  document.getElementById('guestBox').style.display = 'block';
  document.getElementById('usernameInput').focus();
});
document.getElementById('ownerBtn').addEventListener('click', function() {
  document.getElementById('roleBox').style.display = 'none';
  document.getElementById('adminBox').style.display = 'block';
  document.getElementById('adminTokenInput').focus();
});
document.getElementById('staffAdminBtn').addEventListener('click', function() {
  document.getElementById('roleBox').style.display = 'none';
  document.getElementById('staffAdminBox').style.display = 'block';
  document.getElementById('staffAdminKeyInput').focus();
});
document.getElementById('backBtn1').addEventListener('click', function() {
  document.getElementById('guestBox').style.display = 'none';
  document.getElementById('roleBox').style.display = 'block';
});
document.getElementById('backBtn2').addEventListener('click', function() {
  document.getElementById('adminBox').style.display = 'none';
  document.getElementById('roleBox').style.display = 'block';
});
document.getElementById('backBtn3').addEventListener('click', function() {
  document.getElementById('staffAdminBox').style.display = 'none';
  document.getElementById('roleBox').style.display = 'block';
});

function switchChannel(channel) {
  currentChannel = channel;
  renderMessages();
  renderSidebar();
  var nameEl = document.getElementById('channelName');
  var headerBar = document.getElementById('channelHeaderBar');
  if (channel === 'general') {
    headerBar.innerHTML = '<span class="channel-icon">#</span> <span id="channelName" data-testid="text-channel-name">General</span>';
    document.getElementById('msgInput').placeholder = 'Message #General';
  } else if (channel.startsWith('dm:')) {
    var target = channel.substring(3);
    headerBar.innerHTML = '<span class="channel-icon" style="color:var(--dm-color);">@</span> <span id="channelName" data-testid="text-channel-name" class="dm-label">' + escapeHtml(target) + '</span>';
    document.getElementById('msgInput').placeholder = 'Message @' + target;
    if (dmUnread[target]) { dmUnread[target] = 0; renderDmChannels(); }
  } else if (channel.startsWith('gc:')) {
    var gcId = channel.substring(3);
    var gc = gcList[gcId];
    var gcName = gc ? gc.name : 'Group';
    headerBar.innerHTML = '<span class="channel-icon" style="color:var(--green);">#</span> <span id="channelName" data-testid="text-channel-name">' + escapeHtml(gcName) + '</span>';
    document.getElementById('msgInput').placeholder = 'Message #' + gcName;
    if (gcUnread[gcId]) { gcUnread[gcId] = 0; renderGcChannels(); }
  } else if (channel.startsWith('spy:')) {
    var parts = channel.substring(4);
    headerBar.innerHTML = '<span class="dm-spy-icon">SPY</span> <span id="channelName" data-testid="text-channel-name" style="color:var(--dm-color);">DM Spy: ' + escapeHtml(parts) + '</span>';
    document.getElementById('msgInput').placeholder = 'Viewing DMs (read-only)';
  }
  document.getElementById('msgInput').focus();
}

function escapeHtml(s) {
  var d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

var IMAGE_EXTS = /\.(png|jpg|jpeg|gif|webp|svg|bmp|apng)(\?.*)?$/i;
var GIF_HOSTS = /tenor\.com|giphy\.com|gfycat\.com|imgur\.com/i;
var URL_RE = /(https?:\/\/[^\s<>"']+)/g;

function isImageUrl(url) {
  if (IMAGE_EXTS.test(url)) return true;
  if (GIF_HOSTS.test(url) && /\.(gif|webp|mp4)(\?.*)?$/i.test(url)) return true;
  if (/media\d*\.giphy\.com/i.test(url)) return true;
  if (/i\.imgur\.com/i.test(url)) return true;
  if (/tenor\.com.*\.gif/i.test(url)) return true;
  return false;
}

function renderRichText(text) {
  var container = document.createElement('span');
  container.className = 'msg-text';
  var parts = text.split(URL_RE);
  var hasImage = false;
  for (var i = 0; i < parts.length; i++) {
    var part = parts[i];
    if (!part) continue;
    if (/^https?:\/\//i.test(part)) {
      if (isImageUrl(part)) {
        hasImage = true;
        var img = document.createElement('img');
        img.className = 'inline-img';
        img.src = part;
        img.alt = 'Image';
        img.loading = 'lazy';
        img.addEventListener('click', function() { window.open(this.src, '_blank'); });
        img.addEventListener('error', function() {
          var link = document.createElement('a');
          link.href = this.src;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          link.textContent = this.src;
          this.parentNode.replaceChild(link, this);
        });
        container.appendChild(img);
      } else {
        var link = document.createElement('a');
        link.href = part;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = part;
        container.appendChild(link);
      }
    } else {
      var span = document.createElement('span');
      span.textContent = part;
      container.appendChild(span);
    }
  }
  return container;
}

function makeMessageDiv(sender, text, admin, isDm, time) {
  var div = document.createElement('div');
  div.className = 'msg msg-inline';
  var senderEl = document.createElement('span');
  senderEl.className = 'msg-sender' + (admin ? ' is-admin' : '');
  senderEl.textContent = sender;
  div.appendChild(senderEl);
  if (admin) {
    var badge = document.createElement('span');
    badge.className = 'msg-badge';
    badge.textContent = 'ADMIN';
    div.appendChild(badge);
  }
  if (isDm && !admin) {
    var dmBadge = document.createElement('span');
    dmBadge.className = 'msg-badge dm-badge-inline';
    dmBadge.textContent = 'DM';
    div.appendChild(dmBadge);
  }
  var colon = document.createElement('span');
  colon.className = 'msg-colon';
  colon.textContent = ': ';
  div.appendChild(colon);
  var textEl = renderRichText(text);
  div.appendChild(textEl);
  var timeEl = document.createElement('span');
  timeEl.className = 'msg-time';
  timeEl.textContent = time || new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  div.appendChild(timeEl);
  return div;
}

function renderMessages() {
  var el = document.getElementById('messages');
  el.innerHTML = '';
  var msgs = [];
  if (currentChannel === 'general') {
    msgs = generalMessages;
  } else if (currentChannel.startsWith('dm:')) {
    var target = currentChannel.substring(3);
    msgs = dmMessages[target] || [];
  } else if (currentChannel.startsWith('gc:')) {
    var gcId = currentChannel.substring(3);
    msgs = gcMessages[gcId] || [];
  } else if (currentChannel.startsWith('spy:')) {
    var pair = currentChannel.substring(4);
    msgs = dmMessages['spy:' + pair] || [];
  }
  if (msgs.length === 0) {
    var empty = document.createElement('div');
    empty.className = 'empty';
    empty.id = 'emptyState';
    empty.textContent = currentChannel === 'general' ? 'No messages yet' : 'No messages in this conversation';
    el.appendChild(empty);
    return;
  }
  msgs.forEach(function(m) {
    if (m.type === 'system') {
      var wrapper = document.createElement('div');
      wrapper.className = 'msg-system';
      var span = document.createElement('span');
      span.textContent = m.text;
      wrapper.appendChild(span);
      el.appendChild(wrapper);
    } else {
      el.appendChild(makeMessageDiv(m.sender, m.text, m.admin || false, m.isDm || false, m.time));
    }
  });
  el.scrollTop = el.scrollHeight;
}

function renderSidebar() {
  renderDmChannels();
  renderGcChannels();
  var generalEl = document.getElementById('channelGeneral');
  generalEl.className = 'channel-item' + (currentChannel === 'general' ? ' active' : '');
}

function renderDmChannels() {
  var section = document.getElementById('dmChannelsSection');
  var list = document.getElementById('dmChannelsList');
  list.innerHTML = '';
  var dmKeys = Object.keys(dmMessages).filter(function(k) { return !k.startsWith('spy:'); });
  if (dmKeys.length === 0) { section.style.display = 'none'; return; }
  section.style.display = 'block';
  dmKeys.forEach(function(target) {
    var item = document.createElement('div');
    item.className = 'channel-item' + (currentChannel === 'dm:' + target ? ' active' : '');
    item.setAttribute('data-testid', 'dm-channel-' + target);
    var icon = document.createElement('span');
    icon.className = 'channel-icon';
    icon.style.color = 'var(--dm-color)';
    icon.textContent = '@';
    item.appendChild(icon);
    var nameSpan = document.createElement('span');
    nameSpan.textContent = ' ' + target;
    item.appendChild(nameSpan);
    if (dmUnread[target] && dmUnread[target] > 0 && currentChannel !== 'dm:' + target) {
      var badge = document.createElement('span');
      badge.className = 'dm-badge';
      badge.textContent = dmUnread[target];
      item.appendChild(badge);
    }
    item.addEventListener('click', function() { switchChannel('dm:' + target); });
    list.appendChild(item);
  });
}

function renderGcChannels() {
  var section = document.getElementById('gcChannelsSection');
  var list = document.getElementById('gcChannelsList');
  list.innerHTML = '';
  var gcIds = Object.keys(gcList);
  if (gcIds.length === 0) { section.style.display = 'none'; return; }
  section.style.display = 'block';
  gcIds.forEach(function(gcId) {
    var gc = gcList[gcId];
    var item = document.createElement('div');
    item.className = 'channel-item' + (currentChannel === 'gc:' + gcId ? ' active' : '');
    item.setAttribute('data-testid', 'gc-channel-' + gcId);
    var icon = document.createElement('span');
    icon.className = 'channel-icon';
    icon.style.color = 'var(--green)';
    icon.textContent = '#';
    item.appendChild(icon);
    var nameSpan = document.createElement('span');
    nameSpan.textContent = ' ' + gc.name;
    item.appendChild(nameSpan);
    if (gcUnread[gcId] && gcUnread[gcId] > 0 && currentChannel !== 'gc:' + gcId) {
      var badge = document.createElement('span');
      badge.className = 'dm-badge';
      badge.textContent = gcUnread[gcId];
      item.appendChild(badge);
    }
    item.addEventListener('click', function() {
      switchChannel('gc:' + gcId);
      gcUnread[gcId] = 0;
      ws.send(JSON.stringify({type: 'gc_open', gc_id: gcId}));
    });
    list.appendChild(item);
  });
}

function showGcCreateModal() {
  var overlay = document.createElement('div');
  overlay.className = 'gc-overlay';
  overlay.setAttribute('data-testid', 'gc-create-modal');
  var modal = document.createElement('div');
  modal.className = 'gc-modal';
  var title = document.createElement('div');
  title.className = 'gc-modal-title';
  title.textContent = 'Create Group Chat';
  modal.appendChild(title);
  var nameInput = document.createElement('input');
  nameInput.className = 'gc-modal-input';
  nameInput.placeholder = 'Group name...';
  nameInput.setAttribute('data-testid', 'input-gc-name');
  modal.appendChild(nameInput);
  var memberLabel = document.createElement('div');
  memberLabel.style.cssText = 'font-size:12px;color:var(--text-muted);margin-bottom:6px;';
  memberLabel.textContent = 'Select members (2+ required):';
  modal.appendChild(memberLabel);
  var memberList = document.createElement('div');
  memberList.className = 'gc-member-list';
  var selected = {};
  onlineUsers.forEach(function(name) {
    if (name === myUsername) return;
    var item = document.createElement('div');
    item.className = 'gc-member-item';
    item.setAttribute('data-testid', 'gc-member-' + name);
    var check = document.createElement('div');
    check.className = 'gc-check';
    item.appendChild(check);
    var nm = document.createElement('span');
    nm.textContent = name;
    item.appendChild(nm);
    item.addEventListener('click', function() {
      if (selected[name]) {
        delete selected[name];
        item.className = 'gc-member-item';
        check.textContent = '';
      } else {
        selected[name] = true;
        item.className = 'gc-member-item selected';
        check.textContent = 'X';
      }
      confirmBtn.disabled = Object.keys(selected).length < 2;
    });
    memberList.appendChild(item);
  });
  modal.appendChild(memberList);
  var btns = document.createElement('div');
  btns.className = 'gc-modal-btns';
  var cancelBtn = document.createElement('button');
  cancelBtn.className = 'gc-cancel';
  cancelBtn.textContent = 'Cancel';
  cancelBtn.setAttribute('data-testid', 'button-gc-cancel');
  cancelBtn.addEventListener('click', function() { overlay.remove(); });
  btns.appendChild(cancelBtn);
  var confirmBtn = document.createElement('button');
  confirmBtn.className = 'gc-confirm';
  confirmBtn.textContent = 'Create';
  confirmBtn.disabled = true;
  confirmBtn.setAttribute('data-testid', 'button-gc-confirm');
  confirmBtn.addEventListener('click', function() {
    var gcName = nameInput.value.trim() || 'Group';
    var members = Object.keys(selected);
    if (members.length < 2) return;
    ws.send(JSON.stringify({type: 'gc_create', name: gcName, members: members}));
    overlay.remove();
  });
  btns.appendChild(confirmBtn);
  modal.appendChild(btns);
  overlay.appendChild(modal);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  document.body.appendChild(overlay);
  nameInput.focus();
  nameInput.addEventListener('keydown', function(e) { e.stopPropagation(); });
}

function hexToRgb(hex) {
  var r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
  return {r:r, g:g, b:b};
}
function blendColor(c, factor) {
  return '#' + [c.r, c.g, c.b].map(function(v) {
    return Math.round(v * factor).toString(16).padStart(2, '0');
  }).join('');
}
function applyTextColor(hex) {
  document.documentElement.style.setProperty('--text-primary', hex);
  var rgb = hexToRgb(hex);
  document.documentElement.style.setProperty('--text-secondary', blendColor(rgb, 0.72));
  document.documentElement.style.setProperty('--text-tertiary', blendColor(rgb, 0.58));
  document.documentElement.style.setProperty('--text-muted', blendColor(rgb, 0.42));
}

function loadUserSettings() {
  var bgUrl = localStorage.getItem('chat-bg-url') || '';
  var accentColor = localStorage.getItem('chat-accent-color') || '';
  var textColor = localStorage.getItem('chat-text-color') || '';
  var fontSize = localStorage.getItem('chat-font-size') || '';
  var chatDensity = localStorage.getItem('chat-density') || '';
  var bgBlur = localStorage.getItem('chat-bg-blur') || '';
  if (bgUrl) {
    document.body.style.backgroundImage = 'url(' + bgUrl + ')';
    document.body.style.backgroundSize = 'cover';
    document.body.style.backgroundPosition = 'center';
  }
  if (bgBlur) {
    document.body.style.backdropFilter = 'blur(' + bgBlur + 'px)';
  }
  if (accentColor) {
    document.documentElement.style.setProperty('--accent', accentColor);
  }
  if (textColor) {
    applyTextColor(textColor);
  }
  if (fontSize) {
    document.documentElement.style.setProperty('font-size', fontSize + 'px');
  }
  if (chatDensity === 'compact') {
    document.documentElement.style.setProperty('--msg-padding', '2px 16px');
  } else if (chatDensity === 'cozy') {
    document.documentElement.style.setProperty('--msg-padding', '8px 16px');
  }
}

function showSettingsModal() {
  var overlay = document.createElement('div');
  overlay.className = 'gc-overlay';
  overlay.setAttribute('data-testid', 'settings-modal');
  var modal = document.createElement('div');
  modal.className = 'gc-modal';
  modal.style.maxHeight = '85vh';
  modal.style.overflowY = 'auto';
  var title = document.createElement('div');
  title.className = 'gc-modal-title';
  title.textContent = 'User Settings';
  modal.appendChild(title);

  function addRow(labelText, inputEl) {
    var row = document.createElement('div');
    row.className = 'settings-row';
    var lbl = document.createElement('span');
    lbl.className = 'settings-label';
    lbl.textContent = labelText;
    row.appendChild(lbl);
    row.appendChild(inputEl);
    modal.appendChild(row);
    return row;
  }

  var bgInput = document.createElement('input');
  bgInput.type = 'text';
  bgInput.placeholder = 'https://...';
  bgInput.value = localStorage.getItem('chat-bg-url') || '';
  bgInput.setAttribute('data-testid', 'input-settings-bg');
  bgInput.addEventListener('keydown', function(e) { e.stopPropagation(); });
  addRow('Background Image URL', bgInput);

  var blurInput = document.createElement('input');
  blurInput.type = 'range';
  blurInput.min = '0'; blurInput.max = '20'; blurInput.step = '1';
  blurInput.value = localStorage.getItem('chat-bg-blur') || '0';
  blurInput.style.cssText = 'flex:1;cursor:pointer;';
  blurInput.setAttribute('data-testid', 'input-settings-blur');
  addRow('Background Blur', blurInput);

  var accentInput = document.createElement('input');
  accentInput.type = 'color';
  accentInput.value = localStorage.getItem('chat-accent-color') || '#5865f2';
  accentInput.setAttribute('data-testid', 'input-settings-accent');
  addRow('Accent Color', accentInput);

  var textInput = document.createElement('input');
  textInput.type = 'color';
  textInput.value = localStorage.getItem('chat-text-color') || '#ffffff';
  textInput.setAttribute('data-testid', 'input-settings-text');
  addRow('Text Color', textInput);

  var fontSelect = document.createElement('select');
  fontSelect.style.cssText = 'padding:4px 8px;border-radius:4px;border:1px solid var(--border);background:var(--input-bg);color:var(--text-primary);font-size:13px;';
  fontSelect.setAttribute('data-testid', 'select-settings-font-size');
  [['Small', '13'], ['Normal', '14'], ['Large', '16'], ['Extra Large', '18']].forEach(function(opt) {
    var o = document.createElement('option');
    o.value = opt[1]; o.textContent = opt[0];
    fontSelect.appendChild(o);
  });
  fontSelect.value = localStorage.getItem('chat-font-size') || '14';
  addRow('Font Size', fontSelect);

  var densitySelect = document.createElement('select');
  densitySelect.style.cssText = 'padding:4px 8px;border-radius:4px;border:1px solid var(--border);background:var(--input-bg);color:var(--text-primary);font-size:13px;';
  densitySelect.setAttribute('data-testid', 'select-settings-density');
  [['Default', 'default'], ['Compact', 'compact'], ['Cozy', 'cozy']].forEach(function(opt) {
    var o = document.createElement('option');
    o.value = opt[1]; o.textContent = opt[0];
    densitySelect.appendChild(o);
  });
  densitySelect.value = localStorage.getItem('chat-density') || 'default';
  addRow('Chat Density', densitySelect);

  var soundCheck = document.createElement('input');
  soundCheck.type = 'checkbox';
  soundCheck.checked = localStorage.getItem('chat-sounds') !== 'off';
  soundCheck.style.cssText = 'width:18px;height:18px;cursor:pointer;';
  soundCheck.setAttribute('data-testid', 'input-settings-sounds');
  addRow('Notification Sounds', soundCheck);

  var btns = document.createElement('div');
  btns.className = 'gc-modal-btns';
  var resetBtn = document.createElement('button');
  resetBtn.className = 'gc-cancel';
  resetBtn.textContent = 'Reset All';
  resetBtn.setAttribute('data-testid', 'button-settings-reset');
  resetBtn.addEventListener('click', function() {
    ['chat-bg-url','chat-accent-color','chat-text-color','chat-font-size','chat-density','chat-bg-blur','chat-sounds'].forEach(function(k) {
      localStorage.removeItem(k);
    });
    document.body.style.backgroundImage = '';
    document.body.style.backdropFilter = '';
    document.documentElement.style.removeProperty('--accent');
    document.documentElement.style.removeProperty('--text-primary');
    document.documentElement.style.removeProperty('--text-secondary');
    document.documentElement.style.removeProperty('--text-tertiary');
    document.documentElement.style.removeProperty('--text-muted');
    document.documentElement.style.removeProperty('font-size');
    document.documentElement.style.removeProperty('--msg-padding');
    overlay.remove();
  });
  btns.appendChild(resetBtn);
  var saveBtn = document.createElement('button');
  saveBtn.className = 'gc-confirm';
  saveBtn.textContent = 'Save';
  saveBtn.setAttribute('data-testid', 'button-settings-save');
  saveBtn.addEventListener('click', function() {
    var bgUrl = bgInput.value.trim();
    var accent = accentInput.value;
    var textClr = textInput.value;
    var fSize = fontSelect.value;
    var density = densitySelect.value;
    var blur = blurInput.value;
    var sounds = soundCheck.checked;
    if (bgUrl) {
      localStorage.setItem('chat-bg-url', bgUrl);
      document.body.style.backgroundImage = 'url(' + bgUrl + ')';
      document.body.style.backgroundSize = 'cover';
      document.body.style.backgroundPosition = 'center';
    } else {
      localStorage.removeItem('chat-bg-url');
      document.body.style.backgroundImage = '';
    }
    localStorage.setItem('chat-bg-blur', blur);
    if (parseInt(blur) > 0) {
      document.body.style.backdropFilter = 'blur(' + blur + 'px)';
    } else {
      document.body.style.backdropFilter = '';
    }
    if (accent) {
      localStorage.setItem('chat-accent-color', accent);
      document.documentElement.style.setProperty('--accent', accent);
    }
    if (textClr) {
      localStorage.setItem('chat-text-color', textClr);
      applyTextColor(textClr);
    }
    localStorage.setItem('chat-font-size', fSize);
    document.documentElement.style.setProperty('font-size', fSize + 'px');
    localStorage.setItem('chat-density', density);
    if (density === 'compact') {
      document.documentElement.style.setProperty('--msg-padding', '2px 16px');
    } else if (density === 'cozy') {
      document.documentElement.style.setProperty('--msg-padding', '8px 16px');
    } else {
      document.documentElement.style.removeProperty('--msg-padding');
    }
    localStorage.setItem('chat-sounds', sounds ? 'on' : 'off');
    overlay.remove();
  });
  btns.appendChild(saveBtn);
  modal.appendChild(btns);
  overlay.appendChild(modal);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  document.body.appendChild(overlay);
}

function showLogsModal(logs, filterOpts) {
  var overlay = document.createElement('div');
  overlay.className = 'gc-overlay';
  overlay.setAttribute('data-testid', 'logs-modal');
  var modal = document.createElement('div');
  modal.className = 'gc-modal';
  modal.style.width = '600px';
  modal.style.maxHeight = '85vh';
  var title = document.createElement('div');
  title.className = 'gc-modal-title';
  title.textContent = 'Chat Logs (' + logs.length + ' entries)';
  modal.appendChild(title);

  var filterBar = document.createElement('div');
  filterBar.style.cssText = 'display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;';
  var typeFilter = document.createElement('select');
  typeFilter.style.cssText = 'padding:4px 8px;border-radius:4px;border:1px solid var(--border);background:var(--input-bg);color:var(--text-primary);font-size:12px;';
  ['all','chat','dm','gc'].forEach(function(t) {
    var opt = document.createElement('option');
    opt.value = t; opt.textContent = t === 'all' ? 'All Types' : t.toUpperCase();
    typeFilter.appendChild(opt);
  });
  filterBar.appendChild(typeFilter);
  var senderFilter = document.createElement('input');
  senderFilter.type = 'text';
  senderFilter.placeholder = 'Filter by sender...';
  senderFilter.style.cssText = 'flex:1;padding:4px 8px;border-radius:4px;border:1px solid var(--border);background:var(--input-bg);color:var(--text-primary);font-size:12px;outline:none;min-width:100px;';
  filterBar.appendChild(senderFilter);
  var searchFilter = document.createElement('input');
  searchFilter.type = 'text';
  searchFilter.placeholder = 'Search text...';
  searchFilter.style.cssText = 'flex:1;padding:4px 8px;border-radius:4px;border:1px solid var(--border);background:var(--input-bg);color:var(--text-primary);font-size:12px;outline:none;min-width:100px;';
  filterBar.appendChild(searchFilter);
  modal.appendChild(filterBar);

  var logList = document.createElement('div');
  logList.style.cssText = 'max-height:50vh;overflow-y:auto;font-size:12px;font-family:monospace;';

  function renderLogEntries() {
    logList.innerHTML = '';
    var ft = typeFilter.value;
    var fs = senderFilter.value.toLowerCase().trim();
    var fq = searchFilter.value.toLowerCase().trim();
    var filtered = logs.filter(function(e) {
      if (ft !== 'all' && e.type !== ft) return false;
      if (fs && (e.sender || '').toLowerCase().indexOf(fs) === -1) return false;
      if (fq && (e.text || '').toLowerCase().indexOf(fq) === -1) return false;
      return true;
    });
    if (filtered.length === 0) {
      logList.textContent = 'No matching logs.';
      logList.style.color = 'var(--text-muted)';
      return;
    }
    logList.style.color = '';
    filtered.forEach(function(entry) {
      var row = document.createElement('div');
      row.style.cssText = 'padding:3px 0;border-bottom:1px solid var(--border);color:var(--text-secondary);display:flex;align-items:flex-start;gap:6px;';
      var textSpan = document.createElement('span');
      textSpan.style.flex = '1';
      var ts = entry.timestamp || '';
      var label = '[' + ts + '] ';
      if (entry.type === 'chat') {
        label += '[CHAT] ' + (entry.sender || '') + ': ' + (entry.text || '');
      } else if (entry.type === 'dm') {
        label += '[DM] ' + (entry.sender || '') + ' -> ' + (entry.recipient || '') + ': ' + (entry.text || '');
      } else if (entry.type === 'gc') {
        label += '[GC:' + (entry.gc_name || '') + '] ' + (entry.sender || '') + ': ' + (entry.text || '');
      } else {
        label += JSON.stringify(entry);
      }
      textSpan.textContent = label;
      row.appendChild(textSpan);
      if (isOwner) {
        var delBtn = document.createElement('button');
        delBtn.style.cssText = 'background:none;border:none;color:var(--red);cursor:pointer;font-size:11px;flex-shrink:0;padding:0 4px;';
        delBtn.textContent = 'X';
        delBtn.title = 'Delete this log entry';
        delBtn.addEventListener('click', function() {
          ws.send(JSON.stringify({type: 'delete_log', log_id: entry.id}));
          logs = logs.filter(function(e) { return e.id !== entry.id; });
          renderLogEntries();
          title.textContent = 'Chat Logs (' + logs.length + ' entries)';
        });
        row.appendChild(delBtn);
      }
      logList.appendChild(row);
    });
  }

  typeFilter.addEventListener('change', renderLogEntries);
  senderFilter.addEventListener('input', renderLogEntries);
  searchFilter.addEventListener('input', renderLogEntries);
  [senderFilter, searchFilter].forEach(function(el) { el.addEventListener('keydown', function(e) { e.stopPropagation(); }); });
  renderLogEntries();

  modal.appendChild(logList);
  var btns = document.createElement('div');
  btns.className = 'gc-modal-btns';
  btns.style.marginTop = '12px';
  var closeBtn = document.createElement('button');
  closeBtn.className = 'gc-confirm';
  closeBtn.textContent = 'Close';
  closeBtn.addEventListener('click', function() { overlay.remove(); });
  btns.appendChild(closeBtn);
  modal.appendChild(btns);
  overlay.appendChild(modal);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  document.body.appendChild(overlay);
}

function showSuggestionsModal(suggestions) {
  var overlay = document.createElement('div');
  overlay.className = 'gc-overlay';
  var modal = document.createElement('div');
  modal.className = 'gc-modal';
  modal.style.width = '500px';
  var title = document.createElement('div');
  title.className = 'gc-modal-title';
  title.textContent = 'Suggestions (' + suggestions.length + ')';
  modal.appendChild(title);
  var list = document.createElement('div');
  list.style.cssText = 'max-height:50vh;overflow-y:auto;';
  if (suggestions.length === 0) {
    list.textContent = 'No suggestions yet.';
    list.style.cssText += 'color:var(--text-muted);font-size:13px;padding:8px 0;';
  } else {
    suggestions.forEach(function(s) {
      var row = document.createElement('div');
      row.style.cssText = 'padding:6px 0;border-bottom:1px solid var(--border);';
      var header = document.createElement('div');
      header.style.cssText = 'font-size:11px;color:var(--text-muted);';
      header.textContent = s.from + ' - ' + (s.timestamp || '');
      row.appendChild(header);
      var body = document.createElement('div');
      body.style.cssText = 'font-size:13px;color:var(--text-secondary);margin-top:2px;';
      body.textContent = s.text;
      row.appendChild(body);
      if (isOwner) {
        var delBtn = document.createElement('button');
        delBtn.style.cssText = 'background:none;border:none;color:var(--red);cursor:pointer;font-size:11px;margin-top:2px;';
        delBtn.textContent = 'Delete';
        delBtn.addEventListener('click', function() {
          ws.send(JSON.stringify({type: 'delete_suggestion', id: s.id}));
          row.remove();
        });
        row.appendChild(delBtn);
      }
      list.appendChild(row);
    });
  }
  modal.appendChild(list);
  var btns = document.createElement('div');
  btns.className = 'gc-modal-btns';
  btns.style.marginTop = '12px';
  var closeBtn = document.createElement('button');
  closeBtn.className = 'gc-confirm';
  closeBtn.textContent = 'Close';
  closeBtn.addEventListener('click', function() { overlay.remove(); });
  btns.appendChild(closeBtn);
  modal.appendChild(btns);
  overlay.appendChild(modal);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  document.body.appendChild(overlay);
}

function showAdminCreatorModal() {
  var overlay = document.createElement('div');
  overlay.className = 'gc-overlay';
  var modal = document.createElement('div');
  modal.className = 'gc-modal';
  var title = document.createElement('div');
  title.className = 'gc-modal-title';
  title.textContent = 'Create Admin Account';
  modal.appendChild(title);
  var nameLabel = document.createElement('div');
  nameLabel.style.cssText = 'font-size:12px;color:var(--text-muted);margin-bottom:4px;';
  nameLabel.textContent = 'Admin display name (permanent):';
  modal.appendChild(nameLabel);
  var nameInput = document.createElement('input');
  nameInput.className = 'gc-modal-input';
  nameInput.placeholder = 'Admin name...';
  nameInput.addEventListener('keydown', function(e) { e.stopPropagation(); });
  modal.appendChild(nameInput);
  var resultDiv = document.createElement('div');
  resultDiv.style.cssText = 'font-size:12px;color:var(--green);display:none;padding:8px;background:var(--bg-tertiary);border-radius:4px;margin-bottom:8px;word-break:break-all;';
  modal.appendChild(resultDiv);
  var btns = document.createElement('div');
  btns.className = 'gc-modal-btns';
  var cancelBtn = document.createElement('button');
  cancelBtn.className = 'gc-cancel';
  cancelBtn.textContent = 'Close';
  cancelBtn.addEventListener('click', function() { overlay.remove(); });
  btns.appendChild(cancelBtn);
  var createBtn = document.createElement('button');
  createBtn.className = 'gc-confirm';
  createBtn.textContent = 'Create';
  createBtn.addEventListener('click', function() {
    var n = nameInput.value.trim();
    if (!n) return;
    ws.send(JSON.stringify({type: 'create_admin', name: n}));
    createBtn.disabled = true;
  });
  btns.appendChild(createBtn);
  modal.appendChild(btns);
  overlay.appendChild(modal);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  document.body.appendChild(overlay);
  window._adminCreatorResult = function(data) {
    resultDiv.style.display = 'block';
    resultDiv.textContent = 'Admin key for "' + data.name + '": ' + data.key + ' (save this!)';
    createBtn.disabled = false;
    nameInput.value = '';
  };
}

function showManageAdminsModal(admins) {
  var overlay = document.createElement('div');
  overlay.className = 'gc-overlay';
  var modal = document.createElement('div');
  modal.className = 'gc-modal';
  modal.style.width = '450px';
  var title = document.createElement('div');
  title.className = 'gc-modal-title';
  title.textContent = 'Admin Accounts (' + admins.length + ')';
  modal.appendChild(title);
  var list = document.createElement('div');
  list.style.cssText = 'max-height:50vh;overflow-y:auto;';
  if (admins.length === 0) {
    list.textContent = 'No admin accounts created.';
    list.style.cssText += 'color:var(--text-muted);font-size:13px;padding:8px 0;';
  } else {
    admins.forEach(function(a) {
      var row = document.createElement('div');
      row.style.cssText = 'padding:6px 0;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;';
      var info = document.createElement('div');
      info.style.cssText = 'font-size:13px;color:var(--text-secondary);';
      info.textContent = a.name + ' (created: ' + a.created + ')';
      row.appendChild(info);
      var delBtn = document.createElement('button');
      delBtn.style.cssText = 'background:var(--bg-tertiary);border:none;color:var(--red);cursor:pointer;font-size:11px;padding:3px 8px;border-radius:4px;';
      delBtn.textContent = 'Remove';
      delBtn.addEventListener('click', function() {
        ws.send(JSON.stringify({type: 'remove_admin', key: a.key}));
        row.remove();
      });
      row.appendChild(delBtn);
      list.appendChild(row);
    });
  }
  modal.appendChild(list);
  var btns = document.createElement('div');
  btns.className = 'gc-modal-btns';
  btns.style.marginTop = '12px';
  var closeBtn = document.createElement('button');
  closeBtn.className = 'gc-confirm';
  closeBtn.textContent = 'Close';
  closeBtn.addEventListener('click', function() { overlay.remove(); });
  btns.appendChild(closeBtn);
  modal.appendChild(btns);
  overlay.appendChild(modal);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  document.body.appendChild(overlay);
}

var statusColors = { online: 'var(--green)', idle: '#f0b232', dnd: 'var(--red)', invisible: 'var(--text-muted)' };
var typingUsers = {};
var typingTimers = {};

function renderUsers(list) {
  onlineUsers = list.map(function(u) { return typeof u === 'string' ? u : u.name; });
  document.getElementById('userCount').textContent = list.length;
  var ul = document.getElementById('userList');
  ul.innerHTML = '';
  list.forEach(function(user) {
    var name = typeof user === 'string' ? user : user.name;
    var status = typeof user === 'string' ? 'online' : (user.status || 'online');
    var div = document.createElement('div');
    div.className = 'user-item';
    div.setAttribute('data-testid', 'user-item-' + name);
    var avatarWrap = document.createElement('div');
    avatarWrap.style.cssText = 'position:relative;flex-shrink:0;';
    var avatar = document.createElement('div');
    avatar.className = 'user-avatar';
    avatar.textContent = name.substring(0,2).toUpperCase();
    var statusDot = document.createElement('div');
    statusDot.style.cssText = 'position:absolute;bottom:-1px;right:-1px;width:10px;height:10px;border-radius:50%;border:2px solid var(--bg-secondary);background:' + (statusColors[status] || statusColors.online) + ';';
    avatarWrap.appendChild(avatar);
    avatarWrap.appendChild(statusDot);
    div.appendChild(avatarWrap);
    var nameEl = document.createElement('span');
    nameEl.className = 'user-name';
    nameEl.textContent = name + (name === myUsername ? ' (you)' : '');
    div.appendChild(nameEl);
    if (name !== myUsername) {
      div.style.cursor = 'pointer';
      div.title = 'Click to DM ' + name;
      div.addEventListener('click', function(e) {
        if (e.target.tagName === 'BUTTON') return;
        openDm(name);
      });
    }
    if (isOwner && name !== myUsername) {
      var actions = document.createElement('div');
      actions.className = 'user-actions';
      var kickBtn = document.createElement('button');
      kickBtn.style.cssText = 'padding:4px 8px;border:none;border-radius:4px;font-size:11px;font-weight:600;cursor:pointer;background:var(--bg-tertiary);color:var(--orange);';
      kickBtn.textContent = 'Kick';
      kickBtn.addEventListener('click', function(e) { e.stopPropagation(); ws.send(JSON.stringify({type:'kick',username:name})); });
      var banBtn = document.createElement('button');
      banBtn.style.cssText = 'padding:4px 8px;border:none;border-radius:4px;font-size:11px;font-weight:600;cursor:pointer;background:var(--bg-tertiary);color:var(--red);';
      banBtn.textContent = 'Ban';
      banBtn.addEventListener('click', function(e) { e.stopPropagation(); ws.send(JSON.stringify({type:'ban',username:name})); });
      actions.appendChild(kickBtn);
      actions.appendChild(banBtn);
      div.appendChild(actions);
    } else if (isStaffAdmin && name !== myUsername) {
      var actions = document.createElement('div');
      actions.className = 'user-actions';
      var kickBtn = document.createElement('button');
      kickBtn.style.cssText = 'padding:4px 8px;border:none;border-radius:4px;font-size:11px;font-weight:600;cursor:pointer;background:var(--bg-tertiary);color:var(--orange);';
      kickBtn.textContent = 'Kick';
      kickBtn.addEventListener('click', function(e) { e.stopPropagation(); ws.send(JSON.stringify({type:'kick',username:name})); });
      actions.appendChild(kickBtn);
      div.appendChild(actions);
    }
    ul.appendChild(div);
  });
}

function showTypingIndicator(username, channel) {
  if (username === myUsername) return;
  var key = channel + ':' + username;
  typingUsers[key] = true;
  if (typingTimers[key]) clearTimeout(typingTimers[key]);
  typingTimers[key] = setTimeout(function() {
    delete typingUsers[key];
    updateTypingDisplay();
  }, 3000);
  updateTypingDisplay();
}

function updateTypingDisplay() {
  var el = document.getElementById('typingIndicator');
  if (!el) return;
  var names = [];
  for (var key in typingUsers) {
    var parts = key.split(':');
    var ch = parts[0];
    var who = parts.slice(1).join(':');
    if (currentChannel === ch || (currentChannel === 'general' && ch === 'general')) {
      names.push(who);
    }
  }
  if (names.length === 0) {
    el.style.display = 'none';
  } else if (names.length === 1) {
    el.style.display = 'block';
    el.textContent = names[0] + ' is typing...';
  } else if (names.length === 2) {
    el.style.display = 'block';
    el.textContent = names[0] + ' and ' + names[1] + ' are typing...';
  } else {
    el.style.display = 'block';
    el.textContent = names.length + ' people are typing...';
  }
}

function openDm(target) {
  if (!dmMessages[target]) { dmMessages[target] = []; }
  switchChannel('dm:' + target);
  ws.send(JSON.stringify({type: 'dm_open', target: target}));
}

function renderBanned(list) {
  var section = document.getElementById('bannedSection');
  var el = document.getElementById('bannedList');
  if (!list || list.length === 0) { section.style.display = 'none'; return; }
  section.style.display = 'block';
  el.innerHTML = '';
  list.forEach(function(u) {
    var item = document.createElement('div');
    item.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:4px 0;';
    var nm = document.createElement('span');
    nm.style.cssText = 'font-size:13px;color:var(--text-muted);text-decoration:line-through;';
    nm.textContent = u;
    var unbanBtn = document.createElement('button');
    unbanBtn.style.cssText = 'padding:4px 8px;border:none;border-radius:4px;font-size:11px;font-weight:600;cursor:pointer;background:var(--bg-tertiary);color:var(--green);';
    unbanBtn.textContent = 'Unban';
    unbanBtn.addEventListener('click', function() { ws.send(JSON.stringify({type:'unban',username:u})); });
    item.appendChild(nm);
    item.appendChild(unbanBtn);
    el.appendChild(item);
  });
}

function renderDmSpy(pairs) {
  activeDmPairs = pairs;
  var section = document.getElementById('dmSpySection');
  var list = document.getElementById('dmSpyList');
  list.innerHTML = '';
  if (!isAdmin || !pairs || pairs.length === 0) { section.style.display = 'none'; return; }
  section.style.display = 'block';
  pairs.forEach(function(pair) {
    var item = document.createElement('div');
    item.className = 'dm-spy-item' + (currentChannel === 'spy:' + pair ? ' active' : '');
    item.setAttribute('data-testid', 'dm-spy-' + pair);
    var icon = document.createElement('span');
    icon.className = 'dm-spy-icon';
    icon.textContent = 'SPY';
    item.appendChild(icon);
    var label = document.createElement('span');
    label.textContent = pair;
    item.appendChild(label);
    item.addEventListener('click', function() {
      if (!dmMessages['spy:' + pair]) { dmMessages['spy:' + pair] = []; }
      switchChannel('spy:' + pair);
      ws.send(JSON.stringify({type: 'dm_spy_open', pair: pair}));
    });
    list.appendChild(item);
  });
}

function playNotifSound() {
  if (localStorage.getItem('chat-sounds') === 'off') return;
  try {
    var ctx = new (window.AudioContext || window.webkitAudioContext)();
    var osc = ctx.createOscillator();
    var gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 800;
    osc.type = 'sine';
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.15);
  } catch(e) {}
}

function handleMessage(data) {
  if (data.type === 'chat') {
    var time = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    generalMessages.push({sender: data.sender, text: data.text, admin: data.admin || false, time: time});
    if (currentChannel === 'general') renderMessages();
    if (data.sender !== myUsername) playNotifSound();
  } else if (data.type === 'system') {
    generalMessages.push({type: 'system', text: data.text});
    if (currentChannel === 'general') renderMessages();
  } else if (data.type === 'users') {
    renderUsers(data.list);
  } else if (data.type === 'banned_list') {
    renderBanned(data.list);
  } else if (data.type === 'dm') {
    var other;
    if (isAdmin) {
      var adminName = document.getElementById('nameInput').value.trim() || 'Admin';
      if (data.sender === adminName || data.admin) {
        other = data.recipient;
      } else {
        other = data.sender;
      }
    } else if (data.admin_dm) {
      other = 'Admin';
    } else {
      other = data.sender === myUsername ? data.recipient : data.sender;
    }
    if (!dmMessages[other]) { dmMessages[other] = []; }
    var time = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    dmMessages[other].push({sender: data.sender, text: data.text, admin: data.admin || false, isDm: true, time: time});
    if (currentChannel === 'dm:' + other) {
      renderMessages();
    } else {
      dmUnread[other] = (dmUnread[other] || 0) + 1;
      playNotifSound();
      renderDmChannels();
    }
  } else if (data.type === 'dm_history') {
    var target = data.target;
    dmMessages[target] = [];
    (data.messages || []).forEach(function(m) {
      dmMessages[target].push({sender: m.sender, text: m.text, admin: m.admin || false, isDm: true, time: m.time || ''});
    });
    if (currentChannel === 'dm:' + target) renderMessages();
  } else if (data.type === 'dm_spy') {
    var pair = data.pair;
    dmMessages['spy:' + pair] = [];
    (data.messages || []).forEach(function(m) {
      dmMessages['spy:' + pair].push({sender: m.sender, text: m.text, admin: m.admin || false, isDm: true, time: m.time || ''});
    });
    if (currentChannel === 'spy:' + pair) renderMessages();
  } else if (data.type === 'dm_spy_update') {
    var pair = data.pair;
    var time = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    if (!dmMessages['spy:' + pair]) dmMessages['spy:' + pair] = [];
    dmMessages['spy:' + pair].push({sender: data.sender, text: data.text, admin: data.admin || false, isDm: true, time: time});
    if (currentChannel === 'spy:' + pair) renderMessages();
  } else if (data.type === 'dm_cleanup') {
    var gone = data.username;
    if (dmMessages[gone]) {
      delete dmMessages[gone];
    }
    if (dmUnread[gone]) {
      delete dmUnread[gone];
    }
    Object.keys(dmMessages).forEach(function(k) {
      if (k.startsWith('spy:') && k.indexOf(gone) !== -1) {
        delete dmMessages[k];
      }
    });
    if (currentChannel === 'dm:' + gone || (currentChannel.startsWith('spy:') && currentChannel.indexOf(gone) !== -1)) {
      switchChannel('general');
    }
    renderDmChannels();
  } else if (data.type === 'dm_pairs') {
    renderDmSpy(data.pairs);
  } else if (data.type === 'logs_data') {
    showLogsModal(data.logs || []);
  } else if (data.type === 'suggestions_data') {
    showSuggestionsModal(data.suggestions || []);
  } else if (data.type === 'admins_data') {
    showManageAdminsModal(data.admins || []);
  } else if (data.type === 'admin_created') {
    if (window._adminCreatorResult) window._adminCreatorResult(data);
  } else if (data.type === 'suggestion_sent') {
    // silently handled
  } else if (data.type === 'new_suggestion') {
    var badge = document.getElementById('mailboxBadge');
    var c = parseInt(badge.textContent || '0') + 1;
    badge.textContent = c;
    badge.style.display = 'inline';
  } else if (data.type === 'typing') {
    showTypingIndicator(data.username, data.channel);
  } else if (data.type === 'gc_created') {
    gcList[data.gc.id] = data.gc;
    gcMessages[data.gc.id] = [];
    renderGcChannels();
    switchChannel('gc:' + data.gc.id);
  } else if (data.type === 'gc_invited') {
    gcList[data.gc.id] = data.gc;
    gcMessages[data.gc.id] = [];
    renderGcChannels();
  } else if (data.type === 'gc_message') {
    var gcId = data.gc_id;
    if (!gcMessages[gcId]) gcMessages[gcId] = [];
    var time = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    gcMessages[gcId].push({sender: data.sender, text: data.text, admin: data.admin || false, time: time});
    if (currentChannel === 'gc:' + gcId) {
      renderMessages();
    } else {
      gcUnread[gcId] = (gcUnread[gcId] || 0) + 1;
      renderGcChannels();
    }
  } else if (data.type === 'gc_history') {
    var gcId = data.gc_id;
    gcMessages[gcId] = [];
    (data.messages || []).forEach(function(m) {
      gcMessages[gcId].push({sender: m.sender, text: m.text, admin: m.admin || false, time: m.time || ''});
    });
    if (currentChannel === 'gc:' + gcId) renderMessages();
  } else if (data.type === 'error') {
    if (!myUsername && !isAdmin) {
      var err = document.getElementById('joinError');
      err.textContent = data.text;
      err.style.display = 'block';
    }
  } else if (data.type === 'bj_room_created' || data.type === 'bj_joined' || data.type === 'bj_state' || data.type === 'bj_error') {
    if (window._bjMultiHandler) window._bjMultiHandler(data);
  }
}

var adminConnected = false;
function connectOwner(token) {
  var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  adminConnected = false;
  ws = new WebSocket(protocol + '//' + location.host + '/owner-ws?token=' + token);
  ws.onopen = function() {
    adminConnected = true;
    isAdmin = true;
    isOwner = true;
    myRole = 'owner';
    document.getElementById('nameInput').style.display = 'block';
    document.getElementById('joinScreen').style.display = 'none';
    document.getElementById('chatScreen').style.display = 'flex';
    document.getElementById('logsSection').style.display = 'block';
    document.getElementById('mailboxSection').style.display = 'block';
    document.getElementById('adminCreatorBtn').style.display = 'flex';
    document.getElementById('manageAdminsBtn').style.display = 'flex';
    document.getElementById('msgInput').focus();
  };
  ws.onclose = function() {
    if (!adminConnected) {
      var err = document.getElementById('adminError');
      err.textContent = 'Invalid owner key or connection failed.';
      err.style.display = 'block';
      ws = null;
      return;
    }
    document.getElementById('sendBtn').disabled = true;
    document.getElementById('msgInput').disabled = true;
  };
  ws.onerror = function() {};
  ws.onmessage = function(event) { handleMessage(JSON.parse(event.data)); };
}

function connectStaffAdmin(key) {
  var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  var staffConnected = false;
  ws = new WebSocket(protocol + '//' + location.host + '/staff-ws?key=' + encodeURIComponent(key));
  ws.onopen = function() {
    staffConnected = true;
    isAdmin = true;
    isStaffAdmin = true;
    myRole = 'admin';
    document.getElementById('joinScreen').style.display = 'none';
    document.getElementById('chatScreen').style.display = 'flex';
    document.getElementById('logsSection').style.display = 'block';
    document.getElementById('suggestBoxSection').style.display = 'block';
    document.getElementById('msgInput').focus();
  };
  ws.onclose = function() {
    if (!staffConnected) {
      var err = document.getElementById('staffAdminError');
      err.textContent = 'Invalid admin key or connection failed.';
      err.style.display = 'block';
      ws = null;
      return;
    }
    document.getElementById('sendBtn').disabled = true;
    document.getElementById('msgInput').disabled = true;
  };
  ws.onerror = function() {};
  ws.onmessage = function(event) { handleMessage(JSON.parse(event.data)); };
}

function connectGuest(username) {
  var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(protocol + '//' + location.host + '/ws');
  ws.onopen = function() {
    ws.send(JSON.stringify({ type: 'join', username: username }));
    document.getElementById('suggestBoxSection').style.display = 'block';
  };
  ws.onmessage = function(event) { handleMessage(JSON.parse(event.data)); };
  ws.onclose = function() {
    if (myUsername) {
      document.getElementById('sendBtn').disabled = true;
      document.getElementById('msgInput').disabled = true;
    }
  };
}

var RESERVED = /admin|mod|owner/i;

document.getElementById('channelGeneral').addEventListener('click', function() {
  switchChannel('general');
});

document.getElementById('gcCreateBtn').addEventListener('click', function() {
  showGcCreateModal();
});

document.getElementById('viewLogsBtn').addEventListener('click', function() {
  ws.send(JSON.stringify({type: 'get_logs'}));
});

document.getElementById('settingsBtn').addEventListener('click', function() {
  showSettingsModal();
});

document.getElementById('adminCreatorBtn').addEventListener('click', function() {
  showAdminCreatorModal();
});

document.getElementById('manageAdminsBtn').addEventListener('click', function() {
  ws.send(JSON.stringify({type: 'get_admins'}));
});

document.getElementById('suggestionsBtn').addEventListener('click', function() {
  ws.send(JSON.stringify({type: 'get_suggestions'}));
});

document.getElementById('suggestSendBtn').addEventListener('click', function() {
  var input = document.getElementById('suggestInput');
  var text = input.value.trim();
  if (!text || !ws) return;
  ws.send(JSON.stringify({type: 'send_suggestion', text: text}));
  input.value = '';
});

document.getElementById('suggestInput').addEventListener('keydown', function(e) {
  e.stopPropagation();
  if (e.key === 'Enter') document.getElementById('suggestSendBtn').click();
});

loadUserSettings();

document.getElementById('joinBtn').addEventListener('click', function() {
  var name = document.getElementById('usernameInput').value.trim();
  var err = document.getElementById('joinError');
  if (!name) { err.textContent = 'Please enter a username.'; err.style.display = 'block'; return; }
  if (!/^[a-zA-Z0-9_-]{1,20}$/.test(name)) { err.textContent = 'Letters, numbers, _ and - only (1-20 chars).'; err.style.display = 'block'; return; }
  if (RESERVED.test(name)) { err.textContent = 'Username cannot contain "admin" or "mod".'; err.style.display = 'block'; return; }
  myUsername = name;
  document.getElementById('joinScreen').style.display = 'none';
  document.getElementById('chatScreen').style.display = 'flex';
  connectGuest(name);
  document.getElementById('msgInput').focus();
});

document.getElementById('usernameInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') document.getElementById('joinBtn').click();
});

document.getElementById('adminLoginBtn').addEventListener('click', function() {
  var token = document.getElementById('adminTokenInput').value.trim();
  var err = document.getElementById('adminError');
  if (!token) { err.textContent = 'Please enter the owner key.'; err.style.display = 'block'; return; }
  connectOwner(token);
});

document.getElementById('adminTokenInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') document.getElementById('adminLoginBtn').click();
});

document.getElementById('staffAdminLoginBtn').addEventListener('click', function() {
  var key = document.getElementById('staffAdminKeyInput').value.trim();
  var err = document.getElementById('staffAdminError');
  if (!key) { err.textContent = 'Please enter your admin key.'; err.style.display = 'block'; return; }
  connectStaffAdmin(key);
});

document.getElementById('staffAdminKeyInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') document.getElementById('staffAdminLoginBtn').click();
});

document.getElementById('sendBtn').addEventListener('click', function() {
  var input = document.getElementById('msgInput');
  var text = input.value.trim();
  if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
  if (currentChannel === 'general') {
    if (isAdmin) {
      var name = document.getElementById('nameInput').value.trim() || 'Admin';
      ws.send(JSON.stringify({ type: 'chat', text: text, name: name }));
    } else {
      ws.send(JSON.stringify({ type: 'chat', text: text }));
    }
  } else if (currentChannel.startsWith('dm:')) {
    var target = currentChannel.substring(3);
    if (isAdmin) {
      var name = document.getElementById('nameInput').value.trim() || 'Admin';
      ws.send(JSON.stringify({ type: 'dm_message', target: target, text: text, name: name }));
    } else {
      ws.send(JSON.stringify({ type: 'dm_message', target: target, text: text }));
    }
  } else if (currentChannel.startsWith('gc:')) {
    var gcId = currentChannel.substring(3);
    if (isAdmin) {
      var name = document.getElementById('nameInput').value.trim() || 'Admin';
      ws.send(JSON.stringify({ type: 'gc_message', gc_id: gcId, text: text, name: name }));
    } else {
      ws.send(JSON.stringify({ type: 'gc_message', gc_id: gcId, text: text }));
    }
  }
  input.value = '';
  input.focus();
});

document.getElementById('msgInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') document.getElementById('sendBtn').click();
});

var _e = function(cp) { return String.fromCodePoint(cp); };
var emojiCodes = {
  'Smileys': [0x1F600,0x1F603,0x1F604,0x1F601,0x1F606,0x1F605,0x1F602,0x1F923,0x1F60A,0x1F607,0x1F642,0x1F643,0x1F609,0x1F60C,0x1F60D,0x1F970,0x1F618,0x1F617,0x1F619,0x1F61A,0x1F60B,0x1F61B,0x1F61C,0x1F92A,0x1F61D,0x1F911,0x1F917,0x1F92D,0x1F92B,0x1F914,0x1F910,0x1F928,0x1F610,0x1F611,0x1F636,0x1F60F,0x1F612,0x1F644,0x1F62C,0x1F925,0x1F60E,0x1F913,0x1F615,0x1F61F,0x1F641,0x1F614,0x1F62E,0x1F62F,0x1F632,0x1F633,0x1F97A,0x1F628,0x1F630,0x1F625,0x1F622,0x1F62D,0x1F631,0x1F616,0x1F623,0x1F61E,0x1F613,0x1F629,0x1F624,0x1F620,0x1F621,0x1F92C,0x1F608,0x1F47F,0x1F480,0x1F4A9,0x1F921,0x1F47B,0x1F47D,0x1F47E,0x1F916],
  'Gestures': [0x1F44D,0x1F44E,0x1F44A,0x270A,0x1F91B,0x1F91C,0x1F44F,0x1F64C,0x1F450,0x1F932,0x1F91D,0x1F64F,0x270D,0x1F4AA,0x1F448,0x1F449,0x261D,0x1F446,0x1F447,0x270C,0x1F91E,0x1F596,0x1F918,0x1F919,0x1F590,0x270B,0x1F44B,0x1F44C,0x2764,0x1F9E1,0x1F49B,0x1F49A,0x1F499,0x1F49C,0x1F5A4,0x1F494,0x1F495,0x1F496,0x1F497,0x1F498,0x1F49D,0x1F49E,0x1F49F,0x1F48B],
  'Animals': [0x1F436,0x1F431,0x1F42D,0x1F439,0x1F430,0x1F98A,0x1F43B,0x1F43C,0x1F428,0x1F42F,0x1F981,0x1F42E,0x1F437,0x1F438,0x1F435,0x1F648,0x1F649,0x1F64A,0x1F412,0x1F414,0x1F427,0x1F426,0x1F985,0x1F986,0x1F989,0x1F987,0x1F40A,0x1F422,0x1F40D,0x1F432,0x1F409,0x1F433,0x1F42C,0x1F41F,0x1F419,0x1F41A,0x1F40C,0x1F98B,0x1F41B,0x1F41C,0x1F41D,0x1F41E,0x1F577,0x1F982],
  'Food': [0x1F34E,0x1F34F,0x1F350,0x1F34A,0x1F34B,0x1F34C,0x1F349,0x1F347,0x1F353,0x1F348,0x1F352,0x1F351,0x1F34D,0x1F965,0x1F95D,0x1F345,0x1F346,0x1F951,0x1F955,0x1F33D,0x1F336,0x1F344,0x1F35E,0x1F950,0x1F956,0x1F9C0,0x1F354,0x1F355,0x1F32D,0x1F32E,0x1F32F,0x1F959,0x1F373,0x1F958,0x1F372,0x1F35C,0x1F363,0x1F371,0x1F35F,0x1F370,0x1F382,0x1F366,0x1F367,0x1F368,0x1F369,0x1F36A,0x1F36B,0x1F36C,0x1F36D,0x2615,0x1F375,0x1F37A,0x1F37B,0x1F377,0x1F378,0x1F379],
  'Activities': [0x26BD,0x1F3C0,0x1F3C8,0x26BE,0x1F3BE,0x1F3B1,0x1F3D3,0x1F3AF,0x1F3A3,0x1F3BF,0x1F3AE,0x1F3B2,0x1F9E9,0x2660,0x2665,0x2666,0x2663,0x1F3AD,0x1F3A8,0x1F3B5,0x1F3B6,0x1F3B9,0x1F3B7,0x1F3BA,0x1F3B8],
  'Objects': [0x1F4F1,0x1F4BB,0x1F4F7,0x1F4F9,0x1F4FA,0x1F4A1,0x1F526,0x1F4B0,0x1F4B3,0x1F48E,0x1F527,0x1F528,0x2699,0x1F52B,0x1F52A,0x1F52E,0x1F52D,0x1F52C,0x1F48A,0x1F489,0x1F511,0x1F6AA,0x1F6CF],
  'Symbols': [0x2764,0x1F525,0x2B50,0x1F31F,0x26A1,0x2728,0x1F386,0x1F387,0x1F388,0x1F389,0x1F38A,0x2714,0x274C,0x2753,0x2757,0x1F4AF,0x26D4,0x1F6AB,0x1F6D1,0x267B,0x2705,0x2795,0x2796,0x1F4B2,0x1F440]
};
var emojiData = {};
var emojiNameMap = {};
(function() {
  var names = {0x1F600:'grinning',0x1F603:'smiley',0x1F604:'smile',0x1F601:'grin',0x1F606:'laughing',0x1F605:'sweat smile',0x1F602:'joy',0x1F923:'rofl',0x1F60A:'blush',0x1F607:'innocent',0x1F642:'slight smile',0x1F643:'upside down',0x1F609:'wink',0x1F60C:'relieved',0x1F60D:'heart eyes',0x1F970:'hearts',0x1F618:'kissing heart',0x1F60B:'yum',0x1F61B:'tongue',0x1F61C:'wink tongue',0x1F92A:'zany',0x1F914:'thinking',0x1F910:'zipper mouth',0x1F60F:'smirk',0x1F612:'unamused',0x1F644:'eye roll',0x1F60E:'sunglasses',0x1F913:'nerd',0x1F641:'frown',0x1F614:'pensive',0x1F622:'cry',0x1F62D:'sob',0x1F631:'scream',0x1F620:'angry',0x1F621:'rage',0x1F92C:'cursing',0x1F608:'devil',0x1F47F:'imp',0x1F480:'skull',0x1F4A9:'poop',0x1F921:'clown',0x1F47B:'ghost',0x1F47D:'alien',0x1F916:'robot',0x1F44D:'thumbs up',0x1F44E:'thumbs down',0x1F44A:'fist',0x1F44F:'clap',0x1F64C:'raised hands',0x1F64F:'pray',0x1F4AA:'muscle',0x270C:'victory hand',0x1F918:'rock',0x1F44C:'ok',0x1F44B:'wave',0x2764:'heart',0x1F525:'fire',0x2B50:'star',0x1F4AF:'100',0x1F389:'party',0x2714:'check',0x274C:'x',0x1F440:'eyes',0x1F436:'dog',0x1F431:'cat',0x1F42D:'mouse',0x1F430:'rabbit',0x1F98A:'fox',0x1F43C:'panda',0x1F981:'lion',0x1F34E:'apple',0x1F354:'burger',0x1F355:'pizza',0x1F382:'cake',0x2615:'coffee',0x1F37A:'beer',0x26BD:'soccer',0x1F3C0:'basketball',0x1F3AE:'game',0x1F3B5:'music',0x1F3A8:'art',0x1F4F1:'phone',0x1F4BB:'laptop',0x1F4A1:'bulb',0x1F511:'key',0x2728:'sparkles',0x1F388:'balloon',0x2705:'green check',0x26A1:'lightning',0x1F48E:'gem',0x1F527:'wrench',0x2699:'gear'};
  Object.keys(emojiCodes).forEach(function(cat) {
    emojiData[cat] = emojiCodes[cat].map(function(cp) { return _e(cp); });
  });
  Object.keys(names).forEach(function(cp) {
    emojiNameMap[_e(parseInt(cp))] = names[cp];
  });
})();

var currentEmojiCat = 'Smileys';

function renderEmojiPicker(filter) {
  var grid = document.getElementById('emojiGrid');
  grid.innerHTML = '';
  var cats = filter ? Object.keys(emojiData) : [currentEmojiCat];
  cats.forEach(function(cat) {
    emojiData[cat].forEach(function(em) {
      if (filter) {
        var name = emojiNameMap[em] || '';
        if (name.indexOf(filter.toLowerCase()) === -1) return;
      }
      var btn = document.createElement('button');
      btn.className = 'emoji-item';
      btn.textContent = em;
      btn.title = emojiNameMap[em] || '';
      btn.type = 'button';
      btn.addEventListener('click', function() {
        var input = document.getElementById('msgInput');
        var pos = input.selectionStart || input.value.length;
        input.value = input.value.substring(0, pos) + em + input.value.substring(pos);
        input.focus();
        input.selectionStart = input.selectionEnd = pos + em.length;
      });
      grid.appendChild(btn);
    });
  });
}

function renderEmojiCatBar() {
  var bar = document.getElementById('emojiCatBar');
  bar.innerHTML = '';
  var catIcons = {'Smileys':0x1F600,'Gestures':0x1F44D,'Animals':0x1F436,'Food':0x1F34E,'Activities':0x26BD,'Objects':0x1F4F1,'Symbols':0x2764};
  Object.keys(emojiData).forEach(function(cat) {
    var btn = document.createElement('button');
    btn.className = 'emoji-cat-btn' + (cat === currentEmojiCat ? ' active' : '');
    btn.type = 'button';
    btn.textContent = catIcons[cat] ? _e(catIcons[cat]) : cat.charAt(0);
    btn.title = cat;
    btn.addEventListener('click', function() {
      currentEmojiCat = cat;
      document.getElementById('emojiSearch').value = '';
      renderEmojiCatBar();
      renderEmojiPicker('');
    });
    bar.appendChild(btn);
  });
}

document.getElementById('emojiBtn').addEventListener('click', function(e) {
  e.stopPropagation();
  var panel = document.getElementById('emojiPanel');
  var isOpen = panel.classList.contains('open');
  if (isOpen) {
    panel.classList.remove('open');
  } else {
    renderEmojiCatBar();
    renderEmojiPicker('');
    panel.classList.add('open');
    document.getElementById('emojiSearch').focus();
  }
});

document.getElementById('emojiSearch').addEventListener('input', function() {
  var q = this.value.trim();
  renderEmojiPicker(q);
});

document.getElementById('emojiSearch').addEventListener('keydown', function(e) {
  e.stopPropagation();
});

document.addEventListener('click', function(e) {
  var panel = document.getElementById('emojiPanel');
  var btn = document.getElementById('emojiBtn');
  if (!panel.contains(e.target) && e.target !== btn) {
    panel.classList.remove('open');
  }
});

var tabs = [];
var activeTabId = 'chat';
var tabIdCounter = 0;

function createTabId() { return 'tab-' + (++tabIdCounter); }

function findTabByType(type) {
  for (var i = 0; i < tabs.length; i++) {
    if (tabs[i].type === type) return tabs[i];
  }
  return null;
}

function renderTabBar() {
  var bar = document.getElementById('tabItems');
  bar.innerHTML = '';
  tabs.forEach(function(tab) {
    var item = document.createElement('div');
    item.className = 'tab-item' + (tab.id === activeTabId ? ' active' : '');
    item.setAttribute('data-testid', 'tab-' + tab.id);

    var icon = document.createElement('span');
    icon.className = 'tab-icon';
    if (tab.type === 'chat') icon.textContent = '#';
    else if (tab.type === 'games') icon.textContent = 'G';
    else icon.textContent = '+';
    item.appendChild(icon);

    var label = document.createElement('span');
    label.textContent = tab.label;
    item.appendChild(label);

    var closeBtn = document.createElement('button');
    closeBtn.className = 'tab-close';
    closeBtn.textContent = '\u00D7';
    closeBtn.setAttribute('data-testid', 'button-close-tab-' + tab.id);
    closeBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      closeTab(tab.id);
    });
    item.appendChild(closeBtn);

    item.addEventListener('click', function() { switchTab(tab.id); });
    bar.appendChild(item);
  });
}

function switchTab(id) {
  activeTabId = id;
  var contents = document.getElementById('tabContents').children;
  for (var i = 0; i < contents.length; i++) {
    contents[i].classList.remove('active');
  }
  var el = document.getElementById('tabContent-' + id);
  if (el) el.classList.add('active');
  renderTabBar();
}

function closeTab(id) {
  var idx = -1;
  for (var i = 0; i < tabs.length; i++) {
    if (tabs[i].id === id) { idx = i; break; }
  }
  if (idx === -1) return;
  tabs.splice(idx, 1);
  var el = document.getElementById('tabContent-' + id);
  if (el) el.remove();
  if (tabs.length === 0) {
    openNewTab();
    return;
  }
  if (activeTabId === id) {
    var newIdx = Math.min(idx, tabs.length - 1);
    switchTab(tabs[newIdx].id);
  } else {
    renderTabBar();
  }
}

var allNewTabItems = [
  { id: 'chat', type: 'chat', name: 'Chat', desc: 'Group chat and direct messages', badge: '' },
  { id: 'games', type: 'games', name: 'Games', desc: 'Browse and play mini-games', badge: '' },
];

function openNewTab() {
  var existing = findTabByType('newtab');
  if (existing) { switchTab(existing.id); return; }
  var id = createTabId();
  tabs.push({ id: id, type: 'newtab', label: 'New Tab' });

  var content = document.createElement('div');
  content.className = 'tab-content';
  content.id = 'tabContent-' + id;

  var page = document.createElement('div');
  page.className = 'newtab-page';

  var searchDiv = document.createElement('div');
  searchDiv.className = 'newtab-search';
  var searchInput = document.createElement('input');
  searchInput.type = 'text';
  searchInput.placeholder = 'Search...';
  searchInput.setAttribute('data-testid', 'input-newtab-search');
  searchDiv.appendChild(searchInput);
  page.appendChild(searchDiv);

  var listDiv = document.createElement('div');
  listDiv.className = 'newtab-list';
  page.appendChild(listDiv);

  function renderList(filter) {
    listDiv.innerHTML = '';
    var q = (filter || '').toLowerCase();
    var found = false;
    allNewTabItems.forEach(function(item) {
      if (q && item.name.toLowerCase().indexOf(q) === -1 && item.desc.toLowerCase().indexOf(q) === -1) return;
      found = true;
      var row = document.createElement('div');
      row.className = 'newtab-item';
      row.setAttribute('data-testid', 'newtab-option-' + item.id);
      var info = document.createElement('div');
      info.className = 'newtab-item-info';
      var nameEl = document.createElement('div');
      nameEl.className = 'newtab-item-name';
      nameEl.textContent = item.name;
      info.appendChild(nameEl);
      var descEl = document.createElement('div');
      descEl.className = 'newtab-item-desc';
      descEl.textContent = item.desc;
      info.appendChild(descEl);
      row.appendChild(info);
      if (item.badge) {
        var badge = document.createElement('span');
        badge.className = 'newtab-item-badge';
        badge.textContent = item.badge;
        row.appendChild(badge);
      }
      row.addEventListener('click', function() {
        if (item.type === 'chat') {
          var chatTab = findTabByType('chat');
          if (chatTab) { closeTab(id); switchTab(chatTab.id); }
          else { convertTabToChat(id); }
        } else if (item.type === 'games') {
          var gamesTab = findTabByType('games');
          if (gamesTab) { closeTab(id); switchTab(gamesTab.id); }
          else { convertTabToGames(id); }
        }
      });
      listDiv.appendChild(row);
    });
    if (!found) {
      var empty = document.createElement('div');
      empty.className = 'newtab-empty';
      empty.textContent = 'No results found';
      listDiv.appendChild(empty);
    }
  }

  searchInput.addEventListener('input', function() { renderList(this.value); });
  searchInput.addEventListener('keydown', function(e) { e.stopPropagation(); });
  renderList('');

  content.appendChild(page);
  document.getElementById('tabContents').appendChild(content);
  switchTab(id);
}

function convertTabToChat(tabId) {
  for (var i = 0; i < tabs.length; i++) {
    if (tabs[i].id === tabId) {
      tabs[i].type = 'chat';
      tabs[i].label = 'Chat';
      break;
    }
  }
  var el = document.getElementById('tabContent-' + tabId);
  el.innerHTML = '';

  var chatArea = document.createElement('div');
  chatArea.className = 'chat-area';

  var channelHeader = document.createElement('div');
  channelHeader.className = 'channel-header';
  channelHeader.id = 'channelHeaderBar';
  channelHeader.innerHTML = '<span class="channel-icon">#</span> <span id="channelName" data-testid="text-channel-name">General</span>';
  chatArea.appendChild(channelHeader);

  var messagesDiv = document.createElement('div');
  messagesDiv.id = 'messages';
  messagesDiv.setAttribute('data-testid', 'list-messages');
  chatArea.appendChild(messagesDiv);

  var inputBar = document.createElement('div');
  inputBar.className = 'input-bar';

  var nameInput = document.createElement('input');
  nameInput.type = 'text';
  nameInput.id = 'nameInput';
  nameInput.setAttribute('data-testid', 'input-admin-name');
  nameInput.placeholder = 'Your name';
  nameInput.value = 'Admin';
  nameInput.style.cssText = 'display:none;width:140px;flex:unset;';
  if (isAdmin) nameInput.style.display = 'block';
  inputBar.appendChild(nameInput);

  var msgInput = document.createElement('input');
  msgInput.type = 'text';
  msgInput.id = 'msgInput';
  msgInput.setAttribute('data-testid', 'input-message');
  msgInput.placeholder = 'Type a message...';
  msgInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') document.getElementById('sendBtn').click();
  });
  var lastTypingSent = 0;
  msgInput.addEventListener('input', function() {
    var now = Date.now();
    if (now - lastTypingSent > 2000 && ws && ws.readyState === WebSocket.OPEN) {
      lastTypingSent = now;
      ws.send(JSON.stringify({type: 'typing', channel: currentChannel}));
    }
  });
  inputBar.appendChild(msgInput);

  var emojiContainer = document.createElement('div');
  emojiContainer.className = 'emoji-picker-container';
  var emojiBtn = document.createElement('button');
  emojiBtn.className = 'emoji-picker-btn';
  emojiBtn.id = 'emojiBtn';
  emojiBtn.setAttribute('data-testid', 'button-emoji');
  emojiBtn.type = 'button';
  emojiBtn.title = 'Emoji picker';
  emojiBtn.textContent = ':)';
  var emojiPanel = document.createElement('div');
  emojiPanel.className = 'emoji-panel';
  emojiPanel.id = 'emojiPanel';
  var emojiSearchInput = document.createElement('input');
  emojiSearchInput.type = 'text';
  emojiSearchInput.className = 'emoji-search';
  emojiSearchInput.id = 'emojiSearch';
  emojiSearchInput.setAttribute('data-testid', 'input-emoji-search');
  emojiSearchInput.placeholder = 'Search emojis...';
  emojiPanel.appendChild(emojiSearchInput);
  var catBar = document.createElement('div');
  catBar.className = 'emoji-panel-header';
  catBar.id = 'emojiCatBar';
  emojiPanel.appendChild(catBar);
  var emojiGridEl = document.createElement('div');
  emojiGridEl.className = 'emoji-grid';
  emojiGridEl.id = 'emojiGrid';
  emojiGridEl.setAttribute('data-testid', 'grid-emoji');
  emojiPanel.appendChild(emojiGridEl);
  emojiContainer.appendChild(emojiBtn);
  emojiContainer.appendChild(emojiPanel);
  inputBar.appendChild(emojiContainer);

  var sendBtn = document.createElement('button');
  sendBtn.id = 'sendBtn';
  sendBtn.setAttribute('data-testid', 'button-send');
  sendBtn.textContent = 'Send';
  sendBtn.addEventListener('click', function() {
    var input = document.getElementById('msgInput');
    var text = input.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    if (currentChannel === 'general') {
      if (isAdmin) {
        var name = document.getElementById('nameInput').value.trim() || 'Admin';
        ws.send(JSON.stringify({ type: 'chat', text: text, name: name }));
      } else {
        ws.send(JSON.stringify({ type: 'chat', text: text }));
      }
    } else if (currentChannel.startsWith('dm:')) {
      var target = currentChannel.substring(3);
      if (isAdmin) {
        var name = document.getElementById('nameInput').value.trim() || 'Admin';
        ws.send(JSON.stringify({ type: 'dm_message', target: target, text: text, name: name }));
      } else {
        ws.send(JSON.stringify({ type: 'dm_message', target: target, text: text }));
      }
    }
    input.value = '';
    input.focus();
  });
  inputBar.appendChild(sendBtn);
  var typingIndicator = document.createElement('div');
  typingIndicator.id = 'typingIndicator';
  typingIndicator.style.cssText = 'display:none;padding:2px 16px;font-size:12px;color:var(--text-muted);font-style:italic;';
  typingIndicator.setAttribute('data-testid', 'text-typing-indicator');
  chatArea.appendChild(typingIndicator);
  chatArea.appendChild(inputBar);
  el.appendChild(chatArea);

  bindEmojiPicker();
  renderMessages();
  switchChannel(currentChannel);
  renderTabBar();
}

function bindEmojiPicker() {
  var emojiBtn = document.getElementById('emojiBtn');
  var emojiPanel = document.getElementById('emojiPanel');
  var emojiSearch = document.getElementById('emojiSearch');
  if (!emojiBtn) return;
  emojiBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    var isOpen = emojiPanel.classList.contains('open');
    if (isOpen) { emojiPanel.classList.remove('open'); }
    else { renderEmojiCatBar(); renderEmojiPicker(''); emojiPanel.classList.add('open'); emojiSearch.focus(); }
  });
  emojiSearch.addEventListener('input', function() { renderEmojiPicker(this.value.trim()); });
  emojiSearch.addEventListener('keydown', function(e) { e.stopPropagation(); });
}

function convertTabToGames(tabId) {
  for (var i = 0; i < tabs.length; i++) {
    if (tabs[i].id === tabId) {
      tabs[i].type = 'games';
      tabs[i].label = 'Games';
      break;
    }
  }
  var el = document.getElementById('tabContent-' + tabId);
  el.innerHTML = '';
  buildGamesHub(el);
  renderTabBar();
}

var allGames = [
  { id: 'tictactoe', name: 'Tic-Tac-Toe', desc: 'Classic strategy game, play X vs O against the computer', badge: 'single' },
  { id: 'snake', name: 'Snake', desc: 'Navigate the snake to eat food and grow without hitting walls', badge: 'single' },
  { id: 'memory', name: 'Memory Match', desc: 'Flip cards and find all matching pairs with fewest moves', badge: 'single' },
  { id: 'blackjack', name: 'Blackjack', desc: 'Beat the dealer by getting as close to 21 as possible', badge: 'single' },
  { id: 'blackjack_multi', name: 'Blackjack (Multiplayer)', desc: 'Play blackjack with friends in real-time rooms', badge: 'multi' },
  { id: 'minesweeper', name: 'Minesweeper', desc: 'Clear the minefield without detonating any hidden mines', badge: 'single' },
  { id: 'war', name: 'War', desc: 'Classic card game - flip cards and battle for the whole deck', badge: 'single' },
  { id: 'crazy_eights', name: 'Crazy Eights', desc: 'Match suits or ranks, play wild 8s to change the suit', badge: 'single' },
  { id: 'solitaire', name: 'Solitaire', desc: 'Classic Klondike solitaire card game with drag and click controls', badge: 'single' },
  { id: 'checkers', name: 'Checkers', desc: 'Play checkers against a simple AI opponent with kings and multi-jumps', badge: 'single' },
  { id: 'twenty_fortyeight', name: '2048', desc: 'Slide and merge tiles to reach the 2048 tile', badge: 'single' },
  { id: 'hangman', name: 'Hangman', desc: 'Guess the hidden word one letter at a time before the hangman is complete', badge: 'single' },
];

function buildGamesHub(container) {
  var hub = document.createElement('div');
  hub.className = 'games-hub';

  var header = document.createElement('div');
  header.className = 'games-header';
  header.textContent = 'Games';
  hub.appendChild(header);

  var searchDiv = document.createElement('div');
  searchDiv.className = 'games-search';
  var searchInput = document.createElement('input');
  searchInput.type = 'text';
  searchInput.placeholder = 'Search games...';
  searchInput.setAttribute('data-testid', 'input-games-search');
  searchDiv.appendChild(searchInput);
  hub.appendChild(searchDiv);

  var listDiv = document.createElement('div');
  listDiv.className = 'games-list';
  hub.appendChild(listDiv);

  function makeGameRow(g) {
    var row = document.createElement('div');
    row.className = 'game-item';
    row.setAttribute('data-testid', 'game-card-' + g.id);
    var info = document.createElement('div');
    info.className = 'game-item-info';
    var nameEl = document.createElement('div');
    nameEl.className = 'game-item-name';
    nameEl.textContent = g.name;
    info.appendChild(nameEl);
    var descEl = document.createElement('div');
    descEl.className = 'game-item-desc';
    descEl.textContent = g.desc;
    info.appendChild(descEl);
    row.appendChild(info);
    row.addEventListener('click', function() {
      showGame(container, g.id);
    });
    return row;
  }

  function renderGames(filter) {
    listDiv.innerHTML = '';
    var q = (filter || '').toLowerCase();
    var singles = allGames.filter(function(g) {
      if (g.badge !== 'single') return false;
      if (q && g.name.toLowerCase().indexOf(q) === -1 && g.desc.toLowerCase().indexOf(q) === -1) return false;
      return true;
    });
    var multis = allGames.filter(function(g) {
      if (g.badge !== 'multi') return false;
      if (q && g.name.toLowerCase().indexOf(q) === -1 && g.desc.toLowerCase().indexOf(q) === -1) return false;
      return true;
    });
    if (singles.length === 0 && multis.length === 0) {
      var empty = document.createElement('div');
      empty.className = 'newtab-empty';
      empty.textContent = 'No games found';
      listDiv.appendChild(empty);
      return;
    }
    if (singles.length > 0) {
      var sLabel = document.createElement('div');
      sLabel.className = 'newtab-section-label';
      sLabel.textContent = 'Single Player';
      listDiv.appendChild(sLabel);
      singles.forEach(function(g) { listDiv.appendChild(makeGameRow(g)); });
    }
    if (multis.length > 0) {
      var mLabel = document.createElement('div');
      mLabel.className = 'newtab-section-label';
      mLabel.textContent = 'Multiplayer';
      listDiv.appendChild(mLabel);
      multis.forEach(function(g) { listDiv.appendChild(makeGameRow(g)); });
    }
  }

  searchInput.addEventListener('input', function() { renderGames(this.value); });
  searchInput.addEventListener('keydown', function(e) { e.stopPropagation(); });
  renderGames('');

  container.appendChild(hub);
}

var gameNames = {
  tictactoe: 'Tic-Tac-Toe', snake: 'Snake', memory: 'Memory Match',
  blackjack: 'Blackjack', blackjack_multi: 'Blackjack (Multiplayer)', minesweeper: 'Minesweeper',
  solitaire: 'Solitaire', checkers: 'Checkers', hangman: 'Hangman',
  war: 'War', crazy_eights: 'Crazy Eights', twenty_fortyeight: '2048'
};

function showGame(container, gameId) {
  container.innerHTML = '';
  var hub = document.createElement('div');
  hub.className = 'games-hub';

  var header = document.createElement('div');
  header.className = 'games-header';
  var backBtn = document.createElement('button');
  backBtn.className = 'back-btn';
  backBtn.textContent = 'Back';
  backBtn.setAttribute('data-testid', 'button-back-games');
  backBtn.addEventListener('click', function() {
    container.innerHTML = '';
    buildGamesHub(container);
  });
  header.appendChild(backBtn);
  var titleSpan = document.createElement('span');
  titleSpan.textContent = gameNames[gameId] || gameId;
  header.appendChild(titleSpan);
  hub.appendChild(header);

  var playArea = document.createElement('div');
  playArea.className = 'game-play-area';
  hub.appendChild(playArea);
  container.appendChild(hub);

  if (gameId === 'tictactoe') initTicTacToe(playArea);
  else if (gameId === 'snake') initSnake(playArea);
  else if (gameId === 'memory') initMemory(playArea);
  else if (gameId === 'blackjack') initBlackjack(playArea);
  else if (gameId === 'blackjack_multi') initBlackjackMulti(playArea);
  else if (gameId === 'minesweeper') initMinesweeper(playArea);
  else if (gameId === 'solitaire') initSolitaire(playArea);
  else if (gameId === 'checkers') initCheckers(playArea);
  else if (gameId === 'hangman') initHangman(playArea);
  else if (gameId === 'war') initWar(playArea);
  else if (gameId === 'crazy_eights') initCrazyEights(playArea);
  else if (gameId === 'twenty_fortyeight') init2048(playArea);
}

""" + tictactoe.get_js() + snake.get_js() + memory.get_js() + blackjack.get_js() + blackjack_multi.get_js() + minesweeper.get_js() + solitaire.get_js() + checkers.get_js() + hangman.get_js() + war.get_js() + crazy_eights.get_js() + twenty_fortyeight.get_js() + r"""

tabs.push({ id: 'chat', type: 'chat', label: 'Chat' });
renderTabBar();
bindEmojiPicker();

document.getElementById('newTabBtn').addEventListener('click', function() {
  openNewTab();
});
</script>
</body>
</html>"""


async def broadcast_to_clients(message):
    data = json.dumps(message)
    tasks = []
    for ws_conn in list(connected.keys()):
        try:
            tasks.append(ws_conn.send_str(data))
        except Exception:
            pass
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def send_to_admin(message):
    global admin_ws
    if admin_ws is not None:
        try:
            await admin_ws.send_str(json.dumps(message))
        except Exception:
            admin_ws = None


async def broadcast_to_staff(message):
    msg_str = json.dumps(message) if isinstance(message, dict) else message
    for sws in list(staff_connected.keys()):
        try:
            await sws.send_str(msg_str)
        except Exception:
            pass


async def broadcast_all(message):
    await broadcast_to_clients(message)
    await send_to_admin(message)
    await broadcast_to_staff(message)


def user_list():
    users = []
    for info in connected.values():
        users.append({"name": info["username"], "status": info.get("status", "online")})
    for sinfo in staff_connected.values():
        if sinfo["username"] not in [u["name"] for u in users]:
            users.append({"name": sinfo["username"], "status": sinfo.get("status", "online")})
    return users


async def send_user_list():
    users = user_list()
    msg = {"type": "users", "list": users}
    await broadcast_to_clients(msg)
    await send_to_admin(msg)
    await broadcast_to_staff(msg)
    await send_to_admin({"type": "banned_list", "list": list(banned_users)})


async def handle_chat_page(request):
    return web.Response(text=get_client_html(), content_type="text/html")


async def handle_admin_page(request):
    token = ""
    if request.method == "POST":
        data = await request.post()
        token = data.get("token", "")
    else:
        token = request.query.get("token", "")
    if token == OWNER_TOKEN:
        return web.Response(text=get_admin_html(token), content_type="text/html")
    login_html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Login</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'gg sans', 'Noto Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  background: #1e1f22; display: flex; align-items: center; justify-content: center;
  min-height: 100vh; color: #f2f3f5; }
.login-box { background: #313338; border-radius: 8px;
  padding: 32px; max-width: 400px; width: 90%; }
h2 { margin-bottom: 8px; font-size: 22px; font-weight: 700; }
p { color: #b5bac1; margin-bottom: 20px; font-size: 14px; }
label { display: block; font-size: 12px; font-weight: 700; margin-bottom: 6px;
  color: #b5bac1; text-transform: uppercase; letter-spacing: 0.5px; }
input { width: 100%; padding: 10px 12px; border: none; border-radius: 4px;
  font-size: 14px; margin-bottom: 16px; background: #1e1f22; color: #f2f3f5; outline: none; }
input:focus { outline: 2px solid #5865f2; }
button { width: 100%; padding: 10px; background: #5865f2; color: #fff; border: none;
  border-radius: 4px; font-size: 14px; font-weight: 600; cursor: pointer; }
button:hover { background: #4752c4; }
.error { color: #ed4245; font-size: 13px; margin-bottom: 10px; display: none; }
</style>
</head>
<body>
<div class="login-box">
  <h2>Admin Login</h2>
  <p>Enter the admin token from the server console.</p>
  <div class="error" id="errorMsg">Invalid token. Please try again.</div>
  <label for="tokenInput">Admin Token</label>
  <input type="password" id="tokenInput" data-testid="input-token" placeholder="Paste token here..." autofocus />
  <button id="loginBtn" data-testid="button-login">Login</button>
</div>
<script>
document.getElementById('loginBtn').addEventListener('click', function() {
  var token = document.getElementById('tokenInput').value.trim();
  if (!token) { var e = document.getElementById('errorMsg'); e.textContent = 'Please enter a token.'; e.style.display = 'block'; return; }
  var form = document.createElement('form');
  form.method = 'POST';
  form.action = '/admin';
  var inp = document.createElement('input');
  inp.type = 'hidden';
  inp.name = 'token';
  inp.value = token;
  form.appendChild(inp);
  document.body.appendChild(form);
  form.submit();
});
document.getElementById('tokenInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') { document.getElementById('loginBtn').click(); }
});
</script>
</body>
</html>"""
    return web.Response(text=login_html, content_type="text/html")


def get_dm_pairs():
    pairs = []
    for key in dm_store:
        a = "Admin" if key[0] == "~admin~" else key[0]
        b = "Admin" if key[1] == "~admin~" else key[1]
        pairs.append(a + " & " + b)
    return pairs


async def handle_gc_create(ws, creator, data):
    global gc_counter
    gc_counter += 1
    gc_id = f"gc_{gc_counter}"
    name = data.get("name", "Group").strip() or "Group"
    members = data.get("members", [])
    if len(members) < 2:
        await ws.send_str(json.dumps({"type": "error", "text": "Need at least 2 other members."}))
        return
    all_members = [creator] + members
    gc = {"id": gc_id, "name": name, "members": all_members, "creator": creator, "messages": []}
    gc_store[gc_id] = gc
    gc_info = {"id": gc_id, "name": name, "members": all_members}
    await ws.send_str(json.dumps({"type": "gc_created", "gc": gc_info}))
    for m in members:
        for client_ws, info in connected.items():
            if info["username"] == m:
                try:
                    await client_ws.send_str(json.dumps({"type": "gc_invited", "gc": gc_info}))
                except Exception:
                    pass
                break
    print(f"[GC] {creator} created group '{name}' with {all_members}")


async def handle_gc_message(ws, sender, data):
    gc_id = data.get("gc_id", "")
    text = data.get("text", "").strip()
    gc = gc_store.get(gc_id)
    if not gc or sender not in gc["members"] or not text:
        return
    ts = _time.strftime("%H:%M")
    admin = data.get("admin", False)
    display_name = data.get("name", sender)
    gc["messages"].append({"sender": display_name, "text": text, "time": ts, "admin": admin})
    add_log("gc", gc_id=gc_id, gc_name=gc["name"], sender=display_name, text=text, admin=admin)
    msg = {"type": "gc_message", "gc_id": gc_id, "sender": display_name, "text": text, "admin": admin}
    for m in gc["members"]:
        if m == sender:
            continue
        for client_ws, info in connected.items():
            if info["username"] == m:
                try:
                    await client_ws.send_str(json.dumps(msg))
                except Exception:
                    pass
                break
    await ws.send_str(json.dumps(msg))
    print(f"[GC:{gc['name']}] {display_name}: {text}")


async def send_dm_pairs_to_admin():
    pairs = get_dm_pairs()
    await send_to_admin({"type": "dm_pairs", "pairs": pairs})


staff_connected = {}

async def handle_owner_ws(request):
    global admin_ws
    token = request.query.get("token", "")
    if token != OWNER_TOKEN:
        return web.Response(text="Unauthorized", status=403)

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    admin_ws = ws
    print("[OWNER] Owner connected")

    await send_to_admin({"type": "users", "list": user_list()})
    await send_to_admin({"type": "banned_list", "list": list(banned_users)})
    await send_dm_pairs_to_admin()

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)

                if data["type"] == "kick":
                    target = data["username"]
                    for client_ws, info in list(connected.items()):
                        if info["username"] == target:
                            await client_ws.send_str(json.dumps({
                                "type": "error",
                                "text": "You have been kicked by the owner."
                            }))
                            await client_ws.close()
                            break
                    for sws, sinfo in list(staff_connected.items()):
                        if sinfo["username"] == target:
                            await sws.close()
                            break
                    print(f"[OWNER] Kicked: {target}")

                elif data["type"] == "ban":
                    target = data["username"]
                    banned_users.add(target)
                    for client_ws, info in list(connected.items()):
                        if info["username"] == target:
                            await client_ws.send_str(json.dumps({
                                "type": "error",
                                "text": "You have been banned."
                            }))
                            await client_ws.close()
                            break
                    await send_to_admin({"type": "banned_list", "list": list(banned_users)})
                    print(f"[OWNER] Banned: {target}")

                elif data["type"] == "unban":
                    target = data["username"]
                    banned_users.discard(target)
                    await send_to_admin({"type": "banned_list", "list": list(banned_users)})
                    print(f"[OWNER] Unbanned: {target}")

                elif data["type"] == "chat":
                    text = data.get("text", "").strip()
                    name = data.get("name", "").strip() or "Owner"
                    if text:
                        await broadcast_all({"type": "chat", "sender": name, "text": text, "admin": True})
                        add_log("chat", sender=name, text=text, admin=True)
                        print(f"[{name} (Owner)] {text}")

                elif data["type"] == "dm_message":
                    target = data.get("target", "").strip()
                    text = data.get("text", "").strip()
                    name = data.get("name", "").strip() or "Owner"
                    if target and text:
                        key = dm_key("~admin~", target)
                        if key not in dm_store:
                            dm_store[key] = []
                        ts = _time.strftime("%H:%M")
                        dm_store[key].append({"sender": name, "recipient": target, "text": text, "time": ts, "admin": True})
                        dm_msg_to_guest = {"type": "dm", "sender": name, "recipient": target, "text": text, "admin": True, "admin_dm": True}
                        dm_msg_to_admin = {"type": "dm", "sender": name, "recipient": target, "text": text, "admin": True}
                        for client_ws, info in connected.items():
                            if info["username"] == target:
                                try:
                                    await client_ws.send_str(json.dumps(dm_msg_to_guest))
                                except Exception:
                                    pass
                                break
                        await ws.send_str(json.dumps(dm_msg_to_admin))
                        await send_dm_pairs_to_admin()
                        add_log("dm", sender=name, recipient=target, text=text, admin=True)
                        print(f"[DM] {name} (Owner) -> {target}: {text}")

                elif data["type"] == "dm_open":
                    target = data.get("target", "")
                    key = dm_key("~admin~", target)
                    history = dm_store.get(key, [])
                    await ws.send_str(json.dumps({
                        "type": "dm_history",
                        "target": target,
                        "messages": history
                    }))

                elif data["type"] == "dm_spy_open":
                    pair_str = data.get("pair", "")
                    parts = pair_str.split(" & ")
                    if len(parts) == 2:
                        a = "~admin~" if parts[0] == "Admin" else parts[0]
                        b = "~admin~" if parts[1] == "Admin" else parts[1]
                        key = dm_key(a, b)
                        history = dm_store.get(key, [])
                        await ws.send_str(json.dumps({
                            "type": "dm_spy",
                            "pair": pair_str,
                            "messages": history
                        }))

                elif data.get("type") == "get_logs":
                    await ws.send_str(json.dumps({"type": "logs_data", "logs": chat_logs}))

                elif data.get("type") == "delete_log":
                    log_id = data.get("log_id")
                    if log_id is not None:
                        delete_log(log_id)

                elif data.get("type") == "create_admin":
                    admin_name = data.get("name", "").strip()
                    if admin_name:
                        new_key = hashlib.sha256((admin_name + str(_time.time())).encode()).hexdigest()[:16]
                        admin_accounts[new_key] = {
                            "name": admin_name,
                            "created": mtn_now().strftime("%Y-%m-%d %H:%M"),
                            "key": new_key
                        }
                        await ws.send_str(json.dumps({
                            "type": "admin_created",
                            "name": admin_name,
                            "key": new_key
                        }))
                        print(f"[OWNER] Created admin account: {admin_name}")

                elif data.get("type") == "get_admins":
                    admins_list = []
                    for k, v in admin_accounts.items():
                        admins_list.append({"name": v["name"], "created": v["created"], "key": k})
                    await ws.send_str(json.dumps({"type": "admins_data", "admins": admins_list}))

                elif data.get("type") == "remove_admin":
                    key_to_remove = data.get("key", "")
                    if key_to_remove in admin_accounts:
                        removed_name = admin_accounts[key_to_remove]["name"]
                        del admin_accounts[key_to_remove]
                        for sws, sinfo in list(staff_connected.items()):
                            if sinfo.get("admin_key") == key_to_remove:
                                await sws.close()
                        print(f"[OWNER] Removed admin: {removed_name}")

                elif data.get("type") == "get_suggestions":
                    await ws.send_str(json.dumps({"type": "suggestions_data", "suggestions": suggestions}))
                    suggestion_counter[0] = 0

                elif data.get("type") == "delete_suggestion":
                    sid = data.get("id")
                    for i, s in enumerate(suggestions):
                        if s.get("id") == sid:
                            suggestions.pop(i)
                            break

                elif data.get("type") == "gc_create":
                    await handle_gc_create(ws, "~admin~", data)

                elif data.get("type") == "gc_message":
                    await handle_gc_message(ws, "~admin~", data)

                elif data.get("type") == "gc_open":
                    gc_id = data.get("gc_id", "")
                    gc = gc_store.get(gc_id)
                    if gc and "~admin~" in gc["members"]:
                        await ws.send_str(json.dumps({
                            "type": "gc_history",
                            "gc_id": gc_id,
                            "messages": gc["messages"]
                        }))

            except Exception as e:
                print(f"[OWNER] Error: {e}")

        elif msg.type == aiohttp.WSMsgType.ERROR:
            break

    admin_ws = None
    print("[OWNER] Owner disconnected")
    return ws


async def handle_staff_ws(request):
    key = request.query.get("key", "")
    if key not in admin_accounts:
        return web.Response(text="Unauthorized", status=403)

    account = admin_accounts[key]
    staff_name = account["name"]

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    staff_connected[ws] = {"username": staff_name, "admin_key": key, "role": "admin"}
    print(f"[STAFF] Admin '{staff_name}' connected")

    await ws.send_str(json.dumps({"type": "welcome", "username": staff_name, "role": "admin"}))
    await broadcast_all({"type": "users", "list": user_list()})

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)

                if data["type"] == "kick":
                    target = data["username"]
                    for client_ws, info in list(connected.items()):
                        if info["username"] == target:
                            await client_ws.send_str(json.dumps({
                                "type": "error",
                                "text": "You have been kicked by an admin."
                            }))
                            await client_ws.close()
                            break
                    print(f"[STAFF:{staff_name}] Kicked: {target}")

                elif data["type"] == "chat":
                    text = data.get("text", "").strip()
                    if text:
                        await broadcast_all({"type": "chat", "sender": staff_name, "text": text, "admin": True})
                        add_log("chat", sender=staff_name, text=text, admin=True)
                        print(f"[{staff_name} (Admin)] {text}")

                elif data["type"] == "dm_message":
                    target = data.get("target", "").strip()
                    text = data.get("text", "").strip()
                    if target and text:
                        identity = "~staff:" + key + "~"
                        k = dm_key(identity, target)
                        if k not in dm_store:
                            dm_store[k] = []
                        ts = _time.strftime("%H:%M")
                        dm_store[k].append({"sender": staff_name, "recipient": target, "text": text, "time": ts, "admin": True})
                        dm_msg = {"type": "dm", "sender": staff_name, "recipient": target, "text": text, "admin": True, "admin_dm": True}
                        for client_ws, info in connected.items():
                            if info["username"] == target:
                                try:
                                    await client_ws.send_str(json.dumps(dm_msg))
                                except Exception:
                                    pass
                                break
                        await ws.send_str(json.dumps({"type": "dm", "sender": staff_name, "recipient": target, "text": text, "admin": True}))
                        add_log("dm", sender=staff_name, recipient=target, text=text, admin=True)

                elif data["type"] == "dm_open":
                    target = data.get("target", "")
                    identity = "~staff:" + key + "~"
                    k = dm_key(identity, target)
                    history = dm_store.get(k, [])
                    await ws.send_str(json.dumps({
                        "type": "dm_history",
                        "target": target,
                        "messages": history
                    }))

                elif data.get("type") == "get_logs":
                    await ws.send_str(json.dumps({"type": "logs_data", "logs": chat_logs}))

                elif data.get("type") == "send_suggestion":
                    text = data.get("text", "").strip()
                    if text:
                        sid = len(suggestions) + 1
                        suggestions.append({
                            "id": sid,
                            "from": staff_name,
                            "text": text,
                            "timestamp": mtn_now().strftime("%Y-%m-%d %H:%M")
                        })
                        suggestion_counter[0] += 1
                        await ws.send_str(json.dumps({"type": "suggestion_sent"}))
                        if admin_ws:
                            try:
                                await admin_ws.send_str(json.dumps({"type": "new_suggestion"}))
                            except Exception:
                                pass
                        print(f"[STAFF:{staff_name}] Suggestion: {text}")

                elif data.get("type") == "gc_create":
                    identity = "~staff:" + key + "~"
                    await handle_gc_create(ws, identity, data)

                elif data.get("type") == "gc_message":
                    identity = "~staff:" + key + "~"
                    await handle_gc_message(ws, identity, data)

                elif data.get("type") == "gc_open":
                    gc_id = data.get("gc_id", "")
                    identity = "~staff:" + key + "~"
                    gc = gc_store.get(gc_id)
                    if gc and identity in gc["members"]:
                        await ws.send_str(json.dumps({
                            "type": "gc_history",
                            "gc_id": gc_id,
                            "messages": gc["messages"]
                        }))

                elif data.get("type") == "bj_action":
                    await handle_bj_action(ws, staff_name, data)

            except Exception as e:
                print(f"[STAFF:{staff_name}] Error: {e}")

        elif msg.type == aiohttp.WSMsgType.ERROR:
            break

    if ws in staff_connected:
        del staff_connected[ws]
    await broadcast_all({"type": "users", "list": user_list()})
    print(f"[STAFF] Admin '{staff_name}' disconnected")
    return ws


def bj_make_deck():
    suits = ['S', 'H', 'D', 'C']
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    deck = [{"suit": s, "rank": r} for s in suits for r in ranks]
    random.shuffle(deck)
    return deck


def bj_card_value(hand):
    total = 0
    aces = 0
    for c in hand:
        r = c["rank"]
        if r == 'A':
            total += 11
            aces += 1
        elif r in ('J', 'Q', 'K'):
            total += 10
        else:
            total += int(r)
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def bj_room_state(room, reveal_dealer=False):
    dealer_hand = []
    for i, c in enumerate(room["dealer_hand"]):
        if i == 1 and not reveal_dealer:
            dealer_hand.append({"suit": "?", "rank": "?", "hidden": True})
        else:
            dealer_hand.append(c)
    players_data = []
    for p in room["players"]:
        pd = {"id": p["id"], "name": p["name"], "hand": p["hand"], "value": bj_card_value(p["hand"]) if p["hand"] else 0, "score": p.get("score", 0)}
        if p.get("result"):
            pd["result"] = p["result"]
        players_data.append(pd)
    current_turn = None
    if room["phase"] == "playing" and 0 <= room["current_turn_idx"] < len(room["players"]):
        current_turn = room["players"][room["current_turn_idx"]]["id"]
    return {
        "room_id": room["room_id"],
        "phase": room["phase"],
        "host": room["host"],
        "players": players_data,
        "dealer_hand": dealer_hand,
        "dealer_value": bj_card_value(room["dealer_hand"]) if reveal_dealer else None,
        "current_turn": current_turn,
    }


async def bj_broadcast_state(room, reveal=False):
    state = bj_room_state(room, reveal)
    for p in room["players"]:
        ws_conn = p.get("ws")
        if ws_conn:
            try:
                await ws_conn.send_str(json.dumps({"type": "bj_state", "state": state}))
            except Exception:
                pass


async def bj_turn_timeout(room_id, turn_idx):
    await asyncio.sleep(30)
    room = bj_rooms.get(room_id)
    if not room or room["phase"] != "playing":
        return
    if room["current_turn_idx"] != turn_idx:
        return
    room["current_turn_idx"] += 1
    if room["current_turn_idx"] >= len(room["players"]):
        await bj_dealer_play(room)
    else:
        asyncio.create_task(bj_turn_timeout(room_id, room["current_turn_idx"]))
        await bj_broadcast_state(room)


async def handle_bj_action(ws, username, data):
    action = data.get("action", "")

    if action == "create":
        room_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        room = {
            "room_id": room_id,
            "players": [{"id": username, "name": username, "ws": ws, "hand": [], "result": None, "score": 0}],
            "deck": [],
            "dealer_hand": [],
            "phase": "waiting",
            "host": username,
            "current_turn_idx": 0,
        }
        bj_rooms[room_id] = room
        state = bj_room_state(room)
        await ws.send_str(json.dumps({"type": "bj_room_created", "room_id": room_id, "player_id": username, "state": state}))

    elif action == "join":
        room_id = data.get("room_id", "").strip().upper()
        room = bj_rooms.get(room_id)
        if not room:
            await ws.send_str(json.dumps({"type": "bj_error", "text": "Room not found."}))
            return
        if len(room["players"]) >= 4:
            await ws.send_str(json.dumps({"type": "bj_error", "text": "Room is full."}))
            return
        if any(p["id"] == username for p in room["players"]):
            await ws.send_str(json.dumps({"type": "bj_error", "text": "Already in this room."}))
            return
        if room["phase"] != "waiting":
            await ws.send_str(json.dumps({"type": "bj_error", "text": "Game already in progress."}))
            return
        room["players"].append({"id": username, "name": username, "ws": ws, "hand": [], "result": None, "score": 0})
        state = bj_room_state(room)
        await ws.send_str(json.dumps({"type": "bj_joined", "room_id": room_id, "player_id": username, "state": state}))
        await bj_broadcast_state(room)

    elif action == "start":
        room_id = data.get("room_id", "")
        room = bj_rooms.get(room_id)
        if not room:
            return
        room["deck"] = bj_make_deck()
        room["dealer_hand"] = [room["deck"].pop(), room["deck"].pop()]
        for p in room["players"]:
            p["hand"] = [room["deck"].pop(), room["deck"].pop()]
            p["result"] = None
        room["phase"] = "playing"
        room["current_turn_idx"] = 0
        asyncio.create_task(bj_turn_timeout(room_id, 0))
        await bj_broadcast_state(room)

    elif action == "hit":
        room_id = data.get("room_id", "")
        room = bj_rooms.get(room_id)
        if not room or room["phase"] != "playing":
            return
        idx = room["current_turn_idx"]
        if idx >= len(room["players"]):
            return
        player = room["players"][idx]
        if player["id"] != username:
            return
        player["hand"].append(room["deck"].pop())
        if bj_card_value(player["hand"]) > 21:
            player["result"] = "Bust"
            room["current_turn_idx"] += 1
            if room["current_turn_idx"] >= len(room["players"]):
                await bj_dealer_play(room)
            else:
                asyncio.create_task(bj_turn_timeout(room_id, room["current_turn_idx"]))
                await bj_broadcast_state(room)
        else:
            await bj_broadcast_state(room)

    elif action == "stand":
        room_id = data.get("room_id", "")
        room = bj_rooms.get(room_id)
        if not room or room["phase"] != "playing":
            return
        idx = room["current_turn_idx"]
        if idx >= len(room["players"]):
            return
        player = room["players"][idx]
        if player["id"] != username:
            return
        room["current_turn_idx"] += 1
        if room["current_turn_idx"] >= len(room["players"]):
            await bj_dealer_play(room)
        else:
            asyncio.create_task(bj_turn_timeout(room_id, room["current_turn_idx"]))
            await bj_broadcast_state(room)

    elif action == "leave":
        room_id = data.get("room_id", "")
        room = bj_rooms.get(room_id)
        if not room:
            return
        room["players"] = [p for p in room["players"] if p["id"] != username]
        if not room["players"]:
            del bj_rooms[room_id]
        else:
            if room["host"] == username:
                room["host"] = room["players"][0]["id"]
            await bj_broadcast_state(room)


async def bj_dealer_play(room):
    room["phase"] = "dealer"
    while bj_card_value(room["dealer_hand"]) < 17:
        room["dealer_hand"].append(room["deck"].pop())
    dv = bj_card_value(room["dealer_hand"])
    for p in room["players"]:
        if p["result"] == "Bust":
            p["result"] = "Lose"
            p["score"] = p.get("score", 0) - 1
            continue
        pv = bj_card_value(p["hand"])
        if dv > 21:
            p["result"] = "Win"
            p["score"] = p.get("score", 0) + 1
        elif pv > dv:
            p["result"] = "Win"
            p["score"] = p.get("score", 0) + 1
        elif pv < dv:
            p["result"] = "Lose"
            p["score"] = p.get("score", 0) - 1
        else:
            p["result"] = "Push"
    room["phase"] = "done"
    await bj_broadcast_state(room, reveal=True)


async def bj_handle_disconnect(username):
    rooms_to_delete = []
    for room_id, room in bj_rooms.items():
        player_idx = None
        for i, p in enumerate(room["players"]):
            if p["id"] == username:
                player_idx = i
                break
        if player_idx is None:
            continue
        was_current_turn = (room["phase"] == "playing" and room["current_turn_idx"] == player_idx)
        room["players"].pop(player_idx)
        if not room["players"]:
            rooms_to_delete.append(room_id)
            continue
        if room["host"] == username:
            room["host"] = room["players"][0]["id"]
        if room["phase"] == "playing":
            if player_idx < room["current_turn_idx"]:
                room["current_turn_idx"] -= 1
            if was_current_turn or room["current_turn_idx"] >= len(room["players"]):
                if room["current_turn_idx"] >= len(room["players"]):
                    await bj_dealer_play(room)
                    continue
        await bj_broadcast_state(room)
    for rid in rooms_to_delete:
        del bj_rooms[rid]


async def handle_client_ws(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    username = None

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)

                if username is None:
                    if data.get("type") != "join" or not data.get("username", "").strip():
                        await ws.send_str(json.dumps({
                            "type": "error",
                            "text": "Send a join message with a username first."
                        }))
                        continue

                    name = data["username"].strip()

                    if not USERNAME_RE.match(name):
                        await ws.send_str(json.dumps({
                            "type": "error",
                            "text": "Username must be 1-20 characters: letters, numbers, _ or - only."
                        }))
                        continue

                    if RESERVED_RE.search(name):
                        await ws.send_str(json.dumps({
                            "type": "error",
                            "text": "Username cannot contain 'admin', 'mod', or 'owner'."
                        }))
                        continue

                    if name in banned_users:
                        await ws.send_str(json.dumps({
                            "type": "error",
                            "text": "You are banned from this server."
                        }))
                        await ws.close()
                        break

                    if name in [i["username"] for i in connected.values()]:
                        await ws.send_str(json.dumps({
                            "type": "error",
                            "text": f"Username '{name}' is already taken."
                        }))
                        continue

                    username = name
                    connected[ws] = {"username": username, "ws": ws}
                    print(f"[+] {username} joined  ({len(connected)} online)")

                    await broadcast_all({"type": "system", "text": f"{username} joined the chat"})
                    await send_user_list()

                elif data.get("type") == "chat":
                    text = data.get("text", "").strip()
                    if text:
                        await broadcast_all({"type": "chat", "sender": username, "text": text})
                        add_log("chat", sender=username, text=text)
                        print(f"[{username}] {text}")

                elif data.get("type") == "dm_message":
                    target = data.get("target", "").strip()
                    text = data.get("text", "").strip()
                    if target and text and target != username:
                        is_to_admin = (target == "Admin")
                        store_target = "~admin~" if is_to_admin else target
                        key = dm_key(username, store_target)
                        if key not in dm_store:
                            dm_store[key] = []
                        ts = _time.strftime("%H:%M")
                        dm_store[key].append({"sender": username, "recipient": target, "text": text, "time": ts})
                        dm_msg = {"type": "dm", "sender": username, "recipient": target, "text": text}
                        if is_to_admin:
                            await send_to_admin(dm_msg)
                        else:
                            for client_ws_conn, info in connected.items():
                                if info["username"] == target:
                                    try:
                                        await client_ws_conn.send_str(json.dumps(dm_msg))
                                    except Exception:
                                        pass
                                    break
                            spy_pair = key[0] + " & " + key[1]
                            spy_pair_display = spy_pair.replace("~admin~", "Admin")
                            await send_to_admin({"type": "dm_spy_update", "pair": spy_pair_display, "sender": username, "recipient": target, "text": text})
                        await ws.send_str(json.dumps(dm_msg))
                        await send_dm_pairs_to_admin()
                        add_log("dm", sender=username, recipient=target, text=text)
                        print(f"[DM] {username} -> {target}: {text}")

                elif data.get("type") == "dm_open":
                    target = data.get("target", "")
                    store_target = "~admin~" if target == "Admin" else target
                    key = dm_key(username, store_target)
                    history = dm_store.get(key, [])
                    await ws.send_str(json.dumps({
                        "type": "dm_history",
                        "target": target,
                        "messages": history
                    }))

                elif data.get("type") == "gc_create":
                    await handle_gc_create(ws, username, data)

                elif data.get("type") == "gc_message":
                    await handle_gc_message(ws, username, data)

                elif data.get("type") == "gc_open":
                    gc_id = data.get("gc_id", "")
                    gc = gc_store.get(gc_id)
                    if gc and username in gc["members"]:
                        await ws.send_str(json.dumps({
                            "type": "gc_history",
                            "gc_id": gc_id,
                            "messages": gc["messages"]
                        }))

                elif data.get("type") == "send_suggestion":
                    text = data.get("text", "").strip()
                    if text:
                        sid = len(suggestions) + 1
                        suggestions.append({
                            "id": sid,
                            "from": username,
                            "text": text,
                            "timestamp": mtn_now().strftime("%Y-%m-%d %H:%M")
                        })
                        suggestion_counter[0] += 1
                        await ws.send_str(json.dumps({"type": "suggestion_sent"}))
                        if admin_ws:
                            try:
                                await admin_ws.send_str(json.dumps({"type": "new_suggestion"}))
                            except Exception:
                                pass

                elif data.get("type") == "typing":
                    channel = data.get("channel", "general")
                    typing_msg = {"type": "typing", "username": username, "channel": channel}
                    if channel == "general":
                        for c_ws in list(connected.keys()):
                            if c_ws != ws:
                                try:
                                    await c_ws.send_str(json.dumps(typing_msg))
                                except Exception:
                                    pass
                        await send_to_admin(typing_msg)
                        await broadcast_to_staff(typing_msg)
                    elif channel.startswith("dm:"):
                        target = channel[3:]
                        for c_ws, info in connected.items():
                            if info["username"] == target:
                                try:
                                    await c_ws.send_str(json.dumps(typing_msg))
                                except Exception:
                                    pass
                                break

                elif data.get("type") == "set_status":
                    status = data.get("status", "online")
                    if status in ("online", "idle", "dnd", "invisible"):
                        connected[ws]["status"] = status
                        await send_user_list()

                elif data.get("type") == "bj_action":
                    await handle_bj_action(ws, username, data)

            except Exception as e:
                print(f"[!] Error: {e}")

        elif msg.type == aiohttp.WSMsgType.ERROR:
            break

    if ws in connected:
        left = connected.pop(ws)["username"]
        print(f"[-] {left} left  ({len(connected)} online)")

        await bj_handle_disconnect(left)

        keys_to_remove = [k for k in dm_store if left in k]
        for k in keys_to_remove:
            del dm_store[k]

        await broadcast_all({"type": "system", "text": f"{left} left the chat"})
        await broadcast_all({"type": "dm_cleanup", "username": left})
        await send_to_admin({"type": "dm_cleanup", "username": left})
        await send_user_list()
        await send_dm_pairs_to_admin()

    return ws


async def main():
    load_logs()

    app = web.Application()
    app.router.add_get("/", handle_chat_page)
    app.router.add_get("/admin", handle_admin_page)
    app.router.add_post("/admin", handle_admin_page)
    app.router.add_get("/owner-ws", handle_owner_ws)
    app.router.add_get("/staff-ws", handle_staff_ws)
    app.router.add_get("/ws", handle_client_ws)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 5000)
    await site.start()


    print("=" * 50)
    print("  CHAT SERVER - OWNER PANEL")
    print("=" * 50)
    print()
    print("  Server running on port 5000")
    print()
    print("  OWNER URL (keep this secret!):")
    print(f"  /admin?token={OWNER_TOKEN}")
    print()
    print("  Friends open your Replit URL to chat.")
    print("  No token needed - just pick a username.")
    print()
    print("  Waiting for connections...")
    print("=" * 50)
    print()

    await asyncio.Future()

asyncio.run(main())
