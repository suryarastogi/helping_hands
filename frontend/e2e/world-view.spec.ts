import { test, expect } from "@playwright/test";
import { mockApiRoutes } from "./helpers";

test.beforeEach(async ({ page }) => {
  await mockApiRoutes(page);
});

test("Hand World scene is visible on page load", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".hand-world-card")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Hand World" })).toBeVisible();
});

test("world view shows factory scene with stations and player", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".world-scene")).toBeVisible();
  await expect(page.locator(".work-desk").first()).toBeVisible();
  await expect(page.locator(".human-player")).toBeVisible();
});

test("world view shows factory status summary", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Factory Floor")).toBeVisible();
  await expect(page.locator(".zen-status-summary").getByText("Stations")).toBeVisible();
  // Connection status hint renders after WS state settles (connecting → disconnected)
  await expect(page.locator(".status-summary-hint")).toBeVisible();
});

test("Claude usage panel is visible", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Claude Usage")).toBeVisible();
});
