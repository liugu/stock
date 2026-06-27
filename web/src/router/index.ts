import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue')
    },
    {
      path: '/stocks',
      name: 'stocks',
      component: () => import('@/views/StockListView.vue')
    },
    {
      path: '/strategy',
      name: 'strategy',
      component: () => import('@/views/StrategyView.vue')
    },
    {
      path: '/combo',
      name: 'combo',
      component: () => import('@/views/ComboView.vue')
    },
    {
      path: '/analysis',
      name: 'analysis',
      component: () => import('@/views/AnalysisView.vue')
    },
    {
      path: '/backtest',
      name: 'backtest',
      component: () => import('@/views/BacktestView.vue')
    },
    {
      path: '/stock/:code',
      name: 'stock-detail',
      component: () => import('@/views/StockDetailView.vue')
    }
  ]
})

export default router
