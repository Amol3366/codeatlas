import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Source } from "@/lib/types";
import { SourcesPanel, sourceLabel } from "./SourcesPanel";

const SOURCES: Source[] = [
  {
    path: "src/auth/session.py",
    start_line: 42,
    end_line: 88,
    symbol_name: "create_session",
  },
  { path: "README.md", start_line: 1, end_line: 12, symbol_name: null },
];

describe("SourcesPanel", () => {
  it("renders one clickable entry per source with path and line range", () => {
    render(<SourcesPanel sources={SOURCES} onOpen={() => {}} />);
    expect(screen.getByText("src/auth/session.py:42-88")).toBeInTheDocument();
    expect(screen.getByText("README.md:1-12")).toBeInTheDocument();
    expect(screen.getByText("create_session")).toBeInTheDocument();
  });

  it("invokes onOpen with the clicked source", () => {
    const onOpen = vi.fn();
    render(<SourcesPanel sources={SOURCES} onOpen={onOpen} />);
    fireEvent.click(screen.getByText(sourceLabel(SOURCES[0]!)));
    expect(onOpen).toHaveBeenCalledWith(SOURCES[0]);
  });

  it("renders nothing when there are no sources", () => {
    const { container } = render(<SourcesPanel sources={[]} onOpen={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });
});
