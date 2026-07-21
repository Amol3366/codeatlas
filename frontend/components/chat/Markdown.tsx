"use client";

import type { Source } from "@/lib/types";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

const SOURCE_LINK_RE = /^#source-(\d+)$/;

/** Markdown with GFM tables/lists, highlighted code, and clickable source links. */
export function Markdown({
  children,
  sources = [],
  onOpenSource,
}: {
  children: string;
  sources?: Source[];
  onOpenSource?: (source: Source) => void;
}) {
  const components: Components = {
    a({ href, children: linkChildren }) {
      const match = href?.match(SOURCE_LINK_RE);
      if (match) {
        const sourceIndex = Number(match[1]) - 1;
        const source = sources[sourceIndex];
        if (source && onOpenSource) {
          return (
            <button
              type="button"
              onClick={() => onOpenSource(source)}
              className="font-medium text-accent underline underline-offset-2 hover:text-accent-strong"
            >
              {linkChildren}
            </button>
          );
        }
      }

      return (
        <a
          href={href}
          target={href?.startsWith("http") ? "_blank" : undefined}
          rel={href?.startsWith("http") ? "noreferrer" : undefined}
        >
          {linkChildren}
        </a>
      );
    },
  };

  return (
    <div className="prose-chat text-[15px]">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={components}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
