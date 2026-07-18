"use client";

import { useState } from "react";

/** Question input: Enter sends, Shift+Enter inserts a newline (§7a). */
export function Composer({
  disabled,
  onSend,
}: {
  disabled: boolean;
  onSend: (question: string) => void;
}) {
  const [value, setValue] = useState("");

  const submit = () => {
    const question = value.trim();
    if (question === "" || disabled) return;
    setValue("");
    onSend(question);
  };

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
      className="flex items-end gap-2 rounded-xl border border-line bg-panel p-2 shadow-[0_1px_3px_rgba(0,0,0,0.05)] focus-within:border-accent"
    >
      <textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
        rows={Math.min(6, Math.max(1, value.split("\n").length))}
        placeholder="Ask about your codebase… e.g. “where is auth handled?”"
        aria-label="Question"
        className="max-h-40 flex-1 resize-none bg-transparent px-2 py-1.5 text-[15px] outline-none placeholder:text-ink-soft/60"
      />
      <button
        type="submit"
        disabled={disabled || value.trim() === ""}
        className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-opacity disabled:opacity-40"
      >
        Send
      </button>
    </form>
  );
}
