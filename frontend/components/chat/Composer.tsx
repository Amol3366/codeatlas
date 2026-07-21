"use client";

import { useState } from "react";

/** Question input: Enter sends, Shift+Enter inserts a newline. */
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
      className="flex items-end gap-2 rounded-3xl border border-line bg-panel px-3 py-2 shadow-[0_2px_10px_rgba(0,0,0,0.06)] focus-within:border-line-strong"
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
        placeholder="Message CodeAtlas"
        aria-label="Question"
        className="max-h-40 flex-1 resize-none bg-transparent px-2 py-2 text-[15px] outline-none placeholder:text-ink-soft/70"
      />
      <button
        type="submit"
        disabled={disabled || value.trim() === ""}
        className="h-9 shrink-0 rounded-full bg-ink px-4 text-sm font-semibold text-panel transition-opacity hover:opacity-90 disabled:opacity-30"
      >
        Send
      </button>
    </form>
  );
}
