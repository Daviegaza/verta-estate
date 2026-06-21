'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, Spinner, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/authStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import api from '@/lib/api';
import { formatRelativeTime } from '@/lib/utils';
import { MessageSquare, Search, ArrowRight, Mail, Send, User as UserIcon } from 'lucide-react';

interface Conversation {
  message_id: number;
  other_user_id: number;
  property_id: number | null;
  subject: string | null;
  last_message: string;
  is_read: boolean;
  created_at: string;
}

interface Message {
  id: number;
  sender_id: number;
  receiver_id: number;
  body: string;
  is_read: boolean;
  property_id: number | null;
  created_at: string;
}

export default function MessagesPage() {
  return (
    <AuthGuard requireAuth>
      <MessagesContent />
    </AuthGuard>
  );
}

function MessagesContent() {
  const { user } = useAuthStore();
  const { subscribe, sendTyping, requestOnlineStatus } = useWebSocket();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConv, setActiveConv] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMsg, setNewMsg] = useState('');
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [typingUsers, setTypingUsers] = useState<Set<number>>(new Set());
  const [onlineUsers, setOnlineUsers] = useState<Set<number>>(new Set());
  const typingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const typingSentRef = useRef(false);

  // ── Scroll to bottom on new messages ─────────────────────────────────────
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // ── WebSocket subscriptions ──────────────────────────────────────────────
  useEffect(() => {
    // Real-time new messages
    const unsubMsg = subscribe('message', (payload) => {
      if (!user) return;

      // If this is the active conversation, append the message
      if (payload.sender_id === activeConv || payload.receiver_id === activeConv) {
        setMessages((prev) => {
          // Avoid duplicates
          if (prev.some((m) => m.id === payload.id)) return prev;
          return [...prev, payload as Message];
        });
      }

      // Refresh inbox to keep conversation list up to date
      loadInbox();
    });

    // Typing indicators
    const unsubTyping = subscribe('typing', (payload) => {
      if (payload.sender_id === activeConv) {
        setTypingUsers((prev) => {
          const next = new Set(prev);
          if (payload.is_typing) {
            next.add(payload.sender_id);
          } else {
            next.delete(payload.sender_id);
          }
          return next;
        });
      }
    });

    // Online status batch
    const unsubOnline = subscribe('online_status_batch', (payload) => {
      setOnlineUsers((prev) => {
        const next = new Set(prev);
        for (const [uid, isOnline] of Object.entries(payload)) {
          if (isOnline) {
            next.add(Number(uid));
          } else {
            next.delete(Number(uid));
          }
        }
        return next;
      });
    });

    return () => {
      unsubMsg();
      unsubTyping();
      unsubOnline();
    };
  }, [activeConv, user, subscribe]);

  // ── Request online status for conversation partners ──────────────────────
  useEffect(() => {
    const partnerIds = conversations.map((c) => c.other_user_id);
    if (partnerIds.length > 0) {
      requestOnlineStatus(partnerIds);
    }
  }, [conversations, requestOnlineStatus]);

  // ── Request online status for active conversation partner ────────────────
  useEffect(() => {
    if (activeConv) {
      requestOnlineStatus([activeConv]);
    }
  }, [activeConv, requestOnlineStatus]);

  // ── Periodic online status refresh ───────────────────────────────────────
  useEffect(() => {
    if (!activeConv) return;
    const interval = setInterval(() => {
      requestOnlineStatus([activeConv]);
    }, 30000);
    return () => clearInterval(interval);
  }, [activeConv, requestOnlineStatus]);

  const loadInbox = async () => {
    try {
      const res = await api.client.get('/api/messages/inbox');
      setConversations(res.data.conversations || []);
      setUnreadCount(res.data.unread_count || 0);
    } catch (err) {
      console.error('Failed to load inbox:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInbox();
  }, []);

  const loadConversation = async (otherUserId: number) => {
    setActiveConv(otherUserId);
    setTypingUsers(new Set());
    try {
      const res = await api.client.get(`/api/messages/conversation/${otherUserId}`);
      const msgs = res.data.messages || [];
      setMessages(msgs);
    } catch (err) {
      console.error('Failed to load conversation:', err);
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMsg.trim() || !activeConv) return;
    setSending(true);
    // Stop typing indicator
    sendTyping(activeConv, false);
    try {
      await api.client.post('/api/messages/', null, {
        params: { receiver_id: activeConv, body: newMsg.trim() },
      });
      setNewMsg('');
      loadConversation(activeConv);
      loadInbox();
    } catch (err) {
      console.error('Failed to send:', err);
    } finally {
      setSending(false);
    }
  };

  // ── Typing indicator handler ─────────────────────────────────────────────
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setNewMsg(e.target.value);
    if (!activeConv) return;

    // Send typing indicator on first keystroke
    if (!typingSentRef.current && e.target.value.trim()) {
      sendTyping(activeConv, true);
      typingSentRef.current = true;
    }

    // Reset typing timeout — stops typing after 2s of inactivity
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    typingTimeoutRef.current = setTimeout(() => {
      if (activeConv) {
        sendTyping(activeConv, false);
      }
      typingSentRef.current = false;
    }, 2000);
  };

  const getOtherPartyName = (conv: Conversation): string => {
    return conv.subject || `User #${conv.other_user_id}`;
  };

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Messages</h1>
            <p className="text-gray-500 text-sm">
              {unreadCount > 0 ? `${unreadCount} unread message${unreadCount > 1 ? 's' : ''}` : 'All caught up!'}
            </p>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {/* ── Conversation List ── */}
          <div className="md:col-span-1">
            <Card padding="none">
              {loading ? (
                <div className="flex justify-center py-12"><Spinner /></div>
              ) : conversations.length === 0 ? (
                <div className="text-center py-16 px-4">
                  <div className="w-14 h-14 bg-emerald-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                    <Mail className="w-7 h-7 text-emerald-600" />
                  </div>
                  <p className="text-base font-semibold text-gray-700 mb-2">No messages yet</p>
                  <p className="text-xs text-gray-400 mb-6 max-w-xs mx-auto">
                    Browse properties and reach out to agents or sellers to start a conversation.
                  </p>
                  <div className="flex flex-wrap gap-2 justify-center">
                    <Link href="/market">
                      <Button size="sm" className="gap-1.5">
                        <Search className="w-3.5 h-3.5" />
                        Browse Properties
                      </Button>
                    </Link>
                    <Link href="/verify">
                      <Button size="sm" variant="outline" className="gap-1.5">
                        Verify a Property
                      </Button>
                    </Link>
                  </div>
                </div>
              ) : (
                <div className="divide-y divide-gray-50">
                  {conversations.map((conv) => {
                    const isOnline = onlineUsers.has(conv.other_user_id);
                    return (
                      <button
                        key={conv.message_id}
                        onClick={() => loadConversation(conv.other_user_id)}
                        className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${
                          activeConv === conv.other_user_id ? 'bg-emerald-50 border-l-2 border-emerald-500' : ''
                        } ${!conv.is_read ? 'bg-blue-50/30' : ''}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              {/* Online presence dot */}
                              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${isOnline ? 'bg-emerald-500' : 'bg-gray-300'}`}
                                   title={isOnline ? 'Online' : 'Offline'} />
                              <p className={`text-sm truncate ${!conv.is_read ? 'font-semibold text-gray-900' : 'text-gray-700'}`}>
                                {getOtherPartyName(conv)}
                              </p>
                            </div>
                            <p className="text-xs text-gray-400 truncate mt-0.5 ml-4">{conv.last_message}</p>
                          </div>
                          <div className="flex-shrink-0 text-right">
                            <p className="text-xs text-gray-400">{formatRelativeTime(conv.created_at)}</p>
                            {!conv.is_read && <div className="w-2 h-2 bg-blue-500 rounded-full ml-auto mt-1" />}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </Card>
          </div>

          {/* ── Message View ── */}
          <div className="md:col-span-2">
            {activeConv === null ? (
              <Card className="text-center py-16">
                <MessageSquare className="w-12 h-12 text-gray-200 mx-auto mb-3" />
                <h3 className="font-semibold text-gray-700 mb-1">Select a conversation</h3>
                <p className="text-sm text-gray-400">Choose a message from the left to view it</p>
              </Card>
            ) : (
              <Card padding="none" className="flex flex-col h-[500px]">
                {/* Online status header */}
                <div className="border-b border-gray-100 px-4 py-3 flex items-center gap-2">
                  <div className={`w-2.5 h-2.5 rounded-full ${onlineUsers.has(activeConv) ? 'bg-emerald-500' : 'bg-gray-300'}`} />
                  <span className="text-sm font-medium text-gray-700">
                    {onlineUsers.has(activeConv) ? 'Online' : 'Offline'}
                  </span>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {messages.map((msg) => {
                    const isMine = msg.sender_id !== activeConv;
                    return (
                      <div
                        key={msg.id}
                        className={`flex ${isMine ? 'justify-end' : 'justify-start'}`}
                        title={`Sent: ${msg.created_at}`}
                      >
                        <div
                          className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                            isMine
                              ? 'bg-emerald-600 text-white rounded-tr-sm'
                              : 'bg-gray-100 text-gray-900 rounded-tl-sm'
                          }`}
                        >
                          {msg.body}
                        </div>
                      </div>
                    );
                  })}

                  {/* Typing indicator */}
                  {typingUsers.has(activeConv) && (
                    <div className="flex justify-start">
                      <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-2.5">
                        <div className="flex gap-1">
                          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                      </div>
                    </div>
                  )}

                  {messages.length === 0 && (
                    <div className="text-center py-12 text-gray-400 text-sm">No messages in this conversation yet. Send a message to start.</div>
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {/* Compose */}
                <form onSubmit={handleSend} className="border-t border-gray-100 p-3 flex gap-2">
                  <input
                    type="text"
                    value={newMsg}
                    onChange={handleInputChange}
                    placeholder="Type a message..."
                    className="flex-1 border border-gray-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                  <Button type="submit" size="sm" loading={sending} disabled={!newMsg.trim()}>
                    {sending ? (
                      <Spinner size="sm" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </Button>
                </form>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
