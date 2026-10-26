interface RateLimitRecord {
  count: number;
  resetAt: number;
}

// In-memory store for IP rate limiting
const store = new Map<string, RateLimitRecord>();

// Periodically clean up expired entries to prevent memory growth
if (typeof setInterval !== "undefined") {
  const timer = setInterval(() => {
    const now = Date.now();
    for (const [key, value] of store.entries()) {
      if (now > value.resetAt) {
        store.delete(key);
      }
    }
  }, 5 * 60_000);

  // Unref timer in Node environment so it doesn't prevent graceful exit
  if (typeof timer.unref === "function") {
    timer.unref();
  }
}

/**
 * Checks if a client IP has exceeded the allowed quota.
 *
 * @param key Identifier (usually client IP)
 * @param limit Max allowed requests within window
 * @param windowMs Time window in milliseconds (default: 60,000ms = 1 min)
 */
export function isRateLimited(
  key: string,
  limit = 5,
  windowMs = 60_000
): { limited: boolean; remaining: number; resetInSec: number } {
  // shortcut: in-memory limiter for single instance, upgrade to @upstash/ratelimit for multi-replica serverless
  const now = Date.now();
  const record = store.get(key);

  if (!record || now > record.resetAt) {
    store.set(key, { count: 1, resetAt: now + windowMs });
    return {
      limited: false,
      remaining: limit - 1,
      resetInSec: Math.ceil(windowMs / 1000),
    };
  }

  if (record.count >= limit) {
    const resetInSec = Math.max(1, Math.ceil((record.resetAt - now) / 1000));
    return { limited: true, remaining: 0, resetInSec };
  }

  record.count += 1;
  const resetInSec = Math.max(1, Math.ceil((record.resetAt - now) / 1000));
  return { limited: false, remaining: limit - record.count, resetInSec };
}

/**
 * Resolves the real client IP from incoming request headers.
 */
export function getClientIp(req: Request): string {
  const forwarded = req.headers.get("x-forwarded-for");
  if (forwarded) {
    return forwarded.split(",")[0].trim();
  }
  return (
    req.headers.get("cf-connecting-ip") ||
    req.headers.get("x-real-ip") ||
    "127.0.0.1"
  );
}
