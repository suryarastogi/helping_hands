import { render, fireEvent } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AppOverlays from "./AppOverlays";
import type { AppOverlaysProps } from "./AppOverlays";

function makeProps(overrides: Partial<AppOverlaysProps> = {}): AppOverlaysProps {
  return {
    serviceHealthState: null,
    toasts: [],
    onRemoveToast: vi.fn(),
    ...overrides,
  };
}

function renderOverlays(overrides: Partial<AppOverlaysProps> = {}) {
  const props = makeProps(overrides);
  const result = render(<AppOverlays {...props} />);
  return { ...result, props };
}

describe("AppOverlays", () => {
  describe("service health bar", () => {
    it("renders health bar when no data", () => {
      const { container } = renderOverlays();
      const bar = container.querySelector('[aria-label="Service health"]');
      expect(bar).toBeTruthy();
    });

    it("renders all health indicators plus test notification button", () => {
      const { container } = renderOverlays({
        serviceHealthState: {
          reachable: true,
          health: { redis: "ok", db: "ok", workers: "ok" },
        },
      });
      const bar = container.querySelector('[aria-label="Service health"]')!;
      const items = bar.querySelectorAll(".service-health-item");
      // api, redis, db, workers + test notification button
      expect(items.length).toBe(5);
    });

    it("shows ok title for reachable API", () => {
      const { container } = renderOverlays({
        serviceHealthState: {
          reachable: true,
          health: { redis: "ok", db: "ok", workers: "ok" },
        },
      });
      const bar = container.querySelector('[aria-label="Service health"]')!;
      expect(bar.querySelector('[title="api: ok"]')).toBeTruthy();
      expect(bar.querySelector('[title="redis: ok"]')).toBeTruthy();
    });

    it("shows error title for unreachable API", () => {
      const { container } = renderOverlays({
        serviceHealthState: {
          reachable: false,
          health: null,
        },
      });
      const bar = container.querySelector('[aria-label="Service health"]')!;
      expect(bar.querySelector('[title="api: error"]')).toBeTruthy();
    });

    it("hides db indicator when state is na", () => {
      const { container } = renderOverlays({
        serviceHealthState: {
          reachable: true,
          health: { redis: "ok", db: "na", workers: "ok" },
        },
      });
      const bar = container.querySelector('[aria-label="Service health"]')!;
      // db should be filtered out, so no "db: na" or "db: ok" item
      expect(bar.querySelector('[title="db: na"]')).toBeNull();
      expect(bar.querySelector('[title="db: ok"]')).toBeNull();
    });

    it("renders test notification button", () => {
      const { container } = renderOverlays();
      const btn = container.querySelector('[title="Send a test OS notification"]');
      expect(btn).toBeTruthy();
    });

    it("applies checking CSS class when state is null", () => {
      const { container } = renderOverlays();
      const dots = container.querySelectorAll(".service-health-dot--checking");
      // api, redis, db, workers all checking when serviceHealthState is null
      expect(dots.length).toBe(4);
    });
  });

  describe("toasts", () => {
    it("renders nothing when toasts array is empty", () => {
      const { container } = renderOverlays({ toasts: [] });
      expect(container.querySelector(".toast-container")).toBeNull();
    });

    it("renders toast with task id and status", () => {
      const { container } = renderOverlays({
        toasts: [{ id: 1, taskId: "abc-123-def-456", status: "SUCCESS" }],
      });
      const toastContainer = container.querySelector(".toast-container");
      expect(toastContainer).toBeTruthy();
      expect(toastContainer!.textContent).toContain("abc-12");
      expect(toastContainer!.textContent).toContain("SUCCESS");
    });

    it("calls onRemoveToast when dismiss is clicked", () => {
      const onRemove = vi.fn();
      const { container } = renderOverlays({
        toasts: [{ id: 42, taskId: "task-1", status: "FAILURE" }],
        onRemoveToast: onRemove,
      });
      const closeBtn = container.querySelector(".toast-close") as HTMLButtonElement;
      fireEvent.click(closeBtn);
      expect(onRemove).toHaveBeenCalledWith(42);
    });

    it("renders multiple toasts", () => {
      const { container } = renderOverlays({
        toasts: [
          { id: 1, taskId: "t1", status: "SUCCESS" },
          { id: 2, taskId: "t2", status: "FAILURE" },
        ],
      });
      const toasts = container.querySelectorAll(".toast");
      expect(toasts.length).toBe(2);
    });

    it("applies correct tone class for success", () => {
      const { container } = renderOverlays({
        toasts: [{ id: 1, taskId: "t1", status: "SUCCESS" }],
      });
      const toast = container.querySelector(".toast");
      expect(toast!.className).toContain("toast--ok");
    });

    it("applies correct tone class for failure", () => {
      const { container } = renderOverlays({
        toasts: [{ id: 1, taskId: "t1", status: "FAILURE" }],
      });
      const toast = container.querySelector(".toast");
      expect(toast!.className).toContain("toast--fail");
    });
  });

  describe("notification banner", () => {
    const origNotification = globalThis.Notification;

    beforeEach(() => {
      // Mock Notification with permission "default" to test banner rendering
      globalThis.Notification = {
        permission: "default",
        requestPermission: vi.fn().mockResolvedValue("granted"),
      } as unknown as typeof Notification;
    });

    afterEach(() => {
      globalThis.Notification = origNotification;
    });

    it("shows notification banner when permission is default", () => {
      const { container } = renderOverlays();
      const banner = container.querySelector(".notif-banner");
      expect(banner).toBeTruthy();
      expect(banner!.textContent).toContain("Enable OS notifications");
    });

    it("hides notification banner after dismiss", () => {
      const { container } = renderOverlays();
      const banner = container.querySelector(".notif-banner")!;
      const dismissBtn = banner.querySelectorAll("button")[1];
      fireEvent.click(dismissBtn);
      expect(container.querySelector(".notif-banner")).toBeNull();
    });
  });

  describe("test notification button", () => {
    const origNotification = globalThis.Notification;

    afterEach(() => {
      globalThis.Notification = origNotification;
    });

    it("alerts when Notification API is unavailable", () => {
      // Remove Notification entirely
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (globalThis as any).Notification;
      const alertSpy = vi.spyOn(globalThis, "alert").mockImplementation(() => {});

      const { container } = renderOverlays();
      const btn = container.querySelector('[title="Send a test OS notification"]') as HTMLButtonElement;
      fireEvent.click(btn);

      expect(alertSpy).toHaveBeenCalledWith("Notification API not available in this context");
      alertSpy.mockRestore();
    });

    it("requests permission when not granted and retries on grant", async () => {
      const requestMock = vi.fn().mockResolvedValue("granted");
      globalThis.Notification = {
        permission: "denied",
        requestPermission: requestMock,
      } as unknown as typeof Notification;

      const { container } = renderOverlays();
      const btn = container.querySelector('[title="Send a test OS notification"]') as HTMLButtonElement;
      fireEvent.click(btn);

      // requestPermission should have been called
      expect(requestMock).toHaveBeenCalled();
    });

    it("creates new Notification when granted and no service worker", () => {
      const notifConstructor = vi.fn();
      globalThis.Notification = Object.assign(notifConstructor, {
        permission: "granted",
        requestPermission: vi.fn(),
      }) as unknown as typeof Notification;

      const { container } = renderOverlays();
      const btn = container.querySelector('[title="Send a test OS notification"]') as HTMLButtonElement;
      fireEvent.click(btn);

      expect(notifConstructor).toHaveBeenCalledWith("Helping Hands — Test", {
        body: "If you see this, OS notifications are working!",
      });
    });

    it("handles Notification constructor error gracefully", () => {
      const notifConstructor = vi.fn().mockImplementation(() => {
        throw new Error("Not allowed");
      });
      globalThis.Notification = Object.assign(notifConstructor, {
        permission: "granted",
        requestPermission: vi.fn(),
      }) as unknown as typeof Notification;
      const alertSpy = vi.spyOn(globalThis, "alert").mockImplementation(() => {});

      const { container } = renderOverlays();
      const btn = container.querySelector('[title="Send a test OS notification"]') as HTMLButtonElement;
      fireEvent.click(btn);

      expect(alertSpy).toHaveBeenCalledWith(expect.stringContaining("Notification failed"));
      alertSpy.mockRestore();
    });
  });
});
