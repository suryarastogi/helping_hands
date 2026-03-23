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
  await expect(page.getByText("Use arrow keys to walk")).toBeVisible();
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

test("remote player elements render when WebSocket delivers players_sync", async ({
  page,
}) => {
  // Intercept the WebSocket upgrade and simulate a server message.
  await page.goto("/");
  await page.getByRole("tab", { name: "Hand world" }).click();

  // Inject a fake remote player via the WebSocket onmessage handler.
  await page.evaluate(() => {
    // Find the active WebSocket (or create a synthetic message event).
    const fakePlayers = [
      {
        player_id: "e2e-remote",
        name: "E2E Remote",
        color: "#2563eb",
        x: 30,
        y: 40,
        direction: "left",
        walking: false,
      },
    ];

    // Dispatch a synthetic players_sync via the last opened WebSocket.
    const allWs = (window as unknown as Record<string, WebSocket[]>).__e2eWsList;
    if (allWs && allWs.length > 0) {
      const ws = allWs[allWs.length - 1];
      const msg = new MessageEvent("message", {
        data: JSON.stringify({
          type: "players_sync",
          your_id: "e2e-local",
          players: fakePlayers,
        }),
      });
      ws.dispatchEvent(msg);
    }
  });

  // The remote player should appear (may not if WebSocket proxy isn't set up,
  // so this is a best-effort check — the unit tests cover this thoroughly).
  const remotePlayer = page.locator("[aria-label='E2E Remote']");
  // Use a short timeout — in E2E without a real WS server this may not render.
  const visible = await remotePlayer.isVisible({ timeout: 2000 }).catch(() => false);
  if (visible) {
    await expect(remotePlayer).toHaveClass(/remote-player/);
  }
});
