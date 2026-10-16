# The Project Management MVP web app

## Business Requirements

This project is building a Project Management App. Key features:
- A user can register an account and sign in (passwords are hashed)
- When signed in, the user sees their Kanban boards and can create, rename, switch, and delete boards
- Each Kanban board has five fixed columns that can be renamed
- Cards can be moved with drag and drop, edited, and carry a priority and optional due date
- Each card has a checklist of items that can be added, checked off, and removed
- There is an AI chat feature in a sidebar; the AI is able to create / edit / move one or more cards

## Limitations

The default MVP account is hardcoded to 'user' / 'password' and seeded on first startup; additional users register through the app. Passwords are hashed with stdlib PBKDF2 and are not stored in plaintext.

A user may have multiple boards; the database enforces per-user ownership. A user cannot delete their only board.

This runs locally.

## Technical Decisions

- NextJS frontend
- Python FastAPI backend, including serving the static NextJS site at /
- Use "uv" as the package manager for Python
- Use Groq for AI calls via the `litellm` Python library. A `GROQ_API_KEY` is in `.env` in the project root
- Use `groq/openai/gpt-oss-120b` as the model
- Use SQLLite local database for the database, creating a new db if it doesn't exist
- Start and Stop server scripts for Mac, PC, Linux in scripts/

## Starting Point

A working MVP of the frontend has been built and is already in frontend. It is a pure frontend-only demo and has not yet been integrated with the backend.

## Color Scheme

- Accent Yellow: `#ecad0a` - accent lines, highlights
- Blue Primary: `#209dd7` - links, key sections
- Purple Secondary: `#753991` - submit buttons, important actions
- Dark Navy: `#032147` - main headings
- Gray Text: `#888888` - supporting text, labels

## Coding standards

1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal. IMPORTANT: no emojis ever
4. When hitting issues, always identify root cause before trying a fix. Do not guess. Prove with evidence, then fix the root cause.

## Working documentation

All documents for planning and executing this project will be in the docs/ directory.
Please review the docs/PLAN.md document before proceeding.