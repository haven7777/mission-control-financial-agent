"use client"

import { TrendingUp, TrendingDown, Activity, BarChart3, DollarSign, Users, Clock, Target } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface StockData {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
  volume: string
  marketCap: string
  pe: string
  eps: string
  high52w: number
  low52w: number
  avgVolume: string
  aiSentiment: "bullish" | "bearish" | "neutral"
  aiConfidence: number
}

// Extended mock data based on search query
const getStockData = (query: string): StockData => {
  const stocks: Record<string, StockData> = {
    "NVDA": { symbol: "NVDA", name: "NVIDIA Corporation", price: 875.42, change: 23.54, changePercent: 2.76, volume: "52.3M", marketCap: "2.16T", pe: "65.2", eps: "13.42", high52w: 974.00, low52w: 222.97, avgVolume: "45.8M", aiSentiment: "bullish", aiConfidence: 87 },
    "AAPL": { symbol: "AAPL", name: "Apple Inc.", price: 178.92, change: -1.24, changePercent: -0.69, volume: "48.2M", marketCap: "2.78T", pe: "28.4", eps: "6.30", high52w: 199.62, low52w: 164.08, avgVolume: "52.1M", aiSentiment: "neutral", aiConfidence: 62 },
    "MSFT": { symbol: "MSFT", name: "Microsoft Corporation", price: 425.18, change: 5.67, changePercent: 1.35, volume: "22.1M", marketCap: "3.15T", pe: "36.8", eps: "11.55", high52w: 468.35, low52w: 309.45, avgVolume: "19.4M", aiSentiment: "bullish", aiConfidence: 79 },
    "GOOGL": { symbol: "GOOGL", name: "Alphabet Inc.", price: 141.56, change: -2.34, changePercent: -1.63, volume: "28.4M", marketCap: "1.78T", pe: "24.1", eps: "5.87", high52w: 155.20, low52w: 115.83, avgVolume: "24.2M", aiSentiment: "bearish", aiConfidence: 71 },
    "TSLA": { symbol: "TSLA", name: "Tesla, Inc.", price: 245.67, change: 12.89, changePercent: 5.54, volume: "112.5M", marketCap: "780B", pe: "78.3", eps: "3.14", high52w: 299.29, low52w: 138.80, avgVolume: "98.7M", aiSentiment: "bullish", aiConfidence: 68 },
    "META": { symbol: "META", name: "Meta Platforms, Inc.", price: 512.34, change: 8.21, changePercent: 1.63, volume: "15.7M", marketCap: "1.31T", pe: "31.2", eps: "16.42", high52w: 542.81, low52w: 274.38, avgVolume: "14.2M", aiSentiment: "neutral", aiConfidence: 74 },
    "AMZN": { symbol: "AMZN", name: "Amazon.com, Inc.", price: 186.42, change: 3.21, changePercent: 1.75, volume: "38.9M", marketCap: "1.94T", pe: "58.7", eps: "3.18", high52w: 201.20, low52w: 118.35, avgVolume: "42.3M", aiSentiment: "bullish", aiConfidence: 81 },
  }
  
  const upperQuery = query.toUpperCase()
  if (stocks[upperQuery]) return stocks[upperQuery]
  
  // Default fallback for unknown queries
  return {
    symbol: upperQuery.slice(0, 4),
    name: `${query} Analysis`,
    price: 150 + Math.random() * 200,
    change: (Math.random() - 0.5) * 20,
    changePercent: (Math.random() - 0.5) * 8,
    volume: `${(Math.random() * 50 + 10).toFixed(1)}M`,
    marketCap: `${(Math.random() * 2 + 0.5).toFixed(2)}T`,
    pe: (Math.random() * 50 + 15).toFixed(1),
    eps: (Math.random() * 15 + 2).toFixed(2),
    high52w: 200 + Math.random() * 300,
    low52w: 50 + Math.random() * 100,
    avgVolume: `${(Math.random() * 40 + 10).toFixed(1)}M`,
    aiSentiment: ["bullish", "bearish", "neutral"][Math.floor(Math.random() * 3)] as "bullish" | "bearish" | "neutral",
    aiConfidence: Math.floor(Math.random() * 30 + 60)
  }
}

interface FocusedStockPanelProps {
  query: string
}

export function FocusedStockPanel({ query }: FocusedStockPanelProps) {
  const stock = getStockData(query)
  const isPositive = stock.change >= 0

  return (
    <div className="space-y-4">
      {/* Main Stock Card */}
      <Card className="bg-card border-border overflow-hidden">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                <span className="font-mono font-bold text-primary text-lg">{stock.symbol.slice(0, 2)}</span>
              </div>
              <div>
                <CardTitle className="text-xl font-bold">{stock.symbol}</CardTitle>
                <p className="text-sm text-muted-foreground">{stock.name}</p>
              </div>
            </div>
            <Badge variant="outline" className="text-primary border-primary/30 bg-primary/10">
              <Activity className="w-3 h-3 mr-1" />
              Live
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          {/* Price Section */}
          <div className="flex items-end justify-between mb-6">
            <div>
              <p className="text-4xl font-mono font-bold tracking-tight">
                ${stock.price.toFixed(2)}
              </p>
              <div className={cn(
                "flex items-center gap-2 mt-1",
                isPositive ? "text-success" : "text-destructive"
              )}>
                {isPositive ? (
                  <TrendingUp className="w-5 h-5" />
                ) : (
                  <TrendingDown className="w-5 h-5" />
                )}
                <span className="text-lg font-semibold">
                  {isPositive ? "+" : ""}{stock.change.toFixed(2)} ({isPositive ? "+" : ""}{stock.changePercent.toFixed(2)}%)
                </span>
              </div>
            </div>
            <Badge 
              variant="outline" 
              className={cn(
                "text-sm px-3 py-1.5",
                stock.aiSentiment === "bullish" && "text-success border-success/30 bg-success/10",
                stock.aiSentiment === "bearish" && "text-destructive border-destructive/30 bg-destructive/10",
                stock.aiSentiment === "neutral" && "text-muted-foreground border-muted-foreground/30 bg-muted/20"
              )}
            >
              AI: {stock.aiSentiment.charAt(0).toUpperCase() + stock.aiSentiment.slice(1)}
            </Badge>
          </div>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 gap-3">
            <MetricCard 
              icon={BarChart3} 
              label="Volume" 
              value={stock.volume}
              subValue={`Avg: ${stock.avgVolume}`}
            />
            <MetricCard 
              icon={DollarSign} 
              label="Market Cap" 
              value={stock.marketCap}
            />
            <MetricCard 
              icon={Target} 
              label="P/E Ratio" 
              value={stock.pe}
              subValue={`EPS: $${stock.eps}`}
            />
            <MetricCard 
              icon={Clock} 
              label="52W Range" 
              value={`$${stock.low52w.toFixed(0)} - $${stock.high52w.toFixed(0)}`}
            />
          </div>
        </CardContent>
      </Card>

      {/* AI Analysis Summary */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium flex items-center gap-2">
            <Users className="w-4 h-4 text-primary" />
            AI Analysis Summary
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Confidence Level</span>
            <span className={cn(
              "font-mono font-bold text-lg",
              stock.aiConfidence >= 75 ? "text-success" : stock.aiConfidence >= 50 ? "text-warning" : "text-destructive"
            )}>
              {stock.aiConfidence}%
            </span>
          </div>
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div 
              className={cn(
                "h-full rounded-full transition-all duration-1000",
                stock.aiConfidence >= 75 ? "bg-success" : stock.aiConfidence >= 50 ? "bg-warning" : "bg-destructive"
              )}
              style={{ width: `${stock.aiConfidence}%` }}
            />
          </div>
          <div className="grid grid-cols-2 gap-2 pt-2">
            <div className="text-center p-3 rounded-lg bg-muted/30 border border-border">
              <p className="text-xs text-muted-foreground mb-1">Recommendation</p>
              <p className={cn(
                "font-semibold",
                stock.aiSentiment === "bullish" ? "text-success" : stock.aiSentiment === "bearish" ? "text-destructive" : "text-muted-foreground"
              )}>
                {stock.aiSentiment === "bullish" ? "BUY" : stock.aiSentiment === "bearish" ? "SELL" : "HOLD"}
              </p>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/30 border border-border">
              <p className="text-xs text-muted-foreground mb-1">Risk Level</p>
              <p className="font-semibold text-warning">
                {stock.changePercent > 3 ? "High" : stock.changePercent > 1 ? "Medium" : "Low"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function MetricCard({ 
  icon: Icon, 
  label, 
  value, 
  subValue 
}: { 
  icon: React.ElementType
  label: string
  value: string
  subValue?: string 
}) {
  return (
    <div className="p-3 rounded-lg bg-muted/30 border border-border">
      <div className="flex items-center gap-2 mb-1">
        <Icon className="w-4 h-4 text-muted-foreground" />
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <p className="font-mono font-semibold">{value}</p>
      {subValue && <p className="text-xs text-muted-foreground mt-0.5">{subValue}</p>}
    </div>
  )
}
