import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ChatView } from "./ChatView";

/** Build a fetch Response whose body streams the given SSE frames. */
function sseResponse(frames: string[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const frame of frames) controller.enqueue(encoder.encode(frame));
      controller.close();
    },
  });
  return { ok: true, status: 200, statusText: "OK", body } as unknown as Response;
}

function jsonResponse(payload: unknown): Response {
  return {
    ok: true,
    status: 200,
    statusText: "OK",
    json: () => Promise.resolve(payload),
  } as unknown as Response;
}

const CHAT_FRAMES = [
  'data: {"type":"token","value":"Auth is handled "}\n\n',
  'data: {"type":"token","value":"in the session module."}\n\n',
  'data: {"type":"final","answer":"Auth is handled in the session module.","sources":[{"path":"auth.py","start_line":5,"end_line":9,"symbol_name":"create_session"}]}\n\n',
];

const FILE_CONTENT = {
  repo: "test",
  path: "auth.py",
  language: "python",
  content: "l1\nl2\nl3\nl4\ndef create_session():\n    pass\nl7\nl8\nl9\nl10",
  total_lines: 10,
};

describe("ChatView smoke test", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/chat")) return Promise.resolve(sseResponse(CHAT_FRAMES));
        if (url.includes("/files/content"))
          return Promise.resolve(jsonResponse(FILE_CONTENT));
        return Promise.reject(new Error(`Unexpected fetch: ${url}`));
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("streams an answer and renders an inline source link that opens the preview", async () => {
    render(<ChatView />);

    fireEvent.change(screen.getByLabelText("Question"), {
      target: { value: "where is auth handled?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(screen.getAllByText("where is auth handled?").length).toBeGreaterThan(0);
    await waitFor(() =>
      expect(
        screen.getByText("Auth is handled in the session module."),
      ).toBeInTheDocument(),
    );

    const sourceButton = await screen.findByRole("button", { name: "here" });
    fireEvent.click(sourceButton);

    await waitFor(() =>
      expect(screen.getByText("def create_session():")).toBeInTheDocument(),
    );
    expect(screen.getByText("Lines 5-9 - create_session")).toBeInTheDocument();
  });

  it("stores chats in local history", async () => {
    render(<ChatView />);

    fireEvent.change(screen.getByLabelText("Question"), {
      target: { value: "where is auth handled?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() =>
      expect(screen.getAllByText("where is auth handled?").length).toBeGreaterThan(0),
    );
    expect(screen.getAllByText("where is auth handled?").length).toBeGreaterThan(1);
  });

  it("deletes a saved chat from local history", async () => {
    window.localStorage.setItem(
      "codeatlas.chat.sessions.v1",
      JSON.stringify({
        activeId: "first",
        sessions: [
          {
            id: "first",
            title: "Auth question",
            updatedAt: 2,
            messages: [],
          },
          {
            id: "second",
            title: "Install question",
            updatedAt: 1,
            messages: [],
          },
        ],
      }),
    );

    render(<ChatView />);

    await waitFor(() => expect(screen.getByText("Auth question")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Delete chat Auth question" }));

    await waitFor(() =>
      expect(screen.queryByText("Auth question")).not.toBeInTheDocument(),
    );
    expect(screen.getByText("Install question")).toBeInTheDocument();

    const stored = JSON.parse(
      window.localStorage.getItem("codeatlas.chat.sessions.v1") ?? "{}",
    ) as { activeId: string; sessions: Array<{ id: string }> };
    expect(stored.activeId).toBe("second");
    expect(stored.sessions).toHaveLength(1);
  });

  it("shows an error state when the backend is unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new Error("connection refused"))),
    );
    render(<ChatView />);
    fireEvent.change(screen.getByLabelText("Question"), {
      target: { value: "anything" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Could not reach the backend"),
    );
  });
});
