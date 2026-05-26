"use client"

import { useState } from "react"
import { TrendingUp, TrendingDown, Activity, ChevronRight, Star } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"

interface StockData {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
  volume: string
  marketCap: string
  aiSentiment: "bullish" | "bearish" | "neutral"
  isWatchlisted: boolean
}

const mockStocks: StockData[] = [
  { symbol: "NVDA", name: "NVIDIA Corp", price: 875.42, change: 23.54, changePercent: 2.76, volume: "52.3M", marketCap: "2.16T", aiSentiment: "bullish", isWatchlisted: true },
  { symbol: "AAPL", name: "Apple Inc", price: 178.92, change: -1.24, changePercent: -0.69, volume: "48.2M", marketCap: "2.78T", aiSentiment: "neutral", isWatchlisted: true },
  { symbol: "MSFT", name: "Microsoft", price: 425.18, change: 5.67, changePercent: 1.35, volume: "22.1M", marketCap: "3.15T", aiSentiment: "bullish", isWatchlisted: false },
  { symbol: "GOOGL", name: "Alphabet Inc", price: 141.56, change: -2.34, changePercent: -1.63, volume: "28.4M", marketCap: "1.78T", aiSentiment: "bearish", isWatchlisted: false },
  { symbol: "TSLA", name: "Tesla Inc", price: 245.67, change: 12.89, changePercent: 5.54, volume: "112.5M", marketCap: "780B", aiSentiment: "bullish", isWatchlisted: true },
  { symbol: "META", name: "Meta Platforms", price: 512.34, change: 8.21, changePercent: 1.63, volume: "15.7M", marketCap: "1.31T", aiSentiment: "neutral", isWatchlisted: false },
]

export function StockSidebar() {
  const [selectedStock, setSelectedStock] = useState<string>("NVDA")

  return (
    <aside className="w-80 border-r border-border bg-sidebar flex flex-col h-full">
      <div className="p-4 border-b border-sidebar-border">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-sidebar-foreground">Stock Monitor</h2>
          <Badge variant="outline" className="text-primary border-primary/30 bg-primary/10">
            <Activity className="w-3 h-3 mr-1" />
            Live
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground mt-1">AI-powered analysis</p>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-2 space-y-1">
          {mockStocks.map((stock) => (
            <button
              key={stock.symbol}
              onClick={() => setSelectedStock(stock.symbol)}
              className={cn(
                "w-full p-3 rounded-lg text-left transition-all duration-200",
                "hover:bg-sidebar-accent",
                selectedStock === stock.symbol && "bg-sidebar-accent border border-sidebar-border"
              )}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  {stock.isWatchlisted && (
                    <Star className="w-3 h-3 text-warning fill-warning" />
                  )}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-sidebar-foreground">{stock.symbol}</span>
                      <Badge 
                        variant="outline" 
                        className={cn(
                          "text-[10px] px-1.5 py-0",
                          stock.aiSentiment === "bullish" && "text-success border-success/30 bg-success/10",
                          stock.aiSentiment === "bearish" && "text-destructive border-destructive/30 bg-destructive/10",
                          stock.aiSentiment === "neutral" && "text-muted-foreground border-muted-foreground/30"
                        )}
                      >
                        {stock.aiSentiment}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground truncate max-w-[120px]">{stock.name}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-mono font-medium text-sidebar-foreground">${stock.price.toFixed(2)}</p>
                  <div className={cn(
                    "flex items-center justify-end gap-1 text-xs",
                    stock.change >= 0 ? "text-success" : "text-destructive"
                  )}>
                    {stock.change >= 0 ? (
                      <TrendingUp className="w-3 h-3" />
                    ) : (
                      <TrendingDown className="w-3 h-3" />
                    )}
                    <span>{stock.change >= 0 ? "+" : ""}{stock.changePercent.toFixed(2)}%</span>
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </ScrollArea>

      {/* Selected Stock Detail */}
      {selectedStock && (
        <div className="p-4 border-t border-sidebar-border bg-sidebar-accent/50">
          {(() => {
            const stock = mockStocks.find(s => s.symbol === selectedStock)
            if (!stock) return null
            return (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{stock.symbol} Details</span>
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-sidebar/50 p-2 rounded">
                    <p className="text-muted-foreground">Volume</p>
                    <p className="font-mono font-medium">{stock.volume}</p>
                  </div>
                  <div className="bg-sidebar/50 p-2 rounded">
                    <p className="text-muted-foreground">Market Cap</p>
                    <p className="font-mono font-medium">{stock.marketCap}</p>
                  </div>
                </div>
              </div>
            )
          })()}
        </div>
      )}
    </aside>
  )
}
