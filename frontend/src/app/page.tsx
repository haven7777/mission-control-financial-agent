"use client";

import { useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchQuote, QuoteFetchError, type StockQuote } from "@/lib/api";

export default function Home() {
  const [input, setInput] = useState("");
  const [ticker, setTicker] = useState<string | null>(null);

  const query = useQuery<StockQuote, QuoteFetchError>({
    queryKey: ["quote", ticker],
    queryFn: () => fetchQuote(ticker!),
    enabled: ticker !== null,
  });

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const next = input.trim().toUpperCase();
    if (next) setTicker(next);
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-6 py-16">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">
          Multi-Agent Financial System
        </h1>
        <p className="text-sm text-muted-foreground">
          Enter a stock ticker to fetch a real-time quote. Try{" "}
          <span className="font-mono">IBM</span> on the demo key.
        </p>
      </header>

      <form onSubmit={onSubmit} className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. IBM"
          aria-label="Stock ticker"
          autoCapitalize="characters"
          className="font-mono uppercase"
        />
        <Button type="submit" disabled={!input.trim() || query.isFetching}>
          {query.isFetching ? "Fetching…" : "Fetch quote"}
        </Button>
      </form>

      <section aria-live="polite">
        {query.isFetching && <QuoteSkeleton />}
        {!query.isFetching && query.isError && (
          <ErrorCard message={query.error?.message ?? "Unknown error."} />
        )}
        {!query.isFetching && query.isSuccess && (
          <QuoteCard quote={query.data} />
        )}
      </section>
    </main>
  );
}

function QuoteCard({ quote }: { quote: StockQuote }) {
  const changeNum = parseFloat(quote.change);
  const positive = changeNum >= 0;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-mono text-2xl">{quote.symbol}</CardTitle>
        <CardDescription>As of {quote.latest_trading_day}</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4 text-sm">
        <Field label="Price" value={`$${quote.price}`} />
        <Field
          label="Change"
          value={`${positive ? "+" : ""}${quote.change} (${quote.change_percent}%)`}
          tone={positive ? "positive" : "negative"}
        />
        <Field label="Open" value={`$${quote.open_price}`} />
        <Field label="Previous close" value={`$${quote.previous_close}`} />
        <Field label="Day high" value={`$${quote.high}`} />
        <Field label="Day low" value={`$${quote.low}`} />
        <Field
          label="Volume"
          value={quote.volume.toLocaleString()}
          colSpan={2}
        />
      </CardContent>
    </Card>
  );
}

function Field({
  label,
  value,
  tone,
  colSpan,
}: {
  label: string;
  value: string;
  tone?: "positive" | "negative";
  colSpan?: 1 | 2;
}) {
  const toneClass =
    tone === "positive"
      ? "text-emerald-500"
      : tone === "negative"
        ? "text-red-500"
        : "";
  return (
    <div className={colSpan === 2 ? "col-span-2" : undefined}>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className={`mt-1 font-mono text-base ${toneClass}`}>{value}</div>
    </div>
  );
}

function QuoteSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-7 w-24" />
        <Skeleton className="mt-2 h-4 w-40" />
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i}>
            <Skeleton className="h-3 w-16" />
            <Skeleton className="mt-2 h-5 w-24" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <Card className="border-destructive/40">
      <CardHeader>
        <CardTitle className="text-destructive">Could not fetch quote</CardTitle>
        <CardDescription>{message}</CardDescription>
      </CardHeader>
    </Card>
  );
}
