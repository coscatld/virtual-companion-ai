import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/useAuth'

import DashboardLayout from '../layouts/DashboardLayout.vue'

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/login',
            name: 'Login',
            component: () => import('../views/LoginView.vue'),
            meta: { requiresAuth: false }
        },
        {
            path: '/profile-setup',
            name: 'ProfileSetup',
            component: () => import('../views/ProfileSetupView.vue'),
            meta: { requiresAuth: true }
        },
        {
            path: '/',
            component: DashboardLayout,
            redirect: '/dashboard',
            meta: { requiresAuth: true },
            children: [
                {
                    path: 'dashboard',
                    name: 'Dashboard',
                    component: () => import('../views/DashboardView.vue'),
                    meta: { title: '控制面板' }
                },
                {
                    path: 'chat',
                    name: 'Chat',
                    component: () => import('../views/ChatView.vue'),
                    meta: { title: '聊天室' }
                },
                {
                    path: 'briefing',
                    name: 'Briefing',
                    component: () => import('../views/BriefingSetupView.vue'),
                    meta: { title: '每日简报' }
                },
                {
                    path: 'companion',
                    name: 'Companion',
                    component: () => import('../views/AvatarCompanionView.vue'),
                    meta: { title: '语音陪伴 (适老版)' }
                },
                {
                    path: 'digital-human',
                    name: 'DigitalHuman',
                    component: () => import('../views/DigitalHuman.vue'),
                    meta: { title: '3D数字人 (V1.0)' }
                }
            ]
        }
    ]
})

router.beforeEach((to, from, next) => {
    const authStore = useAuthStore()
    if (to.meta.requiresAuth && !authStore.isLoggedIn) {
        next('/login')
    } else if (to.path === '/login' && authStore.isLoggedIn) {
        next('/dashboard')
    } else {
        next()
    }
})

export default router
