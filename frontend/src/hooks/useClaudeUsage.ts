/**
 * useClaudeUsage — polls the Claude Code usage endpoint every hour and
 * exposes a manual force-refresh callback.
 */
import { useCallback, useEffect, useState } from "react";

import { fetchClaudeUsage } from "../App.utils";
import type { ClaudeUsageResponse } from "../types";

/** Polling interval in milliseconds (1 hour). */
export const CLAUDE_USAGE_POLL_MS = 3_600_000;

export type UseClaudeUsageReturn = {
  claudeUsage: ClaudeUsageResponse | null;
  claudeUsageLoading: boolean;
  refreshClaudeUsage: () => Promise<void>;
};

export function useClaudeUsage(): UseClaudeUsageReturn {
  const [claudeUsage, setClaudeUsage] = useState<ClaudeUsageResponse | null>(null);
  const [claudeUsageLoading, setClaudeUsageLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      const data = await fetchClaudeUsage();
      if (!cancelled) setClaudeUsage(data);
    };
    void refresh();
    const handle = window.setInterval(() => void refresh(), CLAUDE_USAGE_POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, []);

  const refreshClaudeUsage = useCallback(async () => {
    setClaudeUsageLoading(true);
    const data = await fetchClaudeUsage(true);
    setClaudeUsage(data);
    setClaudeUsageLoading(false);
  }, []);

  return { claudeUsage, claudeUsageLoading, refreshClaudeUsage };
}
