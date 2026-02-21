<script setup lang="ts">
import { MoonIcon, BellIcon, Cog6ToothIcon } from '@heroicons/vue/24/outline'
</script>

<template>
  <header class="bg-white border-b border-gray-100 flex items-center justify-between px-6 h-16 shrink-0 relative z-10">
    <!-- 移动端占位（若加 hamburger menu） -->
    <div class="flex items-center gap-4 text-gray-800 font-semibold text-lg md:hidden">
      AI App
    </div>

    <!-- 面包屑或其他顶部内容（PC端预留） -->
    <div class="hidden md:block text-gray-800 font-medium text-sm">
      Workspace / <span class="text-gray-500">Dashboard</span>
    </div>

    <!-- 右侧功能区 -->
    <div class="flex items-center gap-4">
      <button class="p-2 rounded-full hover:bg-gray-100 transition-colors text-gray-500">
        <MoonIcon class="w-5 h-5" />
      </button>
      <button class="p-2 rounded-full hover:bg-gray-100 transition-colors text-gray-500 relative">
        <BellIcon class="w-5 h-5" />
        <span class="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
      </button>
      <button class="p-2 rounded-full hover:bg-gray-100 transition-colors text-gray-500">
        <Cog6ToothIcon class="w-5 h-5" />
      </button>
      
      <!-- 用户头像 -->
      <div class="hidden md:flex items-center gap-3 pl-2 border-l border-gray-200 ml-2">
        <div class="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 text-white flex items-center justify-center font-bold text-sm shadow-sm ring-2 ring-white">
          A
        </div>
        <span class="text-sm font-medium text-gray-700">Admin User</span>
      </div>
    </div>
  </header>
</template>
