# Frontend Stack

The frontend is a Next.js application under `frontend/`. It provides the
CodeAtlas chat experience, local chat history, source-link handling, source
preview, and index-management UI.

## Node 22

Node 22 is the pinned JavaScript runtime. It is declared in `.nvmrc` and
`frontend/package.json`.

Why we use it:

- It gives the frontend a single runtime target.
- It supports the modern JavaScript and tooling expected by Next.js 16.
- Pinning reduces "works on my machine" dependency issues.

Need it solves:

- The frontend build, test, and dev server all need a predictable Node runtime.

## pnpm

pnpm is the frontend package manager, pinned through
`packageManager: "pnpm@10.12.4"` in `frontend/package.json`.

Why we use it:

- It installs dependencies efficiently.
- It uses a lockfile for reproducible installs.
- It avoids accidental package-manager drift.

Need it solves:

- The frontend has its own JavaScript dependency graph and needs deterministic
  installation separate from the Python workspace.

## Next.js

Next.js is the React application framework used by the frontend.

Why we use it:

- It provides routing through the `app/` directory.
- It gives a standard structure for pages, layout, metadata, and builds.
- It works well with React, TypeScript, and Tailwind.

Need it solves:

- CodeAtlas needs a maintainable browser app with multiple views, including chat
  and index management.

## React

React powers the interactive UI components such as `ChatView`, `Composer`,
`MessageBubble`, `SourcesPanel`, `SourcePreview`, and `ManageView`.

Why we use it:

- Chat state, streaming responses, local history, source drawer state, and form
  actions map naturally to component state.
- Components keep the UI split into focused pieces.

Need it solves:

- The frontend needs responsive client-side interactions while the backend
  streams answer tokens.

## TypeScript

TypeScript is used across frontend code.

Why we use it:

- It gives compile-time checks for API payloads, chat events, source objects,
  and component props.
- It reduces accidental mismatches between frontend code and backend contracts.

Need it solves:

- The frontend consumes structured backend responses. Types make those response
  shapes explicit and easier to maintain.

## Tailwind CSS 4

Tailwind CSS is used through `@import "tailwindcss"` and theme tokens in
`frontend/app/globals.css`.

Why we use it:

- It supports fast, consistent UI styling without large custom CSS files.
- The project defines named theme colors such as `paper`, `sidebar`, `ink`,
  `line`, `accent`, and `danger`.
- It keeps layout and spacing close to the components that use them.

Need it solves:

- CodeAtlas needs a clean, readable chat interface with source previews and
  management controls.

## PostCSS

PostCSS is part of the frontend CSS toolchain.

Why we use it:

- Tailwind CSS integrates through the PostCSS pipeline.
- It keeps CSS processing aligned with the Next.js build.

Need it solves:

- The frontend needs a build step that can process Tailwind directives and theme
  tokens.

## react-markdown

`react-markdown` renders assistant responses as markdown.

Why we use it:

- LLM answers commonly contain paragraphs, lists, links, tables, and code.
- Rendering markdown produces a better reading experience than plain text.

Need it solves:

- The backend streams answer text that may include citations and formatted code
  explanations.

## remark-gfm

`remark-gfm` adds GitHub Flavored Markdown support.

Why we use it:

- It supports useful markdown features such as tables and task-list-like syntax.
- Codebase answers often benefit from richer technical formatting.

Need it solves:

- The UI should render developer-oriented answer formats cleanly.

## rehype-highlight and highlight.js

`rehype-highlight` and `highlight.js` provide syntax highlighting for code
blocks in assistant messages.

Why we use them:

- Code answers are easier to scan when syntax is highlighted.
- `highlight.js` has broad language support.

Need it solves:

- The app is centered on codebase understanding, so code readability is a core
  frontend requirement.

## Server-Sent Events

The frontend parses backend SSE frames in `frontend/lib/sse.ts`.

Why we use it:

- SSE is a simple fit for one-way token streaming from backend to browser.
- It avoids waiting for the full answer before showing content.
- It works over plain HTTP responses.

Need it solves:

- Chat answers should feel responsive while retrieval and model generation are
  happening.

## Browser localStorage

The frontend stores chat sessions in browser `localStorage` under
`codeatlas.chat.sessions.v1`.

Why we use it:

- Local history survives refreshes.
- It does not require a user account, database, or backend persistence.
- It matches the local-first scope of the project.

Need it solves:

- Users can keep recent conversations without adding authentication or server
  storage complexity.

## Frontend Quality Tools

The frontend uses:

- ESLint with `eslint-config-next` for linting.
- TypeScript compiler checks through `tsc --noEmit`.
- Prettier for formatting.
- Vitest for unit tests.
- Testing Library and jsdom for component tests.
- Vite React plugin in the Vitest setup.

Why we use them:

- UI behavior such as streaming, source links, and source panels can regress.
- Type checks catch API-shape and prop mistakes.
- Formatting and linting keep the project readable.
