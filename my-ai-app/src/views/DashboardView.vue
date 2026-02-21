<template>
  <div class="max-w-6xl mx-auto space-y-8">
    <div class="flex justify-between items-end">
      <div>
        <h1 class="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">AI Templates</h1>
        <p class="text-gray-400 mt-2">Choose an AI personality or build your own.</p>
      </div>
      <button @click="showCustomModal = true" class="px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-600 rounded-lg shadow transition">
        + Custom AI
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="text-blue-400 text-center py-12 animate-pulse">
      Loading Templates...
    </div>

    <!-- Error State -->
    <div v-else-if="errorMsg" class="text-red-400 text-center py-12 bg-red-900/20 border border-red-800 rounded-lg">
      {{ errorMsg }}
    </div>

    <!-- Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="template in templates" :key="template.id" class="group bg-gray-800 border border-gray-700 rounded-xl overflow-hidden hover:border-blue-500 transition-colors shadow-lg relative">
        <div class="absolute inset-0 bg-gradient-to-t from-gray-900 via-transparent to-transparent opacity-80 z-0"></div>
        <img :src="template.avatarUrl || 'https://via.placeholder.com/400x200/2D3748/FFFFFF?text=AI'" class="w-full h-48 object-cover filter brightness-75 group-hover:brightness-100 transition-all duration-300" />
        
        <div class="p-5 relative z-10 w-full flex flex-col h-40 justify-between bg-gray-800/90 backdrop-blur">
          <div>
            <h3 class="text-xl font-bold text-white mb-1">{{ template.name }}</h3>
            <p class="text-sm text-gray-400 line-clamp-2">{{ template.description }}</p>
          </div>
          <div class="flex justify-between items-center mt-4">
            <span class="text-xs bg-blue-900/50 text-blue-300 px-2 py-1 rounded">Preset</span>
            <button @click="handleUseTemplate(template.id)" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded shadow transition">
              Use Template
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Notification Toast -->
    <div v-if="toastMsg" class="fixed bottom-6 right-6 bg-blue-600 text-white px-6 py-3 rounded-lg shadow-xl animate-fade-in-up">
      {{ toastMsg }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getTemplates, useTemplate } from '../api/template'

const router = useRouter()
const templates = ref<any[]>([])
const isLoading = ref(true)
const errorMsg = ref('')
const toastMsg = ref('')
const showCustomModal = ref(false)

const loadTemplates = async () => {
  try {
    const res: any = await getTemplates()
    templates.value = res.data || []
  } catch (err: any) {
    errorMsg.value = err.message || 'Failed to load templates'
  } finally {
    isLoading.value = false
  }
}

const handleUseTemplate = async (templateId: number) => {
  try {
    await useTemplate({ templateId })
    showToast('Template APPLIED! Ready for chat.')
    setTimeout(() => {
       router.push('/chat')
    }, 1500)
  } catch(err: any) {
    showToast(`Error: ${err.message}`)
  }
}

const showToast = (msg: string) => {
  toastMsg.value = msg
  setTimeout(() => toastMsg.value = '', 3000)
}

onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in-up {
  animation: fadeInUp 0.3s ease-out forwards;
}
</style>
