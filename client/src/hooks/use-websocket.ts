import { useState, useEffect, useRef, useCallback } from "react";
import { WS_TYPE, type WSMessage, type WSPayload } from "@shared/routes";
import { useToast } from "@/hooks/use-toast";

type MessageHandler = (payload: WSPayload) => void;

interface ChatMessage {
  id: string; // generated locally for list keys
  sender: string;
  text: string;
  timestamp: string;
  isMe: boolean;
}

export function useWebSocket() {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [onlineUsers, setOnlineUsers] = useState<string[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const { toast } = useToast();
  
  // Keep track of the current username ref for "isMe" checks inside callbacks
  const usernameRef = useRef<string | null>(null);
  useEffect(() => { usernameRef.current = username; }, [username]);

  const connect = useCallback((user: string) => {
    const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    const wsUrl = `${protocol}${window.location.host}/ws`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("Connected to WebSocket");
      setIsConnected(true);
      setUsername(user);
      
      // Send join message immediately
      const joinMsg: WSMessage = { type: WS_TYPE.JOIN, username: user };
      ws.send(JSON.stringify(joinMsg));
    };

    ws.onmessage = (event) => {
      try {
        const payload: WSPayload = JSON.parse(event.data);
        handlePayload(payload);
      } catch (err) {
        console.error("Failed to parse WS message", err);
      }
    };

    ws.onclose = () => {
      console.log("Disconnected from WebSocket");
      setIsConnected(false);
      setUsername(null);
      toast({
        title: "Disconnected",
        description: "Connection to chat server lost.",
        variant: "destructive",
      });
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setIsConnected(false);
    };

    setSocket(ws);
  }, [toast]);

  const disconnect = useCallback(() => {
    if (socket) {
      socket.close();
      setSocket(null);
      setIsConnected(false);
      setUsername(null);
      setMessages([]);
      setOnlineUsers([]);
    }
  }, [socket]);

  const sendMessage = useCallback((text: string) => {
    if (socket && isConnected) {
      const msg: WSMessage = { type: WS_TYPE.CHAT, text };
      socket.send(JSON.stringify(msg));
    }
  }, [socket, isConnected]);

  const handlePayload = (payload: WSPayload) => {
    switch (payload.type) {
      case WS_TYPE.USER_LIST:
        setOnlineUsers(payload.users);
        break;
        
      case WS_TYPE.HISTORY:
        const history = payload.messages.map((msg, idx) => ({
          id: `hist-${idx}-${msg.timestamp}`,
          sender: msg.sender,
          text: msg.text,
          timestamp: msg.timestamp,
          isMe: msg.sender === usernameRef.current,
        }));
        setMessages(history);
        break;

      case WS_TYPE.CHAT:
        const newMsg: ChatMessage = {
          id: `msg-${Date.now()}-${Math.random()}`,
          sender: payload.sender,
          text: payload.text,
          timestamp: payload.timestamp,
          isMe: payload.sender === usernameRef.current,
        };
        setMessages((prev) => [...prev, newMsg]);
        break;

      case WS_TYPE.ERROR:
        toast({
          title: "Error",
          description: payload.message,
          variant: "destructive",
        });
        break;
    }
  };

  return {
    connect,
    disconnect,
    sendMessage,
    isConnected,
    username,
    onlineUsers,
    messages
  };
}
