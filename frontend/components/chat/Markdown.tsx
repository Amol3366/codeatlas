"use client";

import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

/** Markdown with GFM tables/lists and syntax-highlighted code blocks (§7a). */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="prose-chat text-[15px]">
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
