'use client'

import { useState, useCallback, useEffect } from 'react'

/**
 * Generic localStorage hook with SSR safety, cross-tab sync, and error handling.
 *
 * @example
 * const [recentViews, setRecentViews] = useLocalStorage<number[]>('recent_views', [])
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T,
): [T, (value: T | ((prev: T) => T)) => void, () => void] {
  // Initialize with initialValue for SSR safety
  const [storedValue, setStoredValue] = useState<T>(initialValue)
  const [isHydrated, setIsHydrated] = useState(false)

  // Hydrate from localStorage on mount
  useEffect(() => {
    try {
      const item = window.localStorage.getItem(key)
      if (item !== null) {
        setStoredValue(JSON.parse(item))
      }
    } catch (error) {
      console.warn(`useLocalStorage: Error reading key "${key}":`, error)
    }
    setIsHydrated(true)
  }, [key])

  // Listen for cross-tab changes
  useEffect(() => {
    if (!isHydrated) return

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === key && e.newValue !== null) {
        try {
          setStoredValue(JSON.parse(e.newValue))
        } catch {
          // Ignore parse errors from other tabs
        }
      } else if (e.key === key && e.newValue === null) {
        setStoredValue(initialValue)
      }
    }

    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [key, initialValue, isHydrated])

  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      try {
        setStoredValue((prev) => {
          const newValue = value instanceof Function ? value(prev) : value
          window.localStorage.setItem(key, JSON.stringify(newValue))
          return newValue
        })
      } catch (error) {
        console.warn(`useLocalStorage: Error setting key "${key}":`, error)
      }
    },
    [key],
  )

  const removeValue = useCallback(() => {
    try {
      window.localStorage.removeItem(key)
      setStoredValue(initialValue)
    } catch (error) {
      console.warn(`useLocalStorage: Error removing key "${key}":`, error)
    }
  }, [key, initialValue])

  return [storedValue, setValue, removeValue]
}

/**
 * Non-reactive localStorage helper for use outside React components or
 * when you don't need re-renders on value changes.
 */
export const localStorageHelper = {
  get<T>(key: string, fallback: T): T {
    try {
      const item = localStorage.getItem(key)
      return item ? JSON.parse(item) : fallback
    } catch {
      return fallback
    }
  },

  set<T>(key: string, value: T): void {
    try {
      localStorage.setItem(key, JSON.stringify(value))
    } catch (error) {
      console.warn(`localStorageHelper: Error setting "${key}":`, error)
    }
  },

  remove(key: string): void {
    try {
      localStorage.removeItem(key)
    } catch (error) {
      console.warn(`localStorageHelper: Error removing "${key}":`, error)
    }
  },
}
