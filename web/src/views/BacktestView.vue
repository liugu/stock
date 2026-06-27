<template>
  <div class="backtest-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>策略回测</span>
        </div>
      </template>

      <el-form :model="form" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="选择策略">
              <el-select v-model="form.strategy" style="width: 100%">
                <el-option v-for="s in strategies" :key="s.name" :label="s.description" :value="s.name" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="初始资金">
              <el-input-number v-model="form.initial_capital" :min="10000" :step="10000" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="开始日期">
              <el-date-picker v-model="form.start_date" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束日期">
              <el-date-picker v-model="form.end_date" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item>
          <el-button type="primary" @click="runBacktest" :loading="loading">
            开始回测
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 回测结果 -->
    <el-card class="result-card" v-if="result">
      <template #header>
        <span>回测结果</span>
      </template>

      <el-row :gutter="20" class="stats-row">
        <el-col :span="6">
          <el-statistic title="总收益率" :value="result.total_return" :precision="2" suffix="%">
            <template #suffix>
              <span :class="result.total_return >= 0 ? 'positive' : 'negative'">%</span>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="年化收益" :value="result.annual_return" :precision="2" suffix="%" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="最大回撤" :value="result.max_drawdown" :precision="2" suffix="%" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="夏普比率" :value="result.sharpe_ratio" :precision="2" />
        </el-col>
      </el-row>

      <el-row :gutter="20">
        <el-col :span="12">
          <el-statistic title="胜率" :value="result.win_rate" :precision="2" suffix="%" />
        </el-col>
        <el-col :span="12">
          <el-statistic title="交易次数" :value="result.trade_count" />
        </el-col>
      </el-row>

      <!-- 交易记录 -->
      <el-divider>交易记录</el-divider>
      <el-table :data="result.trades" stripe max-height="400">
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column prop="action" label="操作" width="80">
          <template #default="{ row }">
            <el-tag :type="row.action === 'buy' ? 'success' : 'danger'">
              {{ row.action === 'buy' ? '买入' : '卖出' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="code" label="代码" width="100" />
        <el-table-column prop="price" label="价格" width="100">
          <template #default="{ row }">{{ row.price.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="shares" label="股数" width="100" />
        <el-table-column prop="profit" label="盈亏">
          <template #default="{ row }">
            <span v-if="row.profit" :class="row.profit >= 0 ? 'positive' : 'negative'">
              {{ row.profit >= 0 ? '+' : '' }}{{ row.profit.toFixed(2) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as api from '@/api'
import type { BacktestResult } from '@/types'

const strategies = ref<{ name: string, description: string }[]>([])
const loading = ref(false)
const result = ref<BacktestResult | null>(null)

const form = ref({
  strategy: 'ma_cross',
  initial_capital: 100000,
  start_date: '',
  end_date: ''
})

const runBacktest = async () => {
  if (!form.value.start_date || !form.value.end_date) {
    ElMessage.warning('请选择日期范围')
    return
  }
  
  loading.value = true
  try {
    result.value = await api.runBacktest(form.value)
    ElMessage.success('回测完成')
  } catch (e) {
    ElMessage.error('回测失败，请重试')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  strategies.value = await api.getStrategyList()
  // 设置默认日期
  const today = new Date()
  const yearAgo = new Date(today)
  yearAgo.setFullYear(yearAgo.getFullYear() - 1)
  form.value.end_date = today.toISOString().slice(0, 10)
  form.value.start_date = yearAgo.toISOString().slice(0, 10)
})
</script>

<style scoped>
.result-card {
  margin-top: 20px;
}

.stats-row {
  margin-bottom: 20px;
}

.positive { color: #f56c6c; }
.negative { color: #67c23a; }
</style>