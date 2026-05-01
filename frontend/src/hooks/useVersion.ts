/**
 * useVersion — fetches /version on mount and on window focus.
 *
 * Compares the frontend version (baked at Vite startup via __APP_VERSION__)
 * against the backend + per-worker versions surfaced by the API. Returns a
 * coarse status used by the version badge:
 *   - "match"   — all components agree
 *   - "mismatch" — at least two components disagree (deploy-state only)
 *   - "missing" — workers map is empty or backend is unreachable (deploy-state only)
 *   - "tampered" — backend git SHA differs from the deploy sentinel
 *   - "dev"     — sentinel absent → not a deployed instance, all signals informational
 *   - "loading" — initial fetch hasn't completed
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { apiUrl } from "../App.utils";
import {
  FRONTEND_COMMIT_DATE,
  FRONTEND_DISPLAY,
  FRONTEND_LONG_SHA,
} from "../version-generated";

export interface VersionResponse {
  backend: string;
  workers: Record<string, string>;
  git_sha: string;
  commit_date: string | null;
  is_deployed: boolean;
  sentinel_sha: string | null;
}

export type VersionStatus =
  | "loading"
  | "dev"
  | "match"
  | "mismatch"
  | "missing"
  | "tampered";

export interface VersionState {
  frontend: string;
  frontendLongSha: string;
  frontendCommitDate: string | null;
  backend: string | null;
  workers: Record<string, string>;
  gitSha: string | null;
  commitDate: string | null;
  isDeployed: boolean;
  sentinelSha: string | null;
  status: VersionStatus;
  reachable: boolean;
}

function deriveStatus(
  frontend: string,
  data: VersionResponse | null,
): VersionStatus {
  if (!data) return "loading";
  if (!data.is_deployed) return "dev";

  if (data.sentinel_sha && data.git_sha && data.sentinel_sha !== data.git_sha) {
    return "tampered";
  }

  const workerVals = Object.values(data.workers);
  if (workerVals.length === 0) return "missing";

  if (frontend !== data.backend) return "mismatch";
  for (const wv of workerVals) {
    if (wv !== data.backend) return "mismatch";
  }
  return "match";
}

export function useVersion(): VersionState {
  const [data, setData] = useState<VersionResponse | null>(null);
  const [reachable, setReachable] = useState<boolean>(true);
  const inFlight = useRef<boolean>(false);

  const refetch = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const res = await fetch(apiUrl("/version"));
      if (!res.ok) {
        setReachable(false);
        return;
      }
      const json = (await res.json()) as VersionResponse;
      setData(json);
      setReachable(true);
    } catch {
      setReachable(false);
    } finally {
      inFlight.current = false;
    }
  }, []);

  useEffect(() => {
    void refetch();
    const onFocus = () => void refetch();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [refetch]);

  return useMemo<VersionState>(
    () => ({
      frontend: FRONTEND_DISPLAY,
      frontendLongSha: FRONTEND_LONG_SHA,
      frontendCommitDate: FRONTEND_COMMIT_DATE,
      backend: data?.backend ?? null,
      workers: data?.workers ?? {},
      gitSha: data?.git_sha ?? null,
      commitDate: data?.commit_date ?? null,
      isDeployed: data?.is_deployed ?? false,
      sentinelSha: data?.sentinel_sha ?? null,
      status: reachable ? deriveStatus(FRONTEND_DISPLAY, data) : "missing",
      reachable,
    }),
    [data, reachable],
  );
}
