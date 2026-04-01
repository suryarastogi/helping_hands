import { test, expect } from "@playwright/test";
import { mockApiRoutes } from "./helpers";

test.beforeEach(async ({ page }) => {
  await mockApiRoutes(page);
  await page.goto("/");
  // Open the submission overlay
  await page.getByRole("button", { name: "New Task" }).click();
  await expect(page.locator(".submission-overlay")).toBeVisible();
});

test("submission form has required fields", async ({ page }) => {
  await expect(page.locator("input.repo-input")).toBeVisible();
  await expect(page.locator("input.prompt-input")).toBeVisible();
  await expect(page.locator("button.submit-inline")).toBeVisible();
});

test("advanced settings expand on click", async ({ page }) => {
  const details = page.locator("details.compact-advanced");
  // Initially collapsed — backend select not visible
  await expect(details.locator("select")).not.toBeVisible();
  // Expand
  await details.locator("summary").first().click();
  await expect(details.locator("select").first()).toBeVisible();
});

test("submitting a run navigates to monitor view", async ({ page }) => {
  // Mock the build endpoint
  await page.route("**/build", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        task_id: "test-task-123",
        status: "PENDING",
        backend: "e2e",
      }),
    }),
  );
  // Mock task polling
  await page.route("**/tasks/test-task-123*", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        task_id: "test-task-123",
        status: "STARTED",
        result: null,
      }),
    }),
  );

  await page.locator("input.repo-input").fill("owner/repo");
  await page.locator("input.prompt-input").fill("Fix the bug");
  await page.locator("button.submit-inline").click();

  // Overlay should close and monitor view should appear
  await expect(page.locator(".monitor-title")).toBeVisible();
});

test("repo input has required attribute", async ({ page }) => {
  await expect(page.locator("input.repo-input")).toHaveAttribute("required", "");
});

test("prompt input has required attribute", async ({ page }) => {
  await expect(page.locator("input.prompt-input")).toHaveAttribute("required", "");
});
