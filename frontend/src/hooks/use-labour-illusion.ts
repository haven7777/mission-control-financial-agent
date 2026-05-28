"use client";

import { useEffect, useRef, useState } from "react";
import type { FinalReport } from "@/lib/api";

const ILLUSION_STAGES = [
  { atMs: 0,     text: "Initializing research pipeline…" },
  { atMs: 4000,  text: "Fetching real-time market data…" },
  { atMs: 9000,  text: "Analyzing earnings call transcripts…" },
  { atMs: 14000, text: "Retrieving historical SEC filing vectors…" },
  { atMs: 19000, text: "Running bull vs. bear debate analysis…" },
  { atMs: 24000, text: "Validating cached analytical insights…" },
  { atMs: 29000, text: "Synthesizing institutional report…" },
  { atMs: 34000, text: "Critic agent validating findings…" },
  { atMs: 38000, text: "Applying final calibration…" },
  { atMs: 42000, text: "Finalizing report…" },
] as const;

const MIN_MS = 30_000;
const MAX_MS = 45_000;

export interface LabourIllusionState {
  revealedReport: FinalReport | null;
  illusionMessage: string;
  progressPercent: number;
}

/**
 * Holds `report` until a randomized 30–45 s timer elapses, then reveals it.
 *
 * `active`     — true while analysis is running or result is being held.
 * `sessionKey` — pass the current ticker so the timer resets on new searches.
 */
export function useLabourIllusion(
  report: FinalReport | null,
  active: boolean,
  sessionKey: string | null,
): LabourIllusionState {
  const [elapsed, setElapsed] = useState(0);
  const [revealedReport, setRevealedReport] = useState<FinalReport | null>(null);

  const startRef = useRef<number>(0);
  const targetRef = useRef<number>(MIN_MS);
  const reportRef = useRef<FinalReport | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Keep reportRef in sync without causing re-renders.
  useEffect(() => {
    reportRef.current = report;
  }, [report]);

  // Reset and (re-)start the timer whenever active state or session changes.
  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setElapsed(0);
    setRevealedReport(null);
    reportRef.current = null;

    if (!active) return;

    startRef.current = Date.now();
    targetRef.current = MIN_MS + Math.floor(Math.random() * (MAX_MS - MIN_MS));

    intervalRef.current = setInterval(() => {
      const now = Date.now() - startRef.current;
      setElapsed(now);
      if (now >= targetRef.current && reportRef.current !== null) {
        setRevealedReport(reportRef.current);
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    }, 250);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, sessionKey]);

  const currentStage =
    [...ILLUSION_STAGES].reverse().find((s) => elapsed >= s.atMs) ??
    ILLUSION_STAGES[0];

  return {
    revealedReport,
    illusionMessage: currentStage.text,
    progressPercent: Math.min(100, (elapsed / (targetRef.current || MIN_MS)) * 100),
  };
}
