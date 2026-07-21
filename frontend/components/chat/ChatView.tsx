"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SourcePreview } from "@/components/preview/SourcePreview";
import { chat } from "@/lib/api";
import type { ChatTurn, Source, ThreadMessage } from "@/lib/types";
import { Composer } from "./Composer";
import { MessageBubble } from "./MessageBubble";

const STORAGE_KEY = "codeatlas.chat.sessions.v1";
const EMPTY_MESSAGES: ThreadMessage[] = [];

let nextId = 0;
const newId = () => `msg-${Date.now()}-${nextId++}`;

interface ChatSession {
  id: string;
  title: string;
  updatedAt: number;
  messages: ThreadMessage[];
}

interface ChatState {
  sessions: ChatSession[];
  activeId: string;
}

function createSession(): ChatSession {
  const id = `chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  return {
    id,
    title: "New chat",
    updatedAt: Date.now(),
    messages: [],
  };
}

function initialState(): ChatState {
  const session = createSession();
  return { sessions: [session], activeId: session.id };
}

function loadStoredState(): ChatState | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ChatState;
    if (!Array.isArray(parsed.sessions) || typeof parsed.activeId !== "string") {
      return null;
    }
    if (parsed.sessions.length === 0) return null;
    return parsed;
  } catch {
    return null;
  }
}

function titleFromQuestion(question: string): string {
  const title = question.replace(/\s+/g, " ").trim();
  return title.length > 42 ? `${title.slice(0, 39)}...` : title || "New chat";
}

/** Chat page with local chat history, streaming answers, and source previews. */
export function ChatView() {
  const [chatState, setChatState] = useState<ChatState>(() => initialState());
  const [hydrated, setHydrated] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [preview, setPreview] = useState<Source | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const activeSession = useMemo(
    () =>
      chatState.sessions.find((session) => session.id === chatState.activeId) ??
      chatState.sessions[0],
    [chatState],
  );
  const messages = activeSession?.messages ?? EMPTY_MESSAGES;

  useEffect(() => {
    const stored = loadStoredState();
    if (stored) setChatState(stored);
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(chatState));
  }, [chatState, hydrated]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const updateSessionMessages = useCallback(
    (
      sessionId: string,
      patch: (messages: ThreadMessage[]) => ThreadMessage[],
      title?: string,
    ) => {
      setChatState((current) => ({
        ...current,
        sessions: current.sessions
          .map((session) => {
            if (session.id !== sessionId) return session;
            return {
              ...session,
              title: title ?? session.title,
              updatedAt: Date.now(),
              messages: patch(session.messages),
            };
          })
          .sort((a, b) => b.updatedAt - a.updatedAt),
      }));
    },
    [],
  );

  const updateLast = useCallback(
    (sessionId: string, patch: (message: ThreadMessage) => ThreadMessage) => {
      updateSessionMessages(sessionId, (current) => {
        if (current.length === 0) return current;
        const last = current[current.length - 1];
        if (last === undefined) return current;
        return [...current.slice(0, -1), patch(last)];
      });
    },
    [updateSessionMessages],
  );

  const startNewChat = useCallback(() => {
    const session = createSession();
    setChatState((current) => ({
      activeId: session.id,
      sessions: [session, ...current.sessions],
    }));
  }, []);

  const deleteChat = useCallback((sessionId: string) => {
    setPreview(null);
    setChatState((current) => {
      const remaining = current.sessions.filter((session) => session.id !== sessionId);
      if (remaining.length === 0) {
        const session = createSession();
        return { activeId: session.id, sessions: [session] };
      }
      const nextActiveId = remaining[0]?.id ?? current.activeId;
      return {
        activeId: current.activeId === sessionId ? nextActiveId : current.activeId,
        sessions: remaining,
      };
    });
  }, []);

  const send = useCallback(
    async (question: string) => {
      if (!activeSession) return;
      const sessionId = activeSession.id;
      const history: ChatTurn[] = activeSession.messages
        .filter((message) => message.error === null)
        .map((message) => ({ role: message.role, content: message.content }));

      const userMessage: ThreadMessage = {
        id: newId(),
        role: "user",
        content: question,
        sources: [],
        streaming: false,
        error: null,
      };
      const assistantMessage: ThreadMessage = {
        id: newId(),
        role: "assistant",
        content: "",
        sources: [],
        streaming: true,
        error: null,
      };

      updateSessionMessages(
        sessionId,
        (current) => [...current, userMessage, assistantMessage],
        activeSession.messages.length === 0
          ? titleFromQuestion(question)
          : activeSession.title,
      );
      setStreaming(true);

      try {
        await chat(question, history, (event) => {
          if (event.type === "token") {
            updateLast(sessionId, (message) => ({
              ...message,
              content: message.content + event.value,
            }));
          } else if (event.type === "final") {
            updateLast(sessionId, (message) => ({
              ...message,
              content: event.answer,
              sources: event.sources,
              streaming: false,
            }));
          } else {
            updateLast(sessionId, (message) => ({
              ...message,
              streaming: false,
              error: event.message,
            }));
          }
        });
        updateLast(sessionId, (message) =>
          message.streaming ? { ...message, streaming: false } : message,
        );
      } catch (error: unknown) {
        updateLast(sessionId, (message) => ({
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
    [activeSession, updateLast, updateSessionMessages],
  );

  return (
    <div className="flex h-screen bg-paper text-ink">
      <aside className="hidden w-72 shrink-0 flex-col border-r border-line bg-sidebar px-3 py-3 md:flex">
        <button
          type="button"
          onClick={startNewChat}
          className="mb-3 rounded-lg border border-line bg-panel px-3 py-2 text-left text-sm font-medium hover:bg-hover"
        >
          New chat
        </button>
        <Link
          href="/manage"
          className="mb-5 rounded-lg px-3 py-2 text-sm text-ink-soft hover:bg-hover hover:text-ink"
        >
          Index repository
        </Link>
        <div className="mb-2 px-3 text-xs font-medium text-ink-soft">Chats</div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          {chatState.sessions.map((session) => (
            <div
              key={session.id}
              className={`group mb-1 w-full truncate rounded-lg px-3 py-2 text-left text-sm ${
                session.id === activeSession?.id
                  ? "bg-active text-ink"
                  : "text-ink-soft hover:bg-hover hover:text-ink"
              }`}
            >
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() =>
                    setChatState((current) => ({ ...current, activeId: session.id }))
                  }
                  className="min-w-0 flex-1 truncate text-left"
                >
                  {session.title}
                </button>
                <button
                  type="button"
                  onClick={() => deleteChat(session.id)}
                  aria-label={`Delete chat ${session.title}`}
                  title="Delete chat"
                  className="h-6 w-6 shrink-0 rounded-md text-xs text-ink-soft opacity-0 hover:bg-line hover:text-ink focus:opacity-100 group-hover:opacity-100"
                >
                  x
                </button>
              </div>
            </div>
          ))}
        </div>
        <div className="border-t border-line pt-3">
          <div className="text-sm font-semibold text-ink">CodeAtlas</div>
          <p className="mt-1 truncate text-xs text-ink-soft">
            Explore codebases and related docs with grounded code-source answers.
          </p>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-line px-4 md:hidden">
          <button
            type="button"
            onClick={startNewChat}
            className="rounded-lg border border-line px-3 py-1.5 text-sm"
          >
            New
          </button>
          <span className="text-sm font-semibold">CodeAtlas</span>
          <Link href="/manage" className="text-sm text-ink-soft">
            Index
          </Link>
        </header>

        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center px-6 text-center">
              <h1 className="text-3xl font-semibold tracking-normal">
                What can I help you find?
              </h1>
              <p className="mt-3 max-w-md text-[15px] text-ink-soft">
                Ask about code files, project docs, or implementation flow. Short
                source links open the exact evidence behind each answer.
              </p>
            </div>
          ) : (
            <div>
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

        <div className="mx-auto w-full max-w-3xl px-4 pb-4 sm:px-6">
          <Composer disabled={streaming} onSend={send} />
          <p className="mt-2 text-center text-[11px] text-ink-soft">
            Enter to send. Shift+Enter for a new line.
          </p>
        </div>
      </main>

      {preview !== null ? (
        <SourcePreview
          key={`${preview.path}:${preview.start_line}-${preview.end_line}`}
          source={preview}
          onClose={() => setPreview(null)}
        />
      ) : null}
    </div>
  );
}
