import { beforeEach, describe, expect, it, vi } from "vitest";

import { createUIStore } from "./uiStore";

describe("uiStore theme", () => {
  const attributes = new Map<string, string>();
  const storage = new Map<string, string>();

  beforeEach(() => {
    attributes.clear();
    storage.clear();
    vi.stubGlobal("localStorage", {
      clear: () => storage.clear(),
      getItem: (key: string) => storage.get(key) ?? null,
      removeItem: (key: string) => storage.delete(key),
      setItem: (key: string, value: string) => storage.set(key, value),
    });
    vi.stubGlobal("document", {
      documentElement: {
        getAttribute: (name: string) => attributes.get(name) ?? null,
        removeAttribute: (name: string) => attributes.delete(name),
        setAttribute: (name: string, value: string) => attributes.set(name, value),
      },
    });
  });

  it("toggles theme and persists it to localStorage and data-theme", () => {
    const store = createUIStore();

    store.getState().toggleTheme();

    expect(store.getState().theme).toBe("dark");
    expect(localStorage.getItem("cr-theme")).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");

    store.getState().toggleTheme();

    expect(store.getState().theme).toBe("light");
    expect(localStorage.getItem("cr-theme")).toBe("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("restores a persisted theme on initialization", () => {
    localStorage.setItem("cr-theme", "dark");
    const store = createUIStore();

    store.getState().initializeTheme();

    expect(store.getState().theme).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
