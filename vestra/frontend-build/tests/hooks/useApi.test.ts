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
    const fetcher = () => mockGet("/test");
    const { result } = renderHook(() => useApi(fetcher, { immediate: false }));
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("fetches data on execute", async () => {
    mockGet.mockResolvedValueOnce({ items: [1, 2, 3] });

    const fetcher = () => mockGet("/test");
    const { result } = renderHook(() => useApi(fetcher, { immediate: false }));

    await act(async () => {
      await result.current.execute();
    });

    await waitFor(() => {
      expect(result.current.data).toEqual({ items: [1, 2, 3] });
    });
  });

  it("handles errors", async () => {
    const errorMessage = "Network error";
    // Mock always rejects — with retries:0 so no retry attempts
    mockGet.mockRejectedValue(new Error(errorMessage));

    const fetcher = () => mockGet("/test");
    const { result } = renderHook(() => useApi(fetcher, { immediate: false, retries: 0 }));

    await act(async () => {
      await result.current.execute();
    });

    await waitFor(() => {
      expect(result.current.error).toBe(errorMessage);
    });
  });

  it("sets loading during fetch", async () => {
    let resolvePromise: (value: unknown) => void;
    const promise = new Promise((resolve) => { resolvePromise = resolve; });
    mockGet.mockReturnValueOnce(promise);

    const fetcher = () => mockGet("/test");
    const { result } = renderHook(() => useApi(fetcher, { immediate: false }));

    act(() => {
      result.current.execute();
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(true);
    });

    await act(async () => {
      resolvePromise!({ data: "done" });
    });
  });

  it("caches data with cacheKey", async () => {
    mockGet.mockResolvedValueOnce({ count: 42 });

    const fetcher = () => mockGet("/test");
    const { result } = renderHook(() => useApi(fetcher, { cacheKey: "test-cache", immediate: false }));

    await act(async () => {
      await result.current.execute();
    });

    // Second call should use cached data
    await act(async () => {
      await result.current.execute();
    });

    // Should only have called API once
    expect(mockGet).toHaveBeenCalledTimes(1);
  });

  it("retries data", async () => {
    mockGet.mockResolvedValueOnce("first");
    mockGet.mockResolvedValueOnce("second");

    const fetcher = () => mockGet("/test");
    const { result } = renderHook(() => useApi(fetcher, { immediate: false }));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.data).toBe("first");

    await act(async () => {
      await result.current.retry();
    });

    await waitFor(() => {
      expect(result.current.data).toBe("second");
    });
  });
});
