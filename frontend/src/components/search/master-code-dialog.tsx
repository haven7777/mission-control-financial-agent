"use client";

import { useEffect, useState } from "react";
import { Lock } from "lucide-react";
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
import { setMasterCode } from "@/lib/auth";

interface MasterCodeDialogProps {
  open: boolean;
  onSuccess: (code: string) => void;
  onCancel: () => void;
}

export function MasterCodeDialog({ open, onSuccess, onCancel }: MasterCodeDialogProps) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      setCode("");
      setError(null);
    }
  }, [open]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = code.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);

    const credits = await validateMasterCode(trimmed);
    if (credits > 0) {
      setMasterCode(trimmed);
      onSuccess(trimmed);
    } else {
      setError("Invalid or inactive Master Code. Please check and try again.");
    }
    setLoading(false);
  }

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onCancel(); }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lock className="w-5 h-5 text-primary" />
            Deep Research Access
          </DialogTitle>
          <DialogDescription>
            Enter your Master Code to unlock institutional-grade analysis with full
            AI agent pipeline, SEC filings, earnings transcripts, and the Labor Illusion Engine.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 mt-2">
          <Input
            placeholder="Enter your access code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="font-mono"
            autoFocus
            disabled={loading}
          />
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="ghost" onClick={onCancel} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading || !code.trim()}>
              {loading ? "Validating…" : "Activate"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
