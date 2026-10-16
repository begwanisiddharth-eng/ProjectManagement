# End-to-end review

Final comprehensive end-to-end validation of the Kanban Studio MVP, run on 2026-10-15,
after the backend route refactor that split `main.py` into focused modules
(`schemas.py`, `dependencies.py`, `auth_routes.py`, `board_routes.py`, `ai_routes.py`).

## Summary

All layers pass. No defects were found. Backend, frontend, production build, browser
tests, and a live smoke test of the running server all succeed, including the live Groq
AI path through the refactored `ai_routes.py`. The findings below are observations and
known limitations, not bugs.

## Environment

- Windows 10 Pro, PowerShell start/stop scripts.
- Python 3.13.14, pytest 9.1.1, managed with `uv` (73 packages, lock in sync).
- Next.js 16.1.6 (Turbopack), React 19.2.3, Vitest 3.2.4, Playwright (Chromium).

## Automated suites

| Check | Command | Result |
| --- | --- | --- |
| Backend tests | `uv run --project backend pytest` | 47 passed, 1 skipped (11.2s) |
| Frontend lint | `npm run lint` (eslint) | Clean, no warnings |
| Frontend unit/component | `npm run test:unit` (vitest) | 15 passed, 2 files (9.6s) |
| Production build | `npm run build` (next build) | Success; static export of `/`, `/login`, `/_not-found` |
| Browser e2e | `npm run test:e2e` (playwright) | 11 passed (~1 min) |
| Dependency lock | `uv lock --project backend --check` | In sync |
| Whitespace | `git diff --check` | No errors (only CRLF conversion notices) |

The one skipped backend test is the opt-in live-Groq arithmetic check
(`test_ai_live.py`), which runs only with `RUN_GROQ_CONNECTIVITY=1` and a key.

### Refactor-specific confirmation

The route split moved every handler out of `main.py` into `APIRouter` modules that reach
the database and session store through `Depends` providers backed by `app.state`. The
full backend suite (which exercises every endpoint) and the browser suite both pass
unchanged, and the route table resolves at identical paths. `main.py` is now 63 lines of
app assembly; behavior and the public API are unchanged.

## Live smoke test (running server)

Started with `scripts/start.ps1` (health check passed, served at `127.0.0.1:8000`),
exercised with real HTTP requests, then stopped with `scripts/stop.ps1` (port released).

| # | Scenario | Expected | Actual |
| --- | --- | --- | --- |
| 1 | `GET /api/health` (public) | 200 `{"status":"ok"}` | matched |
| 2 | `GET /api/board` without session | 401 | matched |
| 3 | `POST /api/auth/login` wrong password | 401 | matched |
| 4 | `POST /api/auth/login` valid | 200, sets HttpOnly cookie | matched |
| 5 | `GET /api/auth/session` with cookie | `{"username":"user"}` | matched |
| 6 | `GET /api/board` with cookie | 5 columns, 8 cards | matched |
| 7 | `GET /` with cookie | 200 (static index) | matched |
| 8 | `GET /` without cookie | 303 redirect to `/login/` | matched |
| 9-12 | Create -> edit -> move -> delete a card | each 200 | matched |
| 13 | Card count after the net-zero cycle | back to 8, test card gone | matched |
| 14 | Create card in unknown column | 404 | matched |
| 15 | Create card with blank details | 422 (validation) | matched |
| 16 | `POST /api/ai/chat` (live Groq) | 200 with grounded reply | matched; reply described the real columns, `changed:false`, board unchanged |
| 17 | `POST /api/auth/logout` | 204, cookie cleared | matched |
| 18 | `GET /api/board` after logout | 401 | matched |

The live AI reply was: "Exploration, In Progress, and Review each have the most cards,
with two cards each." It proposed no changes and left the board untouched, confirming the
refactored AI route applies the same ownership and validation path as before.

## Observations (not defects)

1. **Persistent database reflects prior edits.** The live board shows columns
   `Backlog, Exploration, In Progress, Review, Finished` rather than the seeded
   `Backlog, Discovery, In Progress, Review, Done`. This is correct persistence in
   `.data/kanban.sqlite3` from earlier use, not a regression; a fresh database seeds the
   documented defaults (covered by the backend seeding test).
2. **A live Groq call was made during this review.** Verifying the AI path end-to-end
   through the refactored route sent the board and question to the external provider
   once. The response was coherent, grounded in the actual board, and proposed no changes
   (`changed:false`). The default test suites never call the provider.
3. **First smoke-test attempt had a shell-quoting error (resolved).** An initial inline
   script mangled JSON request bodies and produced spurious 422/405 codes; re-running the
   checks from a clean script file produced the correct results recorded above. This was
   a test-harness issue, not an application defect.

## Not exercised / out of scope

- macOS and Linux `start.sh` / `stop.sh` runtime behavior (this run was on Windows;
  Unix scripts pass `bash -n` syntax checks only).
- Session expiry after the 8-hour TTL (logic is unit-level; not time-simulated).
- Concurrent or multi-user access (MVP is hardcoded to one account; the schema supports
  multiple users but it is not an MVP scenario).
- `npm audit` advisories reported in an earlier acceptance run were not re-triaged here.

## Conclusion

The codebase remains in a healthy, releasable state for the MVP after the route refactor.
Every automated suite and the live application path pass, writes persist and are correctly
rejected when invalid, authentication gates the board and AI routes, and the AI
integration works against the real provider while never partially mutating the board.
