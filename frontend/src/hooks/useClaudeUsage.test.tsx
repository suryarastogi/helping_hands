import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";

import type { ClaudeUsageResponse } from "../types";
import { useClaudeUsage, CLAUDE_USAGE_POLL_MS } from "./useClaudeUsage";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const usageResponse: ClaudeUsageResponse = {
  levels: [{ tier: "free", used: 10, limit: 100, resets_at: "2026-04-01T00:00:00Z" }],
  error: null,
  fetched_at: "2026-03-26T12:00:00Z",
};

const errorResponse: ClaudeUsageResponse = {
  levels: [],
  error: "Server returned 500",
  fetched_at: "2026-03-26T12:01:00Z",
};

vi.mock("../App.utils", () => ({
  fetchClaudeUsage: vi.fn(),
}));

import { fetchClaudeUsage } from "../App.utils";
const mockFetch = vi.mocked(fetchClaudeUsage);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useClaudeUsage", () => {
  beforeEach(() => {
    mockFetch.mockResolvedValue(usageResponse);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns null usage and loading=false initially", () => {
    const { result } = renderHook(() => useClaudeUsage());
    expect(result.current.claudeUsage).toBeNull();
    expect(result.current.claudeUsageLoading).toBe(false);
  });

  it("fetches usage on mount", async () => {
    const { result } = renderHook(() => useClaudeUsage());

    await waitFor(() => {
      expect(result.current.claudeUsage).toEqual(usageResponse);
    });
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("polls at CLAUDE_USAGE_POLL_MS interval", async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useClaudeUsage());

    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(result.current.claudeUsage).toEqual(usageResponse);
    mockFetch.mockClear();

    await act(async () => { await vi.advanceTimersByTimeAsync(CLAUDE_USAGE_POLL_MS); });
    expect(mockFetch).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
  });

  it("refreshClaudeUsage calls fetchClaudeUsage with force=true", async () => {
    const { result } = renderHook(() => useClaudeUsage());

    await waitFor(() => {
      expect(result.current.claudeUsage).toEqual(usageResponse);
    });

    mockFetch.mockResolvedValueOnce(errorResponse);
    await act(async () => {
      await result.current.refreshClaudeUsage();
    });

    expect(mockFetch).toHaveBeenCalledWith(true);
    expect(result.current.claudeUsage).toEqual(errorResponse);
  });

  it("sets loading state during manual refresh", async () => {
    const { result } = renderHook(() => useClaudeUsage());

    await waitFor(() => {
      expect(result.current.claudeUsage).toEqual(usageResponse);
    });
    expect(result.current.claudeUsageLoading).toBe(false);

    let resolveRefresh!: (value: ClaudeUsageResponse) => void;
    mockFetch.mockImplementationOnce(
      () => new Promise<ClaudeUsageResponse>((resolve) => { resolveRefresh = resolve; }),
    );

    let refreshPromise: Promise<void>;
    act(() => {
      refreshPromise = result.current.refreshClaudeUsage();
    });
    expect(result.current.claudeUsageLoading).toBe(true);

    await act(async () => {
      resolveRefresh(usageResponse);
      await refreshPromise!;
    });
    expect(result.current.claudeUsageLoading).toBe(false);
  });

  it("cleans up interval on unmount", async () => {
    vi.useFakeTimers();
    const { unmount } = renderHook(() => useClaudeUsage());

    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(mockFetch).toHaveBeenCalledTimes(1);

    unmount();
    mockFetch.mockClear();

    await act(async () => { await vi.advanceTimersByTimeAsync(CLAUDE_USAGE_POLL_MS * 3); });
    expect(mockFetch).toHaveBeenCalledTimes(0);

    vi.useRealTimers();
  });
});
