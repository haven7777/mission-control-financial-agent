"use client"

import { TrendingUp, TrendingDown } from "lucide-react"
import type { BullCase, BearCase } from "@/lib/api"

interface DebatePanelProps {
  bull_case: BullCase
  bear_case: BearCase
}

export function DebatePanel({ bull_case, bear_case }: DebatePanelProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Bull Case */}
      <div className="p-6 rounded-2xl bg-success/5 border border-success/20">
        <h3 className="flex items-center gap-3 text-base font-semibold text-success mb-4">
          <TrendingUp className="w-5 h-5" />
          Bull Case
        </h3>
        <p className="text-sm text-foreground/80 leading-relaxed mb-5 italic">
          &ldquo;{bull_case.thesis}&rdquo;
        </p>
        <ul className="space-y-3">
          {bull_case.key_arguments.map((arg) => (
            <li key={arg} className="flex items-start gap-3 text-sm text-foreground/90">
              <span className="text-success font-bold mt-0.5 shrink-0">+</span>
              <span className="leading-relaxed">{arg}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Bear Case */}
      <div className="p-6 rounded-2xl bg-destructive/5 border border-destructive/20">
        <h3 className="flex items-center gap-3 text-base font-semibold text-destructive mb-4">
          <TrendingDown className="w-5 h-5" />
          Bear Case
        </h3>
        <p className="text-sm text-foreground/80 leading-relaxed mb-5 italic">
          &ldquo;{bear_case.thesis}&rdquo;
        </p>
        <ul className="space-y-3">
          {bear_case.key_arguments.map((arg) => (
            <li key={arg} className="flex items-start gap-3 text-sm text-foreground/90">
              <span className="text-destructive font-bold mt-0.5 shrink-0">−</span>
              <span className="leading-relaxed">{arg}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
