---
name: Client-resolved game rewards — server integrity guardrails
description: Why in-game reward grants here are client-trusted, and the minimum server-side checks that keep the exposure bounded.
---

Every game in this app resolves its own outcome on the client; the server only persists state and grants currency on the reported outcome. So a reward message is inherently client-trusted — a crafted WebSocket client can claim a "win" it never played.

**Rule:** every currency-granting handler must be (a) server-authoritative on balance via the economy table + a transaction-log row, (b) idempotent so the same reward can't be paid twice, and (c) precondition/sequence validated so claims can't be made out of order or for locked content. Together these bound the worst case to a small finite amount instead of infinite farming.

**Why:** full server-side combat resolution or signed battle sessions would be a large architecture change inconsistent with the rest of this play-money app; bounded client trust is the accepted tradeoff (raised in an architect review of Dice RPG).

**How to apply:** when adding any new reward/grant message, replicate the idempotency + precondition + economy-authority pattern and never trust a client-supplied amount. Example: Dice RPG first-clear rewards are one-time per stage AND require the previous stage already cleared (mirroring the client's unlock order), all inside one `FOR UPDATE` transaction.
