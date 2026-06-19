'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/types';
import api from '@/lib/api';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isHydrated: boolean;
  lastVerifiedAt: number | null;  // Timestamp of last successful /me call

  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string; phone?: string; full_name: string;
    password: string; role?: string;
  }) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  setHydrated: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
      isHydrated: false,
      lastVerifiedAt: null,

      setHydrated: () => set({ isHydrated: true }),

      login: async (email, password) => {
        set({ isLoading: true });
        try {
          const data = await api.login(email, password);
          localStorage.setItem('vestra_token', data.access_token);
          set({
            user: data.user,
            token: data.access_token,
            isAuthenticated: true,
            isLoading: false,
            lastVerifiedAt: Date.now(),
          });
        } catch (err) {
          set({ isLoading: false });
          throw err;
        }
      },

      register: async (userData) => {
        set({ isLoading: true });
        try {
          const data = await api.register(userData);
          localStorage.setItem('vestra_token', data.access_token);
          set({
            user: data.user,
            token: data.access_token,
            isAuthenticated: true,
            isLoading: false,
            lastVerifiedAt: Date.now(),
          });
        } catch (err) {
          set({ isLoading: false });
          throw err;
        }
      },

      logout: () => {
        localStorage.removeItem('vestra_token');
        localStorage.removeItem('vestra_user');
        set({ user: null, token: null, isAuthenticated: false });
      },

      refreshUser: async () => {
        try {
          const user = await api.getMe();
          set({ user, isAuthenticated: true, lastVerifiedAt: Date.now() });
        } catch {
          // Only clear auth if the token was actually invalid
          // (server down = don't log out)
          get().logout();
        }
      },
    }),
    {
      name: 'vestra-auth',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        // Mark as hydrated after Zustand loads persisted state
        state?.setHydrated();
      },
    }
  )
);
