"use client"

import { useEffect, useRef } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { Check, Loader2, AlertTriangle, CheckCircle2 } from "lucide-react"

export type AgentEventStatus = "running" | "done" | "conflict" | "approved"

export interface AgentEvent {
  id: string
  agent: string
  message: string
  status: AgentEventStatus
  timestamp: Date
}

interface AgentTerminalProps {
  events: AgentEvent[]
}

export function AgentTerminal({ events }: AgentTerminalProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [events])

  const formatTime = (date: Date) =>
    date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false })

  const getStatusIcon = (status: AgentEventStatus) => {
    switch (status) {
      case "running":  return <Loader2 className="w-4 h-4 text-primary animate-spin" />
      case "done":     return <Check className="w-4 h-4 text-success" />
      case "conflict": return <AlertTriangle className="w-4 h-4 text-destructive" />
      case "approved": return <CheckCircle2 className="w-4 h-4 text-success" />
    }
  }

  const getStatusText = (status: AgentEventStatus) => {
    switch (status) {
      case "running":  return <span className="text-primary">[Running]</span>
      case "done":     return <span className="text-success">[Done]</span>
      case "conflict": return <span className="text-destructive">[Conflict!]</span>
      case "approved": return <span className="text-success">[Approved]</span>
    }
  }

  const getAgentColor = (agent: string) => {
    if (agent.includes("Data"))      return "text-agent-data"
    if (agent.includes("Sentiment")) return "text-agent-sentiment"
    if (agent.includes("Manager"))   return "text-agent-manager"
    if (agent.includes("Critic"))    return "text-agent-critic"
    return "text-foreground"
  }

  return (
    <div className="h-full flex flex-col bg-[oklch(0.10_0.01_240)] rounded-lg border border-border overflow-hidden">
      {/* Terminal Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-[oklch(0.08_0.01_240)]">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-destructive/80" />
          <div className="w-3 h-3 rounded-full bg-warning/80" />
          <div className="w-3 h-3 rounded-full bg-success/80" />
        </div>
        <span className="ml-2 text-xs font-mono text-muted-foreground">agent_terminal.log</span>
        <div className="ml-auto flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
          </span>
          <span className="text-xs text-success font-mono">LIVE</span>
        </div>
      </div>

      {/* Terminal Content */}
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="space-y-1 font-mono text-sm">
          {events.length === 0 ? (
            <div className="py-1.5 px-2 text-muted-foreground">Awaiting agent events…</div>
          ) : (
            events.map((event) => (
              <div
                key={event.id}
                className={cn(
                  "flex items-start gap-3 py-1.5 px-2 rounded transition-colors",
                  event.status === "running"  && "bg-primary/5",
                  event.status === "conflict" && "bg-destructive/5"
                )}
              >
                <span className="text-muted-foreground text-xs shrink-0 pt-0.5">
                  {formatTime(event.timestamp)}
                </span>
                <span className="shrink-0 pt-0.5">{getStatusIcon(event.status)}</span>
                <span className={cn("font-semibold shrink-0", getAgentColor(event.agent))}>
                  {event.agent}:
                </span>
                <span className="text-foreground/90 flex-1">{event.message}</span>
                <span className="shrink-0 text-xs font-semibold">{getStatusText(event.status)}</span>
              </div>
            ))
          )}
          <div className="flex items-center gap-2 pt-2 text-muted-foreground">
            <span className="animate-pulse">_</span>
          </div>
        </div>
      </ScrollArea>
    </div>
  )
}
