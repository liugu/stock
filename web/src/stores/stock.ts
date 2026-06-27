import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Stock, StockDaily, StrategyResult } from '@/types'
import * as api from '@/api'

export const useStockStore = defineStore('stock', () => {
  // State
  const stocks = ref<Stock[]>([])
  const selectedStocks = ref<StockDaily[]>([])
  const dataStatus = ref('')
  const loading = ref(false)
  const totalStocks = ref(0)

  // Actions
  const fetchStocks = async (params?: { page?: number, pageSize?: number, keyword?: string }) => {
    loading.value = true
    try {
      const res = await api.getStockList(params)
      stocks.value = res.data
      totalStocks.value = res.total
    } finally {
      loading.value = false
    }
  }

  const fetchDataStatus = async () => {
    try {
      const res = await api.getDataStatus()
      dataStatus.value = res.last_update
    } catch {
      dataStatus.value = ''
    }
  }

  const syncData = async () => {
    loading.value = true
    try {
      await api.syncData()
      await fetchDataStatus()
    } finally {
      loading.value = false
    }
  }

  const runStrategy = async (name: string, params?: Record<string, any>) => {
    loading.value = true
    try {
      const result = await api.runStrategy(name, params)
      selectedStocks.value = result.stocks
      return result
    } finally {
      loading.value = false
    }
  }

  const getLatestQuotes = async (codes?: string[]) => {
    return await api.getLatestQuotes(codes)
  }

  return {
    stocks,
    selectedStocks,
    dataStatus,
    loading,
    totalStocks,
    fetchStocks,
    fetchDataStatus,
    syncData,
    runStrategy,
    getLatestQuotes
  }
})
