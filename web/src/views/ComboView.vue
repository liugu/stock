<template>
  <div class="combo-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>组合选股</span>
          <el-button type="primary" @click="runComboFilter" :loading="loading">
            开始筛选
          </el-button>
        </div>
      </template>

      <!-- 条件列表 -->
      <div class="filter-list">
        <el-card v-for="(filter, index) in filters" :key="index" class="filter-item" shadow="hover">
          <el-row :gutter="20" align="middle">
            <el-col :span="4">
              <el-select v-model="filter.field" placeholder="选择指标" @change="updateFilter(index)">
                <el-option label="涨跌幅" value="change_percent" />
                <el-option label="换手率" value="turnover_rate" />
                <el-option label="成交量" value="volume" />
                <el-option label="成交额" value="amount" />
                <el-option label="现价" value="close" />
              </el-select>
            </el-col>
            <el-col :span="3">
              <el-select v-model="filter.op" placeholder="条件">
                <el-option label="大于" value=">" />
                <el-option label="小于" value="<" />
                <el-option label="等于" value="=" />
                <el-option label="区间" value="between" />
              </el-select>
            </el-col>
            <el-col :span="5">
              <div v-if="filter.op === 'between'" style="display: flex; gap: 8px;">
                <el-input-number v-model="filter.min" :step="getStep(filter.field)" placeholder="最小值" />
                <span style="line-height: 32px;">-</span>
                <el-input-number v-model="filter.max" :step="getStep(filter.field)" placeholder="最大值" />
              </div>
              <el-input-number v-else v-model="filter.value" :step="getStep(filter.field)" placeholder="数值" />
            </el-col>
            <el-col :span="4">
              <el-radio-group v-model="filter.logic">
                <el-radio label="AND">且</el-radio>
                <el-radio label="OR">或</el-radio>
              </el-radio-group>
            </el-col>
            <el-col :span="2">
              <el-button type="danger" :icon="Delete" circle @click="removeFilter(index)" />
            </el-col>
          </el-row>
        </el-card>

        <el-button type="primary" plain @click="addFilter" style="margin-top: 16px;">
          + 添加条件
        </el-button>
      </div>

      <!-- 快捷模板 -->
      <el-divider />
      <div class="templates">
        <span style="margin-right: 12px;">快捷模板：</span>
        <el-button size="small" @click="applyTemplate('涨停板')">涨停板</el-button>
        <el-button size="small" @click="applyTemplate('放量上涨')">放量上涨</el-button>
        <el-button size="small" @click="applyTemplate('强势股')">强势股</el-button>
        <el-button size="small" @click="applyTemplate('活跃股')">活跃股</el-button>
        <el-button size="small" @click="applyTemplate('低价股')">低价股</el-button>
      </div>
    </el-card>

    <!-- 筛选结果 -->
    <el-card class="result-card" v-if="results.length > 0">
      <template #header>
        <div class="card-header">
          <span>筛选结果 ({{ results.length }} 只)</span>
          <div>
            <el-button type="success" @click="exportResults">导出CSV</el-button>
          </div>
        </div>
      </template>

      <el-table :data="results" stripe style="width: 100%" max-height="500">
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
        <el-table-column prop="turnover_rate" label="换手率" width="100">
          <template #default="{ row }">
            {{ row.turnover_rate?.toFixed(2) || '-' }}%
          </template>
        </el-table-column>
        <el-table-column prop="volume" label="成交量" width="120">
          <template #default="{ row }">
            {{ formatVolume(row.volume) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button type="primary" link @click="goToDetail(row.code)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import type { StockDaily } from '@/types'

const router = useRouter()

interface Filter {
  field: string
  op: string
  value: number
  min: number
  max: number
  logic: 'AND' | 'OR'
}

const filters = reactive<Filter[]>([])
const results = ref<StockDaily[]>([])
const loading = ref(false)

const getStep = (field: string) => {
  if (field === 'change_percent' || field === 'turnover_rate') return 0.5
  if (field === 'close') return 0.1
  return 1
}

const addFilter = () => {
  filters.push({
    field: 'change_percent',
    op: '>',
    value: 0,
    min: 0,
    max: 10,
    logic: 'AND'
  })
}

const removeFilter = (index: number) => {
  filters.splice(index, 1)
}

const updateFilter = (index: number) => {
  // 重置值
  filters[index].value = 0
  filters[index].min = 0
  filters[index].max = 10
}

const applyTemplate = (name: string) => {
  filters.length = 0
  
  const templates: Record<string, Filter[]> = {
    '涨停板': [
      { field: 'change_percent', op: 'between', value: 9.5, min: 9.5, max: 20, logic: 'AND' }
    ],
    '放量上涨': [
      { field: 'change_percent', op: '>', value: 3, min: 0, max: 0, logic: 'AND' },
      { field: 'turnover_rate', op: '>', value: 5, min: 0, max: 0, logic: 'AND' }
    ],
    '强势股': [
      { field: 'change_percent', op: '>', value: 5, min: 0, max: 0, logic: 'AND' },
      { field: 'turnover_rate', op: '>', value: 3, min: 0, max: 0, logic: 'AND' }
    ],
    '活跃股': [
      { field: 'turnover_rate', op: '>', value: 10, min: 0, max: 0, logic: 'AND' }
    ],
    '低价股': [
      { field: 'close', op: 'between', value: 0, min: 2, max: 10, logic: 'AND' },
      { field: 'change_percent', op: '>', value: 0, min: 0, max: 0, logic: 'AND' }
    ]
  }
  
  if (templates[name]) {
    templates[name].forEach(f => filters.push({ ...f }))
    ElMessage.success(`已加载模板：${name}`)
  }
}

const runComboFilter = async () => {
  if (filters.length === 0) {
    ElMessage.warning('请至少添加一个筛选条件')
    return
  }
  
  loading.value = true
  try {
    const response = await fetch('/api/combo/filter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filters })
    })
    const data = await response.json()
    
    if (data.success) {
      results.value = data.stocks
      ElMessage.success(`筛选完成，共 ${data.stocks.length} 只股票`)
    } else {
      ElMessage.error(data.message || '筛选失败')
    }
  } catch (e) {
    ElMessage.error('筛选失败，请重试')
  } finally {
    loading.value = false
  }
}

const formatVolume = (vol: number) => {
  if (!vol) return '-'
  if (vol >= 100000000) return (vol / 100000000).toFixed(2) + '亿'
  if (vol >= 10000) return (vol / 10000).toFixed(2) + '万'
  return vol.toString()
}

const goToDetail = (code: string) => {
  router.push(`/stock/${code}`)
}

const exportResults = () => {
  if (results.value.length === 0) return
  
  const headers = ['代码', '名称', '现价', '涨跌幅', '换手率', '成交量']
  const data = results.value.map(s => 
    [s.code, s.name, s.close, `${s.change_percent}%`, `${s.turnover_rate}%`, formatVolume(s.volume)].join(',')
  ).join('\n')
  
  const blob = new Blob([headers.join(',') + '\n' + data], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `组合选股_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.filter-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-item {
  margin-bottom: 0;
}

.templates {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.result-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.positive {
  color: #f56c6c;
}

.negative {
  color: #67c23a;
}
</style>
