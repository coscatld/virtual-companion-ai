<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { fetchAgents, deleteAgent, type Agent } from '../api/agent'
import { 
  MagnifyingGlassIcon, 
  PlusIcon,
  EllipsisVerticalIcon,
  TrashIcon,
  PlayIcon,
  StopIcon
} from '@heroicons/vue/24/outline'

const agents = ref<Agent[]>([])
const loading = ref(true)
const searchQuery = ref('')

const loadData = async () => {
  loading.value = true
  try {
    agents.value = await fetchAgents()
  } catch (error) {
    console.error('Failed to load agents', error)
  } finally {
    loading.value = false
  }
}

const filteredAgents = computed(() => {
  if (!searchQuery.value) return agents.value
  return agents.value.filter(a => 
    a.name.toLowerCase().includes(searchQuery.value.toLowerCase()) || 
    a.model.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

const handleDelete = async (id: string) => {
  if (confirm('Are you sure you want to delete this agent?')) {
    const success = await deleteAgent(id)
    if (success) {
      agents.value = agents.value.filter(a => a.id !== id)
    }
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header区 -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 tracking-tight">AI Agents</h1>
        <p class="text-sm text-gray-500 mt-1">Manage and orchestrate your deployed AI models and behaviors.</p>
      </div>
      
      <div class="flex items-center gap-3">
        <!-- 搜索框 -->
        <div class="relative max-w-xs">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MagnifyingGlassIcon class="h-4 w-4 text-gray-400" />
          </div>
          <input 
            v-model="searchQuery"
            type="text" 
            placeholder="Search agents..." 
            class="block w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors bg-white shadow-sm"
          >
        </div>
        
        <!-- 新增按钮 -->
        <button class="inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors shadow-sm focus:ring-2 focus:ring-offset-2 focus:ring-indigo-600">
          <PlusIcon class="w-4 h-4" />
          <span>New Agent</span>
        </button>
      </div>
    </div>

    <!-- 顶部数据概览卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col hover:shadow-md transition-shadow">
        <span class="text-sm font-medium text-gray-500">Total Agents</span>
        <div class="mt-2 flex items-baseline gap-2">
          <span class="text-3xl font-bold text-gray-900">{{ agents.length }}</span>
          <span class="text-xs font-semibold text-green-600 bg-green-50 px-2 py-0.5 rounded-full">+12%</span>
        </div>
      </div>
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col hover:shadow-md transition-shadow">
        <span class="text-sm font-medium text-gray-500">Active Sessions</span>
        <div class="mt-2 flex items-baseline gap-2">
          <span class="text-3xl font-bold text-gray-900">1,204</span>
        </div>
      </div>
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col hover:shadow-md transition-shadow">
        <span class="text-sm font-medium text-gray-500">API Usage (Today)</span>
        <div class="mt-2 flex items-baseline gap-2">
          <span class="text-3xl font-bold text-gray-900">45.2k</span>
          <span class="text-sm text-gray-500 font-medium">/ 100k limits</span>
        </div>
      </div>
    </div>

    <!-- 数据列表视图 -->
    <div class="bg-white border border-gray-100 shadow-sm rounded-2xl overflow-hidden relative min-h-[400px]">
      
      <!-- 加载状态 -->
      <div v-if="loading" class="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-10">
        <div class="flex flex-col items-center">
          <div class="w-8 h-8 border-4 border-indigo-100 border-t-indigo-600 rounded-full animate-spin"></div>
          <span class="mt-3 text-sm text-gray-500 font-medium">Loading agents...</span>
        </div>
      </div>

      <!-- 表头 -->
      <div class="grid grid-cols-12 gap-4 px-6 py-4 border-b border-gray-100 bg-gray-50/50 text-xs font-semibold text-gray-500 uppercase tracking-wider">
        <div class="col-span-5 md:col-span-4">Agent Name</div>
        <div class="hidden md:block col-span-3">Model Engine</div>
        <div class="col-span-4 md:col-span-2">Status</div>
        <div class="hidden md:block col-span-2">Last Updated</div>
        <div class="col-span-3 md:col-span-1 text-right">Actions</div>
      </div>

      <!-- 数据空状态 -->
      <div v-if="!loading && filteredAgents.length === 0" class="flex flex-col items-center justify-center py-20 text-center">
        <div class="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mb-4">
          <CpuChipIcon class="w-8 h-8 text-gray-400" />
        </div>
        <h3 class="text-sm font-medium text-gray-900">No agents found</h3>
        <p class="text-sm text-gray-500 mt-1">Try adjusting your search or create a new agent.</p>
      </div>

      <!-- 列表内容 -->
      <div class="divide-y divide-gray-50">
        <div 
          v-for="agent in filteredAgents" 
          :key="agent.id"
          class="grid grid-cols-12 gap-4 px-6 py-4 items-center hover:bg-gray-50/50 transition-colors group"
        >
          <!-- Agent Name -->
          <div class="col-span-5 md:col-span-4 flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center shrink-0 border border-indigo-100 shadow-sm">
              <CpuChipIcon class="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <div class="text-sm font-semibold text-gray-900">{{ agent.name }}</div>
              <div class="text-xs text-gray-500 font-medium mt-0.5">{{ agent.id }}</div>
            </div>
          </div>

          <!-- Model Engine -->
          <div class="hidden md:flex col-span-3 items-center">
            <span class="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200">
              {{ agent.model }}
            </span>
          </div>

          <!-- Status -->
          <div class="col-span-4 md:col-span-2 flex items-center">
            <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border"
                 :class="agent.status === 'running' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-gray-50 text-gray-600 border-gray-200'">
              <span class="w-1.5 h-1.5 rounded-full" :class="agent.status === 'running' ? 'bg-emerald-500 animate-pulse' : 'bg-gray-400'"></span>
              {{ agent.status === 'running' ? 'Running' : 'Stopped' }}
            </div>
          </div>

          <!-- Last Updated -->
          <div class="hidden md:flex col-span-2 items-center text-sm text-gray-500">
            {{ agent.updatedAt }}
          </div>

          <!-- Actions -->
          <div class="col-span-3 md:col-span-1 flex items-center justify-end gap-2">
            <!-- 启动/停止 -->
            <button class="p-1.5 rounded-lg text-gray-400 hover:text-gray-900 hover:bg-white border border-transparent hover:border-gray-200 hover:shadow-sm transition-all focus:outline-none">
              <StopIcon v-if="agent.status === 'running'" class="w-4 h-4" />
              <PlayIcon v-else class="w-4 h-4" />
            </button>
            
            <!-- 删除 -->
            <button @click="handleDelete(agent.id)" class="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 border border-transparent hover:border-red-100 transition-all focus:outline-none">
              <TrashIcon class="w-4 h-4" />
            </button>

            <!-- 更多选项 -->
            <button class="p-1.5 rounded-lg text-gray-400 hover:text-gray-900 hover:bg-gray-100 transition-colors focus:outline-none">
              <EllipsisVerticalIcon class="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
