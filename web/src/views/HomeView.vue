<template>
  <div class="home-view">
    <!-- 市场概览 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card-clickable" @click="goToFilter('up')">
          <div class="stat-card">
            <div class="stat-icon up">
              <el-icon :size="32"><TrendCharts /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ marketStats.up_count }}</div>
              <div class="stat-label">上涨</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card-clickable" @click="goToFilter('down')">
          <div class="stat-card">
            <div class="stat-icon down">
              <el-icon :size="32"><TrendCharts /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ marketStats.down_count }}</div>
              <div class="stat-label">下跌</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card-clickable" @click="goToFilter('flat')">
          <div class="stat-card">
            <div class="stat-icon flat">
              <el-icon :size="32"><Minus /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ marketStats.flat_count }}</div>
              <div class="stat-label">平盘</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card-clickable" @click="goToFilter('limit_up')">
          <div class="stat-card">
            <div class="stat-icon limit-up">
              <el-icon :size="32"><Top /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ marketStats.limit_up }}</div>
              <div class="stat-label">涨停</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷策略 -->
    <el-card class="strategy-card">
      <template #header>
        <div class="card-header">
          <span>快捷选股</span>
        </div>
      </template>
      <el-row :gutter="16">
        <el-col :span="6" v-for="strategy in quickStrategies" :key="strategy.name">
          <el-button 
            type="primary" 
            :loading="loadingStrategy === strategy.name"
            @click="runQuickStrategy(strategy.name)"
            class="strategy-btn"
          >
            {{ strategy.label }}
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 今日热门 -->
    <el-card class="hot-stocks-card">
      <template #header>
        <div class="card-header">
          <span>今日热门</span>
          <el-tag type="success">{{ hotStocks.length }} 只</el-tag>
        </div>
      </template>
      <el-table :data="hotStocks" stripe style="width: 100%">
        <el-table-column prop="code" label="代码" width="100" />
        <el-table-column prop="name" label="名称" width="120" />
        <el-table-column prop="close" label="现价" width="100">
          <template #default="{ row }">
            <span :class="row.change_percent >= 0 ? 'positive' : 'negative'">
              {{ row.close?.toFixed(2) || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="change_percent" label="涨跌幅" width="100">
          <template #default="{ row }">
            <span :class="row.change_percent >= 0 ? 'positive' : 'negative'">
              {{ row.change_percent >= 0 ? '+' : '' }}{{ row.change_percent?.toFixed(2) || '-' }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="volume" label="成交量" width="120">
          <template #default="{ row }">
            {{ formatVolume(row.volume) }}
          </template>
        </el-table-column>
        <el-table-column prop="turnover_rate" label="换手率" width="100">
          <template #default="{ row }">
            {{ row.turnover_rate?.toFixed(2) || '-' }}%
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="成交额">
          <template #default="{ row }">
            {{ formatAmount(row.amount) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 涨幅排行图表 -->
    <el-card class="chart-card">
      <template #header>
        <div class="card-header">
          <span>涨跌幅分布</span>
        </div>
      </template>
      <div ref="chartRef" class="chart-container"></div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { TrendCharts, Minus, Top } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { useStockStore } from '@/stores/stock'
import { useRouter } from 'vue-router'
import * as api from '@/api'
import type { StockDaily } from '@/types'

const stockStore = useStockStore()
const router = useRouter()

const marketStats = ref({
  up_count: 0,
  down_count: 0,
  flat_count: 0,
  limit_up: 0,
  limit_down: 0
})

const hotStocks = ref<StockDaily[]>([])
const loadingStrategy = ref('')
const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null
let isMounted = true

const quickStrategies = [
  { name: 'hot', label: '今日热门' },
  { name: 'limit_up', label: '涨停板' },
  { name: 'ma_cross', label: '均线金叉' },
  { name: 'volume_break', label: '放量突破' }
]

const runQuickStrategy = async (name: string) => {
  loadingStrategy.value = name
  try {
    const result = await stockStore.runStrategy(name)
    hotStocks.value = result.stocks
  } finally {
    loadingStrategy.value = ''
  }
}

const formatVolume = (vol: number) => {
  if (!vol) return '-'
  if (vol >= 100000000) return (vol / 100000000).toFixed(2) + '亿'
  if (vol >= 10000) return (vol / 10000).toFixed(2) + '万'
  return vol.toString()
}

const formatAmount = (amt: number) => {
  if (!amt) return '-'
  if (amt >= 100000000) return (amt / 100000000).toFixed(2) + '亿'
  if (amt >= 10000) return (amt / 10000).toFixed(2) + '万'
  return amt.toString()
}

const initChart = async () => {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  
  // 获取涨跌幅分布数据
  try {
    const quotes = await api.getLatestQuotes()
    if (!isMounted) return  // 组件已卸载不继续
    
    const ranges = [
      { name: '涨停', min: 9.9, max: 20 },
      { name: '7%-10%', min: 7, max: 9.9 },
      { name: '5%-7%', min: 5, max: 7 },
      { name: '3%-5%', min: 3, max: 5 },
      { name: '1%-3%', min: 1, max: 3 },
      { name: '0%-1%', min: 0, max: 1 },
      { name: '-1%-0%', min: -1, max: 0 },
      { name: '-3%--1%', min: -3, max: -1 },
      { name: '-5%--3%', min: -5, max: -3 },
      { name: '-7%--5%', min: -7, max: -5 },
      { name: '-10%--7%', min: -10, max: -7 },
      { name: '跌停', min: -20, max: -10 }
    ]
    
    const data = ranges.map(r => {
      return quotes.filter(q => q.change_percent >= r.min && q.change_percent < r.max).length
    })
    
    chartInstance.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: ranges.map(r => r.name),
        axisLabel: { rotate: 45 }
      },
      yAxis: { type: 'value', name: '股票数' },
      series: [{
        type: 'bar',
        data: data.map((value, index) => ({
          value,
          itemStyle: {
            color: index < 6 ? '#f56c6c' : index === 5 ? '#e6a23c' : '#67c23a'
          }
        }))
      }]
    })
  } catch (e) {
    console.error('Failed to load chart data:', e)
  }
}

const goToFilter = (filter: string) => {
  router.push({ path: '/stocks', query: { filter } })
}

// 组件卸载时只设标记，防止异步回调操作已卸载的DOM
// 不手动 dispose echarts，Vue 会自然清理 DOM，避免 'vnode is null' 错误
onUnmounted(() => {
  isMounted = false
  chartInstance = null
})

onMounted(async () => {
  try {
    marketStats.value = await api.getMarketStats()
    const result = await stockStore.runStrategy('hot')
    hotStocks.value = result.stocks
    initChart()
  } catch (e) {
    console.error('Failed to load data:', e)
  }
})
</script>

<style scoped>
.home-view {
  padding: 0;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-card-clickable {
  cursor: pointer;
  transition: transform 0.2s;
}
.stat-card-clickable:hover {
  transform: translateY(-2px);
}

.stat-icon {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-icon.up { background: linear-gradient(135deg, #f56c6c, #e91e63); }
.stat-icon.down { background: linear-gradient(135deg, #67c23a, #4caf50); }
.stat-icon.flat { background: linear-gradient(135deg, #909399, #607d8b); }
.stat-icon.limit-up { background: linear-gradient(135deg, #ff5722, #f44336); }

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.strategy-card {
  margin-bottom: 20px;
}

.strategy-btn {
  width: 100%;
  height: 48px;
  font-size: 14px;
}

.hot-stocks-card {
  margin-bottom: 20px;
}

.chart-card {
  margin-bottom: 20px;
}

.chart-container {
  height: 300px;
}
</style>