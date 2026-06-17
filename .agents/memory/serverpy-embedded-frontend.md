---
name: server.py embedded frontend
description: How the chat app's frontend is structured and how to validate edits to it
---

`server.py` (~10800 lines) is a Python aiohttp WebSocket chat server where the ENTIRE
frontend (HTML/CSS/JS) is embedded inside triple-quoted Python strings and served as one
big `<script>` block. Node `server/index.ts` spawns the Python process; port 5000;
workflow "Start application" runs `npm run dev`.

**How to apply / validate after editing embedded JS:**
- Don't trust a regex extraction of `<script>` from the raw source for JS syntax checks —
  Python string escapes (e.g. `\\'`) aren't applied, producing false-positive syntax
  errors. Instead fetch the rendered page (`curl localhost:5000/` or urllib) and run
  `node --check` on the served script block. The served page has exactly one big script.
- Standard loop after any edit: `python3 -m py_compile server.py` → restart the workflow →
  `curl localhost:5000/` (expect HTTP 200) → validate served JS.
- Escaping inside the Python strings: apostrophes are often written as `\u2019`, emojis as
  real UTF-8 or `\UXXXXXXXX`.
- Cosmetics/economy: catalog item IDs and style maps live in the embedded JS; server is the
  authority for balances and persists economy by username in PostgreSQL (`user_economy`).
