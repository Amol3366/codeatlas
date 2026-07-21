"use client";

import type { Source, ThreadMessage } from "@/lib/types";
import { Markdown } from "./Markdown";

function answerWithSourceLinks(content: string, sources: Source[]): string {
  if (sources.length === 0 || content.includes("#source-")) return content;
  const links = sources
    .slice(0, 3)
    .map((_, index) => `[here](#source-${index + 1})`)
    .join(", ");
  return `${content.trim()}\n\nSource: ${links}.`;
}

/** One user or assistant turn in the thread. */
export function MessageBubble({
  message,
  onOpenSource,
}: {
  message: ThreadMessage;
  onOpenSource: (source: Source) => void;
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end px-4 py-3 sm:px-6">
        <div className="max-w-[min(80%,42rem)] rounded-3xl bg-user px-5 py-3 text-[15px] whitespace-pre-wrap text-ink">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 py-5 sm:px-6">
      <div className="mx-auto flex max-w-3xl gap-4">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ink text-xs font-semibold text-panel">
          CA
        </div>
        <div className="min-w-0 flex-1 pt-1">
          {message.error !== null ? (
            <p role="alert" className="text-[14px] text-danger">
              {message.error}
            </p>
          ) : message.content === "" && message.streaming ? (
            <p className="text-[14px] text-ink-soft italic">Searching the index...</p>
          ) : (
            <div className={message.streaming ? "stream-caret" : undefined}>
              <Markdown sources={message.sources} onOpenSource={onOpenSource}>
                {answerWithSourceLinks(message.content, message.sources)}
              </Markdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
