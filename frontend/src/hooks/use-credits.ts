"use client";

import { useState } from "react";

const CREDITS_KEY = "fast_credits";
const USED_VIP_KEY = "used_vip_codes";
export const INITIAL_CREDITS = 3;

export function useCredits() {
  const [credits, setCredits] = useState<number>(() => {
    if (typeof window === "undefined") return INITIAL_CREDITS;
    const raw = localStorage.getItem(CREDITS_KEY);
    return raw !== null ? Math.max(0, parseInt(raw, 10)) : INITIAL_CREDITS;
  });

  const [usedVipCodes, setUsedVipCodes] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const raw = localStorage.getItem(USED_VIP_KEY);
      return raw ? (JSON.parse(raw) as string[]) : [];
    } catch {
      return [];
    }
  });

  function consumeCredit(): void {
    setCredits((prev) => {
      if (prev <= 0) return prev;
      const next = prev - 1;
      localStorage.setItem(CREDITS_KEY, String(next));
      return next;
    });
  }

  function addCredits(n: number): void {
    setCredits((prev) => {
      const next = prev + n;
      localStorage.setItem(CREDITS_KEY, String(next));
      return next;
    });
  }

  function isVipCodeUsed(code: string): boolean {
    return usedVipCodes.map((c) => c.toUpperCase()).includes(code.toUpperCase());
  }

  function markVipCodeUsed(code: string): void {
    const upper = code.toUpperCase();
    setUsedVipCodes((prev) => {
      const next = [...prev, upper];
      localStorage.setItem(USED_VIP_KEY, JSON.stringify(next));
      return next;
    });
  }

  return { credits, consumeCredit, addCredits, isVipCodeUsed, markVipCodeUsed };
}
