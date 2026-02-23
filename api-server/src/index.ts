/**
 * API Server entry point.
 *
 * Wires together:
 * - Express.js with JSON parsing
 * - /chat endpoint (query → cache → search → generate → respond)
 * - /documents endpoint (list, stats, cache invalidation)
 * - Health check
 * - Graceful shutdown (close Redis + SQLite)
 */

import express from "express";
import { config } from "./config.js";
import { chatRouter } from "./api/chat.js";
import { documentsRouter } from "./api/documents.js";
import { getRedisClient, disconnectRedis, isRedisHealthy } from "./cache/redis-client.js";
import { closeDb } from "./history/conversation.js";

const app = express();

// ── Middleware ──────────────────────────────────────────────
app.use(express.json({ limit: "1mb" }));

// Request logging
app.use((req, _res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  next();
});

// ── Routes ─────────────────────────────────────────────────
app.use("/chat", chatRouter);
app.use("/documents", documentsRouter);

// Health check
app.get("/health", async (_req, res) => {
  const redisOk = await isRedisHealthy();

  // Check ingestion service
  let ingestionOk = false;
  try {
    const resp = await fetch(`${config.ingestion.baseUrl}/health`);
    ingestionOk = resp.ok;
  } catch {
    ingestionOk = false;
  }

  const healthy = redisOk && ingestionOk;

  res.status(healthy ? 200 : 503).json({
    status: healthy ? "healthy" : "degraded",
    services: {
      redis: redisOk ? "connected" : "disconnected",
      ingestion: ingestionOk ? "connected" : "disconnected",
    },
    timestamp: new Date().toISOString(),
  });
});

// ── Start server ───────────────────────────────────────────
const server = app.listen(config.api.port, () => {
  console.log(`
╔══════════════════════════════════════════════════╗
║     Document Intelligence RAG — API Server       ║
╠══════════════════════════════════════════════════╣
║  Port:       ${String(config.api.port).padEnd(35)}║
║  LLM:        ${(config.llm.provider + " / " + config.llm.model).padEnd(35)}║
║  Redis:      ${config.redis.url.padEnd(35)}║
║  Ingestion:  ${config.ingestion.baseUrl.padEnd(35)}║
╚══════════════════════════════════════════════════╝
  `);

  // Connect to Redis eagerly
  getRedisClient().connect().catch((err) => {
    console.warn("[Redis] Initial connection failed:", err.message);
    console.warn("[Redis] Caching will be unavailable — queries still work");
  });
});

// ── Graceful shutdown ──────────────────────────────────────
async function shutdown() {
  console.log("\n[Server] Shutting down...");
  server.close();
  await disconnectRedis();
  closeDb();
  console.log("[Server] Goodbye");
  process.exit(0);
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
