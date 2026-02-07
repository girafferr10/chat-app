import asyncio
import hashlib
import json
import os
import secrets
import re
import aiohttp
from aiohttp import web

connected = {}       # ws -> {"username": str, "ws": ws}
banned_users = set() # set of banned usernames
admin_ws = None      # admin websocket connection
dm_store = {}        # (sorted_user_a, sorted_user_b) -> [{"sender":..., "recipient":..., "text":..., "ts":...}]
import time as _time

def dm_key(a, b):
    return tuple(sorted([a, b]))
_raw_secret = os.environ.get("SESSION_SECRET", secrets.token_urlsafe(16))
ADMIN_TOKEN = hashlib.sha256(_raw_secret.encode()).hexdigest()[:24]

USERNAME_RE = re.compile(r'^[a-zA-Z0-9_-]{1,20}$')
RESERVED_RE = re.compile(r'admin|mod', re.IGNORECASE)


def get_admin_html(token):
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chat Server - Admin Panel</title>
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
const ADMIN_TOKEN = '__TOKEN__';
history.replaceState({}, '', '/admin');
const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = protocol + '//' + location.host + '/admin-ws?token=' + ADMIN_TOKEN;
let ws;
const themes = ['theme-dark', 'theme-light', 'theme-midnight'];
const themeLabels = ['Dark', 'Light', 'Midnight'];
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
  users.forEach(u => {
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

.chat-area { flex: 1; display: flex; flex-direction: column; }

.channel-header {
  padding: 10px 16px; border-bottom: 1px solid var(--bg-tertiary);
  font-size: 15px; font-weight: 600; display: flex; align-items: center; gap: 8px;
}
.channel-header .dm-label { color: var(--dm-color); }

#messages { flex: 1; overflow-y: auto; padding: 16px 16px; }
.msg { padding: 2px 8px; border-radius: 4px; line-height: 1.4; }
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
  padding: 12px 16px; display: flex; gap: 8px;
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

@media (max-width: 600px) {
  .sidebar { display: none; }
}
</style>
</head>
<body>
<div class="join-screen" id="joinScreen">
  <div class="join-box" id="roleBox">
    <h2>Join Chat</h2>
    <p>How would you like to join?</p>
    <div style="display:flex;gap:8px;">
      <button id="guestBtn" data-testid="button-guest" style="flex:1;">Guest</button>
      <button id="adminBtn" data-testid="button-admin" style="flex:1;background:var(--admin-color);">Admin</button>
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
  <div class="join-box" id="adminBox" style="display:none;">
    <h2>Join as Admin</h2>
    <p>Enter the admin token to continue.</p>
    <div class="join-error" id="adminError"></div>
    <label for="adminTokenInput">Admin Token</label>
    <input type="password" id="adminTokenInput" data-testid="input-token" placeholder="Paste token here..." />
    <button id="adminLoginBtn" data-testid="button-admin-login">Login</button>
    <button id="backBtn2" data-testid="button-back-admin" style="margin-top:8px;background:var(--input-bg);color:var(--text-secondary);">Back</button>
  </div>
</div>

<div class="chat-screen" id="chatScreen">
  <header>
    <h1 data-testid="text-header">Chat</h1>
    <div class="header-right">
      <div class="status"><div class="dot"></div> Connected</div>
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
    </div>
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

<script>
var ws = null;
var myUsername = '';
var isAdmin = false;
var currentChannel = 'general';
var generalMessages = [];
var dmMessages = {};
var dmUnread = {};
var onlineUsers = [];
var activeDmPairs = [];
var themes = ['theme-dark', 'theme-light', 'theme-midnight'];
var themeLabels = ['Dark', 'Light', 'Midnight'];
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
document.getElementById('adminBtn').addEventListener('click', function() {
  document.getElementById('roleBox').style.display = 'none';
  document.getElementById('adminBox').style.display = 'block';
  document.getElementById('adminTokenInput').focus();
});
document.getElementById('backBtn1').addEventListener('click', function() {
  document.getElementById('guestBox').style.display = 'none';
  document.getElementById('roleBox').style.display = 'block';
});
document.getElementById('backBtn2').addEventListener('click', function() {
  document.getElementById('adminBox').style.display = 'none';
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

function renderUsers(list) {
  onlineUsers = list;
  document.getElementById('userCount').textContent = list.length;
  var ul = document.getElementById('userList');
  ul.innerHTML = '';
  list.forEach(function(name) {
    var div = document.createElement('div');
    div.className = 'user-item';
    div.setAttribute('data-testid', 'user-item-' + name);
    var avatar = document.createElement('div');
    avatar.className = 'user-avatar';
    avatar.textContent = name.substring(0,2).toUpperCase();
    var nameEl = document.createElement('span');
    nameEl.className = 'user-name';
    nameEl.textContent = name + (name === myUsername ? ' (you)' : '');
    div.appendChild(avatar);
    div.appendChild(nameEl);
    if (name !== myUsername && !isAdmin) {
      div.style.cursor = 'pointer';
      div.title = 'Click to DM ' + name;
      div.addEventListener('click', function(e) {
        if (e.target.tagName === 'BUTTON') return;
        openDm(name);
      });
    }
    if (isAdmin) {
      if (name !== myUsername) {
        div.style.cursor = 'pointer';
        div.title = 'Click to DM ' + name;
        div.addEventListener('click', function(e) {
          if (e.target.tagName === 'BUTTON') return;
          openDm(name);
        });
      }
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
    }
    ul.appendChild(div);
  });
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

function handleMessage(data) {
  if (data.type === 'chat') {
    var time = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    generalMessages.push({sender: data.sender, text: data.text, admin: data.admin || false, time: time});
    if (currentChannel === 'general') renderMessages();
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
  } else if (data.type === 'error') {
    if (!myUsername && !isAdmin) {
      var err = document.getElementById('joinError');
      err.textContent = data.text;
      err.style.display = 'block';
    }
  }
}

var adminConnected = false;
function connectAdmin(token) {
  var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  adminConnected = false;
  ws = new WebSocket(protocol + '//' + location.host + '/admin-ws?token=' + token);
  ws.onopen = function() {
    adminConnected = true;
    isAdmin = true;
    document.getElementById('nameInput').style.display = 'block';
    document.getElementById('joinScreen').style.display = 'none';
    document.getElementById('chatScreen').style.display = 'flex';
    document.getElementById('msgInput').focus();
  };
  ws.onclose = function() {
    if (!adminConnected) {
      var err = document.getElementById('adminError');
      err.textContent = 'Invalid token or connection failed.';
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
  };
  ws.onmessage = function(event) { handleMessage(JSON.parse(event.data)); };
  ws.onclose = function() {
    if (myUsername) {
      document.getElementById('sendBtn').disabled = true;
      document.getElementById('msgInput').disabled = true;
    }
  };
}

var RESERVED = /admin|mod/i;

document.getElementById('channelGeneral').addEventListener('click', function() {
  switchChannel('general');
});

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
  if (!token) { err.textContent = 'Please enter the admin token.'; err.style.display = 'block'; return; }
  connectAdmin(token);
});

document.getElementById('adminTokenInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') document.getElementById('adminLoginBtn').click();
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


async def broadcast_all(message):
    await broadcast_to_clients(message)
    await send_to_admin(message)


def user_list():
    return [info["username"] for info in connected.values()]


async def send_user_list():
    users = user_list()
    await broadcast_to_clients({"type": "users", "list": users})
    await send_to_admin({"type": "users", "list": users})
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
    if token == ADMIN_TOKEN:
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


async def send_dm_pairs_to_admin():
    pairs = get_dm_pairs()
    await send_to_admin({"type": "dm_pairs", "pairs": pairs})


async def handle_admin_ws(request):
    global admin_ws
    token = request.query.get("token", "")
    if token != ADMIN_TOKEN:
        return web.Response(text="Unauthorized", status=403)

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    admin_ws = ws
    print("[ADMIN] Admin panel connected")

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
                                "text": "You have been kicked by the admin."
                            }))
                            await client_ws.close()
                            break
                    print(f"[ADMIN] Kicked: {target}")

                elif data["type"] == "ban":
                    target = data["username"]
                    banned_users.add(target)
                    for client_ws, info in list(connected.items()):
                        if info["username"] == target:
                            await client_ws.send_str(json.dumps({
                                "type": "error",
                                "text": "You have been banned by the admin."
                            }))
                            await client_ws.close()
                            break
                    await send_to_admin({"type": "banned_list", "list": list(banned_users)})
                    print(f"[ADMIN] Banned: {target}")

                elif data["type"] == "unban":
                    target = data["username"]
                    banned_users.discard(target)
                    await send_to_admin({"type": "banned_list", "list": list(banned_users)})
                    print(f"[ADMIN] Unbanned: {target}")

                elif data["type"] == "chat":
                    text = data.get("text", "").strip()
                    name = data.get("name", "").strip() or "Admin"
                    if text:
                        await broadcast_all({"type": "chat", "sender": name, "text": text, "admin": True})
                        print(f"[{name} (Admin)] {text}")

                elif data["type"] == "dm_message":
                    target = data.get("target", "").strip()
                    text = data.get("text", "").strip()
                    name = data.get("name", "").strip() or "Admin"
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
                        print(f"[DM] {name} (Admin) -> {target}: {text}")

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

            except Exception as e:
                print(f"[ADMIN] Error: {e}")

        elif msg.type == aiohttp.WSMsgType.ERROR:
            break

    admin_ws = None
    print("[ADMIN] Admin panel disconnected")
    return ws


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
                            "text": "Username cannot contain 'admin' or 'mod'."
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

            except Exception as e:
                print(f"[!] Error: {e}")

        elif msg.type == aiohttp.WSMsgType.ERROR:
            break

    if ws in connected:
        left = connected.pop(ws)["username"]
        print(f"[-] {left} left  ({len(connected)} online)")

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
    app = web.Application()
    app.router.add_get("/", handle_chat_page)
    app.router.add_get("/admin", handle_admin_page)
    app.router.add_post("/admin", handle_admin_page)
    app.router.add_get("/admin-ws", handle_admin_ws)
    app.router.add_get("/ws", handle_client_ws)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 5000)
    await site.start()

    print("=" * 50)
    print("  CHAT SERVER - ADMIN PANEL")
    print("=" * 50)
    print()
    print("  Server running on port 5000")
    print()
    print("  ADMIN URL (keep this secret!):")
    print(f"  /admin?token={ADMIN_TOKEN}")
    print()
    print("  Friends open your Replit URL to chat.")
    print("  No token needed - just pick a username.")
    print()
    print("  Waiting for connections...")
    print("=" * 50)
    print()

    await asyncio.Future()

asyncio.run(main())
