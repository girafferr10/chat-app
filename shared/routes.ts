import { z } from "zod";
import { insertUserSchema, insertMessageSchema, users, messages } from "./schema";

export const api = {
  // We primarily use WebSockets, but REST is good for checking availability or history
  messages: {
    list: {
      method: "GET" as const,
      path: "/api/messages",
      responses: {
        200: z.array(z.custom<typeof messages.$inferSelect>()),
      },
    },
  },
  users: {
    checkAvailability: {
      method: "POST" as const,
      path: "/api/users/check",
      input: z.object({ username: z.string() }),
      responses: {
        200: z.object({ available: z.boolean() }),
      },
    },
  }
};

// WebSocket Message Types
export const WS_TYPE = {
  JOIN: 'join',
  CHAT: 'chat',
  USER_LIST: 'user_list',
  HISTORY: 'history',
  ERROR: 'error'
} as const;

export type WSMessage = 
  | { type: typeof WS_TYPE.JOIN; username: string }
  | { type: typeof WS_TYPE.CHAT; text: string };

export type WSPayload = 
  | { type: typeof WS_TYPE.USER_LIST; users: string[] }
  | { type: typeof WS_TYPE.CHAT; sender: string; text: string; timestamp: string }
  | { type: typeof WS_TYPE.HISTORY; messages: {sender: string, text: string, timestamp: string}[] }
  | { type: typeof WS_TYPE.ERROR; message: string };

export function buildUrl(path: string, params?: Record<string, string | number>): string {
  let url = path;
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (url.includes(`:${key}`)) {
        url = url.replace(`:${key}`, String(value));
      }
    });
  }
  return url;
}
