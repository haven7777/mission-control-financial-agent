"use client"

import { useState, useRef, useEffect } from "react"
import { Search, TrendingUp, Cpu, Rocket, Zap, ChevronRight, Sparkles } from "lucide-react"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface SearchHomeProps {
  onSearch: (query: string) => void
}

const popularStocks = [
  { symbol: "NVDA", name: "NVIDIA Corp", change: "+3.2%" },
  { symbol: "AAPL", name: "Apple Inc", change: "+1.1%" },
  { symbol: "MSFT", name: "Microsoft", change: "+0.8%" },
  { symbol: "GOOGL", name: "Alphabet", change: "+2.4%" },
  { symbol: "TSLA", name: "Tesla Inc", change: "-1.2%" },
  { symbol: "AMZN", name: "Amazon", change: "+1.8%" },
]

const categories = [
  {
    id: "ai",
    label: "AI & Machine Learning",
    icon: Cpu,
    color: "text-agent-data",
    bgColor: "bg-agent-data/10 hover:bg-agent-data/20",
    stocks: ["NVDA", "GOOGL", "MSFT", "AMD", "PLTR"],
  },
  {
    id: "space",
    label: "Space & Aerospace",
    icon: Rocket,
    color: "text-agent-sentiment",
    bgColor: "bg-agent-sentiment/10 hover:bg-agent-sentiment/20",
    stocks: ["RKLB", "LMT", "BA", "NOC", "RTX"],
  },
  {
    id: "tech",
    label: "Big Tech",
    icon: Zap,
    color: "text-agent-manager",
    bgColor: "bg-agent-manager/10 hover:bg-agent-manager/20",
    stocks: ["AAPL", "META", "AMZN", "NFLX", "CRM"],
  },
  {
    id: "energy",
    label: "Clean Energy",
    icon: Sparkles,
    color: "text-primary",
    bgColor: "bg-primary/10 hover:bg-primary/20",
    stocks: ["ENPH", "SEDG", "FSLR", "NEE", "PLUG"],
  },
]

export function SearchHome({ onSearch }: SearchHomeProps) {
  const [query, setQuery] = useState("")
  const [isFocused, setIsFocused] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      onSearch(query.trim())
    }
  }

  const handleStockClick = (symbol: string) => {
    onSearch(symbol)
  }

  const handleCategoryClick = (category: typeof categories[0]) => {
    onSearch(category.stocks.join(", "))
  }

  const filteredStocks = query
    ? popularStocks.filter(
        (s) =>
          s.symbol.toLowerCase().includes(query.toLowerCase()) ||
          s.name.toLowerCase().includes(query.toLowerCase())
      )
    : []

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4 py-12">
      {/* Logo/Title */}
      <div className="text-center mb-12">
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="relative">
            <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-primary" />
            </div>
            <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-success animate-pulse" />
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-balance">
            Mission Control
          </h1>
        </div>
        <p className="text-muted-foreground text-lg max-w-md mx-auto text-pretty">
          AI-powered financial analysis. Enter a stock symbol or explore market sectors.
        </p>
      </div>

      {/* Search Bar */}
      <div className="w-full max-w-2xl mb-12">
        <form onSubmit={handleSubmit} className="relative">
          <div
            className={cn(
              "relative rounded-2xl border-2 transition-all duration-300",
              isFocused
                ? "border-primary bg-card shadow-lg shadow-primary/10"
                : "border-border bg-card/50 hover:border-muted-foreground/30"
            )}
          >
            <Search
              className={cn(
                "absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 transition-colors",
                isFocused ? "text-primary" : "text-muted-foreground"
              )}
            />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setTimeout(() => setIsFocused(false), 200)}
              placeholder="Enter stock ticker (e.g., NVDA)..."
              className="w-full bg-transparent py-5 pl-14 pr-32 text-lg text-foreground placeholder:text-muted-foreground focus:outline-none"
            />
            <button
              type="submit"
              disabled={!query.trim()}
              className={cn(
                "absolute right-3 top-1/2 -translate-y-1/2 px-6 py-2.5 rounded-xl font-medium transition-all",
                query.trim()
                  ? "bg-primary text-primary-foreground hover:bg-primary/90"
                  : "bg-muted text-muted-foreground cursor-not-allowed"
              )}
            >
              Analyze
            </button>
          </div>

          {/* Search Suggestions Dropdown */}
          {isFocused && filteredStocks.length > 0 && (
            <Card className="absolute top-full left-0 right-0 mt-2 p-2 border-border bg-card z-50">
              {filteredStocks.map((stock) => (
                <button
                  key={stock.symbol}
                  type="button"
                  onClick={() => handleStockClick(stock.symbol)}
                  className="w-full flex items-center justify-between px-4 py-3 rounded-lg hover:bg-secondary transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-semibold text-foreground">
                      {stock.symbol}
                    </span>
                    <span className="text-muted-foreground">{stock.name}</span>
                  </div>
                  <span
                    className={cn(
                      "font-mono text-sm",
                      stock.change.startsWith("+") ? "text-success" : "text-destructive"
                    )}
                  >
                    {stock.change}
                  </span>
                </button>
              ))}
            </Card>
          )}
        </form>
      </div>

      {/* Popular Stocks */}
      <div className="w-full max-w-4xl mb-12">
        <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-4 text-center">
          Popular Stocks
        </h2>
        <div className="flex flex-nowrap justify-center gap-2">
          {popularStocks.map((stock) => (
            <button
              key={stock.symbol}
              onClick={() => handleStockClick(stock.symbol)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-secondary/50 hover:bg-secondary border border-transparent hover:border-border transition-all"
            >
              <span className="font-mono font-semibold text-foreground text-sm">
                {stock.symbol}
              </span>
              <span
                className={cn(
                  "font-mono text-xs",
                  stock.change.startsWith("+") ? "text-success" : "text-destructive"
                )}
              >
                {stock.change}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Category Cards */}
      <div className="w-full max-w-4xl">
        <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-4 text-center">
          Explore Sectors
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {categories.map((category) => {
            const Icon = category.icon
            return (
              <button
                key={category.id}
                onClick={() => handleCategoryClick(category)}
                className={cn(
                  "group p-5 rounded-xl border border-border transition-all text-left",
                  category.bgColor
                )}
              >
                <div className="flex items-start justify-between mb-3">
                  <Icon className={cn("w-6 h-6", category.color)} />
                  <ChevronRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <h3 className="font-semibold text-foreground mb-1">{category.label}</h3>
                <p className="text-xs text-muted-foreground font-mono">
                  {category.stocks.slice(0, 3).join(" · ")}
                </p>
              </button>
            )
          })}
        </div>
      </div>


    </div>
  )
}
