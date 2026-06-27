<template>
  <div class="stock-detail-view">
    <el-page-header @back="goBack" :title="stockCode">
      <template #content>
        <span class="stock-title">{{ stockName }} ({{ stockCode }})</span>
      </template>
    </el-page-header>

    <!-- 股票信息卡片 -->
    <el-card class="info-card" v-if="stockInfo">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-statistic title="最新价" :value="stockInfo.close" :precision="2" suffix="元" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="涨跌幅" :value="stockInfo.change_percent" :precision="2" suffix="%" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="成交量" :value="formatVolume(stockInfo.volume)" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="换手率" :value="stockInfo.turnover_rate" :precision="2" suffix="%" />
        </el-col>
      </el-row>
      <el-row :gutter="20" style="margin-top: 20px">
        <el-col :span="6">
          <el-statistic title="今开" :value="stockInfo.open" :precision="2" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="最高" :value="stockInfo.high" :precision="2" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="最低" :value="stockInfo.low" :precision="2" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="成交额" :value="formatAmount(stockInfo.amount)" />
        </el-col>
      </el-row>
    </el-card>

    <!-- K线图 -->
    <el-card class="chart-card">
      <template #header>
        <div class="card-header">
          <span>K线走势</span>
          <el-radio-group v-model="chartPeriod" @change="loadChartData">
            <el-radio-button label="30">30天</el-radio-button>
            <el-radio-button label="60">60天</el-radio-button>
            <el-radio-button label="120">120天</el-radio-button>
            <el-radio-button label="250">250天</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <div ref="klineChartRef" class="chart-container"></div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import * as api from '@/api'
import type { StockDaily } from '@/types'

const route = useRoute()
const router = useRouter()

const stockCode = ref(route.params.code as string)
const stockName = ref('')
const stockInfo = ref<StockDaily | null>(null)
const chartPeriod = ref(60)
const historyData = ref<StockDaily[]>([])

const klineChartRef = ref<HTMLElement>()

const goBack = () => {
  router.back()
}

const formatVolume = (vol: number) => {
  if (vol >= 100000000) return (vol / 100000000).toFixed(2) + '亿'
  if (vol >= 10000) return (vol / 10000).toFixed(2) + '万'
  return vol.toString()
}

const formatAmount = (amt: number) => {
  if (amt >= 100000000) return (amt / 100000000).toFixed(2) + '亿'
  if (amt >= 10000) return (amt / 10000).toFixed(2) + '万'
  return amt.toString()
}

const loadChartData = async () => {
  try {
    const data = await api.getStockHistory(stockCode.value, chartPeriod.value)
    historyData.value = data
    if (data.length > 0) {
      stockInfo.value = data[data.length - 1]
      stockName.value = data[0].name
      await nextTick()
      renderKline()
    }
  } catch (e) {
    console.error('Failed to load data:', e)
  }
}

const renderKline = () => {
  if (!klineChartRef.value || historyData.value.length === 0) return
  
  const chart = echarts.init(klineChartRef.value)
  const dates = historyData.value.map(d => d.date)
  const ohlc = historyData.value.map(d => [d.open, d.close, d.low, d.high])
  const volumes = historyData.value.map(d => d.volume)
  
  // 计算MA均线
  const calcMA = (data: number[], period: number) => {
    const result: (number | null)[] = []
    for (let i = 0; i < data.length; i++) {
      if (i < period - 1) {
        result.push(null)
      } else {
        const sum = data.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0)
        result.push(sum / period)
      }
    }
    return result
  }
  
  const closes = historyData.value.map(d => d.close)
  const ma5 = calcMA(closes, 5)
  const ma20 = calcMA(closes, 20)
  
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        const idx = params[0].dataIndex
        const d = historyData.value[idx]
        return `
          <div style="font-weight:bold">${d.date}</div>
          <div>开盘: ${d.open.toFixed(2)}</div>
          <div>收盘: ${d.close.toFixed(2)}</div>
          <div>最高: ${d.high.toFixed(2)}</div>
          <div>最低: ${d.low.toFixed(2)}</div>
          <div>成交量: ${formatVolume(d.volume)}</div>
          <div>涨跌幅: ${d.change_percent?.toFixed(2) || '-'}%</div>
        `
      }
    },
    legend: { data: ['K线', 'MA5', 'MA20'], top: 10 },
    grid: [
      { left: '10%', right: '10%', top: '15%', height: '55%' },
      { left: '10%', right: '10%', top: '75%', height: '15%' }
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0 },
      { type: 'category', data: dates, gridIndex: 1 }
    ],
    yAxis: [
      { type: 'value', scale: true, gridIndex: 0 },
      { type: 'value', gridIndex: 1 }
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 50, end: 100 },
      { show: true, xAxisIndex: [0, 1], type: 'slider', top: '92%' }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: ohlc,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: '#f56c6c',
          color0: '#67c23a',
          borderColor: '#f56c6c',
          borderColor0: '#67c23a'
        }
      },
      {
        name: 'MA5',
        type: 'line',
        data: ma5,
        smooth: true,
        lineStyle: { width: 1 },
        showSymbol: false
      },
      {
        name: 'MA20',
        type: 'line',
        data: ma20,
        smooth: true,
        lineStyle: { width: 1 },
        showSymbol: false
      },
      {
        name: '成交量',
        type: 'bar',
        data: volumes,
        xAxisIndex: 1,
        yAxisIndex: 1
      }
    ]
  })
}

onMounted(() => {
  loadChartData()
})
</script>

<style scoped>
.stock-title {
  font-size: 20px;
  font-weight: bold;
}

.info-card {
  margin-top: 20px;
}

.chart-card {
  margin-top: 20px;
}

.chart-container {
  height: 500px;
}
</style>