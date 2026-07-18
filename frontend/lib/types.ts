/**
 * TypeScript mirrors of the backend API schemas (CLAUDE.md §6).
 * Keep in sync with backend/app/models.py.
 */

export interface Source {
  path: string;
  start_line: number;
  end_line: number;
  symbol_name: string | null;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

/** One SSE frame emitted by POST /chat. */
export type ChatEvent =
  | { type: "token"; value: string }
  | { type: "final"; answer: string; sources: Source[] }
  | { type: "error"; message: string };

export interface IngestResponse {
  job_id: string;
  status: string;
}

export interface IndexSummary {
  repo_label: string;
  path: string;
  files_indexed: number;
  chunks_indexed: number;
  finished_at: string;
}

export interface StatusResponse {
  job_id: string | null;
  state: "idle" | "running" | "completed" | "failed";
  message: string | null;
  files_seen: number;
  files_indexed: number;
  chunks_indexed: number;
  error: string | null;
  last_successful_index: IndexSummary | null;
}

export interface FileInfo {
  repo: string;
  path: string;
  kind: "code" | "doc";
  language: string | null;
  chunk_count: number;
}

export interface FilesResponse {
  files: FileInfo[];
  total_files: number;
  total_chunks: number;
}

export interface FileContentResponse {
  repo: string;
  path: string;
  language: string | null;
  content: string;
  total_lines: number;
}

/** A chat message as rendered in the thread (assistant turns carry sources). */
export interface ThreadMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: Source[];
  streaming: boolean;
  error: string | null;
}
