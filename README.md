# Mission Control — AI Financial Analysis System

An autonomous multi-agent financial research system. Enter a stock ticker and get a structured, self-corrected analysis report in seconds — powered by a LangGraph reflection loop, real-time market data, and live news sentiment.

![Mission Control](https://img.shields.io/badge/stack-FastAPI%20%2B%20Next.js-blue) ![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-purple) ![OpenAI](https://img.shields.io/badge/LLM-GPT--4o--mini-green)

---

## How it works

Four AI agents run in a cyclical pipeline:

```
Data Agent ──┐
             ├──▶ Manager Agent (draft) ──▶ Critic Agent ──▶ approved?
Sentiment    ┘          ▲                        │
Agent                   └────── revise ──────────┘
```

1. **Data Agent** — fetches price, P/E, market cap, EPS, 52-week range via yfinance
2. **Sentiment Agent** — pulls the 5 most recent news articles via Tavily and classifies each as Bullish / Bearish / Neutral
3. **Manager Agent** — synthesizes both data streams into a structured report with a verdict and risk/opportunity breakdown
4. **Critic Agent** — audits the report for factual consistency and logical contradictions; sends it back for revision or signs off with a confidence score

Results stream to the frontend in real time via SSE. The "Under the Hood" panel shows every agent event as it happens.

---

## Tech stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11, FastAPI, LangGraph, LangChain |
| LLM | OpenAI `gpt-4o-mini` |
| Market data | yfinance (no API key needed) |
| News & sentiment | Tavily AI |
| Frontend | Next.js 15, React, Tailwind CSS v4, shadcn/ui |
| Streaming | Server-Sent Events (SSE) |

---

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 20+
- API keys: `OPENAI_API_KEY`, `TAVILY_API_KEY`

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in OPENAI_API_KEY and TAVILY_API_KEY in .env

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Environment variables

Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | Powers all three LLM agents |
| `TAVILY_API_KEY` | Yes | Real-time news search |
| `LANGSMITH_API_KEY` | No | LangSmith tracing (optional) |

**Never commit `.env`.** It is in `.gitignore`.

---

## Project structure

```
├── backend/
│   ├── app/
│   │   ├── agents/          # Data, Sentiment, Manager, Critic agents
│   │   ├── models/          # Pydantic schemas
│   │   ├── services/        # yfinance, Tavily, cache, rate limiter
│   │   ├── routers/         # FastAPI SSE endpoint
│   │   └── config.py        # Settings via pydantic-settings
│   └── requirements.txt
└── frontend/
    └── src/
        ├── app/             # Next.js App Router
        ├── components/
        │   ├── dashboard/   # Header, terminal, synthesis console, evidence panel
        │   ├── search/      # SearchHome, LoadingSkeleton
        │   └── ui/          # shadcn components
        └── lib/
            └── api.ts       # SSE streaming client
```
