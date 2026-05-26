"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { Database, BarChart3, Users, AlertTriangle, CheckCircle2 } from "lucide-react"

interface LoadingSkeletonProps {
  query: string
}

const agents = [
  {
    id: "data",
    name: "Data Agent",
    icon: Database,
    color: "text-agent-data",
    bgColor: "bg-agent-data",
    tasks: [
      "Fetching historical price data...",
      "Analyzing trading volume patterns...",
      "Processing market indicators...",
      "Compiling financial metrics...",
    ],
  },
  {
    id: "sentiment",
    name: "Sentiment Agent",
    icon: BarChart3,
    color: "text-agent-sentiment",
    bgColor: "bg-agent-sentiment",
    tasks: [
      "Scanning news sources...",
      "Analyzing social media sentiment...",
      "Processing analyst ratings...",
      "Evaluating market mood...",
    ],
  },
  {
    id: "manager",
    name: "Manager Agent",
    icon: Users,
    color: "text-agent-manager",
    bgColor: "bg-agent-manager",
    tasks: [
      "Coordinating agent inputs...",
      "Building analysis framework...",
      "Synthesizing recommendations...",
      "Preparing final assessment...",
    ],
  },
  {
    id: "critic",
    name: "Critic Agent",
    icon: AlertTriangle,
    color: "text-agent-critic",
    bgColor: "bg-agent-critic",
    tasks: [
      "Validating data accuracy...",
      "Checking for anomalies...",
      "Stress testing conclusions...",
      "Finalizing confidence score...",
    ],
  },
]

export function LoadingSkeleton({ query }: LoadingSkeletonProps) {
  const [agentStates, setAgentStates] = useState<
    Record<string, { taskIndex: number; complete: boolean }>
  >({
    data: { taskIndex: 0, complete: false },
    sentiment: { taskIndex: 0, complete: false },
    manager: { taskIndex: 0, complete: false },
    critic: { taskIndex: 0, complete: false },
  })

  useEffect(() => {
    const intervals: NodeJS.Timeout[] = []

    agents.forEach((agent, agentIndex) => {
      const startDelay = agentIndex * 800

      setTimeout(() => {
        let currentTask = 0
        const interval = setInterval(() => {
          currentTask++
          if (currentTask >= agent.tasks.length) {
            setAgentStates((prev) => ({
              ...prev,
              [agent.id]: { taskIndex: currentTask - 1, complete: true },
            }))
            clearInterval(interval)
          } else {
            setAgentStates((prev) => ({
              ...prev,
              [agent.id]: { taskIndex: currentTask, complete: false },
            }))
          }
        }, 600 + Math.random() * 400)
        intervals.push(interval)
      }, startDelay)
    })

    return () => intervals.forEach(clearInterval)
  }, [])

  const overallProgress =
    Object.values(agentStates).filter((s) => s.complete).length / agents.length

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4 py-12">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-2xl font-bold tracking-tight mb-2">
          Analyzing <span className="text-primary font-mono">{query}</span>
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
            className="stroke-primary transition-all duration-500"
            strokeDasharray={`${overallProgress * 264} 264`}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold font-mono">
            {Math.round(overallProgress * 100)}%
          </span>
        </div>
      </div>

      {/* Agent Cards */}
      <div className="w-full max-w-4xl grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {agents.map((agent) => {
          const Icon = agent.icon
          const state = agentStates[agent.id]
          const isActive = state.taskIndex > 0 || agent.id === "data"
          const isComplete = state.complete

          return (
            <Card
              key={agent.id}
              className={cn(
                "border-border transition-all duration-500",
                isActive ? "bg-card" : "bg-card/50",
                isComplete && "border-success/50"
              )}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className={cn(
                        "w-8 h-8 rounded-lg flex items-center justify-center",
                        isActive ? `${agent.bgColor}/20` : "bg-muted"
                      )}
                    >
                      <Icon
                        className={cn(
                          "w-4 h-4",
                          isActive ? agent.color : "text-muted-foreground"
                        )}
                      />
                    </div>
                    <span
                      className={cn(
                        "font-medium text-sm",
                        isActive ? "text-foreground" : "text-muted-foreground"
                      )}
                    >
                      {agent.name}
                    </span>
                  </div>
                  {isComplete && (
                    <CheckCircle2 className="w-4 h-4 text-success" />
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 min-h-[80px]">
                  {isActive ? (
                    <>
                      <p className="text-sm text-muted-foreground">
                        {agent.tasks[state.taskIndex]}
                      </p>
                      {!isComplete && (
                        <div className="flex gap-1">
                          {[0, 1, 2].map((i) => (
                            <div
                              key={i}
                              className={cn(
                                "w-1.5 h-1.5 rounded-full animate-pulse",
                                agent.bgColor
                              )}
                              style={{ animationDelay: `${i * 200}ms` }}
                            />
                          ))}
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="space-y-2">
                      <div className="h-3 bg-muted rounded animate-pulse w-3/4" />
                      <div className="h-3 bg-muted rounded animate-pulse w-1/2" />
                    </div>
                  )}
                </div>

                {/* Progress bar */}
                <div className="mt-4 h-1 bg-secondary rounded-full overflow-hidden">
                  <div
                    className={cn(
                      "h-full transition-all duration-500 rounded-full",
                      agent.bgColor
                    )}
                    style={{
                      width: isComplete
                        ? "100%"
                        : `${((state.taskIndex + 1) / agent.tasks.length) * 100}%`,
                    }}
                  />
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Streaming text effect */}
      <div className="mt-12 w-full max-w-2xl">
        <Card className="bg-card/50 border-border">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse mt-2" />
              <div className="flex-1">
                <p className="text-sm text-muted-foreground font-mono">
                  <StreamingText
                    texts={[
                      `Initializing analysis for ${query}...`,
                      "Connecting to market data feeds...",
                      "Running sentiment analysis algorithms...",
                      "Cross-referencing historical patterns...",
                      "Calculating risk metrics...",
                      "Preparing comprehensive report...",
                    ]}
                  />
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function StreamingText({ texts }: { texts: string[] }) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [displayText, setDisplayText] = useState("")
  const [charIndex, setCharIndex] = useState(0)

  useEffect(() => {
    const currentText = texts[currentIndex]

    if (charIndex < currentText.length) {
      const timeout = setTimeout(() => {
        setDisplayText(currentText.slice(0, charIndex + 1))
        setCharIndex(charIndex + 1)
      }, 30 + Math.random() * 20)
      return () => clearTimeout(timeout)
    } else {
      const timeout = setTimeout(() => {
        setCurrentIndex((currentIndex + 1) % texts.length)
        setCharIndex(0)
        setDisplayText("")
      }, 1500)
      return () => clearTimeout(timeout)
    }
  }, [currentIndex, charIndex, texts])

  return (
    <>
      {displayText}
      <span className="animate-pulse">|</span>
    </>
  )
}
