# replit.md

## Overview

This is a real-time chat application built with Python using aiohttp for WebSocket-based communication. Features a Discord-like dark theme with Light and Midnight alternatives. Three-tier role system: Owner, Admin (staff), and Guest. The app supports group chat (#General channel), direct messaging (DMs), group chats (GCs), a tabbed interface with games, role-based moderation controls, suggestion/mailbox system, JSON logging with Mountain Time timestamps, and user customization.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Python Application
- **File**: `server.py` - Contains all server logic and embedded HTML/CSS/JS for the client
- **Games**: `games/` directory - Each game in its own `.py` file returning JS via `get_js()` and optional CSS via `get_css()`
- **Framework**: aiohttp (Python async web framework with WebSocket support)
- **Server**: Node.js `server/index.ts` spawns the Python process
- **Port**: 5000

### Games Directory
- `games/tictactoe.py` - Tic-Tac-Toe (singleplayer vs AI)
- `games/snake.py` - Snake game (singleplayer)
- `games/memory.py` - Memory Match card game (singleplayer)
- `games/blackjack.py` - Blackjack (singleplayer vs dealer)
- `games/blackjack_multi.py` - Multiplayer Blackjack (WebSocket rooms, scoring, 30s turn timeout)
- `games/minesweeper.py` - Minesweeper (singleplayer)
- `games/war.py` - War card game (singleplayer)
- `games/crazy_eights.py` - Crazy Eights card game (singleplayer vs AI)
- `games/solitaire.py` - Klondike Solitaire (singleplayer)
- `games/checkers.py` - Checkers vs AI (singleplayer)
- `games/twenty_fortyeight.py` - 2048 puzzle game (singleplayer)
- `games/hangman.py` - Hangman word guessing (singleplayer)
- `games/dice_rpg.py` - Dice RPG (v3.0): turn-based tactical gacha RPG (client engine: gacha, team, dex, combat)
- `games/dice_data.py` - Dice RPG catalog (~19 dice), constants, banners, constellation/shard config, `CAMPAIGN_STAGE_IDS`, `public_catalog()`

### Routes
- `GET /` - Main page with unified Guest/Admin/Owner join flow
- `GET /admin` - Owner login page (requires owner token)
- `GET /owner-ws` - WebSocket endpoint for owner (requires `?token=...`)
- `GET /staff-ws` - WebSocket endpoint for staff admins (requires `?key=...`)
- `GET /ws` - WebSocket endpoint for guest clients

### Three-Tier Role System
1. **Owner**: Full control - kick, ban, unban, view/delete logs, DM spy, create/manage admin accounts, view/delete suggestions
2. **Admin (Staff)**: Limited moderation - kick users, view logs (read-only), send suggestions to owner, chat
3. **Guest**: Standard user - chat, DM, group chats, games, send suggestions

### WebSocket Message Types
- `join` - Guest sends username to join
- `chat` - Group message in #General
- `dm_message` - Send a direct message to another user
- `dm_open` - Request DM history with a user
- `dm` - Server delivers DM to participants
- `dm_history` - Server sends DM conversation history
- `dm_pairs` - Server sends list of active DM pairs (owner only)
- `dm_spy_open` - Owner requests to view a specific DM pair
- `dm_spy` - Server sends full DM conversation for spy viewing
- `dm_spy_update` - Real-time DM update sent to owner
- `gc_create` - Create a group chat (name + members, 2+ others required)
- `gc_created` - Server confirms GC creation to creator
- `gc_invited` - Server notifies other members of new GC
- `gc_message` - Send a message to a group chat
- `gc_open` - Request GC history
- `gc_history` - Server sends GC message history
- `get_logs` - Owner/Admin requests chat logs (JSON)
- `logs_data` - Server sends log entries
- `delete_log` - Owner deletes individual log entry by ID
- `create_admin` - Owner creates a new admin account
- `admin_created` - Server confirms admin creation with key
- `get_admins` - Owner requests list of admin accounts
- `admins_data` - Server sends admin accounts list
- `remove_admin` - Owner removes an admin account
- `send_suggestion` - Admin/Guest sends a suggestion to owner
- `suggestion_sent` - Server confirms suggestion was sent
- `get_suggestions` - Owner requests all suggestions
- `suggestions_data` - Server sends suggestions list
- `delete_suggestion` - Owner deletes a suggestion
- `new_suggestion` - Server notifies owner of new suggestion
- `users` - Online user list broadcast
- `system` - System messages (join/leave)
- `banned_list` - Banned user list (owner only)
- `kick` - Owner/Admin kicks a user
- `ban` / `unban` - Owner bans/unbans a user
- `bj_action` - Multiplayer blackjack actions (create/join/hit/stand/leave/start)
- `bj_room_created` / `bj_joined` / `bj_state` / `bj_error` - Server responses for multiplayer blackjack
- `dg_get_state` - Client requests Dice RPG catalog + per-user state + balance
- `dg_state` - Server sends catalog, full dice state, and balance
- `dg_pull` - Client requests a gacha pull (`{banner, count}`)
- `dg_pull_result` - Server sends pull results, updated state, and balance
- `dg_set_team` - Client saves its battle team
- `dg_team_result` - Server confirms saved team
- `dg_claim_reward` - Client claims a campaign first-clear reward (`{stage}`)
- `dg_reward_result` - Server grants (or refuses) the one-time first-clear reward
- `dg_set_best_wave` - Client reports endless-arena best wave
- `dg_best_wave_result` - Server confirms the stored best wave

### Key Design Decisions
1. **Three-tier join page**: Single page at `/` offers Guest, Admin, or Owner choice
2. **Owner stable identity**: Owner DMs use internal `~admin~` identity for dm_key
3. **Staff admin identity**: Staff DMs use `~staff:<key>~` identity for dm_key
4. **Admin accounts**: Created by owner with fixed display names, stored in `admin_accounts` dict
5. **In-memory storage**: All messages and DM history stored in Python dicts (not persistent)
6. **Eight theme system**: Dark (default), Light, Midnight, Ocean, Forest, Sunset, Neon, Rose - stored in localStorage
7. **Username restrictions**: Guest usernames cannot contain "admin", "mod", or "owner" (case-insensitive)
8. **Tabbed interface**: Tab bar at TOP of main panel with singleton tabs. New Tab picker for adding tabs.
9. **Game modules**: Each game in its own Python file returning JS code strings, injected into the HTML at render time
10. **Games split**: Games hub shows "Single Player" and "Multiplayer" sections with filtered search
11. **JSON logging**: All chat/DM/GC messages logged to `chat_logs.json` with Mountain Time timestamps, no auto-clear, per-entry deletion by owner
12. **User customization**: Background image URL (covers full page via body), accent color, text color saved to localStorage
13. **Suggestion system**: Guests and admins can send suggestions to owner's mailbox

### Owner Features
- **Owner Token**: Derived from SESSION_SECRET environment variable via SHA-256 hash
- **Display Name**: Changeable anytime via input field; applies to both chat and DMs
- **Kick/Ban**: Hover over users in sidebar to see kick/ban buttons
- **DM Spy**: View all active DM conversations between users
- **Banned List**: See and unban banned users
- **Log Viewer**: View all chat/DM/GC logs with filters (type/sender/text), per-entry delete
- **Admin Creator**: Create new admin accounts with fixed display names
- **Manage Admins**: View/remove admin accounts
- **Suggestions/Mailbox**: View and delete suggestions from admins and guests

### Admin (Staff) Features
- **Fixed Display Name**: Set at account creation by owner, cannot be changed
- **Kick Users**: Can kick (but not ban) other users
- **Log Viewer**: View logs (read-only, no deletion)
- **Send Suggestions**: Send suggestions to owner's mailbox
- **Chat/DM/GC**: Full chat, DM, and group chat capabilities

### Tabbed Interface
- **Tab bar**: At the TOP of the main panel (border-bottom style)
- **Chat tab**: Singleton - contains the chat area with messages, emoji picker, send button
- **Games tab**: Singleton - games split into Single Player and Multiplayer sections with search
- **New Tab**: Opens a picker with Chat and Games options, searchable
- **Auto-open**: When all tabs closed, auto-opens a new picker tab

### Group Chats
- **Creation**: Click "+" in Group Chats sidebar section, name the group, select 2+ online members
- **Messaging**: Members can send messages visible to all group members
- **Sidebar**: GC channels listed in sidebar with unread badges
- **In-memory**: GC data stored in `gc_store` dict, not persistent across restarts

### Multiplayer Blackjack
- **Full 52-card deck**: No duplicate cards
- **Scoring**: +1 for win, -1 for loss, displayed per player
- **30s turn timeout**: Auto-stands if player doesn't act within 30 seconds
- **UI layout**: Your hand on the left, other players on the right
- **Room system**: Create/join rooms with 5-char alphanumeric codes

### Dice RPG (v3.0)
- **What it is**: Turn-based tactical gacha RPG inside the Games tab. Premium Genshin/HSR-style UI with a dice-wall loading screen, full Dex, and a live battle log.
- **Currency**: Uses the main account balance (start 1000). 1-pull = 160, 10-pull = 1600. Beginner banner is −20% (128/pull).
- **Gacha**: 94% common / 5% rare / 1% mythic. Mythic soft pity starts at pull 70 (5%) ramping to 100% at 89; rare guaranteed every 10th pull. First copy unlocks the die; dupes raise Constellation C1→C6, then overflow into Universal Shards.
- **Banners**: Standard, Limited (50/50 featured), Beginner (first 50 pulls, −20%, rare by pull 10, mythic by pull 40). Last-200 pull history per user.
- **Modes**: Story campaign (Normal → Elite → Boss, stages `c1`..`c6`) plus an endless arena. First-clear reward = 50 balance, one-time per stage (not farmable).
- **Combat**: Client-resolved engine (initiative, energy/ult, Omen detonate, Break, elements/resist, crit). Like all games here, outcomes are computed on the client.
- **Free starters**: Two common dice (`green_pip`, `chain_pip`) seeded on first load.
- **Persistence**: `dice_game` table (username PK; JSONB columns: collection, gacha, history, campaign, team). Catalog/constants live in `games/dice_data.py`.

### Dice RPG Server Authority
- **Pulls**: `dice_pull_txn` — `FOR UPDATE` lock, cost check, pity engine, 50/50, dupes→constellation/shards, history cap 200, balance deducted via the economy table + transaction log.
- **First-clear reward**: `dice_claim_first_clear_txn` — server-authoritative balance credit, **idempotent** on `campaign.first_clear` (can't pay twice), and **sequential** (a stage's reward requires the previous stage already cleared, mirroring the client's unlock order). Validates `stage` against `dice_data.CAMPAIGN_STAGE_IDS`.
- **Best wave**: `dg_set_best_wave` stores the endless high score (monotonic, cosmetic/untrusted).
- **Trust model**: Because combat is client-resolved (consistent with every other game in this app), reward grants are client-trusted but bounded by idempotency + sequence checks to a small finite amount.

### Logging System
- **File**: `chat_logs.json` - JSON array of log entries with unique IDs
- **Types**: chat, dm, gc - each with timestamp, sender, text, and type-specific fields
- **Timezone**: Mountain Time (America/Denver) via ZoneInfo or pytz fallback
- **No auto-clear**: Logs persist until manually deleted by owner
- **Per-entry deletion**: Owner can delete individual log entries by ID
- **Filters**: Type, sender, and text search in logs modal

### User Customization
- **Settings modal**: Accessible via gear icon in header
- **Background image**: URL-based, applied to body for full-page coverage
- **Background blur**: Slider (0-20px) for backdrop blur effect
- **Accent color**: Color picker, overrides --accent CSS variable
- **Text color**: Color picker, overrides --text-primary, --text-secondary, --text-tertiary, --text-muted CSS variables (auto-derived)
- **Font size**: Small/Normal/Large/Extra Large options
- **Chat density**: Default/Compact/Cozy message spacing
- **Notification sounds**: Toggle on/off for message notification beeps
- **Persistence**: All settings saved to localStorage
- **Reset**: Button to clear all customizations

### Entertaining Features
- **Typing indicator**: Shows "X is typing..." in chat when others type (debounced 2s)
- **User status**: Online/Idle/DND/Invisible status with colored dot on avatar
- **Notification sounds**: Beep sound for new messages and DMs (Web Audio API)

### External Dependencies
- **aiohttp**: Python async web framework
- **SESSION_SECRET**: Environment variable used to derive owner token

### Environment Variables Required
- `SESSION_SECRET`: Used to generate owner token (falls back to random if not set)
- `DATABASE_URL`: PostgreSQL connection string (available but not currently used by chat)
