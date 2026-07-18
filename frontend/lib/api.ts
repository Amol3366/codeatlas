/**
 * Typed client for the CodeAtlas backend API (CLAUDE.md §6).
 *
 * The backend base URL comes from NEXT_PUBLIC_API_BASE_URL (never hardcoded at
 * call sites); next.config.ts sources it from the project-global .env.
 */

import { streamChat } from "./sse";
import type {
  ChatEvent,
  ChatTurn,
  FileContentResponse,
  FilesResponse,
  IngestResponse,
  StatusResponse,
} from "./types";

export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`);
  if (!response.ok) {
    throw new Error(`GET ${path} failed: ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export async function fetchStatus(): Promise<StatusResponse> {
  return getJson<StatusResponse>("/status");
}

export async function fetchFiles(query?: string): Promise<FilesResponse> {
  const suffix = query ? `?query=${encodeURIComponent(query)}` : "";
  return getJson<FilesResponse>(`/files${suffix}`);
}

export async function fetchFileContent(path: string): Promise<FileContentResponse> {
  return getJson<FileContentResponse>(`/files/content?path=${encodeURIComponent(path)}`);
}

export async function startIngest(
  path: string,
  repoLabel: string,
): Promise<IngestResponse> {
  const response = await fetch(`${apiBaseUrl()}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, repo_label: repoLabel }),
  });
  if (!response.ok) {
    throw new Error(`POST /ingest failed: ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as IngestResponse;
}

export async function chat(
  question: string,
  history: ChatTurn[],
  onEvent: (event: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  await streamChat(`${apiBaseUrl()}/chat`, { question, history }, onEvent, signal);
}
