"use client";

import { useEffect, useRef, useState } from "react";

import { DashboardHeader } from "@/components/dashboard/header";
import { AgentTerminal, type AgentEvent, type AgentEventStatus } from "@/components/dashboard/agent-terminal";
import { ResultsDashboard } from "@/components/dashboard/results-dashboard";
import { SearchHome } from "@/components/search/search-home";
import { LoadingSkeleton } from "@/components/search/loading-skeleton";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Terminal } from "lucide-react";
import {
  streamAnalysis,
  type FinalReport,
  type ProgressPayload,
  type ProgressStage,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Streaming hook
// ---------------------------------------------------------------------------

type StreamStatus = "idle" | "streaming" | "done" | "error";

interface StreamState {
  status: StreamStatus;
  stages: ProgressPayload[];
  report: FinalReport | null;
  error: string | null;
}

function useAnalysisStream(ticker: string | null): StreamState {
  const [state, setState] = useState<StreamState>({
    status: "idle",
    stages: [],
    report: null,
    error: null,
  });

  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    cleanupRef.current?.();
    cleanupRef.current = null;

    if (!ticker) {
      setState({ status: "idle", stages: [], report: null, error: null });
      return;
    }

    setState({ status: "streaming", stages: [], report: null, error: null });

    const cleanup = streamAnalysis(ticker, (event) => {
      if (event.type === "progress") {
        setState((prev) => ({ ...prev, stages: [...prev.stages, event.data] }));
      } else if (event.type === "result") {
        setState((prev) => ({ ...prev, status: "done", report: event.data }));
      } else {
        setState((prev) => ({ ...prev, status: "error", error: event.data.message }));
      }
    });

    cleanupRef.current = cleanup;
    return () => {
      cleanup();
      cleanupRef.current = null;
    };
  }, [ticker]);

  return state;
}

// ---------------------------------------------------------------------------
// Helpers: convert SSE stages → AgentTerminal events
// ---------------------------------------------------------------------------

const STAGE_AGENT: Record<ProgressStage, string> = {
  cache_hit:             "Report Cache",
  cache_miss:            "Report Cache",
  started:               "System",
  filings_fetching:      "SEC Filings",
  filings_complete:      "SEC Filings",
  filings_unavailable:   "SEC Filings",
  data_complete:         "Data Agent",
  sentiment_complete:    "Sentiment Agent",
  sentiment_unavailable: "Sentiment Agent",
  debating:              "Debate Agents",
  debate_complete:       "Debate Agents",
  debate_skipped:        "Debate Agents",
  synthesizing:          "Manager Agent",
  critiquing:            "Critic Agent",
  revising:              "Critic Agent",
  approved:              "Critic Agent",
};

const STAGE_STATUS: Record<ProgressStage, AgentEventStatus> = {
  cache_hit:             "approved",
  cache_miss:            "running",
  started:               "running",
  filings_fetching:      "running",
  filings_complete:      "approved",
  filings_unavailable:   "approved",
  data_complete:         "done",
  sentiment_complete:    "done",
  sentiment_unavailable: "done",
  debating:              "running",
  debate_complete:       "done",
  debate_skipped:        "done",
  synthesizing:          "running",
  critiquing:            "running",
  revising:              "conflict",
  approved:              "approved",
};

function stagesToEvents(stages: ProgressPayload[]): AgentEvent[] {
  return stages.map((s, i) => {
    const isLast = i === stages.length - 1;
    const status = STAGE_STATUS[s.stage];
    return {
      id:        `stage-${i}`,
      agent:     STAGE_AGENT[s.stage],
      message:   s.message,
      // A "running" event that isn't the last has since completed — show it as done.
      status:    status === "running" && !isLast ? "done" : status,
      timestamp: new Date(),
    };
  });
}

function parseConfidence(stages: ProgressPayload[]): number {
  const msg = stages.find((s) => s.stage === "approved")?.message ?? "";
  return parseInt(msg.match(/confidence (\d+)%/)?.[1] ?? "0", 10);
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function Home() {
  const [ticker, setTicker] = useState<string | null>(null);
  const [terminalOpen, setTerminalOpen] = useState(false);

  const { status, stages, report, error } = useAnalysisStream(ticker);

  function handleSearch(query: string) {
    // Category clicks pass comma-separated tickers — take only the first
    const first = query.split(",")[0].trim().toUpperCase();
    if (!first) return;
    setTicker(first);
  }

  // ── Results ───────────────────────────────────────────────────────────────
  if (status === "done" && report && ticker) {
    return (
      <ResultsDashboard
        ticker={ticker}
        report={report}
        terminalEvents={stagesToEvents(stages)}
        confidence={parseConfidence(stages)}
        onBack={() => setTicker(null)}
      />
    );
  }

  // ── Loading ───────────────────────────────────────────────────────────────
  if (status === "streaming" && ticker) {
    return (
      <div className="h-screen flex flex-col bg-background">
        <DashboardHeader query={ticker} onBack={() => setTicker(null)} status="processing">
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
                  <AgentTerminal events={stagesToEvents(stages)} />
                </div>
              </ScrollArea>
            </SheetContent>
          </Sheet>
        </DashboardHeader>
        <div className="flex-1 overflow-auto">
          <LoadingSkeleton query={ticker} complete={stages.some((s) => s.stage === "approved")} />
        </div>
      </div>
    );
  }

  // ── Search (idle + error) ─────────────────────────────────────────────────
  return (
    <>
      {status === "error" && error && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-sm max-w-md text-center">
          {error}
        </div>
      )}
      <SearchHome onSearch={handleSearch} />
    </>
  );
}
