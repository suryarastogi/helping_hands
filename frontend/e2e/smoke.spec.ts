import { test, expect } from "@playwright/test";
import { mockApiRoutes } from "./helpers";

test.beforeEach(async ({ page }) => {
  await mockApiRoutes(page);
});

test("app renders with title", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("helping_hands runner");
});

test("sidebar buttons are visible", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "New Task" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Scheduled tasks" })).toBeVisible();
});

test("Hand World scene is visible on load", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".hand-world-card")).toBeVisible();
});

test("clicking Scheduled tasks toggles schedule view", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Scheduled tasks" }).click();
  await expect(page.getByText("Create and manage recurring builds.")).toBeVisible();
  // Click again to hide
  await page.getByRole("button", { name: "Scheduled tasks" }).click();
  await expect(page.getByText("Create and manage recurring builds.")).not.toBeVisible();
});

test("clicking New Task opens submission overlay", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New Task" }).click();
  await expect(page.locator(".submission-overlay")).toBeVisible();
  await expect(page.locator("input.repo-input")).toBeVisible();
});

test("service health bar renders", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("[aria-label='Service health']")).toBeVisible();
});
