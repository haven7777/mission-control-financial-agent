"use client"

import { Badge } from "@/components/ui/badge"
import { Cpu } from "lucide-react"
import { cn } from "@/lib/utils"

interface DashboardHeaderProps {
  query?: string
  onBack?: () => void
  children?: React.ReactNode
  status?: "online" | "processing" | "approved"
}

export function DashboardHeader({ query, onBack, children, status = "online" }: DashboardHeaderProps) {

  return (
    <header className="h-14 border-b border-border bg-card/50 backdrop-blur-sm flex items-center justify-between px-6 relative">
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          disabled={!onBack}
          className={cn(
            "flex items-center gap-2 rounded-lg transition-colors",
            onBack ? "hover:bg-muted/50 px-2 py-1.5 -mx-2 cursor-pointer" : "cursor-default"
          )}
        >
          <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
            <Cpu className="w-5 h-5 text-primary" />
          </div>
          <div className="text-left">
            <h1 className="text-base font-semibold leading-none">Mission Control</h1>
            <p className="text-xs text-muted-foreground">AI Financial System</p>
          </div>
        </button>

        <div className="h-6 w-px bg-border mx-2" />

        <Badge
          variant="outline"
          className={cn(
            "gap-1.5 px-2.5",
            status === "online"     && "text-success border-success/30 bg-success/10",
            status === "processing" && "text-primary border-primary/30 bg-primary/10",
            status === "approved"   && "text-success border-success/30 bg-success/10",
          )}
        >
          <span className="relative flex h-2 w-2">
            <span className={cn(
              "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
              status === "online"     && "bg-success",
              status === "processing" && "bg-primary",
              status === "approved"   && "bg-success",
            )} />
            <span className={cn(
              "relative inline-flex rounded-full h-2 w-2",
              status === "online"     && "bg-success",
              status === "processing" && "bg-primary",
              status === "approved"   && "bg-success",
            )} />
          </span>
          {status === "online"     && "System Online"}
          {status === "processing" && "Processing..."}
          {status === "approved"   && "Approved"}
        </Badge>
      </div>

      {query && (
        <div className="absolute left-1/2 -translate-x-1/2 pointer-events-none">
          <span className="text-base font-mono font-bold tracking-widest text-foreground">
            {query}
          </span>
        </div>
      )}

      <div className="flex items-center gap-3">
        {children}
      </div>
    </header>
  )
}
