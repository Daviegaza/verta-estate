"use client";

import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "vestra_recently_viewed";
const MAX_ITEMS = 8;

export interface RecentView {
  id: number;
  title: string;
  city: string;
  price: number;
  currency: string;
  image?: string;
  viewedAt: number;
}

export function useRecentlyViewed() {
  const [items, setItems] = useState<RecentView[]>([]);
  const [hydrated, setHydrated] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) setItems(parsed.slice(0, MAX_ITEMS));
      }
    } catch { /* corrupted — start fresh */ }
    setHydrated(true);
  }, []);

  // Persist whenever items change
  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch { /* quota exceeded — nothing we can do */ }
  }, [items, hydrated]);

  const addView = useCallback((property: {
    id: number;
    title: string;
    city: string;
    price: number;
    currency?: string;
  }) => {
    setItems((prev) => {
      const now = Date.now();
      // Remove existing entry for this property, add at front
      const filtered = prev.filter((v) => v.id !== property.id);
      const entry: RecentView = {
        id: property.id,
        title: property.title,
        city: property.city,
        price: property.price,
        currency: property.currency || "KES",
        image: undefined,
        viewedAt: now,
      };
      return [entry, ...filtered].slice(0, MAX_ITEMS);
    });
  }, []);

  const clearAll = useCallback(() => {
    setItems([]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const removeItem = useCallback((id: number) => {
    setItems((prev) => prev.filter((v) => v.id !== id));
  }, []);

  return { items, addView, clearAll, removeItem, hydrated };
}
