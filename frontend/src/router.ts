import { createRouter, createWebHistory } from 'vue-router'
import type {
  NavigationGuardReturn,
  RouteLocationNormalizedGeneric,
  RouteRecordNormalized,
  Router,
} from 'vue-router'
import { useAuthStore } from './stores/auth'

// 为路由 meta 扩展自定义字段类型
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
  }
}

const router: Router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/upload' },
    { path: '/login', name: 'login', component: () => import('./views/LoginView.vue') },
    { path: '/register', name: 'register', component: () => import('./views/RegisterView.vue') },
    {
      path: '/upload',
      name: 'upload',
      component: () => import('./views/UploadView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/result/:id',
      name: 'result',
      component: () => import('./views/ResultView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('./views/HistoryView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('./views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/chat/:analysisId/:resumeId',
      name: 'chat',
      component: () => import('./views/ChatView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach((to: RouteLocationNormalizedGeneric): NavigationGuardReturn => {
  const requiresAuth = to.matched.some(
    (record: RouteRecordNormalized) => record.meta.requiresAuth === true,
  )
  if (requiresAuth && !useAuthStore().isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
