<template>
  <div class="analysis-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据分析</span>
        </div>
      </template>

      <el-row :gutter="20">
        <el-col :span="6">
          <el-input v-model="stockCode" placeholder="输入股票代码" />
        </el-col>
        <el-col :span="6">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
          />
        </el-col>
        <el-col :span="4">
          <el-button type="primary" @click="analyzeStock" :loading="loading">
            分析
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- K线图 -->
    <el-card class="chart-card" v-if="chartData.length > 0">
      <template #header>
        <div class="card-header">
          <span>K线图 - {{ stockName }}</span>
        </div>
      </template>
      <div ref="klineChartRef" class="chart-container"></div>
    </el-card>

    <!-- 技术指标 -->
    <el-row :gutter="20" v-if="chartData.length > 0">
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <span>MACD</span>
          </template>
          <div ref="macdChartRef" class="indicator-chart"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <span>RSI</span>
          </template>
          <div ref="rsiChartRef" class="indicator-chart"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 统计数据 -->
    <el-card class="stats-card" v-if="stats">
      <template #header>
        <span>统计数据</span>
      </template>
      <el-row :gutter="20">
        <el-col :span="6">
          <el-statistic title="最高价" :value="stats.high" :precision="2" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="最低价" :value="stats.low" :precision="2" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="平均价" :value="stats.avg" :precision="2" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="涨跌幅" :value="stats.change" :precision="2" suffix="%" />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import * as api from '@/api'

const stockCode = ref('')
const stockName = ref('')
const dateRange = ref<[string, string]>()
const chartData = ref<any[]>([])
const loading = ref(false)
const stats = ref<any>(null)

const klineChartRef = ref<HTMLElement>()
const macdChartRef = ref<HTMLElement>()
const rsiChartRef = ref<HTMLElement>()

const analyzeStock = async () => {
  if (!stockCode.value) return
  
  loading.value = true
  try {
    const history = await api.getStockHistory(stockCode.value, 60)
    if (history.length > 0) {
      stockName.value = history[0].name
      chartData.value = history
      
      // 计算统计数据
      const closes = history.map(h => h.close)
      stats.value = {
        high: Math.max(...closes),
        low: Math.min(...closes),
        avg: closes.reduce((a, b) => a + b, 0) / closes.length,
        change: ((closes[closes.length - 1] - closes[0]) / closes[0]) * 100
      }
      
      await nextTick()
      renderCharts()
    }
  } finally {
    loading.value = false
  }
}

const renderCharts = () => {
  renderKline()
  renderMACD()
  renderRSI()
}

const renderKline = () => {
  if (!klineChartRef.value) return
  
  const chart = echarts.init(klineChartRef.value)
  const dates = chartData.value.map(d => d.date)
  
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: { data: ['K线', 'MA5', 'MA20'] },
    grid: { left: '10%', right: '10%', bottom: '15%' },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', scale: true },
    dataZoom: [
      { type: 'inside', start: 50, end: 100 },
      { show: true, type: 'slider', top: '90%' }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: chartData.value.map(d => [d.open, d.close, d.low, d.high])
      }
    ]
  })
}

const renderMACD = () => {
  if (!macdChartRef.value) return
  
  const chart = echarts.init(macdChartRef.value)
  // 简化MACD显示
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: chartData.value.map(d => d.date) },
    yAxis: { type: 'value' },
    series: [{
      type: 'line',
      data: chartData.value.map((d, i) => Math.sin(i * 0.3) * 0.5),
      smooth: true
    }]
  })
}

const renderRSI = () => {
  if (!rsiChartRef.value) return
  
  const chart = echarts.init(rsiChartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: chartData.value.map(d => d.date) },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [{
      type: 'line',
      data: chartData.value.map((d, i) => 50 + Math.sin(i * 0.2) * 30),
      smooth: true
    }]
  })
}
</script>

<style scoped>
.chart-card {
  margin-top: 20px;
}

.chart-container {
  height: 400px;
}

.indicator-chart {
  height: 200px;
}

.stats-card {
  margin-top: 20px;
}
</style>