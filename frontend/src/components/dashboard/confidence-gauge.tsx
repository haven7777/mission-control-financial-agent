"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown, Minus, Target, Shield, Zap } from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface ConfidenceGaugeProps {
  className?: string
}

export function ConfidenceGauge({ className }: ConfidenceGaugeProps) {
  const [confidence, setConfidence] = useState(78)
  const [trend, setTrend] = useState<"up" | "down" | "stable">("up")
  const [previousConfidence, setPreviousConfidence] = useState(75)

  // Simulate confidence changes
  useEffect(() => {
    const interval = setInterval(() => {
      setConfidence(prev => {
        const change = (Math.random() - 0.45) * 8
        const newValue = Math.max(20, Math.min(98, prev + change))
        setPreviousConfidence(prev)
        
        if (newValue > prev + 1) setTrend("up")
        else if (newValue < prev - 1) setTrend("down")
        else setTrend("stable")
        
        return Math.round(newValue)
      })
    }, 4000)

    return () => clearInterval(interval)
  }, [])

  const getConfidenceLevel = (value: number): { label: string; color: string; bgColor: string } => {
    if (value >= 80) return { label: "High", color: "text-success", bgColor: "bg-success" }
    if (value >= 60) return { label: "Moderate", color: "text-warning", bgColor: "bg-warning" }
    if (value >= 40) return { label: "Low", color: "text-agent-critic", bgColor: "bg-agent-critic" }
    return { label: "Very Low", color: "text-destructive", bgColor: "bg-destructive" }
  }

  const confidenceLevel = getConfidenceLevel(confidence)

  // Calculate stroke dasharray for the circular gauge
  const radius = 70
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (confidence / 100) * circumference

  return (
    <Card className={cn("bg-card border-border", className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-medium">System Confidence</CardTitle>
          <Badge 
            variant="outline" 
            className={cn(
              "text-xs",
              confidenceLevel.color,
              `border-${confidenceLevel.color.replace('text-', '')}/30`,
              `bg-${confidenceLevel.color.replace('text-', '')}/10`
            )}
          >
            {confidenceLevel.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center">
          {/* Circular Gauge */}
          <div className="relative w-44 h-44">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 160 160">
              {/* Background circle */}
              <circle
                cx="80"
                cy="80"
                r={radius}
                fill="none"
                stroke="currentColor"
                strokeWidth="12"
                className="text-muted/20"
              />
              {/* Progress circle */}
              <circle
                cx="80"
                cy="80"
                r={radius}
                fill="none"
                stroke="url(#gaugeGradient)"
                strokeWidth="12"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                className="transition-all duration-1000 ease-out"
              />
              {/* Gradient definition */}
              <defs>
                <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="oklch(0.75 0.15 175)" />
                  <stop offset="50%" stopColor="oklch(0.70 0.18 145)" />
                  <stop offset="100%" stopColor="oklch(0.80 0.16 85)" />
                </linearGradient>
              </defs>
            </svg>
            
            {/* Center content */}
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-4xl font-bold font-mono">{confidence}%</span>
              <div className={cn(
                "flex items-center gap-1 text-xs mt-1",
                trend === "up" && "text-success",
                trend === "down" && "text-destructive",
                trend === "stable" && "text-muted-foreground"
              )}>
                {trend === "up" && <TrendingUp className="w-3 h-3" />}
                {trend === "down" && <TrendingDown className="w-3 h-3" />}
                {trend === "stable" && <Minus className="w-3 h-3" />}
                <span>{trend === "up" ? "+" : trend === "down" ? "-" : ""}{Math.abs(confidence - previousConfidence)}%</span>
              </div>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-3 w-full mt-4">
            <div className="bg-muted/30 rounded-lg p-3 text-center">
              <Target className="w-4 h-4 mx-auto text-primary mb-1" />
              <p className="text-xs text-muted-foreground">Accuracy</p>
              <p className="font-mono font-semibold text-sm">94.2%</p>
            </div>
            <div className="bg-muted/30 rounded-lg p-3 text-center">
              <Shield className="w-4 h-4 mx-auto text-success mb-1" />
              <p className="text-xs text-muted-foreground">Risk Level</p>
              <p className="font-mono font-semibold text-sm">Low</p>
            </div>
            <div className="bg-muted/30 rounded-lg p-3 text-center">
              <Zap className="w-4 h-4 mx-auto text-warning mb-1" />
              <p className="text-xs text-muted-foreground">Signals</p>
              <p className="font-mono font-semibold text-sm">12</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
