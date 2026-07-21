"use client";

import type { Source } from "@/lib/types";

/** Human label like `src/auth/session.py:42-88`. */
export function sourceLabel(source: Source): string {
  return `${source.path}:${source.start_line}-${source.end_line}`;
}

/** Clickable source list retained for focused source-list displays. */
export function SourcesPanel({
  sources,
  onOpen,
}: {
  sources: Source[];
  onOpen: (source: Source) => void;
}) {
  if (sources.length === 0) return null;
  return (
    <section aria-label="Sources" className="mt-3 border-t border-line pt-3">
      <h3 className="mb-2 text-[11px] font-semibold tracking-wider text-ink-soft uppercase">
        Sources
      </h3>
      <ul className="flex flex-col gap-1">
        {sources.map((source) => (
          <li key={`${source.path}:${source.start_line}-${source.end_line}`}>
            <button
              type="button"
              onClick={() => onOpen(source)}
              className="group flex w-full items-baseline gap-2 rounded-md px-2 py-1 text-left font-mono text-[12.5px] text-accent hover:bg-hover"
            >
              <span className="truncate underline-offset-2 group-hover:underline">
                {sourceLabel(source)}
              </span>
              {source.symbol_name ? (
                <span className="shrink-0 font-body text-[11px] text-ink-soft">
                  {source.symbol_name}
                </span>
              ) : null}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
