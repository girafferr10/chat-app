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
_raw_secret = os.environ.get("SESSION_SECRET", secrets.token_urlsafe(16))
ADMIN_TOKEN = hashlib.sha256(_raw_secret.encode()).hexdigest()[:24]

USERNAME_RE = re.compile(r'^[a-zA-Z0-9_-]{1,20}$')


def get_admin_html(token):
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chat Server - Admin Panel</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f5f5f5;
    color: #1a1a1a;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  header {
    background: #fff;
    border-bottom: 1px solid #e0e0e0;
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  header h1 { font-size: 20px; font-weight: 700; color: #1a1a1a; }
  header .status {
    font-size: 13px; color: #666;
    display: flex; align-items: center; gap: 6px;
  }
  header .status .dot {
    width: 8px; height: 8px; border-radius: 50%; background: #22c55e;
  }
  header .status.offline .dot { background: #ef4444; }

  .container { flex: 1; display: flex; overflow: hidden; }

  .sidebar {
    width: 300px; background: #fff;
    border-right: 1px solid #e0e0e0;
    display: flex; flex-direction: column;
  }
  .sidebar-header {
    padding: 14px 20px; border-bottom: 1px solid #eee;
    font-size: 13px; font-weight: 600; color: #666;
    text-transform: uppercase; letter-spacing: 0.5px;
    display: flex; justify-content: space-between; align-items: center;
  }
  .sidebar-header .count {
    background: #e0e0e0; color: #333;
    padding: 2px 8px; border-radius: 10px; font-size: 12px;
  }
  .user-list { flex: 1; overflow-y: auto; padding: 8px; }
  .user-item {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 12px; border-radius: 8px; margin-bottom: 2px;
  }
  .user-item:hover { background: #f5f5f5; }
  .user-info {
    display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0;
  }
  .user-avatar {
    width: 32px; height: 32px; border-radius: 50%; background: #e0e0e0;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 600; color: #555; flex-shrink: 0;
  }
  .user-name {
    font-size: 14px; font-weight: 500; color: #1a1a1a;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .user-actions { display: flex; gap: 4px; visibility: hidden; }
  .user-item:hover .user-actions { visibility: visible; }
  .btn {
    padding: 5px 10px; border: 1px solid #ddd; border-radius: 6px;
    font-size: 12px; font-weight: 500; cursor: pointer;
    background: #fff; color: #333; transition: all 0.15s;
  }
  .btn:hover { background: #f0f0f0; }
  .btn-danger { color: #ef4444; border-color: #fecaca; }
  .btn-danger:hover { background: #fef2f2; }
  .btn-warn { color: #f59e0b; border-color: #fde68a; }
  .btn-warn:hover { background: #fffbeb; }

  .chat-area {
    flex: 1; display: flex; flex-direction: column; background: #fafafa;
  }
  .messages { flex: 1; overflow-y: auto; padding: 20px 24px; }
  .msg {
    margin-bottom: 12px; display: flex; gap: 10px; align-items: flex-start;
  }
  .msg-avatar {
    width: 28px; height: 28px; border-radius: 50%; background: #e0e0e0;
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 600; color: #555;
    flex-shrink: 0; margin-top: 2px;
  }
  .msg-content { flex: 1; min-width: 0; }
  .msg-header {
    display: flex; align-items: baseline; gap: 8px; margin-bottom: 2px;
  }
  .msg-sender { font-size: 13px; font-weight: 600; color: #1a1a1a; }
  .msg-time { font-size: 11px; color: #999; }
  .msg-text {
    font-size: 14px; color: #333; line-height: 1.5; word-break: break-word;
  }
  .msg-system { text-align: center; padding: 8px; margin-bottom: 12px; }
  .msg-system span {
    font-size: 12px; color: #999; background: #eee;
    padding: 4px 12px; border-radius: 10px;
  }

  .admin-input {
    padding: 16px 24px; background: #fff;
    border-top: 1px solid #e0e0e0; display: flex; gap: 8px;
  }
  .admin-input input {
    flex: 1; padding: 10px 14px; border: 1px solid #ddd;
    border-radius: 8px; font-size: 14px; outline: none;
    background: #f9f9f9; color: #1a1a1a;
  }
  .admin-input input:focus { border-color: #999; background: #fff; }
  .admin-input button {
    padding: 10px 20px; background: #1a1a1a; color: #fff;
    border: none; border-radius: 8px; font-size: 14px;
    font-weight: 500; cursor: pointer;
  }
  .admin-input button:hover { background: #333; }

  .banned-section {
    border-top: 1px solid #eee; padding: 12px 20px;
    max-height: 150px; overflow-y: auto;
  }
  .banned-header {
    font-size: 12px; font-weight: 600; color: #999;
    text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;
  }
  .banned-item {
    display: flex; align-items: center; justify-content: space-between; padding: 6px 0;
  }
  .banned-name { font-size: 13px; color: #999; text-decoration: line-through; }
  .btn-unban { font-size: 11px; padding: 3px 8px; color: #22c55e; border-color: #bbf7d0; }
  .btn-unban:hover { background: #f0fdf4; }

  .empty {
    display: flex; align-items: center; justify-content: center;
    height: 100%; color: #bbb; font-size: 14px;
  }
</style>
</head>
<body>
<header>
  <h1>Chat Server</h1>
  <div class="status" id="status">
    <span class="dot"></span>
    <span id="status-text">Connecting...</span>
  </div>
</header>

<div class="container">
  <div class="sidebar">
    <div class="sidebar-header">
      Connected Users
      <span class="count" id="user-count">0</span>
    </div>
    <div class="user-list" id="user-list"></div>
    <div class="banned-section" id="banned-section" style="display:none;">
      <div class="banned-header">Banned</div>
      <div id="banned-list"></div>
    </div>
  </div>
  <div class="chat-area">
    <div class="messages" id="messages">
      <div class="empty" id="empty-state">No messages yet</div>
    </div>
    <div class="admin-input">
      <input type="text" id="msg-input" placeholder="Send a message as Admin..." />
      <button id="send-btn">Send</button>
    </div>
  </div>
</div>

<script>
const ADMIN_TOKEN = '__TOKEN__';
const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = protocol + '//' + location.host + '/admin-ws?token=' + ADMIN_TOKEN;
let ws;

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
      case 'chat': addMessage(data.sender, data.text); break;
      case 'system': addSystemMessage(data.text); break;
      case 'banned_list': renderBanned(data.list); break;
    }
  };
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function renderUsers(users) {
  const el = document.getElementById('user-list');
  document.getElementById('user-count').textContent = users.length;
  if (users.length === 0) {
    el.innerHTML = '<div class="empty" style="height:100px;">No users online</div>';
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
    kickBtn.addEventListener('click', () => {
      ws.send(JSON.stringify({type: 'kick', username: u}));
    });

    const banBtn = document.createElement('button');
    banBtn.className = 'btn btn-danger';
    banBtn.textContent = 'Ban';
    banBtn.addEventListener('click', () => {
      ws.send(JSON.stringify({type: 'ban', username: u}));
    });

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
  if (list.length === 0) {
    section.style.display = 'none';
    return;
  }
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
    unbanBtn.addEventListener('click', () => {
      ws.send(JSON.stringify({type: 'unban', username: u}));
    });

    item.appendChild(name);
    item.appendChild(unbanBtn);
    el.appendChild(item);
  });
}

function addMessage(sender, text) {
  document.getElementById('empty-state')?.remove();
  const el = document.getElementById('messages');
  const time = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});

  const msg = document.createElement('div');
  msg.className = 'msg';

  const avatarEl = document.createElement('div');
  avatarEl.className = 'msg-avatar';
  avatarEl.textContent = sender.substring(0,2).toUpperCase();

  const content = document.createElement('div');
  content.className = 'msg-content';

  const header = document.createElement('div');
  header.className = 'msg-header';

  const senderEl = document.createElement('span');
  senderEl.className = 'msg-sender';
  senderEl.textContent = sender;

  const timeEl = document.createElement('span');
  timeEl.className = 'msg-time';
  timeEl.textContent = time;

  header.appendChild(senderEl);
  header.appendChild(timeEl);

  const textEl = document.createElement('div');
  textEl.className = 'msg-text';
  textEl.textContent = text;

  content.appendChild(header);
  content.appendChild(textEl);

  msg.appendChild(avatarEl);
  msg.appendChild(content);
  el.appendChild(msg);
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
  const input = document.getElementById('msg-input');
  const text = input.value.trim();
  if (!text) return;
  ws.send(JSON.stringify({type: 'chat', text: text}));
  input.value = '';
}

document.getElementById('send-btn').addEventListener('click', sendMsg);
document.getElementById('msg-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendMsg();
});

connectWS();
</script>
</body>
</html>""".replace('__TOKEN__', token)


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


async def handle_admin_page(request):
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
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #f5f5f5; display: flex; align-items: center; justify-content: center;
  min-height: 100vh; color: #333; }
.login-box { background: #fff; border: 1px solid #ddd; border-radius: 8px;
  padding: 40px; max-width: 400px; width: 90%; }
h2 { margin-bottom: 8px; font-size: 22px; }
p { color: #666; margin-bottom: 24px; font-size: 14px; }
label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; }
input { width: 100%; padding: 10px 12px; border: 1px solid #ccc; border-radius: 6px;
  font-size: 14px; margin-bottom: 16px; }
input:focus { outline: none; border-color: #555; }
button { width: 100%; padding: 10px; background: #333; color: #fff; border: none;
  border-radius: 6px; font-size: 14px; cursor: pointer; }
button:hover { background: #555; }
.error { color: #c00; font-size: 13px; margin-bottom: 12px; display: none; }
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
  if (token) { window.location.href = '/?token=' + encodeURIComponent(token); }
  else { var e = document.getElementById('errorMsg'); e.textContent = 'Please enter a token.'; e.style.display = 'block'; }
});
document.getElementById('tokenInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') { document.getElementById('loginBtn').click(); }
});
var params = new URLSearchParams(window.location.search);
if (params.has('token') && params.get('token') !== '') {
  var e = document.getElementById('errorMsg'); e.textContent = 'Invalid token. Please try again.'; e.style.display = 'block';
}
</script>
</body>
</html>"""
    return web.Response(text=login_html, content_type="text/html")


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
                    if text:
                        await broadcast_all({"type": "chat", "sender": "Admin", "text": text})
                        print(f"[Admin] {text}")

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

                    if name.lower() == "admin":
                        await ws.send_str(json.dumps({
                            "type": "error",
                            "text": "The name 'Admin' is reserved."
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

            except Exception as e:
                print(f"[!] Error: {e}")

        elif msg.type == aiohttp.WSMsgType.ERROR:
            break

    if ws in connected:
        left = connected.pop(ws)["username"]
        print(f"[-] {left} left  ({len(connected)} online)")
        await broadcast_all({"type": "system", "text": f"{left} left the chat"})
        await send_user_list()

    return ws


async def main():
    app = web.Application()
    app.router.add_get("/", handle_admin_page)
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
    print(f"  /?token={ADMIN_TOKEN}")
    print()
    print("  Friends connect using client.py")
    print("  and your Replit URL (no token needed).")
    print()
    print("  Waiting for connections...")
    print("=" * 50)
    print()

    await asyncio.Future()

asyncio.run(main())
