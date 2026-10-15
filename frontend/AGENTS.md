# Frontend guide

## Current structure

- `src/app/` contains the Next.js App Router entry page, root layout and global styles. The home page renders the Kanban board.
- `src/components/` contains the columns, cards, drag preview, new-card form, sign-in form, and board UI. The home page checks backend session state before mounting `KanbanBoard`; the board loads and saves its state through the authenticated FastAPI API.
- `src/lib/kanban.ts` defines the board, column and card types, initial demo data, card movement, and ID creation.
- `src/test/` configures Vitest and Testing Library.
- `tests/` contains Playwright browser tests. `playwright.config.ts` builds the static site and serves it through FastAPI for these tests.
- `public/` contains static image and SVG assets.

The app displays a five-column Kanban board with column renaming, card creation, editing and removal, and drag-and-drop movement. Board reads and changes use the authenticated backend API, with updates reflected only after the backend accepts them. The production build is a static export served by FastAPI. Sign-in and sign-out also use the backend session API.

For interactive frontend development, run the backend on port 8000 and start Next.js with `npm run dev`; development API calls go directly to FastAPI with credentialed local CORS. The production build has no Next.js runtime and is served directly by FastAPI.

## Development and checks

Run commands from the `frontend/` directory:

```bash
npm ci
npm run dev
```

Available checks:

```bash
npm run test:unit
npm run test:e2e
npm run test:all
npm run lint
npm run build
```

Unit and component tests use Vitest, jsdom, and Testing Library; they are colocated with source as `*.test.ts` or `*.test.tsx`. Browser tests use Playwright from `tests/`. The TypeScript configuration is strict and maps `@/*` to `src/*`.
