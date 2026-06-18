'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, Spinner, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import { formatRelativeTime } from '@/lib/utils';
import { MessageSquare, ArrowRight, Mail } from 'lucide-react';

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
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConv, setActiveConv] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMsg, setNewMsg] = useState('');
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    loadInbox();
  }, []);

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

  const loadConversation = async (otherUserId: number) => {
    setActiveConv(otherUserId);
    try {
      const res = await api.client.get(`/api/messages/conversation/${otherUserId}`);
      setMessages(res.data.messages || []);
    } catch (err) {
      console.error('Failed to load conversation:', err);
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMsg.trim() || !activeConv) return;
    setSending(true);
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
          {/* Conversation List */}
          <div className="md:col-span-1">
            <Card padding="none">
              {loading ? (
                <div className="flex justify-center py-12"><Spinner /></div>
              ) : conversations.length === 0 ? (
                <div className="text-center py-12 px-4">
                  <Mail className="w-10 h-10 text-gray-200 mx-auto mb-3" />
                  <p className="text-sm text-gray-500">No messages yet</p>
                  <p className="text-xs text-gray-400 mt-1">Messages from buyers and sellers will appear here</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-50">
                  {conversations.map((conv) => (
                    <button
                      key={conv.message_id}
                      onClick={() => loadConversation(conv.other_user_id)}
                      className={`w-full text-left p-4 hover:bg-gray-50 transition-colors ${
                        activeConv === conv.other_user_id ? 'bg-emerald-50 border-l-2 border-emerald-500' : ''
                      } ${!conv.is_read ? 'bg-blue-50/30' : ''}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className={`text-sm truncate ${!conv.is_read ? 'font-semibold text-gray-900' : 'text-gray-700'}`}>
                            {conv.subject || `Property #${conv.property_id || 'N/A'}`}
                          </p>
                          <p className="text-xs text-gray-400 truncate mt-0.5">{conv.last_message}</p>
                        </div>
                        <div className="flex-shrink-0 text-right">
                          <p className="text-xs text-gray-400">{formatRelativeTime(conv.created_at)}</p>
                          {!conv.is_read && <div className="w-2 h-2 bg-blue-500 rounded-full ml-auto mt-1" />}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* Message View */}
          <div className="md:col-span-2">
            {activeConv === null ? (
              <Card className="text-center py-16">
                <MessageSquare className="w-12 h-12 text-gray-200 mx-auto mb-3" />
                <h3 className="font-semibold text-gray-700 mb-1">Select a conversation</h3>
                <p className="text-sm text-gray-400">Choose a message from the left to view it</p>
              </Card>
            ) : (
              <Card padding="none" className="flex flex-col h-[500px]">
                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {messages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex ${msg.sender_id === activeConv ? 'justify-start' : 'justify-end'}`}
                      title={`Sent: ${msg.created_at}`}
                    >
                      <div
                        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                          msg.sender_id === activeConv
                            ? 'bg-gray-100 text-gray-900 rounded-tl-sm'
                            : 'bg-emerald-600 text-white rounded-tr-sm'
                        }`}
                      >
                        {msg.body}
                      </div>
                    </div>
                  ))}
                  {messages.length === 0 && (
                    <div className="text-center py-12 text-gray-400 text-sm">No messages in this conversation yet.</div>
                  )}
                </div>

                {/* Compose */}
                <form onSubmit={handleSend} className="border-t border-gray-100 p-3 flex gap-2">
                  <input
                    type="text"
                    value={newMsg}
                    onChange={(e) => setNewMsg(e.target.value)}
                    placeholder="Type a message..."
                    className="flex-1 border border-gray-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                  <Button type="submit" size="sm" loading={sending} disabled={!newMsg.trim()}>
                    Send
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
