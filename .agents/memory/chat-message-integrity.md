---
name: Chat message integrity
description: Rules for features that reference or mutate existing chat messages (pin, edit, quote)
---

- The server keeps a capped `msg_authors` map (msg_id → {username, display_name, text}) as the authoritative record of recent #General messages.
- **Rule:** any feature that pins, edits, or quotes a message must resolve sender/text server-side from that map by msg_id — never accept client-supplied text/sender for stored or broadcast content.
- **Why:** an architect review flagged that trusting client pin payloads lets any admin session inject arbitrary "pinned" content that was never actually sent.
- **How to apply:** handlers take only a msg_id (+ new text for edits after author check); lookup misses are silently ignored. Edits must also sync any pinned copy and re-broadcast `pins_update`.
- One-time server credits (daily rewards, milestone grants) go through a `FOR UPDATE` row-locked transaction keyed by username + date/step so reconnects can't double-grant.
