import { describe, expect, it } from "vitest";

import { computeBackoffDelay } from "./pollingBackoff";

describe("computeBackoffDelay", () => {
  it("returns the base delay exactly when there are no failures", () => {
    expect(computeBackoffDelay(3000, 0, 30000)).toBe(3000);
    expect(computeBackoffDelay(1500, -1, 10000)).toBe(1500);
  });

  it("grows exponentially with failures (within jitter bounds)", () => {
    for (let i = 0; i < 20; i++) {
      const d1 = computeBackoffDelay(1500, 1, 60000);
      expect(d1).toBeGreaterThanOrEqual(2700); // 3000 - 10%
      expect(d1).toBeLessThanOrEqual(3300); // 3000 + 10%
      const d3 = computeBackoffDelay(1500, 3, 60000);
      expect(d3).toBeGreaterThanOrEqual(10800); // 12000 - 10%
      expect(d3).toBeLessThanOrEqual(13200); // 12000 + 10%
    }
  });

  it("never exceeds the cap", () => {
    for (let i = 0; i < 20; i++) {
      expect(computeBackoffDelay(1500, 10, 10000)).toBeLessThanOrEqual(10000);
      expect(computeBackoffDelay(3000, 50, 30000)).toBeLessThanOrEqual(30000);
    }
  });
});
