# Kanban Studio -- Comprehensive E2E Review

**Date:** 2026-10-16 (updated after UI polish + code simplification)
**Branch:** main (commit 6680e49)

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

## UI/UX Observations

### Fixed in this iteration (commit 6680e49)

1. ~~Card titles break mid-word~~ -- **Fixed.** Columns are now 260px fixed-width with
   a horizontal scroll container. Titles like "Prototype analytics view" display
   without mid-word breaks.
2. ~~Checklist input placeholder truncated~~ -- **Fixed.** "Add checklist item" is now
   fully visible with the wider column width.
3. ~~No horizontal scroll on small screens~~ -- **Fixed.** The board now uses a flex
   row with `overflow-x-auto`; columns scroll horizontally rather than compressing.

### Remaining (minor, not blockers)

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

## Changes Since First Review (commits 8593e32, 6680e49)

### Code simplification (8593e32)

- Sorted stdlib imports in `database.py` (bare imports first).
- Replaced `1 if done else 0` with `int(done)` in `set_checklist_item`.
- Extracted `cardPath(cardId)` helper in `KanbanBoard.tsx` (removes 6 duplicated URL
  constructions).
- Aligned `test_checklist.py` helpers to match `test_main.py` convention (separate
  `sign_in` and `board_id` functions).

### UI polish (6680e49)

- Replaced `grid lg:grid-cols-5` column layout with `flex overflow-x-auto` and 260px
  fixed-width columns.
- Removed `break-words` from card titles and details (no longer needed at 260px width).
- Removed `break-words` from checklist item text.

### Post-change verification

All 121 automated tests pass after both changes:

| Suite | Result |
|---|---|
| Backend | 83 passed, 1 skipped |
| Frontend unit | 24 passed |
| Playwright E2E | 14 passed |

Manual browser walkthrough confirmed: card titles wrap naturally, checklist placeholder
visible, horizontal scroll reaches the 5th column, drag-and-drop still works.

## Verdict

The application is **production-ready for its MVP scope**. All 121 automated tests pass,
all manual edge cases behave correctly, the codebase has been simplified, and the UI
layout issues have been resolved. The two remaining UI observations (delete confirmation,
loading indicators) are minor polish items, not blockers.
