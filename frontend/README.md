# Patent Intelligence: web app

The web interface of the Agentic RAG patent intelligence system. It is a Next.js 16
(App Router, React 19) app styled with Tailwind CSS 4 and animated with framer-motion.
The browser only talks to this Next.js server; requests to `/api/*` are forwarded to
the FastAPI backend (see `next.config.ts`), so the backend address never reaches the
browser and no CORS setup is needed.

## Pages

| Route | What it does |
|---|---|
| `/search` (home) | Ask a question; the answer cites numbered sources, and follow-ups continue the same thread |
| `/chat` | Conversations with attached documents or patents, with memory for follow-ups |
| `/documents`, `/patents`, `/compare` | Library: upload documents, find and import patents, compare 2–4 sources |
| `/invention` | Invention analysis: feature-by-feature comparison against the closest documents |
| `/watches` | Patent watch: follow a topic and see newly published patents |
| `/evaluation`, `/ask`, `/settings` | Research tools: experiment results, the full-option research console, system status |

If the backend cannot be reached, `/search` answers from the backend's built-in
**synthetic** demo patents (country code "XX") and says so on screen.

## Run it

From the project root (the backend must be running too, see the main README):

```bash
make web-setup   # install dependencies
make web         # http://localhost:3000, backend expected at http://localhost:8000
make demo        # or: API on :8100 + this UI on :3000 with the real local models
```

Or directly:

```bash
npm install
BACKEND_URL=http://localhost:8000 npm run dev
```

`BACKEND_URL` is server-side only. It is read when the dev server starts and baked
into a production build, so set it for `npm run build` as well.

## Checks

```bash
npm run typecheck   # TypeScript
npm run lint        # ESLint
npm test            # unit tests (Vitest)
npm run gen:api     # regenerate src/types/api.d.ts after backend API changes
```

## Layout

```
src/app/            routes (one folder per page); template.tsx animates page entry
src/components/     UI by feature (search, chat, ask, invention, evaluation, …) + ui.tsx
src/lib/            API clients, citation parsing, formatting (with unit tests)
src/types/api.d.ts  types generated from the backend's OpenAPI schema
```

Design tokens (colours, fonts, the grid-paper background) and the shared animation
classes live in `src/app/globals.css`. Motion respects `prefers-reduced-motion`.

Technical information only: the app reports technical similarity and evidence from
sources. It is not legal advice and does not assess patent validity or infringement.
