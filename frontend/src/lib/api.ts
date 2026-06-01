// Wire-format types mirror the Pydantic models in backend/app/models/*.
// Decimals are serialized as strings by FastAPI/Pydantic v2; volumes and
// market_capitalization stay as numbers.
//
// Streaming: streamAnalysis() opens a fetch-based SSE stream so we can send
// the X-Master-Code header (native EventSource cannot set headers). Returns
// a cleanup function (AbortController.abort) to close the stream.

import { fetchEventSource } from "@microsoft/fetch-event-source";

export type StockQuote = {
  symbol: string;
  open_price: string;
  high: string;
  low: string;
  price: string;
  volume: number;
  latest_trading_day: string;
  previous_close: string;
  change: string;
  change_percent: string;
};

export type CompanyOverview = {
  symbol: string;
  name: string;
  asset_type: string;
  description: string;
  exchange: string;
  currency: string;
  country: string;
  sector: string;
  industry: string;
  market_capitalization: number | null;
  pe_ratio: string | null;
  eps: string | null;
  dividend_yield: string | null;
  beta: string | null;
  week_52_high: string | null;
  week_52_low: string | null;
  analyst_target_price: string | null;
};

export type DataAgentReport = {
  ticker: string;
  quote: StockQuote;
  overview: CompanyOverview;
  fetched_at: string;
};

export type Sentiment = "bullish" | "bearish" | "neutral";

export type NewsArticle = {
  title: string;
  url: string;
  content: string;
  score: number | null;
  published_date: string | null;
};

export type ClassifiedArticle = {
  article: NewsArticle;
  sentiment: Sentiment;
  confidence: number;
  reason: string;
};

export type SentimentAgentReport = {
  ticker: string;
  query: string;
  articles_analyzed: number;
  overall_sentiment: Sentiment;
  overall_confidence: number;
  classified: ClassifiedArticle[];
  fetched_at: string;
  is_zero_news: boolean;
};

export type OverallView = "positive" | "negative" | "mixed" | "neutral";

export type BullCase = {
  ticker: string;
  thesis: string;
};

export type BearCase = {
  ticker: string;
  thesis: string;
};

export interface FilingChunk {
  section: string;
  content: string;
  similarity: number;
}

export interface FilingsContext {
  ticker: string;
  form_type: string;
  chunks: FilingChunk[];
  is_empty: boolean;
}

export interface DodgedQuestion {
  analyst_question: string;
  management_response: string;
  evasion_signal: string;
}

export interface TranscriptContext {
  ticker: string;
  quarter: number;
  year: number;
  date: string | null;
  executive_tone: "confident" | "cautious" | "defensive" | "neutral";
  management_sentiment: "positive" | "neutral" | "negative";
  key_forward_statements: string[];
  dodged_questions: DodgedQuestion[];
  is_empty: boolean;
}

export type FinalReport = {
  ticker: string;
  company_name: string;
  overall_view: OverallView;
  one_line_summary: string;
  key_strengths: string[];
  key_risks: string[];
  bull_case: BullCase | null;
  bear_case: BearCase | null;
  filings_context: FilingsContext | null;
  transcript_context: TranscriptContext | null;
  deep_narrative: string | null;
  executive_summary: string | null;
  data_snapshot: DataAgentReport;
  sentiment_snapshot: SentimentAgentReport;
  model_used: string;
  generated_at: string;
  delta_refreshed: boolean;
};

// ---------------------------------------------------------------------------

export class ApiFetchError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiFetchError";
  }
}

// Backwards-compat alias for the existing quote page.
export { ApiFetchError as QuoteFetchError };

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function _getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" },
    ...init,
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new ApiFetchError(
      response.status,
      body?.detail ?? `Request failed: HTTP ${response.status}`,
    );
  }
  return (await response.json()) as T;
}

export function fetchQuote(ticker: string): Promise<StockQuote> {
  const trimmed = ticker.trim();
  if (!trimmed) throw new ApiFetchError(400, "Empty ticker.");
  return _getJson<StockQuote>(`/api/quote/${encodeURIComponent(trimmed)}`);
}

export function fetchAnalysis(ticker: string): Promise<FinalReport> {
  const trimmed = ticker.trim();
  if (!trimmed) throw new ApiFetchError(400, "Empty ticker.");
  return _getJson<FinalReport>(`/api/analyze/${encodeURIComponent(trimmed)}`, {
    cache: "no-store",
  });
}

/** Validate a Master Code. Returns credits granted (>0) if valid, 0 if invalid. */
export async function validateMasterCode(code: string): Promise<number> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/ping`, {
      headers: { "X-Master-Code": code },
    });
    if (!res.ok) return 0;
    const data = (await res.json()) as { credits?: number };
    return data.credits ?? 3;
  } catch {
    return 0;
  }
}

/** Export a FinalReport as a PDF file download. Requires a valid Master Code. */
export async function exportPdf(
  report: FinalReport,
  masterCode: string | null = null,
  rtl = false,
): Promise<void> {
  const url = `${API_BASE_URL}/api/export/pdf${rtl ? "?rtl=true" : ""}`;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (masterCode) headers["X-Master-Code"] = masterCode;
  const resp = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(report),
  });
  if (!resp.ok) throw new Error(`PDF export failed: ${resp.status}`);
  const blob = await resp.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = `${report.ticker}_deep_research.pdf`;
  a.click();
  URL.revokeObjectURL(objectUrl);
}

// ---------------------------------------------------------------------------
// SSE streaming
// ---------------------------------------------------------------------------

export type ProgressStage =
  | "cache_hit"
  | "cache_miss"
  | "delta_refreshing"
  | "delta_complete"
  | "started"
  | "filings_fetching"
  | "filings_complete"
  | "filings_unavailable"
  | "transcript_fetching"
  | "transcript_complete"
  | "transcript_unavailable"
  | "data_complete"
  | "sentiment_complete"
  | "sentiment_unavailable"
  | "debating"
  | "debate_complete"
  | "debate_skipped"
  | "synthesizing"
  | "critiquing"
  | "revising"
  | "approved";

export type ProgressPayload = { stage: ProgressStage; message: string };

export type StreamEvent =
  | { type: "progress"; data: ProgressPayload }
  | { type: "result"; data: FinalReport }
  | { type: "stream_error"; data: { message: string } }
  | { type: "connection_error"; data: { message: string } };

/**
 * Open an SSE stream for the given ticker.
 *
 * Calls `onEvent` for every server-sent event.  Returns a cleanup function
 * that closes the EventSource — call it on unmount or when the ticker changes.
 */
export function streamAnalysis(
  ticker: string,
  onEvent: (event: StreamEvent) => void,
  masterCode?: string | null,
): () => void {
  const trimmed = ticker.trim();
  if (!trimmed) {
    onEvent({ type: "stream_error", data: { message: "Empty ticker." } });
    return () => {};
  }

  const controller = new AbortController();
  const url = `${API_BASE_URL}/api/analyze/${encodeURIComponent(trimmed)}/stream`;

  // Track whether the stream reached a logical terminator (final `result` or
  // a server-emitted `stream_error`). If the connection closes WITHOUT one of
  // those, treat it as a mid-analysis drop and surface a recoverable error.
  let cleanlyFinished = false;

  fetchEventSource(url, {
    signal: controller.signal,
    headers: masterCode ? { "X-Master-Code": masterCode } : {},
    openWhenHidden: true,
    onmessage(ev) {
      if (ev.event === "progress") {
        onEvent({ type: "progress", data: JSON.parse(ev.data) as ProgressPayload });
      } else if (ev.event === "result") {
        cleanlyFinished = true;
        onEvent({ type: "result", data: JSON.parse(ev.data) as FinalReport });
        controller.abort();
      } else if (ev.event === "stream_error") {
        cleanlyFinished = true;
        onEvent({ type: "stream_error", data: JSON.parse(ev.data) as { message: string } });
        controller.abort();
      }
    },
    onclose() {
      // Server-initiated close without a terminator = mid-analysis drop.
      if (!cleanlyFinished) {
        onEvent({
          type: "connection_error",
          data: { message: "Connection interrupted mid-analysis." },
        });
      }
    },
    onerror() {
      if (!cleanlyFinished) {
        onEvent({
          type: "connection_error",
          data: { message: "Connection interrupted mid-analysis." },
        });
      }
      controller.abort();
      // Throw to stop fetch-event-source's auto-retry loop. AbortController
      // is the canonical cleanup path; the throw prevents reconnect attempts.
      throw new Error("stream closed");
    },
  }).catch(() => {
    // onerror already reported to the caller; swallow to avoid an unhandled
    // promise rejection on the AbortError or thrown sentinel above.
  });

  return () => controller.abort();
}
