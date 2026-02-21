<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  HomeIcon,
  CpuChipIcon,
  FolderOpenIcon,
  CogIcon,
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon
} from '@heroicons/vue/24/outline'

const isCollapsed = ref(false)
const router = useRouter()
const route = useRoute()

const menus = [
  { name: 'Dashboard', path: '/dashboard', icon: HomeIcon },
  { name: 'AI Agents', path: '/agents', icon: CpuChipIcon },
  { name: 'Knowledge Base', path: '/knowledge', icon: FolderOpenIcon },
  { name: 'Settings', path: '/settings', icon: CogIcon }
]

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}

const navigateTo = (path: string) => {
  router.push(path)
}
</script>

<template>
  <aside 
    class="bg-white border-r border-gray-100 flex flex-col transition-all duration-300 relative"
    :class="isCollapsed ? 'w-20' : 'w-64'"
  >
    <!-- Logo 区 -->
    <div class="h-16 flex items-center justify-center border-b border-gray-100 px-4 shrink-0 cursor-pointer" @click="navigateTo('/')">
      <div 
        class="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0 shadow-sm shadow-indigo-200"
      >
        <span class="text-white font-bold text-sm">AI</span>
      </div>
      <span 
        v-show="!isCollapsed" 
        class="ml-3 font-semibold text-gray-800 tracking-tight text-lg whitespace-nowrap overflow-hidden"
      >
        AI Console
      </span>
    </div>

    <!-- 菜单区 -->
    <div class="flex-1 overflow-y-auto py-6 px-3 flex flex-col gap-1">
      <div 
        v-for="item in menus" 
        :key="item.path"
        @click="navigateTo(item.path)"
        class="flex items-center px-3 py-2.5 rounded-xl cursor-pointer transition-colors group relative"
        :class="[
          route.path.startsWith(item.path) 
            ? 'bg-indigo-50 text-indigo-600' 
            : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
        ]"
      >
        <component :is="item.icon" class="w-5 h-5 shrink-0" 
          :class="route.path.startsWith(item.path) ? 'text-indigo-600' : 'text-gray-400 group-hover:text-gray-600'" 
        />
        
        <span 
          v-show="!isCollapsed" 
          class="ml-3 text-sm font-medium whitespace-nowrap"
        >
          {{ item.name }}
        </span>

        <!-- 悬浮提示框 (当菜单折叠时) -->
        <div 
          v-if="isCollapsed" 
          class="absolute left-14 bg-gray-900 text-white text-xs px-2 py-1 rounded shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all whitespace-nowrap z-50"
        >
          {{ item.name }}
        </div>
      </div>
    </div>

    <!-- 底部控制栏 -->
    <div class="h-14 border-t border-gray-100 flex items-center shrink-0 px-4" :class="isCollapsed ? 'justify-center' : 'justify-end'">
      <button 
        @click="toggleSidebar"
        class="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors"
      >
        <ChevronDoubleRightIcon v-if="isCollapsed" class="w-5 h-5" />
        <ChevronDoubleLeftIcon v-else class="w-5 h-5" />
      </button>
    </div>
  </aside>
</template>
