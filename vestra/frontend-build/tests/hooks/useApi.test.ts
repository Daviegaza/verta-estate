import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useApi } from "@/hooks/useApi";

// Mock the global API client
const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock("@/lib/api", () => ({
  default: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

describe("useApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useApi("/test"));
    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("fetches data on execute", async () => {
    mockGet.mockResolvedValueOnce({ data: { items: [1, 2, 3] } });

    const { result } = renderHook(() => useApi("/test"));

    await act(async () => {
      await result.current.execute();
    });

    await waitFor(() => {
      expect(result.current.data).toEqual({ items: [1, 2, 3] });
    });
  });

  it("handles errors", async () => {
    mockGet.mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useApi("/test"));

    await act(async () => {
      try {
        await result.current.execute();
      } catch {
        // Expected
      }
    });

    await waitFor(() => {
      expect(result.current.error).toBeTruthy();
    });
  });

  it("sets isLoading during fetch", async () => {
    let resolvePromise: (value: unknown) => void;
    mockGet.mockReturnValueOnce(new Promise((resolve) => { resolvePromise = resolve; }));

    const { result } = renderHook(() => useApi("/test"));

    act(() => {
      result.current.execute();
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(true);
    });

    await act(async () => {
      resolvePromise!({ data: "done" });
    });
  });

  it("caches data with TTL", async () => {
    mockGet.mockResolvedValueOnce({ data: { count: 42 } });

    const { result } = renderHook(() => useApi("/test", { cacheTTL: 30000 }));

    await act(async () => {
      await result.current.execute();
    });

    // Second immediate call should use cached data
    await act(async () => {
      await result.current.execute();
    });

    // Should only have called API once
    expect(mockGet).toHaveBeenCalledTimes(1);
  });

  it("refreshes data", async () => {
    mockGet.mockResolvedValueOnce({ data: "first" });
    mockGet.mockResolvedValueOnce({ data: "second" });

    const { result } = renderHook(() => useApi("/test"));

    await act(async () => {
      await result.current.execute();
    });

    await act(async () => {
      await result.current.refresh();
    });

    await waitFor(() => {
      expect(result.current.data).toBe("second");
    });
  });
});
