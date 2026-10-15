# Kanban Studio

## Run

```bash
npm ci
npm run build
```

Start the combined app from the repository root with `scripts/start.ps1` on Windows or `scripts/start.sh` on macOS and Linux. For frontend development, start FastAPI on port 8000 with `uv run --project backend uvicorn backend.main:app --host 127.0.0.1 --port 8000`, then run `npm run dev`. The development frontend calls the local API directly; the backend allows credentialed requests only from the local frontend origins.

## Production

`npm run build` creates a static site in `out/`. The FastAPI backend serves that build from `/`; use the repository's start scripts to run the combined app.

## Tests

```bash
npm run test:unit
npm run test:e2e
```

The Playwright suite builds the static site and runs it through the FastAPI server.
