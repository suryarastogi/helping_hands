import "@testing-library/jest-dom/vitest";

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
