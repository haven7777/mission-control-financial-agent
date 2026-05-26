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
* **Alpha Vantage cache + throttle landed** (the two rate-limit-protection items from Deferred).
  * `backend/app/services/cache.py` — generic `TTLCache[V]`: thread-safe dict with per-entry monotonic-clock expiry, `get/set/clear/__len__`. Unit-tested for hit / miss / TTL eviction / clear.
  * `backend/app/services/rate_limiter.py` — generic `MinIntervalRateLimiter`: thread-safe gate using `threading.Lock` + `time.monotonic` + a `_next_allowed` timestamp; holds the lock through `sleep` so concurrent callers serialize cleanly. Unit-tested: first `wait()` returns instantly, second `wait()` sleeps within +-5 ms of the configured interval.
  * `backend/app/services/alpha_vantage.py` wires three module-level instances: `_rate_limiter` (1.2s min interval — `1.0s` would race Alpha Vantage's server-side counter under network jitter), `_quote_cache` (60s TTL), `_overview_cache` (24h TTL). `_request()` calls `_rate_limiter.wait()` before the outbound HTTP. `fetch_global_quote` / `fetch_company_overview` consult the cache first and only store on success — errors never poison the cache. Added `clear_caches()` test helper.
* Verified the integration path partially: a fresh `fetch_global_quote("IBM")` hits the network (~0.5s), a repeat call returns the same `StockQuote` from cache in <1 ms (zero network traffic). The third-call timing assertion (cache cleared, throttle should space the call by 1.2s) raised `RateLimitedError` — almost certainly because the day's 25-request quota was already drained by the various smoke / integration / CORS tests run during this session, not a bug in the throttle (which the unit test independently proved correct). The wiring itself is verified by import-time route + instance checks (`/health`, `/api/quote/{ticker}` registered; constants applied).
* **First LangGraph agent — Data Agent — landed.**
  * `backend/app/models/agents.py` — `DataAgentReport` Pydantic model with `ticker`, validated `StockQuote`, validated `CompanyOverview`, UTC `fetched_at`, plus derived properties `market_cap_billions` and `is_within_52_week_band`. `extra="forbid"` ensures no untyped data crosses the agent boundary.
  * `backend/app/agents/__init__.py` package marker.
  * `backend/app/agents/data_agent.py` — single-node LangGraph 1.x graph (`CompiledStateGraph`): Pydantic `_DataAgentState` schema, one `_fetch_node` that calls the protected `fetch_global_quote` + `fetch_company_overview` (cache + throttle still in effect), graph compiled once at import. Public surface: `run_data_agent(ticker) -> DataAgentReport`. No LLM yet (deferred — needs OpenAI/Groq).
  * `backend/scripts/test_data_agent.py` — runnable smoke test (`backend/venv/bin/python backend/scripts/test_data_agent.py IBM`) — invokes the agent, prints the typed report.
* Verified the agent: import-time validation shows the graph compiles to `CompiledStateGraph`; state has `[ticker, quote, overview]`; report has `[ticker, quote, overview, fetched_at]` + derived properties. Live IBM invocation reached the upstream service and ran both fetches with the 1.2s throttle correctly spacing them, but the second response carried the daily-quota `RateLimitedError` envelope — the agent surfaced it cleanly as a typed exception (PASS for the unhappy path; the happy-path report shape stays unverified until the quota resets at 00:00 UTC).
* **🚨 Security fix: stopped Alpha Vantage API key from leaking via `httpx` logs.** During the agent's first live run, `httpx`'s default INFO-level "HTTP Request: GET <full-url>" log included `apikey=<real key>` in the URL (Alpha Vantage only authenticates via query string). The key appeared in stdout / shell scrollback / this session's tool output. Mitigation:
  * `app/main.py`, `scripts/test_data_agent.py`, `scripts/test_fetch.py` all now set `logging.getLogger("httpx").setLevel(WARNING)` (also `httpcore`) so request URLs no longer print at INFO. Verified by re-running: the next invocation log shows only our own structured `data_agent: fetching ticker=IBM` line + the typed error, no URL.
  * **Action item for the user (also in follow-ups below):** rotate the leaked key — generate a new one at alphavantage.co, replace the value in `backend/.env`, restart the backend.
* **Tavily news-search service landed** (first half of the Sentiment Agent work; LLM half next).
  * `backend/app/models/news.py` — `NewsArticle` (title, url, content, score, optional `published_date`) and `NewsSearchResult` (query + list of articles). Provider-agnostic so we can swap Tavily later if needed.
  * `backend/app/services/tavily.py` — POSTs to `api.tavily.com/search` via httpx (the API key sits in the request body, not the URL, so it can't leak through URL logs even if httpx logging were re-enabled). Typed exception hierarchy: `NewsFetchError` base, plus `NewsTimeoutError`, `NewsHTTPError`, `NewsRateLimitedError` (handles upstream 429), `MalformedNewsResponseError`, `MissingNewsAPIKey`. Public surface: `search(query, *, max_results=5, search_depth="basic") -> NewsSearchResult`. Per-article validation tolerates malformed entries (logs + drops) rather than failing the whole result. Defensive 0.25s throttle via the shared `MinIntervalRateLimiter`.
  * `backend/scripts/test_tavily.py` — runnable smoke test with optional CLI query arg.
* Verified live: `IBM stock news` query returned 5 articles (Yahoo Finance, Robinhood, CNN, Morningstar, CNBC) with relevance scores 0.76-0.81; Morningstar entry referenced IBM's 2026-05-21 quantum chip foundry announcement, confirming the search index is fresh.
* **Sentiment Agent landed (LLM half).**
  * `langchain-groq==1.1.2` (pulls `groq==0.37.1`) added to `requirements.txt`. New `groq_model` setting (defaults to `llama-3.3-70b-versatile`) added to `app/config.py`.
  * `backend/app/models/sentiment.py` — `Sentiment` enum (bullish / bearish / neutral), `ArticleSentiment` (article_index + sentiment + confidence 0-1 + one-sentence reason), `SentimentClassificationBatch` (LLM-facing structured-output schema), `ClassifiedArticle` (article + classification pair), `SentimentAgentReport` (final agent output: ticker, query, articles_analyzed, overall_sentiment, overall_confidence, list of `ClassifiedArticle`, UTC `fetched_at`). All `extra="forbid"` where applicable to enforce the architecture's strict-Pydantic-between-steps rule.
  * `backend/app/agents/sentiment_agent.py` — two-node LangGraph (`fetch_news → classify`) over a Pydantic `_SentimentAgentState`. `fetch_news` calls the typed Tavily service. `classify` instantiates `ChatGroq(temperature=0.0)` and uses LangChain's `with_structured_output(SentimentClassificationBatch)` so the LLM is forced into the Pydantic shape — any drift surfaces as a `ValidationError`. Defensive index-alignment fills missing classifications as `neutral / confidence=0.0` rather than crashing. New typed errors: `SentimentAgentError` base, `MissingLLMKey`, `NoArticlesFoundError`. Public surface: `run_sentiment_agent(ticker) -> SentimentAgentReport`.
  * `backend/scripts/test_sentiment_agent.py` — runnable smoke test with optional ticker arg.
* Verified live on IBM (~2.1 s end-to-end): 5 articles analyzed; overall `neutral` with 0.64 confidence; mixed 3-neutral / 2-bullish breakdown. Substantive classifications — Morningstar entry got `bullish 0.90` for the quantum-foundry news, generic stock-quote pages correctly got `neutral`. The LLM-generated `reason` fields are grounded in article snippets, not keyword guesses.
* **Manager Agent landed — 3-of-3 agents now built.**
  * `backend/app/models/manager.py` — `OverallView` enum (positive / negative / mixed / neutral), `ManagerSynthesis` (LLM-facing structured-output schema: `overall_view`, `one_line_summary`, `key_strengths` 1-5 items, `key_risks` 1-5 items), and the public `FinalReport` (synthesis flattened + full `data_snapshot` + `sentiment_snapshot` + `model_used` + UTC `generated_at`). `FinalReport.extra="forbid"`.
  * `backend/app/agents/manager_agent.py` — single-node LangGraph (`synthesize`) over a Pydantic `_ManagerAgentState`. Two prompt-formatting helpers distill the rich `DataAgentReport` and `SentimentAgentReport` into LLM-readable prose (company / sector / price / fundamentals / 52-week-band + sentiment overview + per-article breakdown). Public surface: `run_manager_agent(data, sentiment) -> FinalReport`. Mismatched-ticker guard at the entry point.
  * `backend/scripts/test_manager_agent.py` — runnable end-to-end pipeline test. Tries the live Data Agent first; on `DataFetchError` (e.g. Alpha Vantage daily quota exhausted) falls back to a hand-crafted IBM stub so the Manager's synthesis can still be exercised. Runs Sentiment Agent live, then Manager Agent, prints the final report.
* **Discovered + worked around two Groq structured-output quirks.**
  1. Default `method="function_calling"` produces a `<function=ManagerSynthesis>{...}</function>` wrapper, and `llama-3.3-70b-versatile` occasionally drops the closing `]` of a list inside that wrapper → Groq's API rejects the whole response with `tool_use_failed` even though the inner content is fine. Reproduced once.
  2. `method="json_schema"` (Groq's strict structured-output API) is rejected by `llama-3.3-70b-versatile` (`This model does not support response format 'json_schema'`). Only Llama-4 / GPT-OSS class models on Groq support it.
  3. Resolution: both Sentiment and Manager agents now use `method="json_mode"`, with their system prompts updated to explicitly request a JSON object (Groq's `json_object` mode requires the word "JSON" in the messages). Pydantic validates the output client-side.
* Verified live (~4.0 s end-to-end pipeline): full Data-stub → Sentiment(live) → Manager(live) run for IBM produced a balanced `MIXED` view, four substantive `key_strengths` (dividend, beta, analyst target, sector position) and four substantive `key_risks` (P/E interpretation, 52-week-band positioning, neutral sentiment caveat, sector competition). All bullets traceable back to either the data snapshot or the sentiment classifications — no hallucinated facts.
* **Pipeline graph + `/api/analyze` endpoint + frontend UI shipped — full vertical slice through all three agents.**
  * `backend/app/agents/pipeline.py` — multi-node LangGraph: `START` fans out to `data` and `sentiment` in **parallel** (independent external APIs, no shared state), both join at `manager`. Pydantic `_PipelineState`. Public surface: `run_full_analysis(ticker) -> FinalReport`.
  * `backend/app/routers/analyze.py` — `GET /api/analyze/{ticker}` with the same regex guard as `/api/quote`, `response_model_by_alias=False` for snake_case JSON. Error mapping: `InvalidTickerError` / `NoArticlesFoundError` → 404; `MissingNewsAPIKey` / `MissingLLMKey` → 500 (server misconfigured); `DataFetchError` / `NewsFetchError` → 503; everything else falls through.
  * `app/main.py` wires `include_router(analyze_router.router)` alongside the existing quote router.
  * Frontend `lib/api.ts` rewritten: now exposes typed `FinalReport`, `DataAgentReport`, `SentimentAgentReport`, `ClassifiedArticle`, `NewsArticle`, `OverallView`, `Sentiment`, an `ApiFetchError` class (with `QuoteFetchError` alias for back-compat), shared `_getJson` helper, and `fetchAnalysis(ticker)` alongside the existing `fetchQuote(ticker)`.
  * Frontend `src/app/page.tsx` rebuilt around `useQuery(["analyze", ticker])`. Renders four sections:
    1. `SynthesisCard` — company name + ticker, overall-view badge (tone-coloured: positive/green, negative/red, mixed/amber, neutral/zinc), one-line summary, two-column strengths/risks bullet lists with +/− glyphs.
    2. `QuoteStatsCard` — price + change (green/red), open / prev close / high / low / volume / market cap / P/E / EPS / 52-week range / analyst target / beta — all from `data_snapshot`.
    3. `SentimentCard` — overall sentiment badge with confidence, plus a per-article list with sentiment-coloured chips, clickable titles (open in new tab), and the LLM's one-sentence reason underneath each.
    4. `ProvenanceFooter` — model name + generated_at, so users can see what produced the report.
    Plus `AnalysisSkeleton` (matches the full layout) for loading state and `ErrorCard` for failures.
  * `npm run build` clean (Turbopack: 5.5s compile, 2.3s TS check, 4 static routes).
* Verified end-to-end with both dev servers running:
  * `/health` → 200, `/api/quote/{ticker}` still works (kept for cheap quote-only paths).
  * **Cross-origin `GET /api/analyze/IBM` → HTTP 200 in 2.76 s** (real fresh data: IBM $253.84, market cap $238.58B, P/E 22.46; 5 news articles classified — Morningstar's quantum-chip-foundry article correctly `bullish 0.90`; Manager synthesized into `MIXED` view with 4 grounded strengths and 4 grounded risks, every bullet traceable to either the data snapshot or the sentiment classifications).
  * Parallel execution observed in logs — `pipeline: data node` and `pipeline: sentiment node` started at the same wall-clock timestamp; Sentiment finishes in ~1.3 s while Data runs concurrently, then Manager fires once both are in. Net wall-clock ≈ max(data, sentiment) + manager, not sum.
  * SSR HTML on `http://localhost:3000/` contains all the new UI markers (page title, `Analyze` button, ticker input, aria-label).

* **SSE streaming endpoint + live progress UI shipped.**
  * `backend/app/agents/pipeline_stream.py` — streaming variant of the full pipeline: runs Data + Sentiment agents concurrently via two `daemon` threads, collects results via `queue.Queue`, yields SSE-ready event dicts as each agent completes, then runs Manager and yields the `FinalReport`.  Event types: `progress` (stage updates), `result` (full report), `stream_error` (agent failure — never raises, always yields the error event so the SSE layer can close cleanly).
  * `backend/app/routers/analyze.py` extended with `GET /api/analyze/{ticker}/stream` — returns a `StreamingResponse(media_type="text/event-stream")` with `Cache-Control: no-cache` and `X-Accel-Buffering: no` headers.  Ticker validation reuses the same regex guard as the sync endpoint.  The original `GET /api/analyze/{ticker}` sync endpoint is unchanged.
  * `frontend/src/lib/api.ts` extended with `ProgressStage`, `ProgressPayload`, `StreamEvent` types and `streamAnalysis(ticker, onEvent) → cleanup`.  Uses the browser's native `EventSource` API; listens for `progress`, `result`, and `stream_error` named events; handles native `onerror` (connection drop) as a `connection_error` event.
  * `frontend/src/app/page.tsx` rebuilt around a `useAnalysisStream` custom hook (replaces `useQuery`).  During streaming: renders a `ProgressCard` showing completed stages with ✓ checkmarks and a pulsing `○ Working…` spinner for the next step.  On result: transitions instantly to the four-section report (`SynthesisCard`, `QuoteStatsCard`, `SentimentCard`, `ProvenanceFooter`).  On error: shows `ErrorCard`.  The `Skeleton`-based loading state has been removed.
  * `npm run build` clean (Turbopack 5.4s compile, TypeScript 2.4s, 4 static routes).
  * Backend imports verified: `pipeline_stream` imported cleanly; router exposes both `/api/analyze/{ticker}` and `/api/analyze/{ticker}/stream`.
  * End-to-end UI verified with Playwright (headless Chromium): page loads, IBM ticker submitted, progress card shows ✓ per stage, full 4-section report renders on completion. Provenance footer confirms model `llama-3.3-70b-versatile`. Error card correctly surfaces when Alpha Vantage daily quota is exhausted.
  * **Security fix** (`alpha_vantage.py`): AV's `Note`/`Information` envelopes no longer leak the raw API key in the error message; replaced with safe generic strings ("Alpha Vantage rate limit reached" / "daily quota exceeded").

* **Inbound rate limiting shipped** (`slowapi` + per-IP sliding window).
  * `slowapi==0.1.9` + `limits==5.8.0` added to `requirements.txt`.
  * `backend/app/services/limiter.py` — module-level `Limiter(key_func=get_remote_address)` singleton imported by both routers. Comment explains the `X-Forwarded-For` upgrade path for production-behind-proxy.
  * `backend/app/main.py` — `app.state.limiter = limiter`; custom `_rate_limit_handler` exception handler returns `{"detail": "..."}` JSON + `Retry-After: 60` header (matches the frontend's existing error-parsing path; overrides slowapi's default `{"error": ...}` format).
  * `backend/app/routers/analyze.py` — both `GET /api/analyze/{ticker}` and `GET /api/analyze/{ticker}/stream` decorated with `@limiter.limit("5/minute")`. `request: Request` parameter added (required by slowapi).
  * `backend/app/routers/quote.py` — `GET /api/quote/{ticker}` decorated with `@limiter.limit("30/minute")`. `request: Request` parameter added.
  * `GET /health` left unrestricted (health-check endpoints should not be rate-limited).
  * `backend/scripts/test_rate_limit.py` — TestClient smoke test (no real API calls): fires 31 requests to `/api/quote/IBM` → asserts #31 is 429; fires 6 requests to `/api/analyze/IBM` → asserts #6 is 429; fires 10 rapid `/health` requests → asserts all 200. All 9 checks pass.

* **LangSmith tracing wired** — fully instrumented; zero code changes needed in the agents themselves (LangGraph traces automatically when env vars are present).
  * `langsmith==0.8.5` pinned in `requirements.txt` (was already installed as a transitive dep of `langchain-groq`).
  * `app/config.py` — added `langsmith_endpoint` field (default `https://api.smith.langchain.com`, override for self-hosted) and `langsmith_configured` derived property (true iff both key and `LANGSMITH_TRACING=true` are set).
  * `app/services/tracing.py` — `configure_langsmith_tracing()`: propagates settings from the `Settings` object into `os.environ` using `setdefault` (idempotent). Sets both the modern `LANGSMITH_*` vars and the legacy `LANGCHAIN_*` compat vars so LangGraph 1.x automatic tracing activates for every agent invocation. Returns `bool`.
  * `app/main.py` — calls `configure_langsmith_tracing()` at module level (before any request is processed); result stored in `_tracing_enabled`. Startup log now includes `langsmith_tracing=True/False`. `/health` response extended with `langsmith_tracing` field.
  * `backend/.env.example` — updated with comments and `LANGSMITH_TRACING=false` default (opt-in).
  * `backend/scripts/test_tracing.py` — 13/13 checks pass: env var propagation, idempotency, disabled-when-no-key, `/health` field presence.
  * **To activate:** add `LANGSMITH_API_KEY=<key>` and `LANGSMITH_TRACING=true` to `backend/.env`; get a free key at https://smith.langchain.com. Every subsequent agent run will appear in the LangSmith dashboard with full prompt/response/latency traces.

* **Playwright E2E test suite landed** — full browser-based smoke + regression coverage with session-scoped server fixtures.
  * `backend/tests/e2e/conftest.py` — session-scoped fixtures `backend_server` and `frontend_server` start the respective dev servers (uvicorn / `npm run dev`) only if not already running; poll via HTTP readiness (not just port-open). Session-scoped Playwright `browser` (Chromium headless), function-scoped `context` + `page` (pre-navigated to `http://localhost:3000`).
  * `backend/tests/e2e/test_ui.py` — 11 tests (10 pass, 1 conditionally skipped):
    * Static structure: h1 title visible, input + Analyze button present.
    * Input behaviour: button disabled on empty input, enabled after typing, input accepts text.
    * Submission flow: progress card appears after submit, stream resolves (button returns to "Analyze"), resolved state contains text content.
    * Conditional paths: success path (all 4 report cards) skips gracefully when external APIs are unavailable; error-card path verified separately; re-submit clears prior state.
  * `backend/pytest.ini` — `testpaths = tests`, `asyncio_mode = auto`, `asyncio_default_fixture_loop_scope = session`.
  * **Run:** `cd backend && venv/bin/python -m pytest tests/e2e/ -v` (both servers must be running, or let conftest start them). **Result: 10 passed, 1 skipped in 10.66 s.**

* **Critic Agent landed (v3.0 Task 1).**
  * `backend/app/models/critic.py` — `CritiqueVerdict` enum (`approved`/`needs_revision`), `IssueSeverity` enum (`minor`/`major`/`fatal`), `CritiqueIssue` (field + issue + severity), `CritiqueResult` (LLM-facing structured-output schema: verdict + synthesis_confidence + issues + revision_instruction), `CritiqueReport` (full output: ticker + critique_result + revision_round + critiqued_at).
  * `backend/app/agents/critic_agent.py` — single-node LangGraph (`critique`) using `ChatGroq.with_structured_output(CritiqueResult, method="json_mode")`. System prompt checks four things: numeric grounding, sentiment alignment, completeness, internal consistency. Reuses `_format_data` / `_format_sentiment` helpers from `manager_agent.py`. Exports `MAX_REVISION_CYCLES = 2` for the pipeline (Task 2). Public surface: `run_critic_agent(report, data, sentiment, revision_round=1) -> CritiqueReport`.
  * `backend/scripts/test_critic_agent.py` — full pipeline smoke test (Data → Sentiment → Manager → Critic). Live verified on IBM: `NEEDS_REVISION`, confidence 0.70, 4 issues found (1 MAJOR: sentiment divergence not acknowledged; 3 MINOR). Revision instruction generated correctly.

## 🟡 In Progress
* Upgrading architecture to v3.0 (AI Research Operating System with Critic Agent and Reflection Loops).

* **Cyclical pipeline with Critic reflection loop landed (v3.0 Task 2).**
  * `backend/app/agents/pipeline.py` refactored from a linear DAG to a cyclical graph. New shape: `START → data + sentiment (parallel) → manager → critic → (needs_revision ≤ MAX_REVISION_CYCLES) → manager | END`.
  * `_PipelineState` extended with `critique: CritiqueReport | None` and `revision_round: int = 1`. Critic node increments `revision_round` on each cycle so the routing condition can enforce the cap.
  * `_should_revise` conditional edge: routes back to `manager` when `verdict == needs_revision AND revision_round ≤ MAX_REVISION_CYCLES`; routes to `END` otherwise (approved or cap exhausted).
  * `backend/app/agents/manager_agent.py` updated: `run_manager_agent` now accepts optional `revision_instruction: str | None`. When set, the revision directive is prepended to the user prompt so the Manager knows exactly what to fix. Log line shows `[REVISION]` flag on subsequent rounds.
  * Verified live (IBM): `data → sentiment → manager (round 1) → critic (verdict=approved, confidence=0.95) → END`. Loop fired correctly; no spurious cycles.

* **SSE Streaming updated for Critic loop (v3.0 Task 3).**
  * `backend/app/agents/pipeline_stream.py` rewritten with Manager → Critic reflection loop. New progress stages: `synthesizing`, `critiquing`, `revising` (with short Critic instruction), `approved` (with confidence %).
  * Loops `for revision_round in range(1, MAX_REVISION_CYCLES + 1)` — at most 2 iterations. `is_last` forces exit on final round regardless of verdict. Critic failure is non-fatal (surfaces Manager's last draft).
  * Verified live via `curl`: full reflection sequence observed — `started → data_complete → sentiment_complete → synthesizing → critiquing → revising → synthesizing (revision 1) → critiquing → approved (confidence 95%) → result`.

* **Frontend "Mission Control" UI shipped (v3.0 Task 4).**
  * `frontend/src/lib/api.ts` — `ProgressStage` type extended with `critiquing`, `revising`, `approved`.
  * `frontend/src/app/page.tsx` — `ProgressCard` redesigned as "AI Research Operating System" Mission Control view:
    * Card title is "AI Research Operating System"; description updates dynamically per phase ("Starting up…", "Gathering data…", "Manager synthesizing…", "Critic auditing…", "Revision requested — rewriting…", "Synthesis approved").
    * Stage-specific icons and colors: `▸` gray for started, `✓` green for data/sentiment, `⟳` blue for synthesizing, `⊙` amber for critiquing, `↺` orange for revising (full instruction shown in highlighted block), `✓` emerald for approved (confidence shown in highlighted block).
    * Pulsing `○ Working…` indicator stops when `approved` is received.
  * `npm run build` clean (Turbopack 5.2s, TypeScript 2.3s).
  * Verified with Playwright (headless Chromium): "AI Research Operating System" card visible during stream; stage icons color-coded correctly; description updates in real time; full 4-section report renders on completion.

## 🔴 To Do (Next Tasks)
* None — v3.0 upgrade complete. All four tasks delivered:
  1. Critic Agent (models + agent + smoke test)
  2. Cyclical pipeline with reflection loop
  3. SSE streaming with Critic debate events
  4. Mission Control frontend UI