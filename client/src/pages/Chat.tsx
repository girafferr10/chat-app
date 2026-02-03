import { useEffect, useRef, useState } from "react";
import { 
  Send, 
  Users, 
  LogOut, 
  MessageSquare, 
  MoreVertical,
  Menu
} from "lucide-react";
import { useWebSocket } from "@/hooks/use-websocket";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { 
  Sheet, 
  SheetContent, 
  SheetHeader, 
  SheetTitle, 
  SheetTrigger 
} from "@/components/ui/sheet";
import { format } from "date-fns";
import Login from "./Login";

// Helper to generate consistent avatar colors
const getAvatarColor = (name: string) => {
  const colors = [
    "bg-red-500", "bg-orange-500", "bg-amber-500", 
    "bg-green-500", "bg-emerald-500", "bg-teal-500", 
    "bg-cyan-500", "bg-blue-500", "bg-indigo-500", 
    "bg-violet-500", "bg-purple-500", "bg-fuchsia-500", 
    "bg-pink-500", "bg-rose-500"
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
};

const getInitials = (name: string) => name.substring(0, 2).toUpperCase();

export default function Chat() {
  const {
    connect,
    disconnect,
    sendMessage,
    isConnected,
    username,
    onlineUsers,
    messages
  } = useWebSocket();

  const [inputText, setInputText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (!inputText.trim()) return;
    sendMessage(inputText);
    setInputText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // If not connected or no username, show login
  if (!isConnected || !username) {
    return <Login onJoin={connect} />;
  }

  const UserList = () => (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <h3 className="font-display font-bold text-lg flex items-center gap-2">
          <Users className="w-5 h-5 text-primary" />
          Online ({onlineUsers.length})
        </h3>
      </div>
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-3">
          {onlineUsers.map((user) => (
            <div key={user} className="flex items-center gap-3 p-2 rounded-xl hover:bg-muted/50 transition-colors cursor-default group">
              <div className="relative">
                <Avatar className="border-2 border-background shadow-sm">
                  <AvatarFallback className={`${getAvatarColor(user)} text-white font-medium text-xs`}>
                    {getInitials(user)}
                  </AvatarFallback>
                </Avatar>
                <span className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-background rounded-full animate-pulse"></span>
              </div>
              <div className="flex-1 overflow-hidden">
                <p className="font-medium text-sm truncate">{user}</p>
                <p className="text-xs text-muted-foreground truncate group-hover:text-primary transition-colors">
                  {user === username ? "You" : "Online"}
                </p>
              </div>
            </div>
          ))}
          {onlineUsers.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-4">No one else is online.</p>
          )}
        </div>
      </ScrollArea>
    </div>
  );

  return (
    <div className="h-screen w-full flex flex-col bg-background overflow-hidden">
      {/* Header */}
      <header className="h-16 border-b flex items-center justify-between px-4 lg:px-6 bg-card/80 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-tr from-primary to-violet-400 rounded-xl flex items-center justify-center shadow-lg shadow-primary/20">
            <MessageSquare className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-display font-bold text-xl leading-none">ChatRoom</h1>
            <p className="text-xs text-muted-foreground mt-1">Logged in as <span className="font-medium text-foreground">{username}</span></p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="lg:hidden">
                <Menu className="w-5 h-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-80 p-0 pt-10">
              <UserList />
            </SheetContent>
          </Sheet>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="rounded-full">
                <MoreVertical className="w-5 h-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuLabel>Account</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem 
                className="text-destructive focus:text-destructive cursor-pointer"
                onClick={disconnect}
              >
                <LogOut className="w-4 h-4 mr-2" />
                Leave Chat
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      {/* Main Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar (Desktop) */}
        <aside className="hidden lg:block w-80 border-r bg-card/30 backdrop-blur-sm">
          <UserList />
        </aside>

        {/* Chat Area */}
        <main className="flex-1 flex flex-col bg-slate-50/50 dark:bg-black/20 relative">
          <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 pointer-events-none"></div>

          {/* Messages List */}
          <ScrollArea className="flex-1 p-4 lg:p-6 custom-scrollbar">
            <div className="space-y-6 max-w-4xl mx-auto">
              <div className="flex justify-center my-4">
                <span className="px-3 py-1 bg-muted/50 rounded-full text-xs text-muted-foreground font-medium border">
                  Today, {format(new Date(), "MMMM do")}
                </span>
              </div>

              {messages.map((msg, idx) => {
                // Check if previous message was from same sender to group visually
                const isSequence = idx > 0 && messages[idx - 1].sender === msg.sender;
                
                return (
                  <div
                    key={msg.id}
                    className={`flex flex-col animate-message-pop ${msg.isMe ? "items-end" : "items-start"}`}
                    style={{ animationDelay: `${idx * 0.05}ms` }}
                  >
                    <div className={`flex items-end gap-2 max-w-[85%] sm:max-w-[70%] ${msg.isMe ? "flex-row-reverse" : "flex-row"}`}>
                      {!isSequence && (
                        <Avatar className="w-8 h-8 mb-1 border-2 border-background shadow-sm shrink-0">
                          <AvatarFallback className={`${getAvatarColor(msg.sender)} text-white text-[10px]`}>
                            {getInitials(msg.sender)}
                          </AvatarFallback>
                        </Avatar>
                      )}
                      {isSequence && <div className="w-8 shrink-0" />}

                      <div className={`group relative px-4 py-2.5 shadow-sm transition-all hover:shadow-md
                        ${msg.isMe 
                          ? "bg-primary text-primary-foreground rounded-2xl rounded-tr-sm" 
                          : "bg-white dark:bg-card border border-border/50 text-foreground rounded-2xl rounded-tl-sm"
                        }
                        ${isSequence ? (msg.isMe ? "rounded-tr-2xl mt-1" : "rounded-tl-2xl mt-1") : ""}
                      `}>
                        {/* Sender Name (only if not me and not sequence) */}
                        {!msg.isMe && !isSequence && (
                          <p className={`text-[10px] font-bold mb-1 opacity-70 ${getAvatarColor(msg.sender).replace('bg-', 'text-')}`}>
                            {msg.sender}
                          </p>
                        )}
                        
                        <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">{msg.text}</p>
                        
                        <span className={`text-[10px] absolute -bottom-5 min-w-max opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground
                          ${msg.isMe ? "right-0" : "left-0"}
                        `}>
                          {format(new Date(msg.timestamp), "h:mm a")}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Input Area */}
          <div className="p-4 bg-background border-t z-10">
            <div className="max-w-4xl mx-auto flex gap-3 items-end">
              <div className="flex-1 bg-muted/30 rounded-2xl border focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all">
                <Input
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type a message..."
                  className="bg-transparent border-0 focus-visible:ring-0 h-14 px-4 py-4 resize-none"
                  autoFocus
                />
              </div>
              <Button 
                onClick={handleSend}
                disabled={!inputText.trim()}
                className="h-14 w-14 rounded-2xl shrink-0 shadow-lg shadow-primary/20 hover:shadow-xl hover:shadow-primary/30 transition-all hover:-translate-y-0.5 active:translate-y-0"
              >
                <Send className="w-5 h-5 ml-0.5" />
              </Button>
            </div>
            <p className="text-center text-[10px] text-muted-foreground mt-2">
              Press <kbd className="bg-muted px-1 rounded text-foreground font-sans">Enter</kbd> to send
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}
