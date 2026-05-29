"use client";

import { useEffect, useState } from "react";

const CREDITS_KEY = "fast_credits";
const USED_VIP_KEY = "used_vip_codes";
export const INITIAL_CREDITS = 3;

export function useCredits() {
  // Server + first client render must agree → start from defaults.
  // localStorage is read in useEffect after hydration completes.
  const [credits, setCredits] = useState<number>(INITIAL_CREDITS);
  const [usedVipCodes, setUsedVipCodes] = useState<string[]>([]);

  useEffect(() => {
    const rawCredits = localStorage.getItem(CREDITS_KEY);
    if (rawCredits !== null) {
      setCredits(Math.max(0, parseInt(rawCredits, 10)));
    }
    try {
      const rawVip = localStorage.getItem(USED_VIP_KEY);
      if (rawVip) setUsedVipCodes(JSON.parse(rawVip) as string[]);
    } catch {
      // ignore malformed storage
    }
  }, []);

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
