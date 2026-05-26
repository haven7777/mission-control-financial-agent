"use client"

import { useState, useEffect } from "react"
import { Badge } from "@/components/ui/badge"
import { Activity, Bell, Settings, Cpu, Wifi, Clock, ArrowLeft, Search } from "lucide-react"
import { cn } from "@/lib/utils"

interface DashboardHeaderProps {
  query?: string
  onBack?: () => void
  children?: React.ReactNode
}

export function DashboardHeader({ query, onBack, children }: DashboardHeaderProps) {
  const [currentTime, setCurrentTime] = useState(new Date())
  const [systemStatus, setSystemStatus] = useState<"online" | "processing" | "warning">("online")

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    // Simulate occasional status changes
    const statusInterval = setInterval(() => {
      const statuses: ("online" | "processing" | "warning")[] = ["online", "online", "online", "processing"]
      setSystemStatus(statuses[Math.floor(Math.random() * statuses.length)])
    }, 8000)
    return () => clearInterval(statusInterval)
  }, [])

  return (
    <header className="h-14 border-b border-border bg-card/50 backdrop-blur-sm flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        {onBack && (
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm">Back</span>
          </button>
        )}
        
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
            <Cpu className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-base font-semibold leading-none">Mission Control</h1>
            <p className="text-xs text-muted-foreground">AI Financial System</p>
          </div>
        </div>

        {query && (
          <>
            <div className="h-6 w-px bg-border mx-2" />
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-secondary">
              <Search className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-sm font-mono text-foreground">{query}</span>
            </div>
          </>
        )}
        
        <div className="h-6 w-px bg-border mx-2" />
        
        <Badge 
          variant="outline"
          className={cn(
            "gap-1.5 px-2.5",
            systemStatus === "online" && "text-success border-success/30 bg-success/10",
            systemStatus === "processing" && "text-primary border-primary/30 bg-primary/10",
            systemStatus === "warning" && "text-warning border-warning/30 bg-warning/10"
          )}
        >
          <span className="relative flex h-2 w-2">
            <span className={cn(
              "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
              systemStatus === "online" && "bg-success",
              systemStatus === "processing" && "bg-primary",
              systemStatus === "warning" && "bg-warning"
            )}></span>
            <span className={cn(
              "relative inline-flex rounded-full h-2 w-2",
              systemStatus === "online" && "bg-success",
              systemStatus === "processing" && "bg-primary",
              systemStatus === "warning" && "bg-warning"
            )}></span>
          </span>
          {systemStatus === "online" && "System Online"}
          {systemStatus === "processing" && "Processing..."}
          {systemStatus === "warning" && "Attention Required"}
        </Badge>
      </div>

      <div className="flex items-center gap-4">
        {children}
        
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <Wifi className="w-3.5 h-3.5 text-success" />
            <span>Connected</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-primary" />
            <span>4 Agents Active</span>
          </div>
          <div className="flex items-center gap-1.5 font-mono">
            <Clock className="w-3.5 h-3.5" />
            <span>{currentTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
          </div>
        </div>

        <div className="h-6 w-px bg-border" />

        <div className="flex items-center gap-1">
          <button className="p-2 rounded-md hover:bg-muted transition-colors relative">
            <Bell className="w-4 h-4 text-muted-foreground" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-destructive rounded-full"></span>
          </button>
          <button className="p-2 rounded-md hover:bg-muted transition-colors">
            <Settings className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>
      </div>
    </header>
  )
}
