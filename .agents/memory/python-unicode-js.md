---
name: Python unicode in JS strings
description: JS ES6+ \u{XXXX} escape syntax is invalid inside Python string literals and causes SyntaxError
---

## Rule
Never write `\\u{1F308}` (ES6 Unicode codepoint escape) inside any Python string literal — raw or not.

**Why:** Python's string parser sees `\\u` and expects exactly 4 hex digits. The curly-brace form `\u{...}` is JavaScript-only. It causes `SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes`.

**How to apply:**
- Use actual emoji characters directly in the source file (e.g. `'🌈'`) — the file is UTF-8.
- Or use the 4-digit `\uXXXX` form for BMP chars, or `\UXXXXXXXX` (8 hex digits) for non-BMP chars.
- Search for `\\u{` before every save when embedding JS in Python strings.

## Apostrophe / single-quote problem (non-raw Python strings)

In a non-raw Python string `"""..."""`, `\'` is consumed by Python → outputs bare `'` → breaks JS single-quoted string.

**Fix:** Use `\\'` in Python source (outputs `\'` to HTML, which JS accepts as escaped apostrophe).  
**Alternative:** Rewrite the offending JS string literal to use double quotes `"Don't"` so no escaping is needed at all.
