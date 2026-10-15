# End-to-end review

Comprehensive end-to-end validation of the Kanban Studio MVP, run on 2026-10-15.

## Summary

All layers pass. No defects were found. Backend, frontend, production build, browser
tests, and a live smoke test of the running server all succeed, including the live Groq
AI path. The findings below are observations and known limitations, not bugs.

## Environment

- Windows 10 Pro, PowerShell start/stop scripts.
- Python 3.13.14, pytest 9.1.1, managed with `uv` (73 packages, lock in sync).
- Next.js 16.1.6 (Turbopack), React 19.2.3, Vitest 3.2.4, Playwright (Chromium).

## Automated suites

| Check | Command | Result |
| --- | --- | --- |
| Backend tests | `uv run --project backend pytest` | 47 passed, 1 skipped (10.0s) |
| Frontend lint | `npm run lint` (eslint) | Clean, no warnings |
| Frontend unit/component | `npm run test:unit` (vitest) | 15 passed, 2 files (8.8s) |
| Production build | `npm run build` (next build) | Success; static export of `/`, `/login`, `/_not-found` |
| Browser e2e | `npm run test:e2e` (playwright) | 11 passed (48.9s) |
| Dependency lock | `uv lock --project backend --check` | In sync |
| Whitespace | `git diff --check` | No errors |

Coverage breakdown:

- Backend (48 collected): health and static serving, exported-route fallback, login
  with valid/invalid credentials, session create/read/logout, CORS for the dev origin,
  database creation and seeding without overwrite, persistence across a new app
  instance, board read with ownership enforcement, column rename keeping fixed IDs,
  card create/update/move/delete, cross-user access rejection, and the AI chat endpoint
  (provider mocked) covering apply, no-op, idempotent move, single-field edit, and
  rejection of invalid model output without partial updates.
- Frontend unit: `moveCard` ordering helpers (3) and `KanbanBoard` component behavior
  (12) covering load, save, error and retry states, card-details validation, and chat
  send/reply/error/pending states with board updates.
- Browser e2e: logged-out redirect, invalid-credential error, reload persistence,
  logout, board load, AI reply applying a returned board, card add, card edit persisted
  across reload, column rename persisted across reload, failed-save retry, and card move
  between columns.

The one skipped backend test is `test_ai_live.py::test_groq_connectivity_answers_arithmetic`,
which is opt-in by design (`RUN_GROQ_CONNECTIVITY=1` plus a key).

## Live smoke test (running server)

Started with `scripts/start.ps1` (health check passed, served at `127.0.0.1:8000`),
exercised with real HTTP requests, then stopped with `scripts/stop.ps1` (port released).

| Scenario | Expected | Actual |
| --- | --- | --- |
| `GET /api/health` (public) | 200 `{"status":"ok"}` | matched |
| `GET /api/board` without session | 401 | matched |
| `POST /api/auth/login` wrong password | 401, no cookie | matched |
| `POST /api/auth/login` valid | 200, sets HttpOnly session cookie | matched |
| `GET /api/auth/session` with cookie | `{"username":"user"}` | matched |
| `GET /api/board` with cookie | 5 columns, 8 cards | matched |
| `GET /` with cookie | 200 (static index) | matched |
| `GET /` without cookie | 303 redirect to `/login/` | matched |
| Create then edit then move then delete a card | each 200, card count returns to 8 | matched (net-zero, no residue) |
| Create card in unknown column | 404 | matched |
| Create card with blank details | 422 (validation) | matched |
| `POST /api/auth/logout` | 204, cookie cleared | matched |
| `GET /api/board` after logout | 401 | matched |
| `POST /api/ai/chat` (live Groq) | 200 with grounded reply | matched; reply referenced a real card, `changed:false`, board unchanged |

## Observations (not defects)

1. **Persistent database reflects prior edits.** The live board shows columns
   `Backlog, Exploration, In Progress, Review, Finished` rather than the seeded
   `Backlog, Discovery, In Progress, Review, Done`, and some cards sit in non-seed
   positions. This is correct persistence in `.data/kanban.sqlite3` from earlier use,
   not a regression. A fresh database (no `.data/`) seeds the documented defaults, as
   confirmed by the backend seeding test.
2. **A live Groq call was made during this review.** Verifying the AI path end-to-end
   sent the board and question to the external provider once. The response was coherent,
   grounded in the actual board, and proposed no changes (`changed:false`). The default
   test suites never call the provider.
3. **AI graceful degradation not separately re-verified live.** Because a valid
   `GROQ_API_KEY` is present, the no-key 503 path was not reproduced on the running
   server; it is covered by backend tests with the provider mocked.

## Not exercised / out of scope

- macOS and Linux `start.sh` / `stop.sh` runtime behavior (this run was on Windows;
  Unix scripts pass `bash -n` syntax checks only).
- Session expiry after the 8-hour TTL (logic is unit-level; not time-simulated).
- Concurrent or multi-user access (MVP is hardcoded to one account; the schema supports
  multiple users but it is not an MVP scenario).
- `npm audit` advisories were reported during an earlier acceptance run and were not
  re-triaged here; dependency upgrades are out of scope for this review.

## Conclusion

The codebase is in a healthy, releasable state for the MVP. Every automated suite and
the live application path pass, writes persist and are correctly rejected when invalid,
authentication gates the board and AI routes, and the AI integration works against the
real provider while never partially mutating the board.
