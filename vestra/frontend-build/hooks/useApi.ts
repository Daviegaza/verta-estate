'use client';

import { useState, useCallback, useRef, useEffect } from 'react';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  retryCount: number;
}

interface UseApiOptions {
  immediate?: boolean;
  retries?: number;
  cacheKey?: string;
}

/**
 * Custom hook for API calls with built-in loading, error, retry, and caching.
 *
 * Usage:
 *   const { data, loading, error, execute, retry } = useApi(
 *     () => api.listProperties({ city: 'Nairobi' }),
 *     { immediate: true }
 *   );
 */
export function useApi<T>(
  apiFn: () => Promise<T>,
  options: UseApiOptions = {}
): UseApiState<T> & {
  execute: () => Promise<T | null>;
  retry: () => Promise<T | null>;
  reset: () => void;
} {
  const { immediate = false, retries = 2, cacheKey } = options;
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: immediate,
    error: null,
    retryCount: 0,
  });

  const mountedRef = useRef(true);
  const cacheRef = useRef<Map<string, { data: T; timestamp: number }>>(
    typeof window !== 'undefined' ? new Map() : new Map()
  );

  useEffect(() => {
    return () => { mountedRef.current = false; };
  }, []);

  const executeFn = useCallback(async (isRetry = false): Promise<T | null> => {
    // Check cache first
    if (cacheKey && !isRetry) {
      const cached = cacheRef.current.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < 30000) {
        if (mountedRef.current) {
          setState((s) => ({ ...s, data: cached.data, loading: false, error: null }));
        }
        return cached.data;
      }
    }

    if (mountedRef.current) {
      setState((s) => ({
        ...s,
        loading: true,
        error: null,
        retryCount: isRetry ? s.retryCount + 1 : s.retryCount,
      }));
    }

    let attempt = 0;
    const maxAttempts = 1 + retries;

    while (attempt < maxAttempts) {
      try {
        const data = await apiFn();
        if (mountedRef.current) {
          setState({ data, loading: false, error: null, retryCount: 0 });
        }
        // Cache the result
        if (cacheKey) {
          cacheRef.current.set(cacheKey, { data, timestamp: Date.now() });
        }
        return data;
      } catch (err: any) {
        attempt++;
        const message = err?.response?.data?.message || err?.message || 'Request failed';

        if (attempt >= maxAttempts) {
          if (mountedRef.current) {
            setState((s) => ({ ...s, loading: false, error: message }));
          }
          return null;
        }

        // Exponential backoff
        await new Promise((r) => setTimeout(r, Math.pow(2, attempt) * 500));
      }
    }
    return null;
  }, [apiFn, retries, cacheKey]);

  const retryFn = useCallback(() => executeFn(true), [executeFn]);

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null, retryCount: 0 });
  }, []);

  // Execute immediately if requested
  useEffect(() => {
    if (immediate) {
      executeFn();
    }
  }, [immediate, executeFn]);

  return {
    ...state,
    execute: () => executeFn(false),
    retry: retryFn,
    reset,
  };
}

/**
 * Hook for paginated data with infinite scroll support.
 */
export function usePaginatedApi<T>(
  apiFn: (page: number) => Promise<{ items: T[]; total: number; pages: number }>,
  options: UseApiOptions = {}
) {
  const [items, setItems] = useState<T[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);

  const loadPage = useCallback(async (pageNum: number, append = false) => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFn(pageNum);
      const newItems = result.items || [];
      setItems((prev) => append ? [...prev, ...newItems] : newItems);
      setTotalPages(result.pages || 1);
      setTotal(result.total || 0);
      setHasMore(pageNum < (result.pages || 1));
      setPage(pageNum);
      return result;
    } catch (err: any) {
      setError(err?.message || 'Failed to load data');
      return null;
    } finally {
      setLoading(false);
    }
  }, [apiFn]);

  const loadMore = useCallback(() => {
    if (!loading && hasMore) {
      return loadPage(page + 1, true);
    }
    return Promise.resolve(null);
  }, [loading, hasMore, page, loadPage]);

  const refresh = useCallback(() => loadPage(1), [loadPage]);

  // Load first page on mount
  useEffect(() => {
    if (options.immediate !== false) {
      loadPage(1);
    }
  }, [loadPage, options.immediate]);

  return {
    items, loading, error, page, totalPages, total,
    hasMore, loadMore, refresh, loadPage,
    isEmpty: !loading && items.length === 0,
  };
}
