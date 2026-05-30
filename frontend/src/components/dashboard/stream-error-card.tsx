"use client";

import { AlertTriangle, RotateCw, ArrowLeft } from "lucide-react";

interface StreamErrorCardProps {
  ticker: string;
  message: string;
  onRetry: () => void;
  onBack: () => void;
}

export function StreamErrorCard({ ticker, message, onRetry, onBack }: StreamErrorCardProps) {
  return (
    <div className="flex items-center justify-center px-4 py-12 min-h-[60vh]">
      <div className="w-full max-w-md">
        <div className="relative p-8 rounded-2xl border-2 border-destructive/20 bg-card shadow-xl shadow-destructive/5">
          {/* Pulsing alert badge */}
          <div className="flex justify-center mb-6">
            <div className="relative w-16 h-16 flex items-center justify-center">
              <div className="absolute inset-0 rounded-full bg-destructive/10 animate-ping" />
              <div className="relative z-10 w-14 h-14 rounded-2xl bg-destructive/10 border border-destructive/30 flex items-center justify-center">
                <AlertTriangle className="w-7 h-7 text-destructive" />
              </div>
            </div>
          </div>

          {/* Headline */}
          <div className="text-center space-y-2 mb-6">
            <p className="text-xs font-mono text-muted-foreground/60 uppercase tracking-[0.25em]">
              Analysis Interrupted
            </p>
            <h2 className="text-2xl font-bold tracking-tight text-foreground">
              {ticker}
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-xs mx-auto">
              {message}
            </p>
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-2.5">
            <button
              onClick={onRetry}
              className="flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold text-sm shadow-lg shadow-indigo-500/30 transition-all"
            >
              <RotateCw className="w-4 h-4" />
              Try Again
            </button>
            <button
              onClick={onBack}
              className="flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-lg bg-muted/40 hover:bg-muted/60 text-muted-foreground hover:text-foreground text-sm font-medium border border-border/40 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Search
            </button>
          </div>

          {/* Helpful tail */}
          <p className="text-center text-xs text-muted-foreground/50 mt-5 leading-relaxed">
            Your previous progress was not saved. Retrying will run a fresh analysis.
          </p>
        </div>
      </div>
    </div>
  );
}
