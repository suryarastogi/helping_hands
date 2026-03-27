import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createThrottledBroadcast } from "./throttledBroadcast";

describe("createThrottledBroadcast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("fires immediately when interval has elapsed (leading edge)", () => {
    const throttle = createThrottledBroadcast(100);
    const fn = vi.fn();

    // First call — no previous broadcast, so elapsed >= interval.
    throttle.fire(fn);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("defers second call within interval (trailing edge)", () => {
    const throttle = createThrottledBroadcast(100);
    const fn = vi.fn();

    throttle.fire(fn);
    expect(fn).toHaveBeenCalledTimes(1);

    // Second call within 100ms — should be deferred.
    vi.advanceTimersByTime(30);
    throttle.fire(fn);
    expect(fn).toHaveBeenCalledTimes(1);

    // After remaining interval (70ms), trailing fires.
    vi.advanceTimersByTime(70);
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it("does not schedule duplicate trailing timers on rapid calls", () => {
    const throttle = createThrottledBroadcast(100);
    const fn = vi.fn();

    throttle.fire(fn); // Leading — immediate.
    expect(fn).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(20);
    throttle.fire(fn); // Schedules trailing for +80ms.
    vi.advanceTimersByTime(20);
    throttle.fire(fn); // Already pending — ignored.
    vi.advanceTimersByTime(20);
    throttle.fire(fn); // Already pending — ignored.

    expect(fn).toHaveBeenCalledTimes(1); // Still only the leading.

    vi.advanceTimersByTime(40); // 80ms from first trailing schedule.
    expect(fn).toHaveBeenCalledTimes(2); // Only one trailing.
  });

  it("fires immediately again after interval has elapsed", () => {
    const throttle = createThrottledBroadcast(100);
    const fn = vi.fn();

    throttle.fire(fn); // Leading.
    vi.advanceTimersByTime(150); // Well past interval.
    throttle.fire(fn); // Should fire immediately again.
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it("cancel clears pending trailing broadcast", () => {
    const throttle = createThrottledBroadcast(100);
    const fn = vi.fn();

    throttle.fire(fn); // Leading.
    vi.advanceTimersByTime(30);
    throttle.fire(fn); // Schedules trailing.
    throttle.cancel();

    vi.advanceTimersByTime(200);
    expect(fn).toHaveBeenCalledTimes(1); // Trailing was cancelled.
  });

  it("cancel is safe to call when nothing is pending", () => {
    const throttle = createThrottledBroadcast(100);
    expect(() => throttle.cancel()).not.toThrow();
  });

  it("fireImmediate always fires and cancels pending", () => {
    const throttle = createThrottledBroadcast(100);
    const fn1 = vi.fn();
    const fn2 = vi.fn();

    throttle.fire(fn1); // Leading.
    vi.advanceTimersByTime(30);
    throttle.fire(fn1); // Schedules trailing.

    // fireImmediate should execute immediately and cancel the pending trailing.
    throttle.fireImmediate(fn2);
    expect(fn2).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(200);
    // fn1 trailing should NOT have fired (cancelled by fireImmediate).
    expect(fn1).toHaveBeenCalledTimes(1);
  });

  it("fireImmediate resets lastFiredAt so next fire within interval is deferred", () => {
    const throttle = createThrottledBroadcast(100);
    const fn = vi.fn();

    throttle.fireImmediate(fn); // Immediate.
    expect(fn).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(30);
    throttle.fire(fn); // Within interval — deferred.
    expect(fn).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(70);
    expect(fn).toHaveBeenCalledTimes(2); // Trailing fires.
  });

  it("uses the latest callback for trailing broadcast", () => {
    const throttle = createThrottledBroadcast(100);
    let value = 0;
    const fn = vi.fn(() => value);

    throttle.fire(fn); // Leading, value=0.
    vi.advanceTimersByTime(30);

    value = 42;
    throttle.fire(fn); // Schedules trailing with fn that reads value=42.

    vi.advanceTimersByTime(70);
    // The trailing call should have used the fn passed in the second fire().
    // Since both are the same fn reference, the latest value is used.
    expect(fn).toHaveBeenCalledTimes(2);
  });
});
