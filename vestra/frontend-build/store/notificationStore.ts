'use client'

import { create } from 'zustand'
import { api } from '@/lib/api'

export interface AppNotification {
  id: number
  user_id: number
  type: 'info' | 'success' | 'warning' | 'error' | 'payment' | 'verification' | 'message' | 'rental'
  title: string
  message: string
  action_url?: string | null
  is_read: boolean
  created_at: string
}

/** Internal helper: cast API response items to AppNotification */
function asNotifications(list: Record<string, unknown>[]): AppNotification[] {
  return list as unknown as AppNotification[]
}

interface NotificationState {
  notifications: AppNotification[]
  unreadCount: number
  isLoading: boolean
  error: string | null
  lastFetchedAt: number | null

  fetchNotifications: (force?: boolean) => Promise<void>
  fetchUnreadCount: () => Promise<void>
  markAsRead: (id: number) => Promise<void>
  markAllAsRead: () => Promise<void>
  addNotification: (notification: AppNotification) => void
  clearAll: () => void
}

const CACHE_TTL = 30_000 // 30 seconds

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  isLoading: false,
  error: null,
  lastFetchedAt: null,

  fetchNotifications: async (force = false) => {
    const { lastFetchedAt, isLoading } = get()
    const now = Date.now()

    // Skip if cached and fresh
    if (!force && lastFetchedAt && now - lastFetchedAt < CACHE_TTL) return
    if (isLoading) return

    set({ isLoading: true, error: null })

    try {
      const res = await api.getNotifications()
      const items = asNotifications(res.data || [])
      set({
        notifications: items,
        unreadCount: items.filter((n) => !n.is_read).length,
        isLoading: false,
        lastFetchedAt: now,
      })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch notifications'
      set({ isLoading: false, error: message })
    }
  },

  fetchUnreadCount: async () => {
    try {
      const res = await api.getNotifications()
      const items = asNotifications(res.data || [])
      set({ unreadCount: items.filter((n) => !n.is_read).length })
    } catch {
      // Silent fail for unread count polling
    }
  },

  markAsRead: async (id: number) => {
    set((state) => ({
      notifications: state.notifications.map((n) =>
        n.id === id ? { ...n, is_read: true } : n,
      ),
      unreadCount: Math.max(0, state.unreadCount - 1),
    }))

    try {
      await api.markNotificationRead(id)
    } catch {
      // Revert on failure
      get().fetchNotifications(true)
    }
  },

  markAllAsRead: async () => {
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, is_read: true })),
      unreadCount: 0,
    }))

    try {
      await api.markAllNotificationsRead()
    } catch {
      get().fetchNotifications(true)
    }
  },

  addNotification: (notification: AppNotification) => {
    set((state) => ({
      notifications: [notification, ...state.notifications].slice(0, 50), // Keep max 50
      unreadCount: notification.is_read ? state.unreadCount : state.unreadCount + 1,
    }))
  },

  clearAll: () => {
    set({
      notifications: [],
      unreadCount: 0,
      isLoading: false,
      error: null,
      lastFetchedAt: null,
    })
  },
}))
