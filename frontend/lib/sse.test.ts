import { describe, expect, it } from "vitest";
import { SseParser } from "./sse";

describe("SseParser", () => {
  it("parses complete frames", () => {
    const parser = new SseParser();
    const events = parser.feed('data: {"type":"token","value":"Hi"}\n\n');
    expect(events).toEqual([{ type: "token", value: "Hi" }]);
  });

  it("buffers partial frames across chunks", () => {
    const parser = new SseParser();
    expect(parser.feed('data: {"type":"token",')).toEqual([]);
    expect(parser.feed('"value":"Hello"}\n\n')).toEqual([
      { type: "token", value: "Hello" },
    ]);
  });

  it("handles several frames in one chunk", () => {
    const parser = new SseParser();
    const events = parser.feed(
      'data: {"type":"token","value":"A"}\n\ndata: {"type":"final","answer":"A","sources":[]}\n\n',
    );
    expect(events).toHaveLength(2);
    expect(events[1]).toEqual({ type: "final", answer: "A", sources: [] });
  });

  it("ignores malformed frames", () => {
    const parser = new SseParser();
    expect(parser.feed("data: not-json\n\n")).toEqual([]);
    expect(parser.feed(": comment\n\n")).toEqual([]);
  });
});
