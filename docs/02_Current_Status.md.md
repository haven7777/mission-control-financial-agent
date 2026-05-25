# Current Status & Task Tracker

## 🟢 Done
* Project folder structure initialized.
* Git repository initialized.
* Obsidian vault established for documentation.
* Claude Code memory protocol, strict step-by-step rules, and design system defined.
* Backend Python 3.12 virtual environment created at `backend/venv/` (using `/Library/Frameworks/Python.framework/Versions/3.12/`).
* `backend/requirements.txt` created with pinned versions: fastapi 0.136.3, uvicorn[standard] 0.48.0, langgraph 1.2.1, python-dotenv 1.2.2, pydantic 2.13.4. Verified by importing all five packages and constructing a FastAPI app.
* Repo-level `.gitignore` added (excludes `backend/venv/`, `.env`, `__pycache__/`, `.DS_Store`, editor folders).
* `backend/.env.example` added as a committed template for OpenAI / Groq / Alpha Vantage / Tavily / LangSmith keys.
* Frontend Next.js 16.2.6 scaffolded in `frontend/` (TypeScript, App Router, `src/` dir, ESLint, Turbopack, import alias `@/*`) on React 19.2.4 and Tailwind CSS v4.
* shadcn/ui initialized in `frontend/` (style: `base-nova`, base color: `neutral`, CSS variables, RSC, `lucide` icons). Base components installed: `button`, `card`, `input`, `label`, `separator`, `skeleton`.
* Verified frontend builds cleanly via `npm run build` (Turbopack: compiled in 7.1s, TypeScript in 2.3s, 4 static routes generated).
* NOTE: `create-next-app` dropped a `frontend/CLAUDE.md` + `frontend/AGENTS.md` warning that Next.js 16 has breaking changes from older training data — kept in place; reference `node_modules/next/dist/docs/` before writing Next-specific code.
* `backend/scripts/test_fetch.py` smoke test for Alpha Vantage data fetching. Uses `httpx` (added to `requirements.txt` as `httpx==0.28.1`), loads key from `backend/.env` via `python-dotenv`, falls back to the public `demo` key (IBM only). Resilient against timeouts, HTTP errors, malformed JSON, Alpha Vantage error envelopes (`Note` / `Information` / `Error Message`), and empty responses. Logs via `logging`, not `print`.
* Verified end-to-end run with the demo key: IBM `GLOBAL_QUOTE` + `OVERVIEW` returned real data (price, 50+ fundamentals fields); fake ticker `ZZZFAKE` was rejected gracefully (caught by the error-envelope path, since the demo key only authorizes IBM — once a real `ALPHA_VANTAGE_API_KEY` is set in `backend/.env`, the same script will exercise the empty-response branch instead).

## 🟡 In Progress
* (none — awaiting next task)

## 🔴 To Do (Next Tasks)
1. _(empty — original 3-task bootstrap is complete; next milestone TBD.)_

## 📌 Open follow-ups / known gaps
* User has not yet obtained / placed real API keys (`OPENAI_API_KEY`, `GROQ_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `TAVILY_API_KEY`, `LANGSMITH_API_KEY`). `backend/.env` does not exist yet — only the committed `backend/.env.example` template.
* No `git commit`s yet on this repo; working tree has the entire bootstrap as untracked changes ready for an initial commit when the user chooses.
* The two docs in `docs/` have a doubled `.md.md` extension (an Obsidian save quirk) — flagged earlier; non-blocking but worth a rename later.