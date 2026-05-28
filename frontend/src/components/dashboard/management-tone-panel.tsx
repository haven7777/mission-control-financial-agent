"use client"

import { Mic, AlertTriangle, ChevronRight } from "lucide-react"
import type { TranscriptContext } from "@/lib/api"

const TONE_STYLES: Record<TranscriptContext["executive_tone"], { label: string; className: string }> = {
  confident:  { label: "Confident",  className: "bg-success/10 text-success border-success/30" },
  cautious:   { label: "Cautious",   className: "bg-warning/10 text-warning border-warning/30" },
  defensive:  { label: "Defensive",  className: "bg-destructive/10 text-destructive border-destructive/30" },
  neutral:    { label: "Neutral",    className: "bg-muted/50 text-muted-foreground border-border/50" },
}

const SENTIMENT_STYLES: Record<TranscriptContext["management_sentiment"], { label: string; className: string }> = {
  positive: { label: "Positive",          className: "text-success" },
  neutral:  { label: "Neutral",           className: "text-muted-foreground" },
  negative: { label: "Cautious/Negative", className: "text-destructive" },
}

interface ManagementTonePanelProps {
  ctx: TranscriptContext
}

export function ManagementTonePanel({ ctx }: ManagementTonePanelProps) {
  if (ctx.is_empty) return null

  const tone = TONE_STYLES[ctx.executive_tone]
  const sentiment = SENTIMENT_STYLES[ctx.management_sentiment]

  return (
    <div className="space-y-6">
      {/* Tone + Sentiment badges */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-semibold ${tone.className}`}>
          <Mic className="w-3.5 h-3.5" />
          {tone.label} Tone
        </div>
        <span className={`text-sm font-medium ${sentiment.className}`}>
          Management Sentiment: {sentiment.label}
        </span>
        <span className="text-xs text-muted-foreground ml-auto font-mono">
          Q{ctx.quarter} {ctx.year}{ctx.date ? ` · ${ctx.date.slice(0, 10)}` : ""}
        </span>
      </div>

      {/* Forward-looking statements */}
      {ctx.key_forward_statements.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Forward-Looking Guidance
          </h4>
          <ul className="space-y-2">
            {ctx.key_forward_statements.map((stmt, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-foreground/90">
                <ChevronRight className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                <span className="leading-relaxed">{stmt}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Dodged questions */}
      {ctx.dodged_questions.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-warning" />
            Analyst Questions — Evasive Responses Detected ({ctx.dodged_questions.length})
          </h4>
          <div className="space-y-4">
            {ctx.dodged_questions.map((dq, i) => (
              <div key={i} className="rounded-xl border border-warning/20 bg-warning/5 p-4 space-y-2">
                <p className="text-sm font-medium text-foreground">
                  <span className="text-muted-foreground">Q:</span> {dq.analyst_question}
                </p>
                <p className="text-sm text-foreground/80 italic pl-4 border-l-2 border-border/40">
                  &ldquo;{dq.management_response}&rdquo;
                </p>
                {dq.evasion_signal.length > 0 && (
                  <p className="text-xs text-warning/90">
                    <span className="font-semibold">Evasion signal:</span> {dq.evasion_signal}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
