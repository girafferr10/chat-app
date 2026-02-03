import type { Express } from "express";
import type { Server } from "http";
import { WebSocketServer, WebSocket } from "ws";
import { storage } from "./storage";
import { api, WS_TYPE, type WSMessage, type WSPayload } from "@shared/routes";
import { z } from "zod";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  // REST API for checking username availability (optional, useful for validation)
  app.post(api.users.checkAvailability.path, async (req, res) => {
    try {
      const { username } = api.users.checkAvailability.input.parse(req.body);
      const existing = await storage.getUserByUsername(username);
      res.json({ available: !existing });
    } catch (error) {
      res.status(400).json({ message: "Invalid input" });
    }
  });
  
  app.get(api.messages.list.path, async (req, res) => {
    const messages = await storage.getMessages();
    res.json(messages);
  });

  // WebSocket Server
  const wss = new WebSocketServer({ server: httpServer, path: '/ws' });

  // Store connected clients: WebSocket -> { userId, username }
  const clients = new Map<WebSocket, { userId: number, username: string }>();

  function broadcast(payload: WSPayload) {
    const message = JSON.stringify(payload);
    wss.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(message);
      }
    });
  }

  function broadcastUserList() {
    const users = Array.from(clients.values()).map(c => c.username);
    broadcast({ type: WS_TYPE.USER_LIST, users });
  }

  wss.on('connection', (ws) => {
    console.log('Client connected');

    ws.on('message', async (data) => {
      try {
        const rawMessage = JSON.parse(data.toString());
        // Simple validation - in real app use Zod
        
        if (rawMessage.type === WS_TYPE.JOIN) {
          const { username } = rawMessage;
          if (!username) return;

          // Find or create user
          let user = await storage.getUserByUsername(username);
          if (!user) {
            user = await storage.createUser({ username });
          }

          clients.set(ws, { userId: user.id, username: user.username });
          
          // Send history to the new user
          const history = await storage.getMessages();
          const historyPayload: WSPayload = {
            type: WS_TYPE.HISTORY,
            messages: history.map(m => ({
              sender: m.displayName,
              text: m.content,
              timestamp: m.createdAt?.toISOString() || new Date().toISOString()
            }))
          };
          ws.send(JSON.stringify(historyPayload));

          // Announce join
          broadcast({
            type: WS_TYPE.CHAT,
            sender: "System",
            text: `${username} joined the chat`,
            timestamp: new Date().toISOString()
          });
          
          broadcastUserList();
        } else if (rawMessage.type === WS_TYPE.CHAT) {
          const clientData = clients.get(ws);
          if (!clientData) return; // Not joined yet

          const content = rawMessage.text;
          
          // Persist message
          const message = await storage.createMessage({
            userId: clientData.userId,
            displayName: clientData.username,
            content
          });

          // Broadcast message
          broadcast({
            type: WS_TYPE.CHAT,
            sender: clientData.username,
            text: content,
            timestamp: message.createdAt?.toISOString() || new Date().toISOString()
          });
        }
      } catch (err) {
        console.error('WebSocket error:', err);
        ws.send(JSON.stringify({ type: WS_TYPE.ERROR, message: "Invalid message format" }));
      }
    });

    ws.on('close', () => {
      const clientData = clients.get(ws);
      if (clientData) {
        clients.delete(ws);
        broadcast({
          type: WS_TYPE.CHAT,
          sender: "System",
          text: `${clientData.username} left the chat`,
          timestamp: new Date().toISOString()
        });
        broadcastUserList();
      }
    });
  });

  return httpServer;
}
