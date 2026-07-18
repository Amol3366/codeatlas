"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchFiles, fetchStatus, startIngest } from "@/lib/api";
import type { FilesResponse, Source, StatusResponse } from "@/lib/types";
import { SourcePreview } from "@/components/preview/SourcePreview";

const POLL_MS = 1500;

/** Index management: trigger /ingest, watch /status, browse /files (§7a). */
export function ManageView() {
  const [path, setPath] = useState("");
  const [repoLabel, setRepoLabel] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [files, setFiles] = useState<FilesResponse | null>(null);
  const [query, setQuery] = useState("");
  const [preview, setPreview] = useState<Source | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshFiles = useCallback(async (filter: string) => {
    try {
      setFiles(await fetchFiles(filter || undefined));
    } catch {
      setFiles(null);
    }
  }, []);

  const refreshStatus = useCallback(async () => {
    try {
      const next = await fetchStatus();
      setStatus(next);
      setStatusError(null);
      return next;
    } catch (error: unknown) {
      setStatusError(
        error instanceof Error ? error.message : "Could not reach the backend",
      );
      return null;
    }
  }, []);

  // Initial load: setState only from promise callbacks (async by construction).
  useEffect(() => {
    fetchStatus()
      .then((next) => setStatus(next))
      .catch(() => setStatusError("Could not reach the backend"));
    fetchFiles()
      .then((next) => setFiles(next))
      .catch(() => setFiles(null));
  }, []);

  useEffect(() => {
    if (status?.state !== "running") return;
    pollRef.current = setInterval(() => {
      void refreshStatus().then((next) => {
        if (next && next.state !== "running") {
          void refreshFiles(query);
        }
      });
    }, POLL_MS);
    return () => {
      if (pollRef.current !== null) clearInterval(pollRef.current);
    };
  }, [status?.state, refreshStatus, refreshFiles, query]);

  const submit = async () => {
    setFormError(null);
    if (path.trim() === "" || repoLabel.trim() === "") {
      setFormError("Both the folder path and a repo label are required.");
      return;
    }
    try {
      await startIngest(path.trim(), repoLabel.trim());
      await refreshStatus();
    } catch (error: unknown) {
      setFormError(error instanceof Error ? error.message : "Ingest request failed");
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        Index management
      </h1>
      <p className="mt-1 text-sm text-ink-soft">
        Point CodeAtlas at a repository or folder, then watch indexing progress.
      </p>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
        className="mt-6 rounded-xl border border-line bg-panel p-5 shadow-[0_1px_3px_rgba(0,0,0,0.04)]"
      >
        <div className="flex flex-col gap-3 sm:flex-row">
          <label className="flex-1 text-sm">
            <span className="mb-1 block font-medium">Folder path</span>
            <input
              value={path}
              onChange={(event) => setPath(event.target.value)}
              placeholder="C:\projects\my-repo"
              className="w-full rounded-lg border border-line bg-paper px-3 py-2 font-mono text-[13px] outline-none focus:border-accent"
            />
          </label>
          <label className="text-sm sm:w-48">
            <span className="mb-1 block font-medium">Repo label</span>
            <input
              value={repoLabel}
              onChange={(event) => setRepoLabel(event.target.value)}
              placeholder="my-repo"
              className="w-full rounded-lg border border-line bg-paper px-3 py-2 text-[13px] outline-none focus:border-accent"
            />
          </label>
        </div>
        {formError !== null ? (
          <p role="alert" className="mt-2 text-sm text-danger">
            {formError}
          </p>
        ) : null}
        <button
          type="submit"
          disabled={status?.state === "running"}
          className="mt-4 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          {status?.state === "running" ? "Indexing…" : "Start indexing"}
        </button>
      </form>

      <section className="mt-6 rounded-xl border border-line bg-panel p-5">
        <h2 className="text-sm font-semibold tracking-wider text-ink-soft uppercase">
          Status
        </h2>
        {statusError !== null ? (
          <p role="alert" className="mt-2 text-sm text-danger">
            {statusError}
          </p>
        ) : status === null ? (
          <p className="mt-2 text-sm text-ink-soft">Loading…</p>
        ) : (
          <div className="mt-3 text-sm">
            <p>
              <StateBadge state={status.state} />
              {status.message ? (
                <span className="ml-2 text-ink-soft">{status.message}</span>
              ) : null}
            </p>
            {status.state === "running" || status.files_indexed > 0 ? (
              <p className="mt-2 text-ink-soft">
                {status.files_indexed} files indexed · {status.chunks_indexed} chunks
                {status.state === "running" ? ` · ${status.files_seen} files seen` : ""}
              </p>
            ) : null}
            {status.error ? (
              <p role="alert" className="mt-2 text-danger">
                {status.error}
              </p>
            ) : null}
            {status.last_successful_index ? (
              <p className="mt-2 border-t border-line pt-2 text-[13px] text-ink-soft">
                Last successful index: <b>{status.last_successful_index.repo_label}</b> —{" "}
                {status.last_successful_index.files_indexed} files,{" "}
                {status.last_successful_index.chunks_indexed} chunks (
                {new Date(status.last_successful_index.finished_at).toLocaleString()})
              </p>
            ) : null}
          </div>
        )}
      </section>

      <section className="mt-6 rounded-xl border border-line bg-panel p-5">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-sm font-semibold tracking-wider text-ink-soft uppercase">
            Indexed files{files ? ` (${files.total_files})` : ""}
          </h2>
          <input
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              void refreshFiles(event.target.value);
            }}
            placeholder="Filter by path…"
            aria-label="Filter files"
            className="w-56 rounded-lg border border-line bg-paper px-3 py-1.5 text-[13px] outline-none focus:border-accent"
          />
        </div>
        {files === null || files.files.length === 0 ? (
          <p className="mt-3 text-sm text-ink-soft">
            {files === null
              ? "No data — is the backend running?"
              : "No files indexed yet."}
          </p>
        ) : (
          <table className="mt-3 w-full text-left text-[13px]">
            <thead>
              <tr className="border-b border-line text-[11px] tracking-wider text-ink-soft uppercase">
                <th className="py-1.5 pr-3 font-medium">Path</th>
                <th className="py-1.5 pr-3 font-medium">Kind</th>
                <th className="py-1.5 pr-3 font-medium">Language</th>
                <th className="py-1.5 text-right font-medium">Chunks</th>
              </tr>
            </thead>
            <tbody>
              {files.files.map((file) => (
                <tr key={`${file.repo}/${file.path}`} className="border-b border-line/60">
                  <td className="py-1.5 pr-3">
                    <button
                      type="button"
                      onClick={() =>
                        setPreview({
                          path: file.path,
                          start_line: 1,
                          end_line: 1,
                          symbol_name: null,
                        })
                      }
                      className="font-mono text-accent underline-offset-2 hover:underline"
                    >
                      {file.path}
                    </button>
                  </td>
                  <td className="py-1.5 pr-3">{file.kind}</td>
                  <td className="py-1.5 pr-3">{file.language ?? "—"}</td>
                  <td className="py-1.5 text-right">{file.chunk_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {preview !== null ? (
        <SourcePreview source={preview} onClose={() => setPreview(null)} />
      ) : null}
    </div>
  );
}

function StateBadge({ state }: { state: StatusResponse["state"] }) {
  const styles: Record<StatusResponse["state"], string> = {
    idle: "bg-paper text-ink-soft border-line",
    running: "bg-accent-soft text-accent border-accent/30",
    completed: "bg-accent-soft text-accent border-accent/30",
    failed: "bg-red-50 text-danger border-danger/30",
  };
  return (
    <span
      className={`inline-block rounded-full border px-2.5 py-0.5 text-[12px] font-medium ${styles[state]}`}
    >
      {state}
    </span>
  );
}
