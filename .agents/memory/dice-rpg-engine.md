---
name: Dice RPG engine & validation
description: How the Dice RPG combat/catalog is structured and how to validate edits safely
---

## Validation recipe (ALWAYS run after editing dice_rpg.py / dice_data.py / server.py)
```
python3 -m py_compile server.py games/dice_data.py games/dice_rpg.py
python3 -c "import games.dice_rpg as d; open('/tmp/dg.js','w').write(d.get_js())" && node --check /tmp/dg.js
```
**Why:** `dice_rpg.py` embeds a huge JS string returned by `get_js()`; Python compiling alone will NOT catch JS syntax errors. NEVER run `node --check` on raw `server.py` (it is Python). Extract the JS to a temp file first.

## Catalog is data-driven; engine reads params by key
- `games/dice_data.py` holds the catalog (`DICE_BY_ID`, `IDS_BY_RARITY`, `ELEMENTS`, `ELEMENT_COLORS`, `ENGINE_TAGS`, `ENGINE_SYNERGY`, `STATUS_INFO`, `BANNERS`) and ships them through `public_catalog()['constants']`.
- Each die's ability `params` keys must match the rider keys the engine reads in `useBasic`/`useSkill`/`useUlt`. Adding a mechanic = add the param key in data AND handle it in the engine; a typo silently does nothing.
- Combat is **client-resolved** (like every game here). Server only persists state and bounds reward grants by idempotency/sequence/monotonic checks.

## Banners
- Adding a banner touches THREE places, all of which must agree or pulls silently break: (1) `dice_data.BANNERS`, (2) the `dg_pull` allowlist in server.py — validate `banner in dice_data.BANNERS`, never a hardcoded tuple, (3) the frontend `renderSummon` `order` array. A new banner defined in data but missing from the server allowlist returns "Unknown banner."
- Any banner with `featured_mythic`/`featured_rares` runs a 50/50 in `_dice_pick_id` (server.py). Guarantee state is per-banner: `guarantee_<banner_id>`, EXCEPT Limited which keeps the legacy key `limited_guarantee` (frontend pityBox + persisted state depend on it). Don't rename `limited_guarantee`.
- Frontend `renderSummon` builds the banner tab list from a fixed `order` array filtered against `G.banners` — add new banner ids there to surface them.

## Tooltips & status UI
- Global hover popup is `.dg-tip`, driven by `data-tip` / `data-tip-h` / `data-tip-tag` attributes; a delegated mouseover/mouseout listener on `root` shows it. Attach tips by setting those attributes on any element inside `root`.
- `statusTip(key)` maps lowercase status keys → `STATUS_INFO` (TitleCase) via `STATUS_ALIAS`, with `STATUS_FALLBACK` for keys with no catalog entry (guard, immune).
