---
name: Embedded game client JS — conventions & validation
description: How games render client JS from Python strings, how server replies route back to a game, and how to actually syntax/runtime-check that JS.
---

This chat app embeds ALL frontend HTML/CSS/JS inside Python triple-quoted strings — `server.py` for the shell, and each `games/<game>.py` exposing `get_js()` / `get_css()` that are injected into the page at render time.

## Validating the client JS
- `python3 -m py_compile` only checks Python. It does NOT validate the embedded client JS, and you must never `node --check` raw `server.py` (it isn't JS).
- To syntax-check the real client JS: either import the module and write `get_js()` to a file, OR `curl http://localhost:5000/` and slice the inline `<script>` out of the served page; then `node --check` THAT file.
- Some runtime bugs pass syntax check — e.g. a **duplicate object-literal key** silently drops the earlier value (this bit the Dice RPG battle state where a live-flag and the acting-unit pointer were both named `active`). To catch these, drive the engine headlessly: load `get_js()` into a Node `vm` context with a stubbed `document`/`window`, a fake-timer queue (setTimeout/clearTimeout drained by a manual clock so auto-battle advances), and a minimal `innerHTML`→node parser (needed so `querySelector` after `innerHTML=` works); feed the state message and simulate clicks by calling each node's `onclick`. Any thrown error surfaces the bug.

**Why:** syntax checks alone gave false confidence; the vm harness reproduced a real dropped-field bug end to end.

## How server replies reach a game
- Games needing server round-trips register globals on `window` (e.g. `window._diceMessageHandler`, plus per-flow callbacks like `window._dgOnPull` / `window._dgOnReward`); the main socket `onmessage` forwards game-typed messages to these globals, and tab-switch cleanup nulls them. Follow this pattern for any new game with a backend.
