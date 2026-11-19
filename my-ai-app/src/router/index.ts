import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/useUserStore'
import { HttpError } from '../api/http'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'Login', component: () => import('../views/LoginView.vue') },
    { path: '/register', name: 'Register', component: () => import('../views/RegisterView.vue') },
    { path: '/onboarding', name: 'Onboarding', component: () => import('../views/OnboardingView.vue'), meta: { requiresAuth: true } },
    { path: '/settings/briefing', name: 'BriefingSettings', component: () => import('../views/BriefingView.vue'), meta: { requiresAuth: true } },
    { path: '/chat', name: 'Chat', component: () => import('../views/ChatView.vue'), meta: { requiresAuth: true, requiresCompanion: true } },
    { path: '/:pathMatch(.*)*', redirect: '/chat' },
  ],
})

router.beforeEach(async (to) => {
  const user = useUserStore()
  if (!to.meta.requiresAuth) return user.isLoggedIn ? { name: 'Chat' } : true
  if (!user.isLoggedIn) return { name: 'Login' }

  try {
    await user.loadAccount()
  } catch (error) {
    if (error instanceof HttpError && error.status === 401) {
      user.clearUser()
      return { name: 'Login' }
    }
    user.accountError = '暂时无法加载账户。确认服务已启动后重试。'
    return true
  }

  if (to.meta.requiresCompanion && !user.companion) return { name: 'Onboarding' }
})

export default router
