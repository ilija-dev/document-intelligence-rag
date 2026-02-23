/**
 * Redis client with connection management and health checks.
 *
 * Redis serves as our L1 cache — the first thing checked on every query.
 * In production, 80% of queries are variations of 20% of questions
 * (Pareto principle). Without caching, every query hits embedding model +
 * vector DB + LLM (~3 seconds). With Redis, repeat queries return in <100ms.
 */

import Redis from "ioredis";
import { config } from "../config.js";

let client: Redis | null = null;

export function getRedisClient(): Redis {
  if (!client) {
    client = new Redis(config.redis.url, {
      maxRetriesPerRequest: 3,
      retryStrategy(times) {
        // Exponential backoff: 200ms, 400ms, 800ms, then give up
        if (times > 3) return null;
        return Math.min(times * 200, 2000);
      },
      lazyConnect: true,
    });

    client.on("connect", () => {
      console.log("[Redis] Connected");
    });

    client.on("error", (err) => {
      console.error("[Redis] Error:", err.message);
    });
  }
  return client;
}

/**
 * Check if Redis is available. Used for graceful degradation —
 * if Redis is down, we skip caching rather than failing the request.
 */
export async function isRedisHealthy(): Promise<boolean> {
  try {
    const redis = getRedisClient();
    const result = await redis.ping();
    return result === "PONG";
  } catch {
    return false;
  }
}

/**
 * Get a cached value. Returns null on cache miss or Redis error.
 */
export async function cacheGet(key: string): Promise<string | null> {
  try {
    const redis = getRedisClient();
    return await redis.get(key);
  } catch (err) {
    console.warn("[Redis] Cache get failed:", (err as Error).message);
    return null;
  }
}

/**
 * Set a cached value with TTL.
 */
export async function cacheSet(
  key: string,
  value: string,
  ttlSeconds?: number
): Promise<void> {
  try {
    const redis = getRedisClient();
    const ttl = ttlSeconds ?? config.redis.cacheTtlSeconds;
    await redis.setex(key, ttl, value);
  } catch (err) {
    console.warn("[Redis] Cache set failed:", (err as Error).message);
  }
}

/**
 * Delete cache entries by pattern. Used for cache invalidation
 * when new documents are ingested.
 */
export async function cacheInvalidatePattern(
  pattern: string
): Promise<number> {
  try {
    const redis = getRedisClient();
    let cursor = "0";
    let deleted = 0;

    do {
      const [nextCursor, keys] = await redis.scan(
        cursor,
        "MATCH",
        pattern,
        "COUNT",
        100
      );
      cursor = nextCursor;

      if (keys.length > 0) {
        await redis.del(...keys);
        deleted += keys.length;
      }
    } while (cursor !== "0");

    return deleted;
  } catch (err) {
    console.warn("[Redis] Cache invalidation failed:", (err as Error).message);
    return 0;
  }
}

/**
 * Disconnect Redis cleanly on shutdown.
 */
export async function disconnectRedis(): Promise<void> {
  if (client) {
    await client.quit();
    client = null;
  }
}
