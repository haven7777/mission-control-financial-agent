"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Gift, Zap } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { validateMasterCode } from "@/lib/api";

interface PaywallModalProps {
  open: boolean;
  onClose: () => void;
  onVipSuccess: (code: string, credits: number) => void;
  isVipCodeUsed: (code: string) => boolean;
}

type SubmitState = "idle" | "loading" | "success" | "error";

export function PaywallModal({
  open,
  onClose,
  onVipSuccess,
  isVipCodeUsed,
}: PaywallModalProps) {
  const [code, setCode] = useState("");
  const [submitState, setSubmitState] = useState<SubmitState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [grantedCredits, setGrantedCredits] = useState<number>(3);

  useEffect(() => {
    if (open) {
      setCode("");
      setSubmitState("idle");
      setErrorMsg(null);
    }
  }, [open]);

  function handleCodeChange(e: React.ChangeEvent<HTMLInputElement>) {
    setCode(e.target.value);
    setSubmitState("idle");
    setErrorMsg(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = code.trim();
    if (!trimmed) return;

    // Single-use enforcement
    if (isVipCodeUsed(trimmed)) {
      setErrorMsg("This code has already been used.");
      setSubmitState("error");
      return;
    }

    setSubmitState("loading");
    setErrorMsg(null);

    const credits = await validateMasterCode(trimmed);
    if (credits > 0) {
      setGrantedCredits(credits);
      setSubmitState("success");
      setTimeout(() => onVipSuccess(trimmed, credits), 1500);
    } else {
      setErrorMsg("Invalid VIP code. Please check and try again.");
      setSubmitState("error");
    }
  }

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-primary" />
            Free Analysis Limit Reached
          </DialogTitle>
          <DialogDescription>
            You&apos;ve used all your free deep analyses. Enter a VIP code to
            unlock +3 more.
          </DialogDescription>
        </DialogHeader>

        {submitState === "success" ? (
          <div className="flex flex-col items-center gap-3 py-8">
            <CheckCircle2 className="w-12 h-12 text-success" />
            <p className="font-semibold text-foreground text-lg">+{grantedCredits} analyses unlocked!</p>
            <p className="text-sm text-muted-foreground">Running your analysis…</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4 mt-2">
            <div className="flex items-center gap-2 p-3 rounded-lg bg-primary/5 border border-primary/20 text-sm text-muted-foreground">
              <Gift className="w-4 h-4 text-primary shrink-0" />
              VIP codes grant bonus analyses. Codes are single-use per device.
            </div>
            <Input
              placeholder="Enter VIP code…"
              value={code}
              onChange={handleCodeChange}
              className="font-mono"
              autoFocus
              disabled={submitState === "loading"}
            />
            {errorMsg && (
              <p className="text-sm text-destructive">{errorMsg}</p>
            )}
            <div className="flex gap-2 justify-end">
              <Button
                type="button"
                variant="ghost"
                onClick={onClose}
                disabled={submitState === "loading"}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={submitState === "loading" || !code.trim()}
              >
                {submitState === "loading" ? "Validating…" : "Redeem"}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
