import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildRunPath,
  initTaskRoute,
  parseTaskIdFromPathname,
  syncTaskIdToUrl,
} from "./router";

const VALID_UUID = "abcd1234-1234-4abc-9def-0123456789ab";
const ANOTHER_UUID = "11111111-2222-3333-4444-555555555555";

describe("parseTaskIdFromPathname", () => {
  it("extracts a uuid-like id from /run/<uuid>", () => {
    expect(parseTaskIdFromPathname(`/run/${VALID_UUID}`)).toBe(VALID_UUID);
  });

  it("tolerates a trailing slash", () => {
    expect(parseTaskIdFromPathname(`/run/${VALID_UUID}/`)).toBe(VALID_UUID);
  });

  it("returns null for non-/run paths", () => {
    expect(parseTaskIdFromPathname("/")).toBeNull();
    expect(parseTaskIdFromPathname(`/tasks/${VALID_UUID}`)).toBeNull();
  });

  it("accepts permissive task identifiers", () => {
    // Backend is the authority on what's valid; router only rejects
    // characters that could break URL parsing or path safety.
    expect(parseTaskIdFromPathname("/run/short-id")).toBe("short-id");
    expect(parseTaskIdFromPathname("/run/qs-task")).toBe("qs-task");
  });

  it("returns null for empty or path-unsafe segments", () => {
    expect(parseTaskIdFromPathname("/run/")).toBeNull();
    // A nested path is not a single id segment — reject.
    expect(parseTaskIdFromPathname("/run/a/b")).toBeNull();
  });
});

describe("buildRunPath", () => {
  it("produces the canonical /run/<uuid> shape", () => {
    expect(buildRunPath(VALID_UUID)).toBe(`/run/${VALID_UUID}`);
  });
});

describe("initTaskRoute", () => {
  let replaceSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // jsdom location is read-only via assignment; fall back to history APIs.
    window.history.replaceState({}, "", "/");
    replaceSpy = vi.spyOn(window.history, "replaceState");
  });

  afterEach(() => {
    replaceSpy.mockRestore();
    window.history.replaceState({}, "", "/");
  });

  it("returns null on a fresh root URL", () => {
    expect(initTaskRoute()).toEqual({ taskId: null, isColdLoad: false });
  });

  it("picks up taskId from /run/<uuid> as cold load", () => {
    window.history.replaceState({}, "", `/run/${VALID_UUID}`);
    expect(initTaskRoute()).toEqual({
      taskId: VALID_UUID,
      isColdLoad: true,
    });
  });

  it("migrates ?task_id=<uuid> to /run/<uuid> via replaceState", () => {
    window.history.replaceState({}, "", `/?task_id=${VALID_UUID}`);
    const result = initTaskRoute();
    expect(result.taskId).toBe(VALID_UUID);
    expect(result.isColdLoad).toBe(true);
    // The migration must have rewritten the URL.
    expect(window.location.pathname).toBe(`/run/${VALID_UUID}`);
  });

  it("preserves other query params during migration", () => {
    window.history.replaceState(
      {},
      "",
      `/?task_id=${VALID_UUID}&backend=claude&repo_path=owner%2Frepo`
    );
    initTaskRoute();
    const search = new URLSearchParams(window.location.search);
    expect(search.has("task_id")).toBe(false);
    expect(search.get("backend")).toBe("claude");
    expect(search.get("repo_path")).toBe("owner/repo");
  });

  it("ignores task_id values that contain unsafe characters", () => {
    // Whitespace, slashes, and other URL-breaking characters are rejected.
    window.history.replaceState({}, "", "/?task_id=has%20space");
    expect(initTaskRoute()).toEqual({ taskId: null, isColdLoad: false });
  });
});

describe("syncTaskIdToUrl", () => {
  let pushSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    pushSpy = vi.spyOn(window.history, "pushState");
  });

  afterEach(() => {
    pushSpy.mockRestore();
    window.history.replaceState({}, "", "/");
  });

  it("pushes /run/<uuid> when taskId set", () => {
    syncTaskIdToUrl(VALID_UUID);
    expect(window.location.pathname).toBe(`/run/${VALID_UUID}`);
    expect(pushSpy).toHaveBeenCalledTimes(1);
  });

  it("is a no-op when URL already matches", () => {
    window.history.replaceState({}, "", `/run/${VALID_UUID}`);
    syncTaskIdToUrl(VALID_UUID);
    expect(pushSpy).not.toHaveBeenCalled();
  });

  it("returns to / when taskId cleared", () => {
    window.history.replaceState({}, "", `/run/${VALID_UUID}`);
    syncTaskIdToUrl(null);
    expect(window.location.pathname).toBe("/");
  });

  it("preserves the existing query string", () => {
    window.history.replaceState({}, "", "/?backend=claude");
    syncTaskIdToUrl(ANOTHER_UUID);
    expect(window.location.pathname).toBe(`/run/${ANOTHER_UUID}`);
    expect(window.location.search).toBe("?backend=claude");
  });
});
