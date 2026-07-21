"use client";

import { useEffect, useRef, useState } from "react";
import { fetchFileContent } from "@/lib/api";
import type { Source } from "@/lib/types";

interface PreviewState {
  loading: boolean;
  error: string | null;
  lines: string[];
}

/** Slide-over code preview for a cited source. */
export function SourcePreview({
  source,
  onClose,
}: {
  source: Source;
  onClose: () => void;
}) {
  const [state, setState] = useState<PreviewState>({
    loading: true,
    error: null,
    lines: [],
  });
  const citedRef = useRef<HTMLTableRowElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchFileContent(source.path)
      .then((file) => {
        if (!cancelled) {
          setState({ loading: false, error: null, lines: file.content.split("\n") });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            loading: false,
            error: error instanceof Error ? error.message : "Failed to load file",
            lines: [],
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [source.path]);

  useEffect(() => {
    if (!state.loading && state.error === null) {
      citedRef.current?.scrollIntoView({ block: "center" });
    }
  }, [state.loading, state.error]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex" role="dialog" aria-modal="true">
      <button
        type="button"
        aria-label="Close preview"
        onClick={onClose}
        className="flex-1 cursor-default bg-ink/25"
      />
      <div className="flex h-full w-full max-w-2xl flex-col border-l border-line bg-panel shadow-xl">
        <header className="flex items-center justify-between gap-3 border-b border-line px-5 py-3">
          <div className="min-w-0">
            <p className="truncate font-mono text-[13px] font-medium">{source.path}</p>
            <p className="text-[12px] text-ink-soft">
              Lines {source.start_line}-{source.end_line}
              {source.symbol_name ? ` - ${source.symbol_name}` : ""}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2.5 py-1 text-sm text-ink-soft hover:bg-hover hover:text-ink"
          >
            Close
          </button>
        </header>
        <div className="flex-1 overflow-auto">
          {state.loading ? (
            <p className="p-5 text-sm text-ink-soft">Loading file...</p>
          ) : state.error !== null ? (
            <p role="alert" className="p-5 text-sm text-danger">
              {state.error}
            </p>
          ) : (
            <table className="w-full border-collapse font-mono text-[12.5px] leading-[1.6]">
              <tbody>
                {state.lines.map((line, index) => {
                  const lineNo = index + 1;
                  const cited = lineNo >= source.start_line && lineNo <= source.end_line;
                  return (
                    <tr
                      key={lineNo}
                      ref={lineNo === source.start_line ? citedRef : undefined}
                      className={cited ? "bg-highlight" : undefined}
                    >
                      <td className="w-12 select-none border-r border-line px-2 text-right text-ink-soft/70">
                        {lineNo}
                      </td>
                      <td className="px-3 whitespace-pre">{line || " "}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
