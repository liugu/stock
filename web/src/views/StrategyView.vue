<template>
  <div class="strategy-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>策略选股</span>
          <el-button type="primary" @click="runSelectedStrategy" :loading="loading">
            执行选股
          </el-button>
        </div>
      </template>

      <el-row :gutter="20">
        <!-- 策略选择 -->
        <el-col :span="6">
          <el-select v-model="selectedStrategy" placeholder="选择策略" style="width: 100%">
            <el-option v-for="s in strategies" :key="s.name" :label="s.description" :value="s.name" />
          </el-select>
        </el-col>

        <!-- 策略参数 -->
        <el-col :span="18">
          <div v-if="selectedStrategy === 'ma_cross'" class="params">
            <el-input-number v-model="params.short_period" :min="5" :max="60" placeholder="短期均线" />
            <el-input-number v-model="params.long_period" :min="10" :max="250" placeholder="长期均线" />
          </div>
          <div v-else-if="selectedStrategy === 'volume_break'" class="params">
            <el-input-number v-model="params.volume_ratio" :min="1" :max="10" :step="0.5" placeholder="量比阈值" />
          </div>
          <div v-else-if="selectedStrategy === 'rsi'" class="params">
            <el-input-number v-model="params.period" :min="5" :max="30" placeholder="RSI周期" />
            <el-input-number v-model="params.oversold" :min="10" :max="30" placeholder="超卖阈值" />
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 选股结果 -->
    <el-card class="result-card" v-if="results.length > 0">
      <template #header>
        <div class="card-header">
          <span>选股结果 ({{ results.length }} 只)</span>
          <el-button type="success" @click="exportResults">导出</el-button>
        </div>
      </template>

      <el-table :data="results" stripe style="width: 100%">
        <el-table-column prop="code" label="代码" width="100" fixed />
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
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button type="primary" link @click="goToDetail(row.code)">详情</el-button>
            <el-button type="warning" link @click="addToWatchlist(row)">加入自选</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 空状态 -->
    <el-empty v-else description="请选择策略并执行选股" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useStockStore } from '@/stores/stock'
import * as api from '@/api'
import type { StockDaily } from '@/types'

const router = useRouter()
const stockStore = useStockStore()

const strategies = ref<{ name: string, description: string }[]>([])
const selectedStrategy = ref('ma_cross')
const params = ref<Record<string, any>>({
  short_period: 5,
  long_period: 20,
  volume_ratio: 2,
  period: 14,
  oversold: 30
})
const results = ref<StockDaily[]>([])
const loading = ref(false)

const runSelectedStrategy = async () => {
  loading.value = true
  try {
    const result = await stockStore.runStrategy(selectedStrategy.value, params.value)
    results.value = result.stocks
    ElMessage.success(`选股完成，共选出 ${result.stocks.length} 只股票`)
  } catch (e) {
    ElMessage.error('选股失败，请重试')
  } finally {
    loading.value = false
  }
}

const formatVolume = (vol: number) => {
  if (vol >= 100000000) return (vol / 100000000).toFixed(2) + '亿'
  if (vol >= 10000) return (vol / 10000).toFixed(2) + '万'
  return vol.toString()
}

const goToDetail = (code: string) => {
  router.push(`/stock/${code}`)
}

const addToWatchlist = (stock: StockDaily) => {
  ElMessage.success(`已将 ${stock.name}(${stock.code}) 加入自选`)
}

const exportResults = () => {
  const data = results.value.map(s => `${s.code},${s.name},${s.close},${s.change_percent}%`).join('\n')
  const blob = new Blob([`代码,名称,价格,涨跌幅\n${data}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `选股结果_${selectedStrategy.value}_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  strategies.value = await api.getStrategyList()
})
</script>

<style scoped>
.result-card {
  margin-top: 20px;
}

.params {
  display: flex;
  gap: 16px;
  align-items: center;
}
</style>