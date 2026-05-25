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
* Initial git commit `b60feff` on branch `main` (renamed from `master`), 39 files / 11,175 insertions; no remote configured yet.
* **FastAPI app skeleton, typed config, healthcheck.** Created `backend/app/__init__.py`, `backend/app/config.py` (pydantic-settings loading `backend/.env`, exposing `env`, `cors_origins`, optional API keys, and an `alpha_vantage_configured` derived property that ignores the `demo` fallback), and `backend/app/main.py` (FastAPI 0.136 instance with CORS for `http://localhost:3000`, lifespan-based startup logging, Pydantic-validated `HealthResponse`, `GET /health`). Added `pydantic-settings==2.14.1` to `requirements.txt`.
* Verified the health endpoint two ways: (a) `TestClient` returned `200 {"status":"ok","env":"dev","alpha_vantage_configured":false}`; (b) real `uvicorn app.main:app` on `127.0.0.1:8000` served the same body to `curl` and the lifespan log fired `Startup: env=dev alpha_vantage_configured=False`.
* **Alpha Vantage fetcher promoted to a typed Pydantic service.**
  * `backend/app/models/financial.py` — `StockQuote` and `CompanyOverview` with Pydantic v2 field aliases that map Alpha Vantage's raw key names (e.g. `"01. symbol"`, `"PERatio"`) to snake_case. `Decimal` for all monetary/ratio fields (no float drift), `date` for the latest trading day. Custom `BeforeValidator`s strip the trailing `%` on percent fields and coerce Alpha Vantage's `"None" / "-" / "N/A"` sentinels to real `None`.
  * `backend/app/services/alpha_vantage.py` — sync `httpx` fetcher with a typed exception hierarchy: `DataFetchError` base, plus `TimeoutFetchError`, `HTTPFetchError`, `MalformedResponseError`, `RateLimitedError` (covers Alpha Vantage `Note` / `Information` envelopes — quota and demo-key restriction), `InvalidTickerError`. Public surface: `fetch_global_quote(ticker) -> StockQuote`, `fetch_company_overview(ticker) -> CompanyOverview`. API key resolved via `app.config.get_settings()` (falls back to `demo`).
  * `backend/scripts/test_fetch.py` reduced to a thin caller (~50 lines) that imports the service, runs the same happy/resilience scenarios, and prints a typed-data summary.
* Verified by re-running the smoke test: `StockQuote.price=Decimal("253.8400")`, `change_percent=Decimal("0.3439")`, `latest_trading_day=date(2026,5,22)`; `CompanyOverview.market_capitalization=237_762_789_000` (int), `pe_ratio=Decimal("22.37")`. `ZZZFAKE` raised the typed `RateLimitedError` (demo-key gate) → still PASS/PASS.
* **End-to-end vertical slice — backend.**
  * `backend/app/routers/quote.py` — `GET /api/quote/{ticker}` calls `fetch_global_quote`, returns the `StockQuote` model with `response_model_by_alias=False` so the wire format is snake_case (no `"01. symbol"` leaking through to the client). Cheap regex guard `^[A-Z0-9.\-]{1,10}$` rejects garbage input with 422; `InvalidTickerError` → 404; every other typed `DataFetchError` (rate-limit / timeout / HTTP / malformed) → 503 with the exception class name in the detail. Router wired into `app.main` via `include_router`.
  * Verified via `TestClient`: `IBM`→200 with `{symbol, price, change_percent, ...}` keys; `ZZZFAKE`→503 with typed-error detail; `ibm`→200 (normalized); `!!bad!!`→422 (regex guard).
* **End-to-end vertical slice — frontend.**
  * Installed `@tanstack/react-query@^5.100.14`.
  * `frontend/src/app/providers.tsx` — client-component `<Providers>` that owns the `QueryClient` (lazy-init via `useState`, 30s `staleTime`, no retries on the demo key).
  * `frontend/src/app/layout.tsx` — wraps `{children}` in `<Providers>`, sets metadata + `dark` class on `<html>` per the architecture's "dark mode by default" rule.
  * `frontend/src/lib/api.ts` — typed `StockQuote` interface, `QuoteFetchError` class, `fetchQuote(ticker)` that resolves the API base URL from `NEXT_PUBLIC_API_BASE_URL` (defaults to `http://localhost:8000`).
  * `frontend/src/app/page.tsx` — submit-gated form using shadcn `Input` + `Button`; on success renders a quote `Card` with price / change (green ↑ red ↓) / open / prev close / high / low / volume; loading → `Skeleton` grid; error → destructive-bordered `Card`.
  * `npm run build` clean: Turbopack compiled in 5.3s, TS in 2.3s, 4 static routes.
* **End-to-end runtime verification.** Both dev servers up; verified four paths:
  * `/health` → 200 typed body.
  * `OPTIONS /api/quote/IBM` (CORS preflight from `http://localhost:3000`) → 200 with `access-control-allow-origin: http://localhost:3000` and `allow-methods: GET, POST, OPTIONS`.
  * `GET /api/quote/IBM` cross-origin → 200, snake_case JSON, CORS headers present.
  * `GET /api/quote/ZZZFAKE` cross-origin → 503 + JSON detail `"Upstream data error (RateLimitedError): The **demo** API key is for demo purposes only…"`, CORS headers still present so the frontend `ErrorCard` will receive and render it.
  * SSR HTML of the Next page contains all UI markers (`"Multi-Agent Financial System"`, `"Fetch quote"`, `"e.g. IBM"`, `"Stock ticker"`).
* CAVEAT: did **not** drive the page in a real headless browser (Playwright not installed; ~150 MB browser binaries). The functional pipe (CORS + endpoint + SSR HTML + clean Next build) is fully covered above; the missing piece is a click-through visual check. See follow-ups.
* **Real Alpha Vantage key landed** (`alpha_vantage_configured=true`). Re-verified the real-key path: `/api/quote/AAPL` → 200 with `price=308.82, change=+3.83, change_percent=1.2558%, latest_trading_day=2026-05-22, volume=43_670_223`. So non-IBM tickers now work end-to-end.
* **Free-tier rate limits surfaced during testing — important for the agent phase.** The follow-up `/api/quote/ZZZFAKE` request (fired immediately after AAPL) was rejected by Alpha Vantage's *free-tier* rate limiter (not the demo-key gate), surfacing as our typed `RateLimitedError → 503`. The envelope explicitly cites two limits: **1 request/second** (burst) and **25 requests/day** (quota). As a result, the typed `InvalidTickerError → 404` path is wired in code but **still not end-to-end verified** — every attempt to probe an unknown ticker has hit a rate limiter first (demo gate, then free-tier burst).

## 🟡 In Progress
* (none — original 3-task bootstrap + 3-task vertical-slice milestone both complete; awaiting next set.)

## 🔴 To Do (Next Tasks)
* (empty — next milestone TBD; natural candidates are LangGraph + the first real Agent, or an SSE streaming endpoint.)

## 🧊 Deferred (intentionally not in the next 3)
* **Alpha Vantage response caching (server-side).** Keyed by `(function, symbol)`; per-function TTLs (OVERVIEW: ~24 h since fundamentals barely change intraday; GLOBAL_QUOTE: ~60 s during market hours). Cuts repeat calls aggressively and reduces 25/day-quota burn. **High priority — should land before the Data Agent enters any LangGraph loop, since an agent retrying a failed step can otherwise burn the daily quota in seconds.**
* **Per-second throttle / single-flight on the Alpha Vantage service.** Enforce ≥1.0 s between outbound requests at the `services/alpha_vantage.py` layer (asyncio lock + monotonic timer, or a small token bucket). Same reasoning: protects against burst-limit 503s during normal multi-call analyses. Likely lands together with the cache.
* LangGraph + Data / Sentiment / Manager agents — next phase after the cache + throttle are in.
* SSE streaming endpoint — added once agents exist and have streamable progress to emit.
* LangSmith tracing setup — only useful once there are LLM/agent traces to capture.
* Rate-limiting middleware (inbound, FastAPI side) — meaningful once endpoints actually hit LLMs and we want to protect *our* upstream from *our* users.
* Headless-browser E2E (Playwright) — set up before the UI gets more complex than a single page; lets us actually click-test agent flows.
* Supabase wiring (RLS, pgvector) — MVP scope excludes report history; pgvector is for future RAG.

## 📌 Open follow-ups / known gaps
* `ALPHA_VANTAGE_API_KEY` is placed and working. Still missing: `OPENAI_API_KEY`, `GROQ_API_KEY`, `TAVILY_API_KEY`, `LANGSMITH_API_KEY` — only needed once the agent phase starts. `backend/.env.example` lists the full set.
* **Alpha Vantage free-tier limits are a real constraint** — 1 req/sec burst, **25 req/day** quota. A single ticker analysis can already consume 3-5 calls (quote + overview + future agent retries), so without the deferred caching + throttle work below, the daily quota easily runs out within a handful of analyses. Plan caching/throttle work *before* introducing any agent loop that retries failed steps.
* `InvalidTickerError → 404` code path is implemented but has **never been exercised end-to-end** — both attempts to probe an unknown ticker hit a rate-limiter first (demo gate, then free-tier burst). Will be straightforward to verify once the per-second throttle + caching are in.
* No git remote configured; `main` lives only locally. Many staged-eligible changes since the initial commit `b60feff` — needs a follow-up commit.
* No headless-browser E2E setup yet (Playwright would be the natural pick, ~150 MB install). All UI verification so far is HTTP-level + SSR-HTML grep. Tracked above in Deferred.
* The two docs in `docs/` have a doubled `.md.md` extension (an Obsidian save quirk) — flagged earlier; non-blocking but worth a rename later.