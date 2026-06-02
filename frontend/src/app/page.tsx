"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { DashboardHeader } from "@/components/dashboard/header";
import { AgentTerminal, type AgentEvent, type AgentEventStatus } from "@/components/dashboard/agent-terminal";
import { ResultsDashboard } from "@/components/dashboard/results-dashboard";
import { StreamErrorCard } from "@/components/dashboard/stream-error-card";
import { SearchHome, type ResearchMode } from "@/components/search/search-home";
import { MasterCodeDialog } from "@/components/search/master-code-dialog";
import { PaywallModal } from "@/components/search/paywall-modal";
import { useCredits } from "@/hooks/use-credits";
import { LoadingSkeleton } from "@/components/search/loading-skeleton";
import { FastLoading } from "@/components/search/fast-loading";
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
  fetchAnalysis,
  sanitizeError,
  type FinalReport,
  type ProgressPayload,
  type ProgressStage,
} from "@/lib/api";
import { getMasterCode, setMasterCode } from "@/lib/auth";
import { useLabourIllusion } from "@/hooks/use-labour-illusion";

// ---------------------------------------------------------------------------
// Streaming hook
// ---------------------------------------------------------------------------

type StreamStatus = "idle" | "streaming" | "done" | "error";

interface StreamState {
  status: StreamStatus;
  stages: ProgressPayload[];
  report: FinalReport | null;
  error: string | null;
  isTickerNotFound: boolean;
  retry: () => void;
}

function useAnalysisStream(ticker: string | null, masterCode: string | null): StreamState {
  const [state, setState] = useState<Omit<StreamState, "retry">>({
    status: "idle",
    stages: [],
    report: null,
    error: null,
    isTickerNotFound: false,
  });

  // Bumping `retryNonce` re-runs the effect with the same ticker — that's how
  // "Try Again" re-triggers the analysis without the user re-typing.
  const [retryNonce, setRetryNonce] = useState(0);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    cleanupRef.current?.();
    cleanupRef.current = null;

    if (!ticker) {
      setState({ status: "idle", stages: [], report: null, error: null, isTickerNotFound: false });
      return;
    }

    setState({ status: "streaming", stages: [], report: null, error: null, isTickerNotFound: false });

    const cleanup = streamAnalysis(ticker, (event) => {
      if (event.type === "progress") {
        setState((prev) => ({ ...prev, stages: [...prev.stages, event.data] }));
      } else if (event.type === "result") {
        setState((prev) => ({ ...prev, status: "done", report: event.data }));
      } else {
        // Both "stream_error" (server-side) and "connection_error" (network
        // drop) land here. The hook treats them identically — the consumer
        // shows the recovery card and lets the user retry.
        const raw = event.data.message ?? "";
        const code = event.type === "stream_error" ? (event.data.code ?? "") : "";
        const isTickerNotFound = code === "ticker_not_found";
        const clean = raw.includes("Connection interrupted")
          ? "The connection was interrupted. Please try again."
          : isTickerNotFound
          ? "Ticker not found. Please check the symbol and try again."
          : "Analysis failed. Please try again.";
        setState((prev) => ({ ...prev, status: "error", error: clean, isTickerNotFound }));
      }
    }, masterCode);

    cleanupRef.current = cleanup;
    return () => {
      cleanup();
      cleanupRef.current = null;
    };
  }, [ticker, masterCode, retryNonce]);

  const retry = useCallback(() => setRetryNonce((n) => n + 1), []);

  return { ...state, retry };
}

// ---------------------------------------------------------------------------
// Fast analysis hook (sync fetch, no auth)
// ---------------------------------------------------------------------------

function useFastAnalysis(ticker: string | null): {
  status: "idle" | "loading" | "done" | "error";
  report: FinalReport | null;
  error: string | null;
  retry: () => void;
} {
  const [state, setState] = useState<{
    status: "idle" | "loading" | "done" | "error";
    report: FinalReport | null;
    error: string | null;
  }>({ status: "idle", report: null, error: null });
  const [retryNonce, setRetryNonce] = useState(0);

  useEffect(() => {
    if (!ticker) {
      setState({ status: "idle", report: null, error: null });
      return;
    }
    let cancelled = false;
    setState({ status: "loading", report: null, error: null });
    const minDelay = new Promise<void>((res) =>
      setTimeout(res, 2500 + Math.random() * 1000)
    );
    // Errors bypass minDelay so invalid tickers surface immediately.
    fetchAnalysis(ticker)
      .then(async (report) => {
        await minDelay;
        if (!cancelled) setState({ status: "done", report, error: null });
      })
      .catch((err: unknown) => {
        if (!cancelled) setState({ status: "error", report: null, error: sanitizeError(err) });
      });
    return () => { cancelled = true; };
  }, [ticker, retryNonce]);

  const retry = useCallback(() => setRetryNonce((n) => n + 1), []);
  return { ...state, retry };
}

// ---------------------------------------------------------------------------
// Helpers: convert SSE stages → AgentTerminal events
// ---------------------------------------------------------------------------

const STAGE_AGENT: Record<ProgressStage, string> = {
  cache_hit:             "Report Cache",
  cache_miss:            "Report Cache",
  delta_refreshing:      "Report Cache",
  delta_complete:        "Report Cache",
  started:               "System",
  filings_fetching:       "SEC Filings",
  filings_complete:       "SEC Filings",
  filings_unavailable:    "SEC Filings",
  transcript_fetching:    "Transcript Agent",
  transcript_complete:    "Transcript Agent",
  transcript_unavailable: "Transcript Agent",
  data_complete:          "Data Agent",
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
  delta_refreshing:      "running",
  delta_complete:        "approved",
  started:               "running",
  filings_fetching:       "running",
  filings_complete:       "approved",
  filings_unavailable:    "approved",
  transcript_fetching:    "running",
  transcript_complete:    "approved",
  transcript_unavailable: "approved",
  data_complete:          "done",
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

function parseConfidence(stages: ProgressPayload[], report: FinalReport | null): number {
  const msg = stages.find((s) => s.stage === "approved")?.message ?? "";
  const fromStage = parseInt(msg.match(/confidence (\d+)%/)?.[1] ?? "0", 10);
  if (fromStage > 0) return fromStage;
  const fromSentiment = report?.sentiment_snapshot?.overall_confidence;
  return fromSentiment ? Math.round(fromSentiment * 100) : 0;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function Home() {
  const [ticker, setTicker] = useState<string | null>(null);
  const [terminalOpen, setTerminalOpen] = useState(false);
  const [mode, setMode] = useState<ResearchMode>("deep");
  const [masterCode, setMasterCodeState] = useState<string | null>(() => getMasterCode());
  const [showCodeDialog, setShowCodeDialog] = useState(false);
  const [showPaywallModal, setShowPaywallModal] = useState(false);
  const [pendingTicker, setPendingTicker] = useState<string | null>(null);

  const { credits, consumeCredit, refundCredit, addCredits, isVipCodeUsed, markVipCodeUsed, hasRedeemedBonus } = useCredits();

  // Deep mode: SSE stream with auth + Labor Illusion
  const deepTicker = mode === "deep" && ticker && !ticker.startsWith("__PENDING__") ? ticker : null;
  const streamState = useAnalysisStream(deepTicker, masterCode);

  // Refund the credit when deep mode fails on an invalid ticker.
  // Guard with a ref so we refund at most once per handleSearch call, not on retries.
  const creditRefundedRef = useRef(false);
  useEffect(() => {
    creditRefundedRef.current = false;
  }, [ticker]);
  useEffect(() => {
    if (
      mode === "deep" &&
      streamState.status === "error" &&
      streamState.isTickerNotFound &&
      !creditRefundedRef.current
    ) {
      creditRefundedRef.current = true;
      refundCredit();
    }
  }, [mode, streamState.status, streamState.isTickerNotFound, refundCredit]);

  // Fast mode: sync fetch, no auth, no illusion
  const fastTicker = mode === "fast" && ticker && !ticker.startsWith("__PENDING__") ? ticker : null;
  const fastState = useFastAnalysis(fastTicker);

  // Unified view
  const status = mode === "deep" ? streamState.status : fastState.status;
  const report = mode === "deep" ? streamState.report : fastState.report;
  const stages = mode === "deep" ? streamState.stages : [];
  const error = mode === "deep" ? streamState.error : fastState.error;

  // Labor Illusion runs only in Deep mode. Uses a unified 20s floor for both
  // cached and uncached searches — the reveal happens at max(realBackend, 20s).
  const isActive = mode === "deep" && (
    status === "streaming" ||
    status === "done" ||
    (status === "error" && report !== null)
  );
  const { revealedReport, illusionMessage } = useLabourIllusion(
    report,
    isActive,
    ticker,
  );

  // Fast mode shows report immediately; Deep mode holds until illusion elapses
  const displayReport = mode === "fast" ? report : revealedReport;

  const handleSearch = useCallback((query: string) => {
    const first = query.split(",")[0].trim().toUpperCase();
    if (!first) return;

    // Fast mode is always free — no credit checks, no paywall.
    if (mode === "fast") {
      setTicker(first);
      return;
    }

    // Deep mode: credit gate only.
    if (credits <= 0) {
      setPendingTicker(first);
      setShowPaywallModal(true);
      return;
    }

    consumeCredit();
    setTicker(first);
  }, [mode, credits, consumeCredit]);

  const handleModeChange = useCallback((newMode: ResearchMode) => {
    setMode(newMode);
    setTicker(null);
  }, []);

  const handleCodeSuccess = useCallback((code: string) => {
    setMasterCodeState(code);
    setMasterCode(code);
    setShowCodeDialog(false);
    setTicker((prev) =>
      prev?.startsWith("__PENDING__") ? prev.replace("__PENDING__", "") : prev
    );
  }, []);

  function handleVipSuccess(code: string, newCredits: number) {
    markVipCodeUsed(code);
    addCredits(newCredits);
    consumeCredit();
    setMasterCodeState(code);
    setMasterCode(code);
    setShowPaywallModal(false);
    if (pendingTicker) {
      setTicker(pendingTicker);
      setPendingTicker(null);
    }
  }

  function handleCodeCancel() {
    setShowCodeDialog(false);
    setMode("fast");
    if (ticker?.startsWith("__PENDING__")) setTicker(null);
  }

  // ── Results ───────────────────────────────────────────────────────────────
  if (displayReport && ticker && !ticker.startsWith("__PENDING__")) {
    return (
      <ResultsDashboard
        ticker={ticker}
        report={displayReport}
        terminalEvents={stagesToEvents(stages)}
        confidence={parseConfidence(stages, displayReport)}
        onBack={() => setTicker(null)}
        mode={mode}
        masterCode={masterCode}
      />
    );
  }

  // ── Error Recovery (both modes) ──────────────────────────────────────────
  if (
    status === "error" &&
    error &&
    !displayReport &&
    ticker &&
    !ticker.startsWith("__PENDING__")
  ) {
    return (
      <div className="h-screen flex flex-col bg-background">
        <DashboardHeader query={ticker} onBack={() => setTicker(null)} status="processing" />
        <div className="flex-1 overflow-auto flex items-center justify-center">
          <StreamErrorCard
            ticker={ticker}
            message={error}
            onRetry={mode === "deep" ? streamState.retry : fastState.retry}
            onBack={() => setTicker(null)}
          />
        </div>
      </div>
    );
  }

  // ── Loading ───────────────────────────────────────────────────────────────
  if ((status === "streaming" || status === "loading" || isActive) && ticker && !ticker.startsWith("__PENDING__")) {
    return (
      <div className="h-screen flex flex-col bg-background">
        <DashboardHeader query={ticker} onBack={() => setTicker(null)} status="processing">
          {mode === "deep" && (
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
          )}
        </DashboardHeader>
        <div className="flex-1 overflow-auto">
          {mode === "deep" ? (
            <LoadingSkeleton
              query={ticker}
              stages={stages}
              complete={stages.some((s) => s.stage === "approved" || s.stage === "delta_complete")}
              illusionMessage={illusionMessage}
            />
          ) : (
            <FastLoading ticker={ticker} />
          )}
        </div>
      </div>
    );
  }

  // ── Search (idle + error) ─────────────────────────────────────────────────
  return (
    <>
      <PaywallModal
        open={showPaywallModal}
        onClose={() => { setShowPaywallModal(false); setPendingTicker(null); }}
        onVipSuccess={handleVipSuccess}
        isVipCodeUsed={isVipCodeUsed}
      />
      <SearchHome
        onSearch={handleSearch}
        mode={mode}
        onModeChange={handleModeChange}
        credits={credits}
        deepLocked={credits <= 0 && hasRedeemedBonus}
      />
    </>
  );
}
