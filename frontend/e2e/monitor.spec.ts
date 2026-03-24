import { test, expect } from "@playwright/test";
import { mockApiRoutes } from "./helpers";

/** Open overlay, fill form, submit, and wait for monitor view. */
async function submitTask(
  page: import("@playwright/test").Page,
  taskId: string,
  taskStatus = "STARTED",
) {
  await page.route("**/build", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ task_id: taskId, status: "PENDING", backend: "e2e" }),
    }),
  );
  await page.route(`**/tasks/${taskId}*`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        task_id: taskId,
        status: taskStatus,
        result: taskStatus === "STARTED" ? { updates: ["Step 1 done"] } : { summary: "All done" },
      }),
    }),
  );

  await page.getByRole("button", { name: "New Task" }).click();
  await page.locator("input.repo-input").fill("owner/repo");
  await page.locator("input.prompt-input").fill("Build feature");
  await page.locator("button.submit-inline").click();
}

test.beforeEach(async ({ page }) => {
  await mockApiRoutes(page);
});

test("monitor view shows output tabs", async ({ page }) => {
  await page.goto("/");
  await submitTask(page, "task-abc");

  await expect(page.getByRole("tab", { name: "Updates" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Raw" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Payload" })).toBeVisible();
});

test("task appears in sidebar after submission", async ({ page }) => {
  await page.goto("/");
  await submitTask(page, "task-xyz-1234");

  await expect(page.locator(".task-list")).toBeVisible();
});

test("clicking a task in the sidebar selects it", async ({ page }) => {
  await page.goto("/");
  await submitTask(page, "task-select-test", "SUCCESS");

  await expect(page.locator(".task-list")).toBeVisible();

  // Open submission overlay to navigate away from monitor
  await page.getByRole("button", { name: "New Task" }).click();
  await expect(page.locator("input.repo-input")).toBeVisible();
  // Close overlay
  await page.locator(".submission-overlay-close").click();

  // Click the task in sidebar — should show monitor view
  await page.locator(".task-row").first().click();
  await expect(page.locator(".monitor-title")).toBeVisible();
});
