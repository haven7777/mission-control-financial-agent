"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";

interface FastLoadingProps {
  ticker: string;
}

export function FastLoading({ ticker }: FastLoadingProps) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Animate ring from 0 → ~85% over ~3s, never reaching 100% until done
    const target = 0.85;
    const duration = 3000;
    const steps = 60;
    const interval = duration / steps;
    let step = 0;

    const id = setInterval(() => {
      step++;
      const t = step / steps;
      // ease-out curve
      setProgress(target * (1 - Math.pow(1 - t, 3)));
      if (step >= steps) clearInterval(id);
    }, interval);

    return () => clearInterval(id);
  }, []);

  const pct = Math.round(progress * 100);
  const circumference = 264;

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4 py-12">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-2xl font-bold tracking-tight mb-2">
          Analyzing <span className="text-primary font-mono">{ticker}</span>
        </h1>
        <p className="text-muted-foreground">
          AI agents are processing your request...
        </p>
      </div>

      {/* Progress Ring */}
      <div className="relative w-32 h-32 mb-12">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="42"
            strokeWidth="8"
            fill="none"
            className="stroke-secondary"
          />
          <circle
            cx="50"
            cy="50"
            r="42"
            strokeWidth="8"
            fill="none"
            strokeLinecap="round"
            className="stroke-primary transition-all duration-300"
            strokeDasharray={`${progress * circumference} ${circumference}`}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold font-mono">{pct}%</span>
        </div>
      </div>

      {/* Streaming text */}
      <div className="w-full max-w-2xl">
        <Card className="bg-card/50 border-border">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse mt-2" />
              <div className="flex-1">
                <p className="text-sm text-muted-foreground font-mono">
                  <StreamingText
                    texts={[
                      `Initializing analysis for ${ticker}...`,
                      "Connecting to market data feeds...",
                      "Running sentiment analysis algorithms...",
                      "Calibrating bull & bear signals...",
                      "Preparing quick report...",
                    ]}
                  />
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StreamingText({ texts }: { texts: string[] }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [displayText, setDisplayText] = useState("");
  const [charIndex, setCharIndex] = useState(0);

  useEffect(() => {
    const currentText = texts[currentIndex];

    if (charIndex < currentText.length) {
      const timeout = setTimeout(() => {
        setDisplayText(currentText.slice(0, charIndex + 1));
        setCharIndex(charIndex + 1);
      }, 30 + Math.random() * 20);
      return () => clearTimeout(timeout);
    } else {
      const timeout = setTimeout(() => {
        setCurrentIndex((currentIndex + 1) % texts.length);
        setCharIndex(0);
        setDisplayText("");
      }, 1500);
      return () => clearTimeout(timeout);
    }
  }, [currentIndex, charIndex, texts]);

  return (
    <>
      {displayText}
      <span className="animate-pulse">|</span>
    </>
  );
}
