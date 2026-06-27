import axios from 'axios'
import type { Stock, StockDaily, StrategyResult, BacktestResult } from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 股票列表
export const getStockList = async (params?: {
  page?: number
  pageSize?: number
  industry?: string
  keyword?: string
}) => {
  const res = await api.get<{ data: Stock[], total: number }>('/stocks', { params })
  return res.data
}

// 股票详情
export const getStockDetail = async (code: string) => {
  const res = await api.get<Stock>(`/stocks/${code}`)
  return res.data
}

// 股票历史数据
export const getStockHistory = async (code: string, days?: number) => {
  const res = await api.get<StockDaily[]>(`/stocks/${code}/history`, { params: { days } })
  return res.data
}

// 获取最新行情
export const getLatestQuotes = async (codes?: string[]) => {
  const res = await api.get<StockDaily[]>('/quotes/latest', { params: { codes: codes?.join(',') } })
  return res.data
}

// 策略选股
export const runStrategy = async (strategyName: string, params?: Record<string, any>) => {
  const res = await api.post<StrategyResult>(`/strategy/${strategyName}`, params)
  return res.data
}

// 获取策略列表
export const getStrategyList = async () => {
  const res = await api.get<{ name: string, description: string }[]>('/strategies')
  return res.data
}

// 回测
export const runBacktest = async (params: {
  strategy: string
  start_date: string
  end_date: string
  initial_capital: number
}) => {
  const res = await api.post<BacktestResult>('/backtest', params)
  return res.data
}

// 数据状态
export const getDataStatus = async () => {
  const res = await api.get<{ last_update: string, count: number }>('/data/status')
  return res.data
}

// 同步数据
export const syncData = async () => {
  const res = await api.post<{ message: string }>('/data/sync')
  return res.data
}

// 行业列表
export const getIndustryList = async () => {
  const res = await api.get<string[]>('/industries')
  return res.data
}

// 市场统计
export const getMarketStats = async () => {
  const res = await api.get<{
    up_count: number
    down_count: number
    flat_count: number
    limit_up: number
    limit_down: number
  }>('/market/stats')
  return res.data
}
