---
name: Server architecture
description: Key facts about the Python aiohttp chat server structure and embedding patterns
---

## Key facts

- All HTML/CSS/JS lives inside `server.py` in the `get_client_html()` function as one large string.
- The string is split across raw Python strings `r"""..."""` concatenated with game module JS.
- **Use `createElement` + `addEventListener`** for any JS that involves single quotes or complex strings. Avoid `innerHTML = '...'` with JS code inside — escaping single quotes inside Python strings is error-prone.
- Games live in `games/*.py`, each returning JS via `get_js()` and optional CSS via `get_css()`.
- Server runs on port 5000; Node.js `server/index.ts` spawns the Python process.
- Owner token is derived from SESSION_SECRET (SHA-256); never store the value — it prints to the workflow console on boot.
- In non-raw sections of the embedded JS, emoji must be written as double-escaped `\\uD83C\\uDF81` or as literal UTF-8 chars — single-escaped surrogate pairs crash page render with UnicodeEncodeError.
- The `wrapSel(before, after)` function is a thin wrapper around `wrapSelection(inputEl, before, after)` for use in onclick HTML attributes.
- Tab system: `tabs[]` array, `openBrowserTab(url)` opens/reuses a browser tab and navigates to URL, go button ID is `browser-go-{tabId}`, URL input ID is `browser-urlinput-{tabId}`.
