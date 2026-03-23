import { test, expect } from "@playwright/test";
import { mockApiRoutes } from "./helpers";

test.beforeEach(async ({ page }) => {
  await mockApiRoutes(page);
});

test("switching to world view shows Hand World", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: "Hand world" }).click();
  await expect(page.getByRole("heading", { name: "Hand World" })).toBeVisible();
});

test("world view shows factory scene with stations and player", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: "Hand world" }).click();

  await expect(page.locator(".world-scene")).toBeVisible();
  await expect(page.locator(".work-desk").first()).toBeVisible();
  await expect(page.locator(".human-player")).toBeVisible();
});

test("world view shows factory status summary", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: "Hand world" }).click();

  await expect(page.getByText("Factory Floor")).toBeVisible();
  await expect(page.locator(".zen-status-summary").getByText("Stations")).toBeVisible();
  await expect(page.getByText("Arrow keys: walk")).toBeVisible();
});

test("switching back to classic view hides the factory", async ({ page }) => {
  await page.goto("/");
  // Go to world view
  await page.getByRole("tab", { name: "Hand world" }).click();
  await expect(page.getByRole("heading", { name: "Hand World" })).toBeVisible();

  // Go back to classic
  await page.getByRole("tab", { name: "Classic view" }).click();
  await expect(page.getByRole("heading", { name: "Hand World" })).not.toBeVisible();
  await expect(page.locator("input.repo-input")).toBeVisible();
});

test("world view submission card appears below the garden", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: "Hand world" }).click();

  // In world view, the submission/monitor card is shown below the garden scene
  await expect(page.locator(".hand-world-card")).toBeVisible();
});

test("Claude usage panel is visible in world view", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: "Hand world" }).click();

  await expect(page.getByText("Claude Usage")).toBeVisible();
});

test("world view renders Yjs connection status indicator", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: "Hand world" }).click();

  // The connection status dot should be present (Yjs provider attempts to connect).
  const statusDot = page.locator(".conn-status-dot");
  await expect(statusDot).toBeVisible();

  // Without a running Yjs backend the status will be "disconnected" or "connecting".
  const label = await statusDot.getAttribute("aria-label");
  expect(label).toMatch(/Connection: (disconnected|connecting|connected)/);
});
