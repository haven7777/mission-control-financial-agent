"use client"

import { useEffect, useState } from "react"
import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, Minus, CheckCircle2, AlertTriangle, Activity } from "lucide-react"
import type { FinalReport, OverallView } from "@/lib/api"

type DisplaySentiment = "BULLISH" | "BEARISH" | "MIXED"

function toDisplaySentiment(view: OverallView): DisplaySentiment {
  if (view === "positive") return "BULLISH"
  if (view === "negative") return "BEARISH"
  return "MIXED"
}

interface SynthesisConsoleProps {
  report: FinalReport
  confidence: number
}

export function SynthesisConsole({ report, confidence }: SynthesisConsoleProps) {
  const [animatedConfidence, setAnimatedConfidence] = useState(0)
  const sentiment = toDisplaySentiment(report.overall_view)

  useEffect(() => {
    setAnimatedConfidence(0)
    const duration = 1500
    const steps = 60
    const increment = confidence / steps
    let current = 0
    const interval = setInterval(() => {
      current += increment
      if (current >= confidence) {
        setAnimatedConfidence(confidence)
        clearInterval(interval)
      } else {
        setAnimatedConfidence(Math.floor(current))
      }
    }, duration / steps)
    return () => clearInterval(interval)
  }, [confidence])

  const getSentimentIcon = () => {
    switch (sentiment) {
      case "BULLISH": return <TrendingUp className="w-6 h-6" />
      case "BEARISH": return <TrendingDown className="w-6 h-6" />
      case "MIXED":   return <Minus className="w-6 h-6" />
    }
  }

  const getSentimentColor = () => {
    switch (sentiment) {
      case "BULLISH": return "bg-success/20 text-success border-success/30"
      case "BEARISH": return "bg-destructive/20 text-destructive border-destructive/30"
      case "MIXED":   return "bg-warning/20 text-warning border-warning/30"
    }
  }

  return (
    <div className="space-y-10">
      {/* Top Row: Sentiment Badge + Confidence Gauge + Summary */}
      <div className="flex flex-wrap items-start gap-8">
        {/* Sentiment Badge */}
        <div className={cn("flex items-center gap-5 px-8 py-6 rounded-2xl border-2 shrink-0", getSentimentColor())}>
          {getSentimentIcon()}
          <div>
            <p className="text-xs uppercase tracking-wider opacity-80 mb-1">Overall Sentiment</p>
            <p className="text-3xl font-bold tracking-tight">{sentiment}</p>
          </div>
        </div>

        {/* Confidence Gauge */}
        <div className="relative flex items-center justify-center shrink-0">
          <svg className="w-36 h-36 -rotate-90">
            <circle cx="72" cy="72" r="60" fill="none" stroke="currentColor" strokeWidth="10" className="text-muted/20" />
            <circle
              cx="72" cy="72" r="60" fill="none" stroke="currentColor" strokeWidth="10" strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 60}
              strokeDashoffset={2 * Math.PI * 60 - (animatedConfidence / 100) * 2 * Math.PI * 60}
              className={cn(
                "transition-all duration-300",
                animatedConfidence >= 75 ? "text-success" : animatedConfidence >= 50 ? "text-warning" : "text-destructive"
              )}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-4xl font-mono font-bold">{animatedConfidence}%</span>
            <span className="text-sm text-muted-foreground mt-1">Confidence</span>
          </div>
        </div>

        {/* Executive Summary */}
        <div className="flex-1 min-w-[300px] p-6 rounded-2xl bg-muted/10 border border-border/30">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-primary" />
            <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Executive Summary</span>
          </div>
          <p className="text-foreground text-lg leading-relaxed">{report.one_line_summary}</p>
        </div>
      </div>

      {/* Strengths & Risks Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="p-6 rounded-2xl bg-success/5 border border-success/20">
          <h3 className="flex items-center gap-3 text-base font-semibold text-success mb-5">
            <CheckCircle2 className="w-5 h-5" />
            Key Strengths
          </h3>
          <ul className="space-y-4">
            {report.key_strengths.map((s, i) => (
              <li key={i} className="flex items-start gap-4 text-foreground/90">
                <span className="text-success font-bold text-lg mt-0.5 shrink-0">+</span>
                <span className="leading-relaxed">{s}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="p-6 rounded-2xl bg-destructive/5 border border-destructive/20">
          <h3 className="flex items-center gap-3 text-base font-semibold text-destructive mb-5">
            <AlertTriangle className="w-5 h-5" />
            Key Risks
          </h3>
          <ul className="space-y-4">
            {report.key_risks.map((r, i) => (
              <li key={i} className="flex items-start gap-4 text-foreground/90">
                <span className="text-destructive font-bold text-lg mt-0.5 shrink-0">-</span>
                <span className="leading-relaxed">{r}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
