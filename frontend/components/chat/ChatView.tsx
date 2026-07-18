"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { chat } from "@/lib/api";
import type { ChatTurn, Source, ThreadMessage } from "@/lib/types";
import { Composer } from "./Composer";
import { MessageBubble } from "./MessageBubble";
import { SourcePreview } from "@/components/preview/SourcePreview";

let nextId = 0;
const newId = () => `msg-${nextId++}`;

/** The full chat experience: thread, streaming, sources, preview (§7a). */
export function ChatView() {
  const [messages, setMessages] = useState<ThreadMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [preview, setPreview] = useState<Source | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const updateLast = useCallback((patch: (message: ThreadMessage) => ThreadMessage) => {
    setMessages((current) => {
      if (current.length === 0) return current;
      const last = current[current.length - 1];
      if (last === undefined) return current;
      return [...current.slice(0, -1), patch(last)];
    });
  }, []);

  const send = useCallback(
    async (question: string) => {
      const history: ChatTurn[] = messages
        .filter((message) => message.error === null)
        .map((message) => ({ role: message.role, content: message.content }));

      setMessages((current) => [
        ...current,
        {
          id: newId(),
          role: "user",
          content: question,
          sources: [],
          streaming: false,
          error: null,
        },
        {
          id: newId(),
          role: "assistant",
          content: "",
          sources: [],
          streaming: true,
          error: null,
        },
      ]);
      setStreaming(true);

      try {
        await chat(question, history, (event) => {
          if (event.type === "token") {
            updateLast((message) => ({
              ...message,
              content: message.content + event.value,
            }));
          } else if (event.type === "final") {
            updateLast((message) => ({
              ...message,
              content: event.answer,
              sources: event.sources,
              streaming: false,
            }));
          } else {
            updateLast((message) => ({
              ...message,
              streaming: false,
              error: event.message,
            }));
          }
        });
        // If the stream closed without a final/error event, stop the caret.
        updateLast((message) =>
          message.streaming ? { ...message, streaming: false } : message,
        );
      } catch (error: unknown) {
        updateLast((message) => ({
          ...message,
          streaming: false,
          error:
            error instanceof Error
              ? `Could not reach the backend: ${error.message}`
              : "Could not reach the backend.",
        }));
      } finally {
        setStreaming(false);
      }
    },
    [messages, updateLast],
  );

  return (
    <div className="mx-auto flex h-screen max-w-3xl flex-col px-6">
      <div className="flex-1 overflow-y-auto py-8">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <h1 className="font-display text-3xl font-semibold tracking-tight">
              Ask your codebase anything
            </h1>
            <p className="mt-3 max-w-md text-[15px] text-ink-soft">
              Every answer is grounded in your indexed files and cites exact paths and
              line ranges. Index a repository first from the{" "}
              <span className="font-medium text-ink">Index</span> tab.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-5">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onOpenSource={setPreview}
              />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>
      <div className="pb-6">
        <Composer disabled={streaming} onSend={send} />
        <p className="mt-2 text-center text-[11px] text-ink-soft">
          Enter to send · Shift+Enter for a new line
        </p>
      </div>
      {preview !== null ? (
        <SourcePreview
          key={preview.path}
          source={preview}
          onClose={() => setPreview(null)}
        />
      ) : null}
    </div>
  );
}
