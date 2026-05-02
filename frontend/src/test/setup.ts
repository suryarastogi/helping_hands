import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";

// Reset the jsdom URL between tests. The router (src/router.ts) writes to
// the URL via history.pushState/replaceState as taskId changes; without this
// reset, state leaks across tests — e.g. one test sets /run/<uuid>, the next
// test mounts the hook and sees a "leaked" taskId, and starts polling.
afterEach(() => {
  if (typeof window !== "undefined" && window.history?.replaceState) {
    try {
      window.history.replaceState({}, "", "/");
    } catch {
      /* ignore — some test setups override window.location read-only */
    }
  }
});

// Polyfill localStorage for jsdom environments where Storage methods may be
// missing or non-functional (observed in some vitest + jsdom setups).
if (typeof window !== "undefined") {
  const store: Record<string, string> = {};
  const localStorageMock: Storage = {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = String(value);
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      for (const key of Object.keys(store)) {
        delete store[key];
      }
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (index: number) => Object.keys(store)[index] ?? null,
  };

  Object.defineProperty(window, "localStorage", { value: localStorageMock });
}
