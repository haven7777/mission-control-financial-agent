"use client"

import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"
import type { DataAgentReport, SentimentAgentReport } from "@/lib/api"

// ---------- formatting helpers ----------

function formatMarketCap(mc: number | null): string {
  if (mc === null) return "—"
  if (mc >= 1e12) return `$${(mc / 1e12).toFixed(2)}T`
  if (mc >= 1e9)  return `$${(mc / 1e9).toFixed(2)}B`
  return `$${(mc / 1e6).toFixed(0)}M`
}

function formatVolume(v: number): string {
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`
  if (v >= 1e3) return `${(v / 1e3).toFixed(0)}K`
  return String(v)
}

function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "")
  } catch {
    return "Source"
  }
}

// ---------- props ----------

interface EvidencePanelProps {
  data: DataAgentReport
  sentiment: SentimentAgentReport
  showOnly?: "market" | "news"
}

export function EvidencePanel({ data, sentiment, showOnly }: EvidencePanelProps) {
  const q = data.quote
  const o = data.overview

  const price         = parseFloat(q.price)
  const change        = parseFloat(q.change)
  const changePercent = parseFloat(q.change_percent)
  const isPositive    = change >= 0

  const marketRows = [
    { label: "Market Cap", value: formatMarketCap(o.market_capitalization) },
    { label: "P/E Ratio",  value: o.pe_ratio ?? "—" },
    { label: "Volume",     value: formatVolume(q.volume) },
    { label: "Avg Volume", value: "N/A" },
    { label: "52W High",   value: o.week_52_high ? `$${o.week_52_high}` : "—" },
    { label: "52W Low",    value: o.week_52_low  ? `$${o.week_52_low}`  : "—" },
    { label: "EPS",        value: o.eps ? `$${o.eps}` : "—" },
    { label: "Dividend",   value: o.dividend_yield ? `${o.dividend_yield}%` : "—" },
  ]

  const newsItems = sentiment.classified.map((ca) => ({
    title:     ca.article.title,
    source:    extractDomain(ca.article.url),
    sentiment: ca.sentiment === "bullish" ? "Bullish" : ca.sentiment === "bearish" ? "Bearish" : "Neutral",
    reasoning: ca.reason,
    time:      ca.article.published_date ?? "Live",
  }))

  const getSentimentColor = (s: string) => {
    if (s === "Bullish") return "bg-success/20 text-success border-success/30"
    if (s === "Bearish") return "bg-destructive/20 text-destructive border-destructive/30"
    return "bg-muted text-muted-foreground border-muted-foreground/30"
  }

  const getSentimentIcon = (s: string) => {
    if (s === "Bullish") return <TrendingUp className="w-3 h-3" />
    if (s === "Bearish") return <TrendingDown className="w-3 h-3" />
    return <Minus className="w-3 h-3" />
  }

  // ---------- market-only ----------
  if (showOnly === "market") {
    return (
      <div className="h-full flex flex-col overflow-hidden">
        <div className="flex-1 overflow-auto space-y-5">
          <div className="flex items-end justify-between pb-4 border-b border-border/50">
            <div>
              <p className="text-3xl font-mono font-bold">${price.toFixed(2)}</p>
              <div className={cn("flex items-center gap-1 mt-1", isPositive ? "text-success" : "text-destructive")}>
                {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                <span className="font-semibold">
                  {isPositive ? "+" : ""}{change.toFixed(2)} ({isPositive ? "+" : ""}{changePercent.toFixed(2)}%)
                </span>
              </div>
            </div>
            <Badge variant="outline" className="text-xs border-border/50">Real-time</Badge>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {marketRows.map((r) => <MetricItem key={r.label} label={r.label} value={r.value} />)}
          </div>
        </div>
      </div>
    )
  }

  // ---------- news-only ----------
  if (showOnly === "news") {
    return (
      <ScrollArea className="h-full">
        <div className="space-y-4">
          {newsItems.map((item, i) => (
            <NewsCard key={i} item={item} getSentimentColor={getSentimentColor} getSentimentIcon={getSentimentIcon} />
          ))}
        </div>
      </ScrollArea>
    )
  }

  // ---------- combined ----------
  return (
    <div className="grid grid-cols-2 gap-6 h-full">
      <div className="flex flex-col rounded-xl border border-border/50 bg-card/50 overflow-hidden">
        <div className="px-5 py-3 border-b border-border/50 bg-muted/20">
          <h3 className="text-sm font-semibold text-muted-foreground">Market Data</h3>
        </div>
        <div className="p-5 space-y-5">
          <div className="flex items-end justify-between pb-4 border-b border-border/50">
            <div>
              <p className="text-3xl font-mono font-bold">${price.toFixed(2)}</p>
              <div className={cn("flex items-center gap-1 mt-1", isPositive ? "text-success" : "text-destructive")}>
                {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                <span className="font-semibold">
                  {isPositive ? "+" : ""}{change.toFixed(2)} ({isPositive ? "+" : ""}{changePercent.toFixed(2)}%)
                </span>
              </div>
            </div>
            <Badge variant="outline" className="text-xs border-border/50">Real-time</Badge>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {marketRows.map((r) => <MetricItem key={r.label} label={r.label} value={r.value} />)}
          </div>
        </div>
      </div>

      <div className="flex flex-col rounded-xl border border-border/50 bg-card/50 overflow-hidden">
        <div className="px-5 py-3 border-b border-border/50 bg-muted/20">
          <h3 className="text-sm font-semibold text-muted-foreground">News & Sentiment</h3>
        </div>
        <ScrollArea className="flex-1 p-5">
          <div className="space-y-4">
            {newsItems.map((item, i) => (
              <NewsCard key={i} item={item} getSentimentColor={getSentimentColor} getSentimentIcon={getSentimentIcon} />
            ))}
          </div>
        </ScrollArea>
      </div>
    </div>
  )
}

function MetricItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-3 rounded-lg bg-muted/20">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className="font-mono font-semibold">{value}</p>
    </div>
  )
}

function NewsCard({
  item,
  getSentimentColor,
  getSentimentIcon,
}: {
  item: { title: string; source: string; sentiment: string; reasoning: string; time: string }
  getSentimentColor: (s: string) => string
  getSentimentIcon: (s: string) => React.ReactNode
}) {
  return (
    <div className="p-4 rounded-lg bg-muted/10 border border-border/30 hover:bg-muted/20 transition-colors">
      <div className="flex items-start justify-between gap-3 mb-2">
        <h4 className="text-sm font-medium leading-tight flex-1">{item.title}</h4>
        <Badge variant="outline" className={cn("text-[10px] shrink-0 flex items-center gap-1", getSentimentColor(item.sentiment))}>
          {getSentimentIcon(item.sentiment)}
          {item.sentiment}
        </Badge>
      </div>
      <p className="text-xs text-muted-foreground italic mb-3 leading-relaxed">&ldquo;{item.reasoning}&rdquo;</p>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{item.source}</span>
        <span>{item.time}</span>
      </div>
    </div>
  )
}
