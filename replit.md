# replit.md

## Overview

This is a real-time chat application built with Python using aiohttp for WebSocket-based communication. Features a Discord-like dark theme with Light and Midnight alternatives. Users join as Guest or Admin from a unified page at `/`. The app supports group chat (#General channel), direct messaging (DMs), a tabbed interface with games, and admin controls.

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
- `games/blackjack_multi.py` - Multiplayer Blackjack (WebSocket rooms)
- `games/minesweeper.py` - Minesweeper (singleplayer)

### Routes
- `GET /` - Main page with unified Guest/Admin join flow
- `GET /admin` - Legacy admin login page
- `GET /ws` - WebSocket endpoint for guest clients
- `GET /admin-ws` - WebSocket endpoint for admin (requires `?token=...`)

### WebSocket Message Types
- `join` - Guest sends username to join
- `chat` - Group message in #General
- `dm_message` - Send a direct message to another user
- `dm_open` - Request DM history with a user
- `dm` - Server delivers DM to participants
- `dm_history` - Server sends DM conversation history
- `dm_pairs` - Server sends list of active DM pairs (admin only)
- `dm_spy_open` - Admin requests to view a specific DM pair
- `dm_spy` - Server sends full DM conversation for spy viewing
- `dm_spy_update` - Real-time DM update sent to admin
- `users` - Online user list broadcast
- `system` - System messages (join/leave)
- `banned_list` - Banned user list (admin only)
- `kick` / `ban` / `unban` - Admin moderation actions
- `bj_action` - Multiplayer blackjack actions (create/join/hit/stand/leave/start)
- `bj_room_created` / `bj_joined` / `bj_state` / `bj_error` - Server responses for multiplayer blackjack

### Key Design Decisions
1. **Unified join page**: Single page at `/` offers Guest or Admin choice
2. **Admin stable identity**: Admin DMs use internal `~admin~` identity for dm_key so changing display name doesn't break conversation history
3. **In-memory storage**: All messages and DM history stored in Python dicts (not persistent)
4. **Three theme system**: Dark (default), Light, Midnight - stored in localStorage
5. **Username restrictions**: Guest usernames cannot contain "admin" or "mod" (case-insensitive)
6. **Tabbed interface**: Bottom tab bar with singleton tabs (one Chat, one Games allowed). New Tab picker for adding tabs.
7. **Game modules**: Each game in its own Python file returning JS code strings, injected into the HTML at render time

### Admin Features
- **Admin Token**: Derived from SESSION_SECRET environment variable via SHA-256 hash
- **Display Name**: Changeable anytime via input field; applies to both chat and DMs
- **Kick/Ban**: Hover over users in sidebar to see kick/ban buttons
- **DM Spy**: View all active DM conversations between users
- **Banned List**: See and unban banned users

### Tabbed Interface
- **Tab bar**: At the bottom of the main panel
- **Chat tab**: Singleton - contains the chat area with messages, emoji picker, send button
- **Games tab**: Singleton - minimalistic list of games with search, each game opens in play area
- **New Tab**: Opens a picker with Chat and Games options, searchable
- **Auto-open**: When all tabs closed, auto-opens a new picker tab

### External Dependencies
- **aiohttp**: Python async web framework
- **SESSION_SECRET**: Environment variable used to derive admin token

### Environment Variables Required
- `SESSION_SECRET`: Used to generate admin token (falls back to random if not set)
- `DATABASE_URL`: PostgreSQL connection string (available but not currently used by chat)
