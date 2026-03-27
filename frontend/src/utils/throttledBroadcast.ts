/**
 * createThrottledBroadcast — leading+trailing throttle for network broadcasts.
 *
 * Used by useMultiplayer for position and cursor broadcasts to limit the rate
 * of Yjs awareness updates without dropping the latest state.
 *
 * Semantics:
 * - If `intervalMs` has elapsed since the last broadcast, `fire` executes
 *   the callback immediately (leading edge).
 * - Otherwise, a single trailing broadcast is scheduled for the remaining time.
 * - `fireImmediate` always executes immediately and cancels any pending timer
 *   (used for "mouse left scene" / cleanup paths).
 * - `cancel` clears any pending trailing broadcast without firing.
 */

export type ThrottledBroadcast = {
  /** Fire with leading+trailing throttle. */
  fire: (fn: () => void) => void;
  /** Fire immediately and cancel any pending trailing broadcast. */
  fireImmediate: (fn: () => void) => void;
  /** Cancel pending trailing broadcast without firing. */
  cancel: () => void;
};

export function createThrottledBroadcast(intervalMs: number): ThrottledBroadcast {
  let lastFiredAt = 0;
  let pendingTimer: ReturnType<typeof setTimeout> | null = null;

  const cancel = (): void => {
    if (pendingTimer !== null) {
      clearTimeout(pendingTimer);
      pendingTimer = null;
    }
  };

  const fire = (fn: () => void): void => {
    const elapsed = Date.now() - lastFiredAt;
    if (elapsed >= intervalMs) {
      cancel();
      fn();
      lastFiredAt = Date.now();
    } else if (pendingTimer === null) {
      pendingTimer = setTimeout(() => {
        pendingTimer = null;
        fn();
        lastFiredAt = Date.now();
      }, intervalMs - elapsed);
    }
  };

  const fireImmediate = (fn: () => void): void => {
    cancel();
    fn();
    lastFiredAt = Date.now();
  };

  return { fire, fireImmediate, cancel };
}
