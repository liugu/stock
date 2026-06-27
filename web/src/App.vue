<template>
  <el-container class="layout-container">
    <el-aside width="220px">
      <div class="logo">
        <h1>📈 智能选股</h1>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#001529"
        text-color="#fff"
        active-text-color="#1890ff"
      >
        <el-menu-item index="/">
          <el-icon><House /></el-icon>
          <span>首页概览</span>
        </el-menu-item>
        <el-menu-item index="/stocks">
          <el-icon><List /></el-icon>
          <span>股票列表</span>
        </el-menu-item>
        <el-menu-item index="/strategy">
          <el-icon><TrendCharts /></el-icon>
          <span>策略选股</span>
        </el-menu-item>
        <el-menu-item index="/combo">
          <el-icon><Filter /></el-icon>
          <span>组合选股</span>
        </el-menu-item>
        <el-menu-item index="/analysis">
          <el-icon><DataAnalysis /></el-icon>
          <span>数据分析</span>
        </el-menu-item>
        <el-menu-item index="/backtest">
          <el-icon><Timer /></el-icon>
          <span>回测中心</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header>
        <div class="header-content">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentPageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
          <div class="header-right">
            <el-tag type="success" v-if="dataStatus">
              数据已更新: {{ dataStatus }}
            </el-tag>
            <el-button type="primary" :icon="Refresh" @click="refreshData">
              同步数据
            </el-button>
          </div>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { House, List, TrendCharts, DataAnalysis, Timer, Refresh, Filter } from '@element-plus/icons-vue'
import { useStockStore } from '@/stores/stock'

const route = useRoute()
const stockStore = useStockStore()

const activeMenu = computed(() => route.path)
const currentPageTitle = computed(() => {
  const titles: Record<string, string> = {
    '/': '首页概览',
    '/stocks': '股票列表',
    '/strategy': '策略选股',
    '/combo': '组合选股',
    '/analysis': '数据分析',
    '/backtest': '回测中心'
  }
  return titles[route.path] || ''
})

const dataStatus = ref('')

const refreshData = async () => {
  await stockStore.syncData()
}

onMounted(async () => {
  await stockStore.fetchDataStatus()
  dataStatus.value = stockStore.dataStatus
})
</script>

<style scoped>
.layout-container {
  height: 100%;
}

.el-aside {
  background-color: #001529;
  height: 100%;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.logo h1 {
  font-size: 20px;
  font-weight: 600;
}

.el-header {
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
}

.header-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.el-main {
  background: #f0f2f5;
  padding: 24px;
}
</style>
