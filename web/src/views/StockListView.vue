<template>
  <div class="stock-list-view">
    <!-- 搜索和筛选 -->
    <el-card class="filter-card">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-input v-model="searchKeyword" placeholder="搜索股票代码或名称" clearable @clear="handleSearch" @keyup.enter="handleSearch">
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
        <el-col :span="6">
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
        <el-table-column prop="industry" label="行业" width="120" />
        <el-table-column prop="market" label="市场" width="80" />
        <el-table-column label="操作" width="100">
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { useStockStore } from '@/stores/stock'
import * as api from '@/api'
import type { Stock } from '@/types'

const router = useRouter()
const stockStore = useStockStore()

const stocks = ref<Stock[]>([])
const industries = ref<string[]>([])
const loading = ref(false)
const searchKeyword = ref('')
const selectedIndustry = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const fetchStocks = async () => {
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

const goToDetail = (row: Stock) => {
  router.push(`/stock/${row.code}`)
}

onMounted(() => {
  fetchStocks()
  api.getIndustryList().then(res => industries.value = res)
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
</style>