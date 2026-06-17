---
name: asyncpg JSONB returns strings
description: Why JSONB reads in this project must be json.loads'd, and the silent-failure symptom it causes
---

When `asyncpg.create_pool()` is created with NO JSON/JSONB type codec, asyncpg returns
`json`/`jsonb` columns as **raw JSON strings**, not Python dicts/lists. Calling
`dict(row["col"])` / `list(row["col"])` on such a string raises (e.g. `dict('{"a":1}')`
→ ValueError).

**Why this matters here:** it presented as the "balance starts at 1000 / economy doesn't
persist" bug. `db_get_economy` did `dict(row["equipped"])` on a reconnect where a row
already existed; it threw, the broad `except Exception` in the WS message loop swallowed
it, `balance_data` was never sent, and the client fell back to its default 1000. Fresh
joins worked (they return hardcoded defaults without reading the row), which made it look
like only reconnect/persistence was broken.

**How to apply:**
- Any read of a JSONB column must tolerate a string: use the `_json_field()` helper in
  `db_get_economy` (json.loads strings, pass through already-decoded values, default on
  NULL/parse error). The only JSONB columns are `user_economy.inventory`, `equipped`,
  `idle_upgrades`.
- The save path uses `json.dumps(...)` + `$n::jsonb` casts and is correct as-is. Do NOT
  register a global codec without also switching the save path to pass Python objects, or
  you'll double-encode.
- Beware broad `except` blocks in the WS loop hiding driver errors — they turn a hard
  failure into a silent client hang/fallback. A `traceback.print_exc()` was added there.
