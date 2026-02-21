<template>
  <div class="min-h-screen bg-gray-900 text-white flex">
    <!-- Sidebar -->
    <aside class="w-64 bg-gray-800 border-r border-gray-700 flex flex-col">
      <div class="h-16 flex items-center px-4 font-bold text-xl border-b border-gray-700 text-blue-400">
        Virtual AI Hub
      </div>
      <nav class="flex-1 py-4 space-y-1">
        <router-link to="/dashboard" class="block px-4 py-2 hover:bg-gray-700 mx-2 rounded transition-colors" active-class="bg-blue-600 hover:bg-blue-500">
          Templates
        </router-link>
        <router-link to="/chat" class="block px-4 py-2 hover:bg-gray-700 mx-2 rounded transition-colors" active-class="bg-blue-600 hover:bg-blue-500">
          Chat Room
        </router-link>
        <router-link to="/briefing" class="block px-4 py-2 hover:bg-gray-700 mx-2 rounded transition-colors" active-class="bg-blue-600 hover:bg-blue-500">
          Daily Briefing
        </router-link>
      </nav>
      <div class="p-4 border-t border-gray-700 text-sm text-gray-400">
        GA-Agent
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col overflow-hidden">
      <!-- Navbar -->
      <header class="h-16 flex items-center justify-between px-6 bg-gray-800 border-b border-gray-700 shadow-sm">
        <h2 class="font-semibold text-lg">{{ $route.meta.title || 'Dashboard' }}</h2>
        <div class="flex items-center space-x-4">
          <button @click="handleLogout" class="text-sm px-4 py-2 rounded border border-gray-600 hover:bg-gray-700 transition">
            Logout
          </button>
        </div>
      </header>

      <!-- Content Area -->
      <div class="flex-1 overflow-auto p-6 bg-gray-900">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '../stores/useAuth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>
