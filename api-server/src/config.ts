/**
 * Centralized environment configuration.
 *
 * All external dependencies (Redis, LLM, ingestion service) are configured
 * here via environment variables with sensible defaults for local dev.
 */

import { z } from "zod";

const envSchema = z.object({
  // LLM Provider
  LLM_PROVIDER: z.enum(["ollama", "groq"]).default("ollama"),
  LLM_BASE_URL: z.string().default("http://localhost:11434/v1"),
  LLM_MODEL: z.string().default("llama3.2"),
  LLM_API_KEY: z.string().default("ollama"),

  // Redis
  REDIS_URL: z.string().default("redis://localhost:6379"),
  CACHE_TTL_SECONDS: z.coerce.number().default(3600),

  // Ingestion Service (Python)
  INGESTION_HOST: z.string().default("localhost"),
  INGESTION_PORT: z.coerce.number().default(8100),

  // API Server
  API_PORT: z.coerce.number().default(3000),

  // Persistence
  DB_PROVIDER: z.enum(["sqlite", "cosmosdb"]).default("sqlite"),
  SQLITE_PATH: z.string().default("./data/conversations.db"),
});

function loadConfig() {
  const result = envSchema.safeParse(process.env);

  if (!result.success) {
    console.error("Invalid environment configuration:");
    console.error(result.error.format());
    process.exit(1);
  }

  const env = result.data;

  return {
    llm: {
      provider: env.LLM_PROVIDER,
      baseUrl: env.LLM_BASE_URL,
      model: env.LLM_MODEL,
      apiKey: env.LLM_API_KEY,
    },
    redis: {
      url: env.REDIS_URL,
      cacheTtlSeconds: env.CACHE_TTL_SECONDS,
    },
    ingestion: {
      baseUrl: `http://${env.INGESTION_HOST}:${env.INGESTION_PORT}`,
    },
    api: {
      port: env.API_PORT,
    },
    db: {
      provider: env.DB_PROVIDER,
      sqlitePath: env.SQLITE_PATH,
    },
  } as const;
}

export const config = loadConfig();
export type Config = ReturnType<typeof loadConfig>;
