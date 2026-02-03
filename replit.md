# replit.md

## Overview

This is a real-time chat application built with a React frontend and Express backend. Users can join with a username and communicate via WebSocket connections. The app features persistent message history stored in PostgreSQL and displays online users in real-time.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: React 18 with TypeScript
- **Routing**: Wouter (lightweight React router)
- **State Management**: TanStack React Query for server state, React hooks for local state
- **UI Components**: shadcn/ui component library built on Radix UI primitives
- **Styling**: Tailwind CSS with CSS variables for theming
- **Build Tool**: Vite with path aliases (`@/` for client/src, `@shared/` for shared code)

### Backend Architecture
- **Framework**: Express 5 running on Node.js
- **Real-time Communication**: Native WebSocket server (ws library) mounted at `/ws` path
- **API Pattern**: REST endpoints for non-realtime operations (username availability check, message history)
- **Build Process**: esbuild bundles server code, Vite handles client build

### Data Flow
- WebSocket handles join, chat messages, user list updates, and message history
- Messages are validated using Zod schemas in the shared routes module
- The shared folder (`/shared`) contains schemas and route definitions used by both client and server

### Key Design Decisions
1. **Single-page chat with conditional login**: The Login component is rendered conditionally inside the Chat page based on WebSocket connection state, avoiding route-based auth complexity
2. **Shared types and validation**: Zod schemas and TypeScript types are shared between client and server via the `/shared` directory
3. **WebSocket-first communication**: Real-time features use WebSocket exclusively; REST is only for initial data fetching and validation

## External Dependencies

### Database
- **PostgreSQL**: Primary data store for users and messages
- **Drizzle ORM**: Type-safe database queries with schema defined in `shared/schema.ts`
- **Connection**: Uses `DATABASE_URL` environment variable via node-postgres pool

### Key Libraries
- **ws**: WebSocket server implementation
- **connect-pg-simple**: PostgreSQL session store (available for session management if needed)
- **date-fns**: Date formatting for message timestamps
- **zod**: Runtime validation for API inputs and WebSocket messages

### Database Schema
- `users` table: id (serial), username (unique text)
- `messages` table: id (serial), userId (integer), displayName (text), content (text), createdAt (timestamp)

### Environment Variables Required
- `DATABASE_URL`: PostgreSQL connection string