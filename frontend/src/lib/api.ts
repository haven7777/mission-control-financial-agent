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

export class QuoteFetchError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "QuoteFetchError";
  }
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchQuote(ticker: string): Promise<StockQuote> {
  const trimmed = ticker.trim();
  if (!trimmed) {
    throw new QuoteFetchError(400, "Empty ticker.");
  }

  const url = `${API_BASE_URL}/api/quote/${encodeURIComponent(trimmed)}`;
  const response = await fetch(url, { headers: { Accept: "application/json" } });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new QuoteFetchError(
      response.status,
      body?.detail ?? `Request failed: HTTP ${response.status}`,
    );
  }

  return (await response.json()) as StockQuote;
}
