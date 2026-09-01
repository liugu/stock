<template>
  <div class="stock-list-view">
    <!-- 搜索和筛选 -->
    <el-card class="filter-card">
      <el-row :gutter="16">
        <el-col :span="6">
          <el-input v-model="searchKeyword" placeholder="搜索股票代码或名称" clearable @clear="handleSearch" @keyup.enter="handleSearch">
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
        <el-col :span="5">
          <el-select v-model="selectedIndustry" placeholder="选择行业" clearable @change="handleSearch">
            <el-option v-for="ind in industries" :key="ind" :label="ind" :value="ind" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
        </el-col>
        <el-col :span="9" v-if="filterType">
          <el-tag type="warning" closable @close="clearFilter" size="large">
            {{ filterLabel }}
          </el-tag>
        </el-col>
      </el-row>
    </el-card>

    <!-- 股票列表 -->
    <el-card>
      <el-table 
        :data="stocks" 
        stripe 
        style="width: 100%"
        v-loading="loading"
        @row-click="goToDetail"
      >
        <el-table-column prop="code" label="代码" width="100" fixed />
        <el-table-column prop="name" label="名称" width="120" />
        <el-table-column prop="close" label="现价" width="100">
          <template #default="{ row }">
            <span :class="(row.change_percent ?? 0) >= 0 ? 'positive' : 'negative'">
              {{ row.close?.toFixed(2) || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="change_percent" label="涨跌幅" width="100" sortable>
          <template #default="{ row }">
            <span :class="(row.change_percent ?? 0) >= 0 ? 'positive' : 'negative'">
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
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button type="primary" link @click.stop="goToDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchStocks"
          @current-change="fetchStocks"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { useStockStore } from '@/stores/stock'
import * as api from '@/api'
import type { Stock, StockDaily } from '@/types'

const route = useRoute()
const router = useRouter()
const stockStore = useStockStore()

const stocks = ref<(Stock | StockDaily)[]>([])
const industries = ref<string[]>([])
const loading = ref(false)
const searchKeyword = ref('')
const selectedIndustry = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterType = ref('')

const filterLabel = computed(() => {
  const labels: Record<string, string> = {
    up: '📈 上涨股票',
    down: '📉 下跌股票',
    flat: '➖ 平盘股票',
    limit_up: '🚀 涨停股票',
    limit_down: '💥 跌停股票',
    strong_up: '🔥 强势股（涨超5%）'
  }
  return labels[filterType.value] || ''
})

const clearFilter = () => {
  filterType.value = ''
  router.push('/stocks')
}

const formatVolume = (vol: number) => {
  if (vol >= 100000000) return (vol / 100000000).toFixed(2) + '亿'
  if (vol >= 10000) return (vol / 10000).toFixed(2) + '万'
  return vol?.toString() || '0'
}

const formatAmount = (amt: number) => {
  if (amt >= 100000000) return (amt / 100000000).toFixed(2) + '亿'
  if (amt >= 10000) return (amt / 10000).toFixed(2) + '万'
  return amt?.toString() || '0'
}

const fetchFilteredStocks = async () => {
  loading.value = true
  try {
    const res = await api.getMarketStocks(filterType.value, currentPage.value, pageSize.value)
    stocks.value = res.data
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const fetchStocks = async () => {
  if (filterType.value) {
    await fetchFilteredStocks()
    return
  }
  loading.value = true
  try {
    const res = await api.getStockList({
      page: currentPage.value,
      pageSize: pageSize.value,
      keyword: searchKeyword.value,
      industry: selectedIndustry.value
    })
    stocks.value = res.data
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchStocks()
}

const goToDetail = (row: any) => {
  router.push(`/stock/${row.code}`)
}

// 监听路由变化
watch(() => route.query.filter, (newFilter) => {
  filterType.value = (newFilter as string) || ''
  currentPage.value = 1
  fetchStocks()
})

onMounted(() => {
  filterType.value = (route.query.filter as string) || ''
  fetchStocks()
  if (!filterType.value) {
    api.getIndustryList().then(res => industries.value = res)
  }
})
</script>

<style scoped>
.filter-card {
  margin-bottom: 20px;
}
.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.el-table {
  cursor: pointer;
}
.positive { color: #f56c6c; font-weight: bold; }
.negative { color: #67c23a; font-weight: bold; }
</style>
