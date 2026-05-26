"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { DashboardHeader } from "@/components/dashboard/header";
import { AgentTerminal, type AgentEvent, type AgentEventStatus } from "@/components/dashboard/agent-terminal";
import { ResultsDashboard } from "@/components/dashboard/results-dashboard";
import {
  streamAnalysis,
  type FinalReport,
  type ProgressPayload,
  type ProgressStage,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Streaming hook (unchanged)
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
  started:            "System",
  data_complete:      "Data Agent",
  sentiment_complete: "Sentiment Agent",
  synthesizing:       "Manager Agent",
  critiquing:         "Critic Agent",
  revising:           "Critic Agent",
  approved:           "Critic Agent",
};

const STAGE_STATUS: Record<ProgressStage, AgentEventStatus> = {
  started:            "running",
  data_complete:      "done",
  sentiment_complete: "done",
  synthesizing:       "running",
  critiquing:         "running",
  revising:           "conflict",
  approved:           "approved",
};

function stagesToEvents(stages: ProgressPayload[]): AgentEvent[] {
  return stages.map((s, i) => ({
    id:        `stage-${i}`,
    agent:     STAGE_AGENT[s.stage],
    message:   s.message,
    status:    STAGE_STATUS[s.stage],
    timestamp: new Date(),
  }));
}

function parseConfidence(stages: ProgressPayload[]): number {
  const msg = stages.find((s) => s.stage === "approved")?.message ?? "";
  return parseInt(msg.match(/confidence (\d+)%/)?.[1] ?? "0", 10);
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function Home() {
  const [input, setInput] = useState("");
  const [ticker, setTicker] = useState<string | null>(null);

  const { status, stages, report, error } = useAnalysisStream(ticker);

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const next = input.trim().toUpperCase();
    if (next) setTicker(next);
  }

  // ── Done: full Mission Control results dashboard ──────────────────────────
  if (status === "done" && report && ticker) {
    return (
      <ResultsDashboard
        ticker={ticker}
        report={report}
        terminalEvents={stagesToEvents(stages)}
        confidence={parseConfidence(stages)}
        onBack={() => { setTicker(null); setInput(""); }}
      />
    );
  }

  // ── Streaming: full-screen terminal view ──────────────────────────────────
  if (status === "streaming" && ticker) {
    return (
      <div className="h-screen flex flex-col bg-background">
        <DashboardHeader query={ticker} />
        <div className="flex-1 p-6 overflow-hidden">
          <AgentTerminal events={stagesToEvents(stages)} />
        </div>
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────
  if (status === "error") {
    return (
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-6 py-12">
        <LandingHeader />
        <form onSubmit={onSubmit} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="e.g. IBM"
            aria-label="Stock ticker"
            autoCapitalize="characters"
            className="font-mono uppercase"
          />
          <Button type="submit" disabled={!input.trim()}>Analyze</Button>
        </form>
        <Card className="border-destructive/40">
          <CardHeader>
            <CardTitle className="text-destructive">Could not analyze</CardTitle>
            <CardDescription>{error ?? "Unknown error."}</CardDescription>
          </CardHeader>
        </Card>
      </main>
    );
  }

  // ── Idle: landing form ────────────────────────────────────────────────────
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-6 py-12">
      <LandingHeader />
      <form onSubmit={onSubmit} className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. IBM"
          aria-label="Stock ticker"
          autoCapitalize="characters"
          className="font-mono uppercase"
        />
        <Button type="submit" disabled={!input.trim()}>Analyze</Button>
      </form>
    </main>
  );
}

function LandingHeader() {
  return (
    <header className="space-y-2">
      <h1 className="text-3xl font-semibold tracking-tight">Mission Control</h1>
      <p className="text-sm text-muted-foreground">
        Enter a stock ticker. A team of AI agents fetches data, analyzes sentiment,
        synthesizes a report, and critiques it — streaming every step live.
      </p>
    </header>
  );
}
