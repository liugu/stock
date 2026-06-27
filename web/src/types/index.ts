export interface Stock {
  id: number
  code: string
  name: string
  industry?: string
  market?: string
}

export interface StockDaily {
  stock_id: number
  code: string
  name: string
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number
  change_percent: number
  turnover_rate?: number
}

export interface StrategyResult {
  strategy_name: string
  stocks: StockDaily[]
  params: Record<string, any>
  timestamp: string
}

export interface BacktestResult {
  strategy_name: string
  total_return: number
  annual_return: number
  max_drawdown: number
  sharpe_ratio: number
  win_rate: number
  trade_count: number
  trades: TradeRecord[]
}

export interface TradeRecord {
  date: string
  action: 'buy' | 'sell'
  code: string
  price: number
  shares: number
  profit?: number
}
