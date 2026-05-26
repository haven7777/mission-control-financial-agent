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
import {
  ApiFetchError,
  fetchAnalysis,
  type ClassifiedArticle,
  type DataAgentReport,
  type FinalReport,
  type OverallView,
  type Sentiment,
  type SentimentAgentReport,
} from "@/lib/api";

export default function Home() {
  const [input, setInput] = useState("");
  const [ticker, setTicker] = useState<string | null>(null);

  const query = useQuery<FinalReport, ApiFetchError>({
    queryKey: ["analyze", ticker],
    queryFn: () => fetchAnalysis(ticker!),
    enabled: ticker !== null,
  });

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const next = input.trim().toUpperCase();
    if (next) setTicker(next);
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-6 py-12">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">
          Multi-Agent Financial System
        </h1>
        <p className="text-sm text-muted-foreground">
          Enter a stock ticker. A team of agents fetches price + fundamentals,
          analyzes news sentiment, and synthesizes a balanced brief.
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
          {query.isFetching ? "Analyzing…" : "Analyze"}
        </Button>
      </form>

      <section aria-live="polite" className="flex flex-col gap-4">
        {query.isFetching && <AnalysisSkeleton />}
        {!query.isFetching && query.isError && (
          <ErrorCard message={query.error?.message ?? "Unknown error."} />
        )}
        {!query.isFetching && query.isSuccess && (
          <>
            <SynthesisCard report={query.data} />
            <QuoteStatsCard data={query.data.data_snapshot} />
            <SentimentCard sentiment={query.data.sentiment_snapshot} />
            <ProvenanceFooter report={query.data} />
          </>
        )}
      </section>
    </main>
  );
}

// ----- Synthesis (top-of-page headline) -------------------------------------

const VIEW_TONE: Record<OverallView, { badge: string; ring: string }> = {
  positive: { badge: "bg-emerald-500/15 text-emerald-400", ring: "ring-emerald-500/30" },
  negative: { badge: "bg-red-500/15 text-red-400", ring: "ring-red-500/30" },
  mixed: { badge: "bg-amber-500/15 text-amber-400", ring: "ring-amber-500/30" },
  neutral: { badge: "bg-zinc-500/15 text-zinc-300", ring: "ring-zinc-500/30" },
};

function SynthesisCard({ report }: { report: FinalReport }) {
  const tone = VIEW_TONE[report.overall_view];
  return (
    <Card className={`ring-1 ${tone.ring}`}>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="text-2xl">
              {report.company_name}{" "}
              <span className="font-mono text-base text-muted-foreground">
                ({report.ticker})
              </span>
            </CardTitle>
            <CardDescription className="mt-1">
              {report.one_line_summary}
            </CardDescription>
          </div>
          <span
            className={`shrink-0 rounded-md px-3 py-1 text-xs font-semibold uppercase tracking-wider ${tone.badge}`}
          >
            {report.overall_view}
          </span>
        </div>
      </CardHeader>
      <CardContent className="grid gap-6 md:grid-cols-2">
        <BulletList title="Key strengths" tone="positive" items={report.key_strengths} />
        <BulletList title="Key risks" tone="negative" items={report.key_risks} />
      </CardContent>
    </Card>
  );
}

function BulletList({
  title,
  tone,
  items,
}: {
  title: string;
  tone: "positive" | "negative";
  items: string[];
}) {
  const mark = tone === "positive" ? "text-emerald-400" : "text-red-400";
  return (
    <div>
      <h3 className="mb-2 text-xs uppercase tracking-wider text-muted-foreground">
        {title}
      </h3>
      <ul className="space-y-2 text-sm">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2">
            <span className={`shrink-0 font-mono ${mark}`}>
              {tone === "positive" ? "+" : "−"}
            </span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ----- Quote / fundamentals stats -------------------------------------------

function QuoteStatsCard({ data }: { data: DataAgentReport }) {
  const q = data.quote;
  const o = data.overview;
  const change = parseFloat(q.change);
  const positive = change >= 0;
  const marketCap =
    o.market_capitalization !== null
      ? `$${(o.market_capitalization / 1_000_000_000).toFixed(2)}B`
      : "—";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          Price &amp; fundamentals{" "}
          <span className="text-xs font-normal text-muted-foreground">
            as of {q.latest_trading_day}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Field label="Price" value={`$${q.price}`} />
        <Field
          label="Change"
          value={`${positive ? "+" : ""}${q.change} (${q.change_percent}%)`}
          tone={positive ? "positive" : "negative"}
        />
        <Field label="Day high" value={`$${q.high}`} />
        <Field label="Day low" value={`$${q.low}`} />
        <Field label="Open" value={`$${q.open_price}`} />
        <Field label="Prev close" value={`$${q.previous_close}`} />
        <Field label="Volume" value={q.volume.toLocaleString()} />
        <Field label="Market cap" value={marketCap} />
        {o.pe_ratio && <Field label="P/E" value={o.pe_ratio} />}
        {o.eps && <Field label="EPS" value={`$${o.eps}`} />}
        {o.week_52_high && o.week_52_low && (
          <Field
            label="52-week"
            value={`$${o.week_52_low} – $${o.week_52_high}`}
            colSpan={2}
          />
        )}
        {o.analyst_target_price && (
          <Field label="Analyst target" value={`$${o.analyst_target_price}`} />
        )}
        {o.beta && <Field label="Beta" value={o.beta} />}
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
      ? "text-emerald-400"
      : tone === "negative"
        ? "text-red-400"
        : "";
  return (
    <div className={colSpan === 2 ? "col-span-2" : undefined}>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className={`mt-1 font-mono text-sm ${toneClass}`}>{value}</div>
    </div>
  );
}

// ----- Sentiment articles ---------------------------------------------------

const SENT_TONE: Record<Sentiment, { badge: string }> = {
  bullish: { badge: "bg-emerald-500/15 text-emerald-400" },
  bearish: { badge: "bg-red-500/15 text-red-400" },
  neutral: { badge: "bg-zinc-500/15 text-zinc-300" },
};

function SentimentCard({ sentiment }: { sentiment: SentimentAgentReport }) {
  const overallTone = SENT_TONE[sentiment.overall_sentiment];
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base">News sentiment</CardTitle>
            <CardDescription>
              {sentiment.articles_analyzed} recent articles · query:{" "}
              <span className="font-mono">{sentiment.query}</span>
            </CardDescription>
          </div>
          <span
            className={`shrink-0 rounded-md px-3 py-1 text-xs font-semibold uppercase tracking-wider ${overallTone.badge}`}
          >
            {sentiment.overall_sentiment} · {sentiment.overall_confidence.toFixed(2)}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3 text-sm">
          {sentiment.classified.map((ca, i) => (
            <ClassifiedRow key={i} index={i + 1} article={ca} />
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function ClassifiedRow({
  index,
  article,
}: {
  index: number;
  article: ClassifiedArticle;
}) {
  const tone = SENT_TONE[article.sentiment];
  return (
    <li className="border-l-2 border-border pl-3">
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">[{index}]</span>
        <span
          className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${tone.badge}`}
        >
          {article.sentiment} · {article.confidence.toFixed(2)}
        </span>
        <a
          href={article.article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="truncate text-sm hover:underline"
        >
          {article.article.title}
        </a>
      </div>
      <div className="ml-12 mt-1 text-xs text-muted-foreground">{article.reason}</div>
    </li>
  );
}

// ----- Footer / loading / error ---------------------------------------------

function ProvenanceFooter({ report }: { report: FinalReport }) {
  return (
    <p className="text-center text-xs text-muted-foreground">
      Synthesized by{" "}
      <span className="font-mono">{report.model_used}</span> ·{" "}
      {new Date(report.generated_at).toLocaleString()}
    </p>
  );
}

function AnalysisSkeleton() {
  return (
    <>
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-64" />
          <Skeleton className="mt-2 h-4 w-96" />
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 2 }).map((_, c) => (
            <div key={c}>
              <Skeleton className="mb-2 h-3 w-20" />
              {Array.from({ length: 3 }).map((_, r) => (
                <Skeleton key={r} className="mb-1 h-4 w-full" />
              ))}
            </div>
          ))}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-48" />
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i}>
              <Skeleton className="h-3 w-14" />
              <Skeleton className="mt-1 h-4 w-20" />
            </div>
          ))}
        </CardContent>
      </Card>
    </>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <Card className="border-destructive/40">
      <CardHeader>
        <CardTitle className="text-destructive">Could not analyze</CardTitle>
        <CardDescription>{message}</CardDescription>
      </CardHeader>
    </Card>
  );
}
