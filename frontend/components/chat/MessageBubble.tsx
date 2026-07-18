"use client";

import type { Source, ThreadMessage } from "@/lib/types";
import { Markdown } from "./Markdown";
import { SourcesPanel } from "./SourcesPanel";

/** One user or assistant turn in the thread, with sources on assistant turns. */
export function MessageBubble({
  message,
  onOpenSource,
}: {
  message: ThreadMessage;
  onOpenSource: (source: Source) => void;
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-2xl rounded-br-sm bg-accent-soft px-4 py-2.5 text-[15px] whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    );
  }
  return (
    <div className="rounded-2xl rounded-bl-sm border border-line bg-panel px-5 py-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
      {message.error !== null ? (
        <p role="alert" className="text-[14px] text-danger">
          {message.error}
        </p>
      ) : message.content === "" && message.streaming ? (
        <p className="text-[14px] text-ink-soft italic">Searching the index…</p>
      ) : (
        <div className={message.streaming ? "stream-caret" : undefined}>
          <Markdown>{message.content}</Markdown>
        </div>
      )}
      {!message.streaming && message.error === null ? (
        <SourcesPanel sources={message.sources} onOpen={onOpenSource} />
      ) : null}
    </div>
  );
}
