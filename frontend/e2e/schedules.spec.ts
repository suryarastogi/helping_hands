import { test, expect } from "@playwright/test";
import { mockApiRoutes } from "./helpers";

test.beforeEach(async ({ page }) => {
  await mockApiRoutes(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Scheduled tasks" }).click();
});

test("schedule view shows empty state", async ({ page }) => {
  await expect(page.getByText("Create and manage recurring builds.")).toBeVisible();
});

test("New schedule button opens the form", async ({ page }) => {
  await page.getByRole("button", { name: "New schedule" }).click();
  await expect(page.getByRole("heading", { name: "New schedule" })).toBeVisible();
  await expect(page.locator("input[placeholder='e.g. Daily docs update']")).toBeVisible();
});

test("schedule form has required fields", async ({ page }) => {
  await page.getByRole("button", { name: "New schedule" }).click();

  await expect(page.locator("input[placeholder='e.g. Daily docs update']")).toBeVisible();
  await expect(page.locator("input[placeholder*='midnight']")).toBeVisible();
  await expect(page.locator("input[placeholder='owner/repo']").last()).toBeVisible();
});

test("schedule list shows existing schedules", async ({ page }) => {
  // Override GET /schedules to return items
  await page.route("**/schedules", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          schedules: [
            {
              id: "sched-1",
              name: "Nightly docs",
              cron_expression: "0 0 * * *",
              repo_path: "org/repo",
              prompt: "Update docs",
              backend: "e2e",
              enabled: true,
            },
          ],
          total: 1,
        }),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ id: "sched-1" }),
    });
  });

  // Re-navigate to trigger fresh schedule load with the new mock
  await page.goto("/");
  await page.getByRole("button", { name: "Scheduled tasks" }).click();
  await expect(page.getByText("Nightly docs")).toBeVisible();
});

test("Refresh button reloads schedule list", async ({ page }) => {
  let callCount = 0;
  await page.route("**/schedules", (route) => {
    if (route.request().method() === "GET") {
      callCount++;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ schedules: [], total: 0 }),
      });
    }
    return route.continue();
  });

  // Re-navigate to pick up the counting mock
  await page.goto("/");
  await page.getByRole("button", { name: "Scheduled tasks" }).click();
  await page.waitForTimeout(300);
  const initialCount = callCount;
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await page.waitForTimeout(300);
  expect(callCount).toBeGreaterThan(initialCount);
});
