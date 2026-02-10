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

### Key Design Decisions
1. **Three-tier join page**: Single page at `/` offers Guest, Admin, or Owner choice
2. **Owner stable identity**: Owner DMs use internal `~admin~` identity for dm_key
3. **Staff admin identity**: Staff DMs use `~staff:<key>~` identity for dm_key
4. **Admin accounts**: Created by owner with fixed display names, stored in `admin_accounts` dict
5. **In-memory storage**: All messages and DM history stored in Python dicts (not persistent)
6. **Three theme system**: Dark (default), Light, Midnight - stored in localStorage
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
- **Accent color**: Color picker, overrides --accent CSS variable
- **Text color**: Color picker, overrides --text-primary CSS variable
- **Persistence**: All settings saved to localStorage
- **Reset**: Button to clear all customizations

### External Dependencies
- **aiohttp**: Python async web framework
- **SESSION_SECRET**: Environment variable used to derive owner token

### Environment Variables Required
- `SESSION_SECRET`: Used to generate owner token (falls back to random if not set)
- `DATABASE_URL`: PostgreSQL connection string (available but not currently used by chat)
