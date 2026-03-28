import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";

import type { ServiceHealthState } from "../types";
import { useServiceHealth, SERVICE_HEALTH_POLL_MS } from "./useServiceHealth";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const healthyState: ServiceHealthState = {
  reachable: true,
  health: { redis: "ok", db: "ok", workers: "ok" },
};

const unreachableState: ServiceHealthState = {
  reachable: false,
  health: null,
};

vi.mock("../App.utils", () => ({
  fetchServiceHealth: vi.fn(),
}));

import { fetchServiceHealth } from "../App.utils";
const mockFetch = vi.mocked(fetchServiceHealth);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useServiceHealth", () => {
  beforeEach(() => {
    mockFetch.mockResolvedValue(healthyState);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns null initially then fetches on mount", async () => {
    const { result } = renderHook(() => useServiceHealth());
    expect(result.current).toBeNull();

    await waitFor(() => {
      expect(result.current).toEqual(healthyState);
    });
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("polls at SERVICE_HEALTH_POLL_MS interval", async () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useServiceHealth());

    // Flush initial fetch
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(result.current).toEqual(healthyState);

    mockFetch.mockClear();

    // Advance one poll interval
    await act(async () => { await vi.advanceTimersByTimeAsync(SERVICE_HEALTH_POLL_MS); });
    expect(mockFetch).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
  });

  it("updates state when health changes", async () => {
    vi.useFakeTimers();
    mockFetch.mockResolvedValueOnce(healthyState).mockResolvedValueOnce(unreachableState);

    const { result } = renderHook(() => useServiceHealth());

    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(result.current).toEqual(healthyState);

    await act(async () => { await vi.advanceTimersByTimeAsync(SERVICE_HEALTH_POLL_MS); });
    expect(result.current).toEqual(unreachableState);

    vi.useRealTimers();
  });

  it("cleans up interval on unmount", async () => {
    vi.useFakeTimers();
    const { unmount } = renderHook(() => useServiceHealth());

    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(mockFetch).toHaveBeenCalledTimes(1);

    unmount();
    mockFetch.mockClear();

    // Advancing timer after unmount should NOT trigger more fetches
    await act(async () => { await vi.advanceTimersByTimeAsync(SERVICE_HEALTH_POLL_MS * 3); });
    expect(mockFetch).toHaveBeenCalledTimes(0);

    vi.useRealTimers();
  });
});
