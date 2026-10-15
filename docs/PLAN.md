# Project Management MVP plan

## Goal

Deliver a locally run project management app with a persistent Kanban board, a single MVP sign-in, and an AI chat sidebar that can make validated board changes.

## Scope and decisions

- The frontend is Next.js and the backend is FastAPI. FastAPI serves the static frontend build at `/` and exposes the API.
- Run locally. Use `uv` for Python dependencies and SQLite for local persistence; create the database when it is missing.
- Use Groq through `litellm` with `groq/openai/gpt-oss-120b`. Load `GROQ_API_KEY` from the project-root `.env`; never expose it to the browser or commit it.
- MVP sign-in uses the hardcoded username `user` and password `password`. The backend manages sign-in state with a session cookie, and API routes identify the signed-in user from that session. Keep the data model capable of supporting multiple users.
- Each user has one board. The board has a fixed set of columns whose names can be changed. Cards can be created, edited, and moved between columns.
- Keep the existing frontend demo as the starting point. Preserve its visual direction and the colors documented in the root `AGENTS.md`.
- Keep changes focused on the MVP. Use automated tests for deterministic behavior; any test requiring a live Groq call must be explicitly opt-in.

## Working rules

- Complete phases in order unless a dependency requires a documented adjustment.
- Check off a task only after its verification passes. Record any necessary deviation and its reason in the relevant documentation.
- A phase is complete only when all its tasks and success criteria are satisfied.
- Phase 1 approval and Phase 5 data-model approval are explicit user gates. Do not proceed beyond either gate until the user approves.
- Run applicable tests after each change and run the combined project checks before calling the MVP complete.

## Phase 1: Detailed plan and frontend orientation

- [x] Expand this plan into sequenced phases with test and completion criteria.
  - **Verify:** Review this plan against the stated MVP requirements and technical decisions.
  - **Complete when:** Every phase has actionable tasks, verification, and measurable completion criteria.
- [x] Inspect the existing frontend and document its structure, state flow, and test commands in `frontend/AGENTS.md`.
  - **Verify:** Confirm each documented path and command against the repository and run the listed frontend test command.
  - **Complete when:** The guide accurately describes the existing frontend without prescribing unimplemented behavior.
- [x] Present the plan and frontend guide for user review and obtain approval before implementation.
  - **Verify:** Obtain explicit user approval of the plan.
  - **Complete when:** The user approves the scope, sequencing, and technical approach; record requested plan changes before proceeding.

## Phase 2: Backend and local-run scaffolding

- [x] Set up a minimal FastAPI application in `backend/`, managed with `uv`; load the root `.env` into the backend process when present.
  - **Verify:** Run backend dependency checks and FastAPI test-client tests for the health endpoint; confirm the local scripts load `.env` only into the backend process.
  - **Complete when:** A fresh local setup can install dependencies and start the API; the health endpoint returns the documented success response.
- [x] Add a temporary Hello World page and a simple API endpoint to prove static-page and API serving.
  - **Verify:** Test both endpoints through the application and make a local HTTP request to each.
  - **Complete when:** The page and API are reachable from the running local server.
- [x] Add start and stop scripts under `scripts/` for macOS, Windows, and Linux.
  - **Verify:** Check script syntax and exercise start, health check, and stop on available platforms; document any platform that cannot be exercised in the current environment.
  - **Complete when:** Scripts use the documented local prerequisites, report startup failures, and stop only the server process they started. Windows start, health, stop, and unrelated-process refusal were exercised; Unix scripts passed syntax checks. macOS and Linux runtime execution remains unverified in this Windows environment.

## Phase 3: Static frontend served by FastAPI

- [x] Configure the Next.js frontend for a static build and update FastAPI to serve the built assets and application routes at `/`.
  - **Verify:** Run the frontend production build and test the backend's static-file and route-fallback behavior.
  - **Complete when:** The built application loads at `/`, assets load successfully, and the temporary Hello World page is replaced by the existing Kanban demo.
- [x] Preserve the existing Kanban demo behavior and add or retain focused unit, component, and browser-level coverage.
  - **Verify:** Run the frontend unit tests and Playwright tests against the served production build.
  - **Complete when:** Existing board interactions covered by the suite still work, with no reliance on a Next.js development server for production serving.

## Phase 4: Backend-managed sign-in

- [x] Add login, current-session, and logout API behavior for the hardcoded MVP credentials, with the server managing the session cookie.
  - **Verify:** Backend tests cover valid and invalid credentials, session creation, session lookup, logout, and access after logout.
  - **Complete when:** Valid login establishes a session, invalid login does not, logout invalidates the session, and session state is not held only in frontend memory.
- [x] Add a frontend sign-in screen and protect the Kanban view using the backend session state.
  - **Verify:** Browser tests cover logged-out access, successful login, failed login, page reload with an active session, and logout.
  - **Complete when:** The board is visible only after successful sign-in and remains accessible after reload while the session is valid.
- [x] Ensure protected API routes reject unauthenticated requests and the browser can send the session cookie to the local API.
  - **Verify:** Backend tests assert unauthorized responses; an integration test makes a protected request both with and without a valid session.
  - **Complete when:** Unauthenticated requests cannot access user board data and authenticated requests resolve the correct MVP user.

## Phase 5: SQLite data model proposal and approval

- [x] Design a multi-user-capable SQLite model for users, one board per user, fixed board columns, and cards; account for ownership and ordering.
  - **Verify:** Review the proposal for primary/foreign keys, uniqueness constraints, and the one-board-per-user rule.
  - **Complete when:** The proposal expresses the MVP requirements and does not allow a card or board to be assigned to the wrong user.
- [x] Save a machine-readable JSON representation of the proposed schema and document the persistence and initialization approach under `docs/`.
  - **Verify:** Parse the JSON and check that its entities, constraints, and initialization notes agree with one another.
  - **Complete when:** The schema artifact and documentation are consistent, explain database creation when absent, and distinguish the design artifact from the runtime SQLite database.
- [x] Obtain explicit user approval of the data model before implementing it.
  - **Verify:** Obtain explicit user sign-off.
  - **Complete when:** The user approves the schema and persistence approach, or requested revisions are incorporated and re-approved.

## Phase 6: Persistent backend board API

- [x] Initialize the SQLite database and schema automatically on application startup or first use, without overwriting existing data.
  - **Verify:** Backend tests cover creation in a fresh temporary database and reuse of an existing database containing data.
  - **Complete when:** A missing database is initialized successfully and existing board data survives application restart.
- [x] Implement authenticated API operations to read a user's board and create, edit, and move cards; support renaming the fixed columns.
  - **Verify:** Backend tests cover normal operations, invalid input, missing records, unauthorized access, and attempts to access another user's records.
  - **Complete when:** All board operations persist to SQLite, enforce ownership and fixed-column rules, and return documented responses and errors.
- [x] Add backend test fixtures that use isolated temporary databases and do not depend on a developer's local database.
  - **Verify:** Run the backend test suite repeatedly and in an empty checkout environment.
  - **Complete when:** Tests are deterministic and leave no project data behind.

## Phase 7: Frontend and backend integration

- [x] Replace frontend-only board state with the authenticated backend API while retaining the existing board interactions.
  - **Verify:** Frontend tests mock API responses for loading, successful updates, and API errors; integration tests use the real backend and a temporary database.
  - **Complete when:** Board state loads from and saves to the backend, including card edits, moves, and column renames.
- [x] Handle loading, empty, and failed API states without presenting failed writes as successful.
  - **Verify:** Tests assert visible error feedback and that the UI does not update as if a rejected change were persisted.
  - **Complete when:** Users can distinguish saved changes from failed requests and can retry through the normal UI.
- [x] Verify persistence across reload and server restart.
  - **Verify:** An integration test writes a board change, creates a new client/session as appropriate, and reads it back from the same database.
  - **Complete when:** The stored board is unchanged after reload and backend restart.

## Phase 8: Groq connectivity

- [x] Add a small backend AI client using `litellm`, the configured Groq model, and the server-side `GROQ_API_KEY`.
  - **Verify:** Unit tests mock the AI provider and assert model selection, request construction, and error propagation without requiring credentials.
  - **Complete when:** Application code can call the provider through one backend boundary and the key is never included in frontend assets or responses.
- [x] Add an opt-in connectivity check that asks the model a simple arithmetic question.
  - **Verify:** Run the live check only when a valid key and network access are available; otherwise confirm the default test suite skips it cleanly.
  - **Complete when:** The opt-in check receives a valid response from Groq when explicitly enabled; the default suite skips it. Missing keys and provider failures are reported clearly, not treated as success. The live request was not run in this implementation.

## Phase 9: Structured AI board assistance

- [x] Define and validate a structured AI response containing a user-facing reply and an optional set of board changes.
  - **Verify:** Tests cover valid responses, missing or malformed fields, invalid column references, and invalid card operations.
  - **Complete when:** Only responses matching the defined structure proceed to application logic.
- [x] Send the authenticated user's current board, question, and relevant conversation history to the model from the backend.
  - **Verify:** Mocked tests assert the correct board and conversation context are sent and that one user's board is never included in another user's request.
  - **Complete when:** The model receives the intended context without exposing credentials or unrelated user data.
- [x] Apply accepted AI changes through the same ownership and board rules as normal API updates; leave the board unchanged when changes are absent or invalid.
  - **Verify:** Backend tests cover create, edit, move, no-op, and rejected updates, and confirm persisted results.
  - **Complete when:** The response clearly reports the outcome and invalid model output cannot corrupt or partially update the board.
- [x] Keep all deterministic tests provider-mocked and the live provider test opt-in.
  - **Verify:** Run the normal backend suite without `GROQ_API_KEY`.
  - **Complete when:** The suite passes offline without making network calls.

## Phase 10: AI chat sidebar and end-to-end behavior

- [ ] Add a sidebar chat interface for submitting questions and displaying conversation replies.
  - **Verify:** Component and browser tests cover sending a message, displaying replies, empty input, loading state, and API errors.
  - **Complete when:** The signed-in user can chat with the backend and receives clear feedback while a request is pending or has failed.
- [ ] Reflect accepted AI board changes in the board UI after the chat response.
  - **Verify:** Integration/browser tests request a mocked or controlled board change and assert that the updated card and column state is visible without a full page reload.
  - **Complete when:** The UI and persisted board agree after AI creates, edits, or moves cards.
- [ ] Verify authentication, chat, board updates, and persistence together.
  - **Verify:** Run the full frontend and backend suites plus an end-to-end flow against the locally served production build and a temporary database.
  - **Complete when:** A user can sign in, modify the board directly and through chat, reload the app, and see persisted changes; logout removes access.

## Final acceptance

- [ ] Run documented setup and start/stop procedures on supported platforms where available; report any platform not exercised.
  - **Verify:** Follow the project setup instructions from a clean local environment.
  - **Complete when:** The app starts and stops using the provided scripts and serves the static frontend and API locally.
- [ ] Run all backend tests, frontend unit tests, browser tests, and production build checks.
  - **Verify:** Record the commands and outcomes in the completion summary; run live Groq checks only when explicitly configured.
  - **Complete when:** Required offline checks pass, known limitations are disclosed, and no credentials or local database artifacts are committed.
