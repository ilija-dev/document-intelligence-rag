/**
 * Conversation history persistence with SQLite.
 *
 * Redis is volatile — restart and cache is gone. SQLite (standing in for
 * CosmosDB in production) provides durable storage for:
 * 1. Conversation history — multi-turn conversations with context
 * 2. Analytics — what questions are asked most (feeds cache warming)
 * 3. Audit trail — who asked what, when, from which sources
 *
 * Interview point: "In production this uses CosmosDB for global distribution
 * and partition-key-based queries. For the demo I use SQLite as a drop-in
 * replacement — the interface is identical, only the storage backend changes."
 */

import Database from "better-sqlite3";
import { v4 as uuidv4 } from "uuid";
import { config } from "../config.js";
import { mkdirSync } from "fs";
import { dirname } from "path";

let db: Database.Database | null = null;

function getDb(): Database.Database {
  if (!db) {
    const dbPath = config.db.sqlitePath;
    mkdirSync(dirname(dbPath), { recursive: true });

    db = new Database(dbPath);
    db.pragma("journal_mode = WAL"); // Better concurrent read performance
    db.pragma("foreign_keys = ON");

    // Create tables
    db.exec(`
      CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        query TEXT NOT NULL,
        response TEXT NOT NULL,
        sources TEXT NOT NULL,
        was_cached INTEGER NOT NULL DEFAULT 0,
        search_time_ms REAL DEFAULT 0,
        generation_time_ms REAL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE INDEX IF NOT EXISTS idx_conversations_user_session
        ON conversations(user_id, session_id, created_at DESC);

      CREATE INDEX IF NOT EXISTS idx_conversations_created
        ON conversations(created_at DESC);
    `);

    console.log("[DB] SQLite initialized at", dbPath);
  }
  return db;
}

// ── Types ──────────────────────────────────────────────────

export interface ConversationEntry {
  userId: string;
  sessionId: string;
  query: string;
  response: string;
  sources: Array<{
    docName: string;
    pageNumber: number;
    chunkText: string;
    score: number;
  }>;
  wasCached: boolean;
  searchTimeMs: number;
  generationTimeMs: number;
}

export interface ConversationRecord {
  id: string;
  userId: string;
  sessionId: string;
  query: string;
  response: string;
  sources: Array<{
    docName: string;
    pageNumber: number;
    chunkText: string;
    score: number;
  }>;
  wasCached: boolean;
  searchTimeMs: number;
  generationTimeMs: number;
  createdAt: string;
}

// ── Operations ─────────────────────────────────────────────

/**
 * Save a conversation turn to the database.
 */
export async function saveConversation(
  entry: ConversationEntry
): Promise<string> {
  const database = getDb();
  const id = uuidv4();

  const stmt = database.prepare(`
    INSERT INTO conversations (id, user_id, session_id, query, response, sources, was_cached, search_time_ms, generation_time_ms)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  stmt.run(
    id,
    entry.userId,
    entry.sessionId,
    entry.query,
    entry.response,
    JSON.stringify(entry.sources),
    entry.wasCached ? 1 : 0,
    entry.searchTimeMs,
    entry.generationTimeMs
  );

  return id;
}

/**
 * Get recent conversation history for a user session.
 * Used to provide multi-turn context to the LLM.
 */
export async function getConversationHistory(
  userId: string,
  sessionId: string,
  limit: number = 5
): Promise<ConversationRecord[]> {
  const database = getDb();

  const stmt = database.prepare(`
    SELECT * FROM conversations
    WHERE user_id = ? AND session_id = ?
    ORDER BY created_at DESC
    LIMIT ?
  `);

  const rows = stmt.all(userId, sessionId, limit) as Array<{
    id: string;
    user_id: string;
    session_id: string;
    query: string;
    response: string;
    sources: string;
    was_cached: number;
    search_time_ms: number;
    generation_time_ms: number;
    created_at: string;
  }>;

  return rows.reverse().map((row) => ({
    id: row.id,
    userId: row.user_id,
    sessionId: row.session_id,
    query: row.query,
    response: row.response,
    sources: JSON.parse(row.sources),
    wasCached: row.was_cached === 1,
    searchTimeMs: row.search_time_ms,
    generationTimeMs: row.generation_time_ms,
    createdAt: row.created_at,
  }));
}

/**
 * Get analytics: most common queries, cache hit rates, etc.
 */
export async function getQueryAnalytics(limit: number = 20) {
  const database = getDb();

  const topQueries = database
    .prepare(
      `
    SELECT query, COUNT(*) as count,
           AVG(CASE WHEN was_cached = 1 THEN 1.0 ELSE 0.0 END) as cache_rate,
           AVG(search_time_ms) as avg_search_ms,
           AVG(generation_time_ms) as avg_gen_ms
    FROM conversations
    GROUP BY query
    ORDER BY count DESC
    LIMIT ?
  `
    )
    .all(limit);

  const totalConversations = database
    .prepare("SELECT COUNT(*) as count FROM conversations")
    .get() as { count: number };

  const cacheRate = database
    .prepare(
      "SELECT AVG(CASE WHEN was_cached = 1 THEN 1.0 ELSE 0.0 END) as rate FROM conversations"
    )
    .get() as { rate: number };

  return {
    totalConversations: totalConversations.count,
    overallCacheRate: Math.round((cacheRate.rate ?? 0) * 100),
    topQueries,
  };
}

/**
 * Close the database connection cleanly.
 */
export function closeDb(): void {
  if (db) {
    db.close();
    db = null;
  }
}
