
# Frontend Notes

## Current UI Direction

The frontend uses a neutral, ChatGPT-style layout:

- The product title in the sidebar should read `CodeAtlas`.
- Left sidebar for chat history.
- Each saved chat row should have a small delete control so users can remove
  old local chat history.
- Main conversation area with user messages aligned right.
- Assistant messages appear as plain conversation text, not heavy cards.
- Composer stays at the bottom of the chat.
- The index-management page is available from the sidebar.
- The left bottom area should show this one-line objective summary:
  `Explore codebases and related docs with grounded code-source answers.`

The UI intentionally does not copy OpenAI branding or logos. It uses a similar
clean light color scheme: white main surface, soft gray sidebar, dark text, and
green source links.

## OpenAI-Inspired Color Scheme

OpenAI's official ChatGPT help documentation describes the product UI as using
theme choices such as System, Dark, and Light, plus a configurable accent color.
It does not publish a complete official web hex-token palette for reuse, so the
colors below are project design targets inspired by the current ChatGPT/OpenAI
interface rather than official brand tokens.

Source note: official ChatGPT visual settings are documented at
`https://help.openai.com/en/articles/11958281`.

Use this light theme first:

```css
:root {
  --color-paper: #ffffff;
  --color-sidebar: #f9f9f9;
  --color-panel: #ffffff;
  --color-hover: #ececec;
  --color-active: #e8e8e8;
  --color-user: #f4f4f4;
  --color-ink: #171717;
  --color-ink-soft: #676767;
  --color-line: #e5e5e5;
  --color-line-strong: #c7c7c7;
  --color-accent: #10a37f;
  --color-accent-strong: #0a7a5e;
  --color-danger: #ef4146;
  --color-highlight: #fff4ce;
}
```

Color roles:

- `#ffffff`: main page background and conversation surface.
- `#f9f9f9`: left sidebar background.
- `#f4f4f4`: user message bubble background.
- `#171717`: primary text and primary button background.
- `#676767`: secondary text, metadata, and quiet sidebar labels.
- `#e5e5e5`: borders and dividers.
- `#10a37f`: source hyperlinks and restrained accent actions.
- `#0a7a5e`: hover/active state for source links.
- `#ef4146`: errors and destructive states.
- `#fff4ce`: cited-line highlight in source preview.

Implementation notes for later:

- Keep the interface near-monochrome; the green accent should be sparse.
- Do not use OpenAI logos, exact branding, or proprietary marks.
- Prefer whitespace, simple borders, and quiet hover states over heavy cards.
- Keep the left-bottom objective summary small, one line, and muted.
- For coding questions, answers should emphasize source code first and use
  documents as supporting context.

## Chat History

Chat history is stored in browser `localStorage` under:

```text
codeatlas.chat.sessions.v1
```

This means:

- Refreshing the page keeps previous chats.
- History is local to the browser and machine.
- Clearing browser site data removes the saved chats.
- Backend restarts do not remove chat history.

## Source Links In Answers

The backend prompt asks the model to cite sources with short markdown links:

```markdown
[here](#source-1)
```

The frontend intercepts links matching `#source-N` and opens the matching source
preview drawer. `N` is one-based and maps to the structured `sources` array sent
by the backend in the final SSE event.

If the model forgets to include a source link but the backend returns sources,
the frontend appends a fallback:

```markdown
Source: [here](#source-1).
```

This keeps raw file paths out of the answer body while preserving clickable
grounding.

## Development Commands

Install dependencies:

```bash
pnpm install --frozen-lockfile
```

Run the dev server:

```bash
pnpm dev
```

Run tests:

```bash
pnpm test
```

On Windows PowerShell, use `pnpm.cmd` if script execution policy blocks `pnpm`:

```powershell
pnpm.cmd dev
pnpm.cmd test
```

## Important Backend Contract

`POST /chat` streams SSE events:

- `token`: one piece of assistant text.
- `final`: full answer plus structured sources.
- `error`: backend or model error message.

The source preview depends on:

```text
GET /files/content?path=<relative-path>
```

All source paths must stay relative to the indexed repository root.
