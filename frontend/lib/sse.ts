/**
 * Minimal Server-Sent Events parsing for the /chat stream.
 *
 * The backend emits frames of the form `data: {json}\n\n`. This parser is
 * incremental: feed it arbitrary byte-chunk strings and it yields complete
 * events, buffering partial frames across chunks.
 */

import type { ChatEvent } from "./types";

export class SseParser {
  private buffer = "";

  /** Feed one decoded chunk; returns any complete events it finished. */
  feed(chunk: string): ChatEvent[] {
    this.buffer += chunk;
    const events: ChatEvent[] = [];
    let separatorIndex = this.buffer.indexOf("\n\n");
    while (separatorIndex !== -1) {
      const frame = this.buffer.slice(0, separatorIndex);
      this.buffer = this.buffer.slice(separatorIndex + 2);
      const event = parseFrame(frame);
      if (event !== null) events.push(event);
      separatorIndex = this.buffer.indexOf("\n\n");
    }
    return events;
  }
}

function parseFrame(frame: string): ChatEvent | null {
  const dataLines = frame
    .split("\n")
    .filter((line) => line.startsWith("data: "))
    .map((line) => line.slice("data: ".length));
  if (dataLines.length === 0) return null;
  try {
    return JSON.parse(dataLines.join("\n")) as ChatEvent;
  } catch {
    return null;
  }
}

/**
 * POST a question to /chat and invoke `onEvent` for each SSE event as it
 * arrives. Resolves when the stream closes; rejects on network failure.
 */
export async function streamChat(
  url: string,
  body: { question: string; history?: { role: string; content: string }[] },
  onEvent: (event: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok || response.body === null) {
    throw new Error(`Chat request failed: ${response.status} ${response.statusText}`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const parser = new SseParser();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    for (const event of parser.feed(decoder.decode(value, { stream: true }))) {
      onEvent(event);
    }
  }
}
