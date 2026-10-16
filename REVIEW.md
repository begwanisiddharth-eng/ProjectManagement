# Kanban Studio -- Comprehensive E2E Review

**Date:** 2026-10-16
**Branch:** main (commit 8236ec9)

## Automated Test Results

| Suite | Result |
|---|---|
| Backend (`uv run --project backend pytest`) | 83 passed, 1 skipped |
| Frontend unit (`npm run test:unit`) | 24 passed (3 files) |
| Playwright E2E (`npm run test:e2e`) | 14 passed |

All three suites green. No flaky tests observed. The one skipped test is the opt-in
live-Groq connectivity check (`test_ai_live.py`), which runs only with
`RUN_GROQ_CONNECTIVITY=1` and a valid `GROQ_API_KEY`.

## Manual API Edge-Case Testing

| Scenario | Expected | Actual |
|---|---|---|
| Empty card title | 422 | 422 |
| Whitespace-only card title | 422 (strip then reject) | 422 |
| Missing required `details` field | 422 | 422 |
| Invalid priority value (`"critical"`) | 422 | 422 |
| Invalid due-date format (`"not-a-date"`) | 422 | 422 |
| Unauthenticated GET `/api/boards` | 401 | 401 |
| Forged session cookie | 401 | 401 |
| Nonexistent board ID | 404 | 404 |
| Nonexistent column ID (card create) | 404 | 404 |
| Delete the only board | 409 | 409 |
| XSS in card title (`<script>`) | Stored; React escapes on render | Correct |

No bugs found in API validation or authorization.

## Manual Browser Walkthrough

Tested with Chrome via browser automation against `http://127.0.0.1:8000/`:

- **Login flow:** Redirects unauthenticated users to `/login/`. Sign in with default
  credentials works; lands on the board with all 5 columns and 8 seeded cards.
- **Board loads correctly:** Board bar (tabs, new board, rename, delete), card count
  badge, sign-out button, AI chat panel all render.
- **No console errors** on page load or navigation.
- **Register page** accessible from login link; form validates username length (3+),
  password length (8+), and password confirmation match.

## Bugs Found

**None.** The application is functionally correct across all tested paths.

## UI/UX Observations (improvement candidates for next iteration)

1. **Card titles break mid-word** on the default viewport. The 5-column grid plus chat
   sidebar leaves each column ~170px wide, causing `break-words` to split normal words
   like "Prototype" into "Prototy pe". The columns need a minimum width or the layout
   should scroll horizontally.
2. **Checklist input placeholder truncated.** "Add checklist item" renders as "Add chec"
   in narrow columns.
3. **No horizontal scroll on small screens.** The 5-column layout compresses rather than
   scrolling below ~1400px viewport width.
4. **Board delete has no confirmation dialog.** The "Delete" button on the board bar
   fires the delete immediately.
5. **No per-operation loading indicator.** Saving/deleting only disables controls (opacity
   change); no spinner or "Saving..." text.

## Code Quality Assessment

### Strengths

- **Clean architecture.** Routes, schemas, database, and AI logic in separate modules.
  The `create_app` factory makes each instance independently testable.
- **Secure auth.** PBKDF2-SHA256 with 200K rounds, constant-time comparison
  (`hmac.compare_digest`), httpOnly + samesite=lax session cookies.
- **No SQL injection risk.** All queries use parameterized statements.
- **Proper CORS.** Only `127.0.0.1:3000` and `localhost:3000` allowed origins.
- **AI prompt injection defense.** System prompt tells the model to treat board content
  as data, not instructions.
- **Ownership enforcement.** Every board/card/checklist mutation verifies the signed-in
  user owns the board via `_owned_board_id`.
- **Cascade deletes.** Board deletion cascades to columns, cards, and checklist items via
  foreign keys.
- **Discriminated union for AI changes.** `BoardChange` uses Pydantic discriminator on
  `operation`, cleanly rejecting unknown operation types.
- **Frontend types match API.** `kanban.ts` types align with `schemas.py` response models.

### Minor Observations (acceptable for MVP)

- `LoginRequest` uses unconstrained `str` fields (unlike `RegisterRequest`'s typed
  `Username`/`Password`). Intentional: login should be permissive to give a consistent
  "invalid credentials" response rather than leaking which field failed validation.
- Session cookie lacks `secure=True` -- correct for HTTP-only development.
- Expired sessions are cleaned lazily (on access), not periodically. Fine for MVP.
- `BoardChat` uses index-based React keys, safe since messages are append-only.

## Verdict

The application is **production-ready for its MVP scope**. All 121 automated tests pass,
all manual edge cases behave correctly, and the codebase is well-structured with proper
security practices. The UI/UX observations above are polish items for the next iteration,
not blockers.
