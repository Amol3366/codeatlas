import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import type { NextConfig } from "next";

/**
 * Read NEXT_PUBLIC_API_BASE_URL from the project-global .env at the repo root
 * (CLAUDE.md §11). Next.js only auto-loads frontend/.env*, so this makes the
 * root .env the single source of truth; frontend/.env.local still wins if set.
 */
function rootEnvApiBaseUrl(): string | undefined {
  const rootEnv = join(__dirname, "..", ".env");
  if (!existsSync(rootEnv)) return undefined;
  const match = /^\s*NEXT_PUBLIC_API_BASE_URL\s*=\s*([^\s#]+)/m.exec(
    readFileSync(rootEnv, "utf-8"),
  );
  return match?.[1];
}

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? rootEnvApiBaseUrl(),
  },
};

export default nextConfig;
