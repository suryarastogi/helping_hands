/**
 * Shared exponential-backoff helper for polling loops.
 */

/**
 * Compute the delay before the next poll attempt.
 *
 * With zero consecutive failures the base delay is returned unchanged so the
 * happy path stays deterministic. Each consecutive failure doubles the delay
 * (base * 2^failures), capped at `maxMs`, with ±10% jitter applied so many
 * clients recovering at once don't retry in lockstep.
 *
 * @param baseMs Normal polling interval in milliseconds.
 * @param failures Number of consecutive failures so far (0 = healthy).
 * @param maxMs Upper bound on the returned delay.
 */
export function computeBackoffDelay(
  baseMs: number,
  failures: number,
  maxMs: number,
): number {
  if (failures <= 0) return baseMs;
  const exponential = Math.min(baseMs * 2 ** failures, maxMs);
  const jitterFactor = 1 + (Math.random() * 0.2 - 0.1);
  return Math.min(Math.round(exponential * jitterFactor), maxMs);
}
