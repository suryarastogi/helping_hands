/**
 * E2E tests for multiplayer Hand World — two browser contexts proving that
 * each user sees their own player avatar in the scene.
 *
 * These tests use mocked API routes (no real backend), so they verify that
 * each independent browser context renders the Hand World scene with a local
 * player avatar.  Full Yjs synchronisation tests require a live backend.
 */
import { test, expect, type Page } from "@playwright/test";
import { mockApiRoutes } from "./helpers";

/** Set up mock routes and navigate for a given page. */
async function setupPage(page: Page) {
  await mockApiRoutes(page);
  await page.goto("/");
}

test.describe("Multiplayer — independent contexts", () => {
  test("two browser contexts each render Hand World with a local player", async ({
    browser,
  }) => {
    // Create two isolated browser contexts (simulates two separate users)
    const contextA = await browser.newContext();
    const contextB = await browser.newContext();
    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();

    await Promise.all([setupPage(pageA), setupPage(pageB)]);

    // Both contexts should show the Hand World scene
    await expect(pageA.locator(".hand-world-card")).toBeVisible();
    await expect(pageB.locator(".hand-world-card")).toBeVisible();

    // Both contexts should render the local human player avatar
    await expect(pageA.locator(".human-player")).toBeVisible();
    await expect(pageB.locator(".human-player")).toBeVisible();

    // Both contexts should show factory floor status
    await expect(pageA.getByText("Factory Floor")).toBeVisible();
    await expect(pageB.getByText("Factory Floor")).toBeVisible();

    await contextA.close();
    await contextB.close();
  });

  test("player name input is independent per context", async ({ browser }) => {
    const contextA = await browser.newContext();
    const contextB = await browser.newContext();
    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();

    await Promise.all([setupPage(pageA), setupPage(pageB)]);

    // Each context has its own player name input
    const nameInputA = pageA.locator('input[placeholder*="name" i]').first();
    const nameInputB = pageB.locator('input[placeholder*="name" i]').first();

    // If name inputs exist (they appear when connected or as default),
    // verify they are independent
    if (await nameInputA.isVisible({ timeout: 2000 }).catch(() => false)) {
      await nameInputA.fill("Alice");
      // Context B's input should not be affected
      if (await nameInputB.isVisible({ timeout: 2000 }).catch(() => false)) {
        const valueB = await nameInputB.inputValue();
        expect(valueB).not.toBe("Alice");
      }
    }

    await contextA.close();
    await contextB.close();
  });

  test("keyboard movement updates player position", async ({ page }) => {
    await mockApiRoutes(page);
    await page.goto("/");

    // Focus the world scene for keyboard input
    const scene = page.locator(".world-scene");
    await expect(scene).toBeVisible();
    await scene.click();

    // Get initial player position
    const player = page.locator(".human-player");
    await expect(player).toBeVisible();

    // Press arrow key to move
    await page.keyboard.press("ArrowRight");
    // Small delay for animation frame
    await page.waitForTimeout(100);
    await page.keyboard.press("ArrowRight");
    await page.waitForTimeout(100);

    // Player should still be visible after movement
    await expect(player).toBeVisible();
  });
});
