<script setup lang="ts">
import Sidebar from '../components/Sidebar.vue'
import Navbar from '../components/Navbar.vue'
</script>

<template>
  <div class="flex h-screen w-screen bg-gray-50 overflow-hidden font-sans">
    <!-- 左侧菜单栏 -->
    <Sidebar />
    
    <!-- 右侧内容区 -->
    <div class="flex flex-col flex-1 overflow-hidden relative">
      <Navbar />
      
      <!-- 主内容视图 -->
      <main class="flex-1 overflow-y-auto p-6 md:p-8">
        <div class="max-w-7xl mx-auto">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
