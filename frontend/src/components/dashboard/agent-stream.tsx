"use client"

import { useEffect, useState, useRef } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { Brain, BarChart3, MessageSquare, AlertTriangle, Zap } from "lucide-react"

type AgentType = "data" | "sentiment" | "manager" | "critic"

interface AgentThought {
  id: string
  agent: AgentType
  thought: string
  timestamp: Date
  confidence?: number
  action?: string
}

const agentConfig: Record<AgentType, { name: string; icon: typeof Brain; colorClass: string; bgClass: string; borderClass: string }> = {
  data: { name: "Data Agent", icon: BarChart3, colorClass: "text-agent-data", bgClass: "bg-agent-data/10", borderClass: "border-agent-data/30" },
  sentiment: { name: "Sentiment Agent", icon: MessageSquare, colorClass: "text-agent-sentiment", bgClass: "bg-agent-sentiment/10", borderClass: "border-agent-sentiment/30" },
  manager: { name: "Manager", icon: Brain, colorClass: "text-agent-manager", bgClass: "bg-agent-manager/10", borderClass: "border-agent-manager/30" },
  critic: { name: "Critic", icon: AlertTriangle, colorClass: "text-agent-critic", bgClass: "bg-agent-critic/10", borderClass: "border-agent-critic/30" },
}

const mockThoughts: Omit<AgentThought, "id" | "timestamp">[] = [
  { agent: "data", thought: "Analyzing NVDA price patterns over 30-day window. Detected ascending triangle formation with strong support at $845.", confidence: 87 },
  { agent: "sentiment", thought: "Social sentiment score: 0.78 (bullish). Twitter mentions up 340% following AI chip announcement.", confidence: 92, action: "Signal: Strong Buy" },
  { agent: "manager", thought: "Aggregating signals from Data and Sentiment agents. Both indicate bullish momentum. Preparing recommendation.", confidence: 85 },
  { agent: "critic", thought: "Warning: RSI approaching overbought territory (68). Consider position sizing adjustment. Historical pullback probability: 23%.", confidence: 79 },
  { agent: "data", thought: "Volume analysis complete. Current volume 2.3x above 20-day average. Institutional accumulation detected.", confidence: 94 },
  { agent: "manager", thought: "Final recommendation: LONG NVDA with 2% portfolio allocation. Stop-loss at $820, target at $920.", action: "Execute Trade" },
  { agent: "sentiment", thought: "Breaking: Federal Reserve comments detected. Running NLP analysis on speech transcript...", confidence: 45 },
  { agent: "critic", thought: "Market correlation check: S&P500 correlation coefficient 0.82. Systemic risk moderate. Proceeding with caution.", confidence: 71 },
  { agent: "data", thought: "AAPL earnings report incoming. Historical post-earnings volatility: ±4.2%. Adjusting risk parameters.", confidence: 88 },
  { agent: "sentiment", thought: "Analyst rating changes: 3 upgrades, 1 downgrade this week. Net sentiment shift: +0.12", confidence: 83 },
]

export function AgentStream() {
  const [thoughts, setThoughts] = useState<AgentThought[]>([])
  const [isStreaming, setIsStreaming] = useState(true)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isStreaming) return

    // Add initial thoughts
    const initialThoughts = mockThoughts.slice(0, 3).map((t, i) => ({
      ...t,
      id: `thought-${i}`,
      timestamp: new Date(Date.now() - (3 - i) * 5000)
    }))
    setThoughts(initialThoughts)

    let thoughtIndex = 3
    const interval = setInterval(() => {
      const mockThought = mockThoughts[thoughtIndex % mockThoughts.length]
      const newThought: AgentThought = {
        ...mockThought,
        id: `thought-${Date.now()}`,
        timestamp: new Date(),
      }
      
      setThoughts(prev => [...prev.slice(-15), newThought])
      thoughtIndex++
    }, 3000)

    return () => clearInterval(interval)
  }, [isStreaming])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [thoughts])

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">Agent Thought Stream</h2>
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
            </span>
            <span className="text-xs text-muted-foreground">Live</span>
          </div>
        </div>
        <button
          onClick={() => setIsStreaming(!isStreaming)}
          className={cn(
            "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
            isStreaming 
              ? "bg-destructive/10 text-destructive hover:bg-destructive/20" 
              : "bg-primary/10 text-primary hover:bg-primary/20"
          )}
        >
          {isStreaming ? "Pause Stream" : "Resume Stream"}
        </button>
      </div>

      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="space-y-3">
          {thoughts.map((thought, index) => {
            const config = agentConfig[thought.agent]
            const Icon = config.icon
            const isLatest = index === thoughts.length - 1

            return (
              <div
                key={thought.id}
                className={cn(
                  "p-4 rounded-lg border transition-all duration-500",
                  config.bgClass,
                  config.borderClass,
                  isLatest && "ring-1 ring-primary/50"
                )}
                style={{
                  animation: isLatest ? "fadeIn 0.5s ease-out" : undefined
                }}
              >
                <div className="flex items-start gap-3">
                  <div className={cn("p-2 rounded-md", config.bgClass)}>
                    <Icon className={cn("w-4 h-4", config.colorClass)} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={cn("font-medium text-sm", config.colorClass)}>
                        {config.name}
                      </span>
                      <span className="text-xs text-muted-foreground font-mono">
                        {formatTime(thought.timestamp)}
                      </span>
                      {thought.confidence && (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                          {thought.confidence}% conf
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-foreground/90 mt-1 leading-relaxed">
                      {thought.thought}
                    </p>
                    {thought.action && (
                      <div className="mt-2 flex items-center gap-2">
                        <Zap className="w-3 h-3 text-warning" />
                        <span className="text-xs font-medium text-warning">{thought.action}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </ScrollArea>

      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  )
}
