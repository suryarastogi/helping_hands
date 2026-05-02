// Tiny hand-rolled router for shareable task-run URLs (/run/<uuid>).
//
// Why hand-rolled: we have one route to add, react-router-dom would be ~30KB
// for a single match. The existing app shell is single-page; this just keeps
// taskId state and the URL in sync.
//
// We use /run/<uuid> rather than /tasks/<uuid> so the path doesn't collide
// with the backend API prefix the vite dev proxy already routes (see
// frontend/vite.config.ts). See also CLAUDE.md notes about lugia's brittle
// vite proxy matching.

const RUN_PREFIX = "/run/";

// Permissive — accepts any reasonable task identifier (Celery UUIDs in
// production, but also short opaque strings used in tests/dev). The backend
// is the authority on what's a real task; the regex's job is just to reject
// path-traversal characters and whitespace so the router never tries to
// navigate to a malformed URL.
const TASK_ID_RE = /^[A-Za-z0-9._-]{1,128}$/;

export interface InitRouteResult {
  taskId: string | null;
  // True when the page was loaded *directly* at /run/<uuid> (or the legacy
  // ?task_id= form). Lets the UI suppress destructive actions for users who
  // are viewing someone else's shared run rather than their own submission.
  isColdLoad: boolean;
}

export function parseTaskIdFromPathname(pathname: string | null | undefined): string | null {
  // Defensive: jsdom-based tests sometimes replace window.location with a
  // plain spread, which strips non-enumerable properties like pathname.
  if (!pathname || typeof pathname !== "string") return null;
  if (!pathname.startsWith(RUN_PREFIX)) return null;
  const rest = pathname.slice(RUN_PREFIX.length).replace(/\/+$/, "");
  return TASK_ID_RE.test(rest) ? rest : null;
}

export function buildRunPath(taskId: string): string {
  return RUN_PREFIX + taskId;
}

// Run once at app mount: pick up taskId from the URL, migrating the legacy
// ?task_id= form to /run/<uuid> via replaceState so bookmarks keep working.
export function initTaskRoute(): InitRouteResult {
  if (typeof window === "undefined") return { taskId: null, isColdLoad: false };

  const fromPath = parseTaskIdFromPathname(window.location?.pathname ?? "");
  if (fromPath) return { taskId: fromPath, isColdLoad: true };

  const params = new URLSearchParams(window.location?.search ?? "");
  const fromQuery = params.get("task_id");
  if (fromQuery && TASK_ID_RE.test(fromQuery)) {
    // Migrate ?task_id=<uuid> → /run/<uuid>, preserving every other param.
    params.delete("task_id");
    const search = params.toString();
    const target = buildRunPath(fromQuery) + (search ? `?${search}` : "");
    try {
      window.history.replaceState({}, "", target);
    } catch {
      // jsdom test setups occasionally make window.location read-only;
      // a failed migration just means the URL bar stays as ?task_id= for
      // this session — still functional, just legacy.
    }
    return { taskId: fromQuery, isColdLoad: true };
  }

  return { taskId: null, isColdLoad: false };
}

// Push or replace the URL to reflect the current taskId. Keeps existing search
// params (e.g. preserved form-prefill params) intact.
export function syncTaskIdToUrl(taskId: string | null): void {
  if (typeof window === "undefined") return;
  const search = window.location?.search ?? "";
  const pathname = window.location?.pathname ?? "/";
  const target = (taskId ? buildRunPath(taskId) : "/") + search;
  if (pathname + search === target) return;
  try {
    window.history.pushState({}, "", target);
  } catch {
    // See initTaskRoute — read-only window.location in some test setups.
  }
}
