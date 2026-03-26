import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "hh_recent_repos";
const MAX_RECENT = 20;

/** Read the recent-repos list from localStorage. */
function loadRecent(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((s): s is string => typeof s === "string") : [];
  } catch {
    return [];
  }
}

/** Persist the list back to localStorage. */
function saveRecent(repos: string[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(repos));
  } catch {
    // quota exceeded — silently ignore
  }
}

/**
 * Hook that manages a shared "recently used repos" list backed by localStorage.
 *
 * Any repo added via `addRepo` is moved to the front of the list (deduped,
 * capped at MAX_RECENT). The list is shared across repo_path and
 * reference_repos fields.
 */
export function useRecentRepos() {
  const [recentRepos, setRecentRepos] = useState<string[]>(loadRecent);

  // Sync across tabs via the storage event.
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) {
        setRecentRepos(loadRecent());
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const addRepo = useCallback((repo: string) => {
    const trimmed = repo.trim();
    if (!trimmed) return;
    setRecentRepos((prev) => {
      const next = [trimmed, ...prev.filter((r) => r !== trimmed)].slice(0, MAX_RECENT);
      saveRecent(next);
      return next;
    });
  }, []);

  const removeRepo = useCallback((repo: string) => {
    setRecentRepos((prev) => {
      const next = prev.filter((r) => r !== repo);
      saveRecent(next);
      return next;
    });
  }, []);

  return { recentRepos, addRepo, removeRepo } as const;
}
