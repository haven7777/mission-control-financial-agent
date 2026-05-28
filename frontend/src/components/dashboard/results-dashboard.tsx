"use client"

import { useState } from "react"
import { DashboardHeader } from "@/components/dashboard/header"
import { AgentTerminal, type AgentEvent } from "@/components/dashboard/agent-terminal"
import { SynthesisConsole } from "@/components/dashboard/synthesis-console"
import { EvidencePanel } from "@/components/dashboard/evidence-panel"
import { DebatePanel } from "@/components/dashboard/debate-panel"
import { ManagementTonePanel } from "@/components/dashboard/management-tone-panel"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { Terminal, Mic } from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { FinalReport } from "@/lib/api"

interface ResultsDashboardProps {
  ticker: string
  report: FinalReport
  terminalEvents: AgentEvent[]
  confidence: number
  onBack: () => void
}

export function ResultsDashboard({ ticker, report, terminalEvents, confidence, onBack }: ResultsDashboardProps) {
  const [terminalOpen, setTerminalOpen] = useState(false)

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header with Under the Hood button */}
      <DashboardHeader query={ticker} onBack={onBack} status="approved">
        <Sheet open={terminalOpen} onOpenChange={setTerminalOpen}>
          <SheetTrigger className="flex items-center gap-2 px-4 py-2 rounded-lg bg-muted/50 hover:bg-muted transition-colors text-sm font-medium border border-border/50">
            <Terminal className="w-4 h-4 text-primary" />
            <span>Under the Hood</span>
          </SheetTrigger>
          <SheetContent side="right" className="w-[480px] sm:w-[540px] p-0 bg-[#0a0f14] border-l border-border/50">
            <SheetHeader className="px-6 py-4 border-b border-border/30">
              <SheetTitle className="flex items-center gap-3 text-foreground">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Agent Terminal
              </SheetTitle>
            </SheetHeader>
            <ScrollArea className="h-[calc(100vh-80px)]">
              <div className="p-4">
                <AgentTerminal events={terminalEvents} />
              </div>
            </ScrollArea>
          </SheetContent>
        </Sheet>
      </DashboardHeader>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto px-8 py-10 space-y-10">

          {/* Hero: Synthesis Console */}
          <section>
            <div className="p-8 rounded-2xl border-2 border-primary/20 bg-card shadow-xl shadow-primary/5">
              <div className="flex items-center gap-3 mb-8">
                <div className="w-3 h-3 rounded-full bg-primary animate-pulse" />
                <h2 className="text-xl font-semibold">Synthesis Console</h2>
                <span className="text-sm text-muted-foreground ml-auto font-mono bg-muted/50 px-4 py-1.5 rounded-lg">
                  {ticker.toUpperCase()}
                </span>
              </div>
              <SynthesisConsole report={report} confidence={confidence} />
            </div>
          </section>

          {/* AI Debate: Bull vs. Bear */}
          {report.bull_case && report.bear_case && (
            <section>
              <div className="p-8 rounded-2xl border border-border/30 bg-card/80">
                <div className="flex items-center gap-3 mb-8">
                  <div className="w-3 h-3 rounded-full bg-warning" />
                  <h2 className="text-xl font-semibold">AI Debate: Bull vs. Bear</h2>
                </div>
                <DebatePanel bull_case={report.bull_case} bear_case={report.bear_case} />
              </div>
            </section>
          )}

          {/* Earnings Call: Management Tone */}
          {report.transcript_context && !report.transcript_context.is_empty && (
            <section>
              <div className="p-8 rounded-2xl border border-border/30 bg-card/80">
                <div className="flex items-center gap-3 mb-8">
                  <div className="w-3 h-3 rounded-full bg-agent-transcript" />
                  <h2 className="text-xl font-semibold">Management Tone Analysis</h2>
                  <span className="text-xs text-muted-foreground ml-2 font-mono bg-muted/50 px-3 py-1 rounded-lg">
                    Earnings Call
                  </span>
                </div>
                <ManagementTonePanel ctx={report.transcript_context} />
              </div>
            </section>
          )}

          {/* Supporting Data: Market & News */}
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="p-6 rounded-xl border border-border/30 bg-card/50">
              <div className="flex items-center gap-2 mb-6">
                <div className="w-2 h-2 rounded-full bg-emerald-500/70" />
                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Market Data</h3>
              </div>
              <EvidencePanel data={report.data_snapshot} sentiment={report.sentiment_snapshot} showOnly="market" />
            </div>

            <div className="p-6 rounded-xl border border-border/30 bg-card/50">
              <div className="flex items-center gap-2 mb-6">
                <div className="w-2 h-2 rounded-full bg-amber-500/70" />
                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">News & Sentiment</h3>
              </div>
              <div className="h-[400px]">
                <EvidencePanel data={report.data_snapshot} sentiment={report.sentiment_snapshot} showOnly="news" />
              </div>
            </div>
          </section>

        </div>
      </div>
    </div>
  )
}
