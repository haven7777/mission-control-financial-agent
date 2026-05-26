"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"
import { Brain, BarChart3, MessageSquare, AlertTriangle, CheckCircle2, Loader2 } from "lucide-react"

interface AgentStatus {
  id: string
  name: string
  icon: typeof Brain
  status: "active" | "processing" | "idle"
  load: number
  tasksCompleted: number
  colorClass: string
}

const initialAgents: AgentStatus[] = [
  { id: "data", name: "Data Agent", icon: BarChart3, status: "active", load: 72, tasksCompleted: 156, colorClass: "text-agent-data" },
  { id: "sentiment", name: "Sentiment Agent", icon: MessageSquare, status: "processing", load: 89, tasksCompleted: 243, colorClass: "text-agent-sentiment" },
  { id: "manager", name: "Manager", icon: Brain, status: "active", load: 45, tasksCompleted: 89, colorClass: "text-agent-manager" },
  { id: "critic", name: "Critic", icon: AlertTriangle, status: "idle", load: 23, tasksCompleted: 67, colorClass: "text-agent-critic" },
]

export function AgentStatusPanel() {
  const [agents, setAgents] = useState(initialAgents)

  useEffect(() => {
    const interval = setInterval(() => {
      setAgents(prev => prev.map(agent => ({
        ...agent,
        load: Math.max(10, Math.min(95, agent.load + (Math.random() - 0.5) * 20)),
        tasksCompleted: agent.tasksCompleted + (Math.random() > 0.7 ? 1 : 0),
        status: Math.random() > 0.85 
          ? (["active", "processing", "idle"] as const)[Math.floor(Math.random() * 3)]
          : agent.status
      })))
    }, 3000)

    return () => clearInterval(interval)
  }, [])

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium">Agent Status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {agents.map(agent => {
          const Icon = agent.icon
          return (
            <div key={agent.id} className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon className={cn("w-4 h-4", agent.colorClass)} />
                  <span className="text-sm font-medium">{agent.name}</span>
                </div>
                <Badge 
                  variant="outline"
                  className={cn(
                    "text-[10px] px-1.5 py-0 gap-1",
                    agent.status === "active" && "text-success border-success/30 bg-success/10",
                    agent.status === "processing" && "text-primary border-primary/30 bg-primary/10",
                    agent.status === "idle" && "text-muted-foreground border-muted-foreground/30"
                  )}
                >
                  {agent.status === "active" && <CheckCircle2 className="w-2.5 h-2.5" />}
                  {agent.status === "processing" && <Loader2 className="w-2.5 h-2.5 animate-spin" />}
                  {agent.status}
                </Badge>
              </div>
              <div className="flex items-center gap-3">
                <Progress value={agent.load} className="h-1.5 flex-1" />
                <span className="text-xs font-mono text-muted-foreground w-12 text-right">
                  {Math.round(agent.load)}%
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {agent.tasksCompleted} tasks completed
              </p>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
