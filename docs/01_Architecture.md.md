# System Architecture & Design: Multi-Agent Financial System

## The Goal
A full-stack application where a user inputs a stock ticker, and a team of AI agents analyzes financial data, news sentiment, and risk, returning a streamed, comprehensive report.

## Tech Stack & Tooling
* **Backend:** Python, FastAPI, LangGraph (for multi-agent orchestration).
* **Frontend:** Next.js (App Router), TypeScript, TanStack Query (for data fetching and state management).
* **Database & RAG:** Supabase (PostgreSQL with pgvector).

## Security & Cost Control (CRITICAL)
* **API Key Protection:** All third-party API keys (OpenAI, Groq, Alpha Vantage, Tavily) MUST live exclusively on the Python Backend in a `.env` file. The Next.js frontend will never call external APIs directly, only our FastAPI endpoints.
* **Database Security:** Supabase Row Level Security (RLS) must be enabled to prevent direct client-side manipulation of the database.
* **Rate Limiting:** The FastAPI backend must implement rate limiting to prevent abuse and runaway LLM costs.
* **Environment Variables:** Never commit `.env` files. Always use `.env.example` in the Git repository.

## Product Philosophy & MVP Scope
* **Quality Over Quantity:** The MVP is scoped down in features but MUST be engineered to Production-Grade standards. "Working" is not enough. The code must be clean, modular, typed, and properly error-handled.
* **Resilience:** The backend MUST gracefully handle API timeouts, bad JSON responses from the LLM, and edge cases (e.g., user enters a fake stock ticker).
* **In Scope for MVP:** A single public page where a user enters a stock ticker, the agents process it (showing loading state/thoughts), and stream back a report.
* **Out of Scope for MVP:** User authentication, saving report history, billing, or multi-language support. Do NOT build these.

## UI/UX & Design System
* **Styling Framework:** Tailwind CSS.
* **Component Library:** shadcn/ui.
* **Design Principles:** Minimalist professional dashboard, dark mode support by default, clear typography for readability.
* **Loading States:** Distinct visual loading states (handling the SSE stream) to keep the user engaged during agent "thinking" times (15-45 seconds).

## Agent Team
1. **Data Agent:** Fetches raw financial data (e.g., balance sheets, income statements).
2. **Sentiment Agent:** Fetches and analyzes recent news articles.
3. **Manager Agent:** Reviews data, resolves conflicts, and outputs the final structured JSON report.

## Testing, Observability & Debugging
* **Tracing (LangSmith):** Agent workflows must be instrumented using LangSmith (or equivalent LangGraph tracing). We need full visibility into every prompt sent and received.
* **Validation:** Every step between agents must pass through strict Pydantic validation. The system must never crash due to a malformed LLM response; it should retry or fallback gracefully.
* **Logging:** Implement a standard Python logger (e.g., `loguru` or standard `logging`), not just raw `print()` statements.