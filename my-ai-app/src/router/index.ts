/**
 * Vue Router 路由配置
 * - 路由懒加载（代码分割）
 * - 导航守卫：需要登录的页面检查 token，需要 AI Profile 的页面额外检查 hasAiProfile
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useUserStore } from '../stores/useUserStore'

// ── 路由表 ──
const routes: RouteRecordRaw[] = [
  // ── 公开页面 ──
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/RegisterView.vue'),
    meta: { requiresAuth: false },
  },

  // ── 需要登录 ──
  {
    path: '/onboarding',
    name: 'Onboarding',
    component: () => import('../views/OnboardingView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings/briefing',
    name: 'BriefingSettings',
    component: () => import('../views/BriefingView.vue'),
    meta: { requiresAuth: true },
  },

  // ── 需要登录 + AI Profile ──
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('../views/ChatView.vue'),
    meta: { requiresAuth: true, requiresAiProfile: true },
  },

  // ── 默认重定向 ──
  {
    path: '/',
    redirect: '/chat',
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ── 全局前置守卫 ──
router.beforeEach((to) => {
  // 注意：守卫内不能直接用 inject，需要直接实例化 store
  const userStore = useUserStore()

  // 1. 需要登录但未登录 → 重定向到 /login
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }

  // 2. 需要 AI Profile 但未设置 → 重定向到 /onboarding
  if (to.meta.requiresAiProfile && !userStore.hasAiProfile) {
    return { name: 'Onboarding' }
  }

  // 3. 已登录用户访问登录/注册页 → 重定向到 /chat
  if (!to.meta.requiresAuth && userStore.isLoggedIn && (to.name === 'Login' || to.name === 'Register')) {
    return { name: 'Chat' }
  }
})

export default router
