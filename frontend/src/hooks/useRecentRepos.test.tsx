import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { useRecentRepos } from "./useRecentRepos";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STORAGE_KEY = "hh_recent_repos";

function seedStorage(repos: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(repos));
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useRecentRepos", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // -- Initial state --------------------------------------------------------

  it("returns an empty list when localStorage is empty", () => {
    const { result } = renderHook(() => useRecentRepos());
    expect(result.current.recentRepos).toEqual([]);
  });

  it("loads existing repos from localStorage on mount", () => {
    seedStorage(["repo-a", "repo-b"]);
    const { result } = renderHook(() => useRecentRepos());
    expect(result.current.recentRepos).toEqual(["repo-a", "repo-b"]);
  });

  it("filters out non-string entries from localStorage", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(["valid", 42, null, "also-valid"]));
    const { result } = renderHook(() => useRecentRepos());
    expect(result.current.recentRepos).toEqual(["valid", "also-valid"]);
  });

  it("returns empty list when localStorage contains invalid JSON", () => {
    localStorage.setItem(STORAGE_KEY, "not-json");
    const { result } = renderHook(() => useRecentRepos());
    expect(result.current.recentRepos).toEqual([]);
  });

  it("returns empty list when localStorage contains a non-array JSON value", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ repo: "a" }));
    const { result } = renderHook(() => useRecentRepos());
    expect(result.current.recentRepos).toEqual([]);
  });

  // -- addRepo --------------------------------------------------------------

  it("adds a repo to the front of the list", () => {
    seedStorage(["repo-a"]);
    const { result } = renderHook(() => useRecentRepos());

    act(() => result.current.addRepo("repo-b"));

    expect(result.current.recentRepos).toEqual(["repo-b", "repo-a"]);
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY)!)).toEqual(["repo-b", "repo-a"]);
  });

  it("deduplicates — moves an existing repo to the front", () => {
    seedStorage(["repo-a", "repo-b", "repo-c"]);
    const { result } = renderHook(() => useRecentRepos());

    act(() => result.current.addRepo("repo-c"));

    expect(result.current.recentRepos).toEqual(["repo-c", "repo-a", "repo-b"]);
  });

  it("caps the list at 20 entries", () => {
    const initial = Array.from({ length: 20 }, (_, i) => `repo-${i}`);
    seedStorage(initial);
    const { result } = renderHook(() => useRecentRepos());

    act(() => result.current.addRepo("repo-new"));

    expect(result.current.recentRepos).toHaveLength(20);
    expect(result.current.recentRepos[0]).toBe("repo-new");
    // The last repo (repo-19) should have been evicted
    expect(result.current.recentRepos).not.toContain("repo-19");
  });

  it("trims whitespace from added repos", () => {
    const { result } = renderHook(() => useRecentRepos());

    act(() => result.current.addRepo("  repo-with-spaces  "));

    expect(result.current.recentRepos).toEqual(["repo-with-spaces"]);
  });

  it("ignores empty or whitespace-only repo strings", () => {
    const { result } = renderHook(() => useRecentRepos());

    act(() => result.current.addRepo(""));
    act(() => result.current.addRepo("   "));

    expect(result.current.recentRepos).toEqual([]);
  });

  // -- removeRepo -----------------------------------------------------------

  it("removes a specific repo from the list", () => {
    seedStorage(["repo-a", "repo-b", "repo-c"]);
    const { result } = renderHook(() => useRecentRepos());

    act(() => result.current.removeRepo("repo-b"));

    expect(result.current.recentRepos).toEqual(["repo-a", "repo-c"]);
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY)!)).toEqual(["repo-a", "repo-c"]);
  });

  it("removing a non-existent repo is a no-op", () => {
    seedStorage(["repo-a"]);
    const { result } = renderHook(() => useRecentRepos());

    act(() => result.current.removeRepo("repo-missing"));

    expect(result.current.recentRepos).toEqual(["repo-a"]);
  });

  // -- Cross-tab sync -------------------------------------------------------

  it("syncs state when a storage event fires for the recent repos key", () => {
    const { result } = renderHook(() => useRecentRepos());
    expect(result.current.recentRepos).toEqual([]);

    // Simulate another tab writing to localStorage
    seedStorage(["from-other-tab"]);
    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", { key: STORAGE_KEY, newValue: JSON.stringify(["from-other-tab"]) }),
      );
    });

    expect(result.current.recentRepos).toEqual(["from-other-tab"]);
  });

  it("ignores storage events for other keys", () => {
    seedStorage(["repo-a"]);
    const { result } = renderHook(() => useRecentRepos());

    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", { key: "other_key", newValue: "irrelevant" }),
      );
    });

    expect(result.current.recentRepos).toEqual(["repo-a"]);
  });

  // -- localStorage error handling ------------------------------------------

  it("handles localStorage.getItem throwing gracefully", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("SecurityError");
    });

    const { result } = renderHook(() => useRecentRepos());
    expect(result.current.recentRepos).toEqual([]);
  });

  it("handles localStorage.setItem throwing gracefully on addRepo", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceededError");
    });

    const { result } = renderHook(() => useRecentRepos());

    // Should not throw — just silently fails to persist
    act(() => result.current.addRepo("repo-a"));

    // State still updates in-memory even if persistence fails
    expect(result.current.recentRepos).toEqual(["repo-a"]);
  });
});
