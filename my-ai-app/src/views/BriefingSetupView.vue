<template>
  <div class="max-w-3xl mx-auto py-8">
    <div class="bg-gray-800 border border-gray-700 rounded-2xl p-8 shadow-2xl relative overflow-hidden">
      <!-- Decorative element -->
      <div class="absolute top-0 right-0 w-64 h-64 bg-blue-600 rounded-full mix-blend-multiply filter blur-3xl opacity-10 translate-x-1/2 -translate-y-1/2 pointer-events-none"></div>

      <div class="mb-8 relative z-10">
        <h2 class="text-3xl font-bold text-white flex items-center gap-3">
          <svg class="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          Daily Briefing Setup
        </h2>
        <p class="text-gray-400 mt-2">Schedule your AI to wake you up with a personalized briefing report every morning.</p>
      </div>

      <form @submit.prevent="handleSave" class="space-y-6 relative z-10">
        <div class="bg-gray-900/50 p-6 rounded-xl border border-gray-700/50 space-y-5">
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Target City</label>
            <input 
              v-model="form.city" 
              required 
              class="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-white placeholder-gray-500 transition-shadow" 
              placeholder="e.g. Beijing, New York"
            >
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Trigger Time (HH:mm)</label>
            <input 
              v-model="form.time" 
              type="time" 
              required 
              class="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-white transition-shadow"
            >
            <p class="text-xs text-gray-500 mt-1">The system will automatically convert this to a cron expression.</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">Report Save Path</label>
            <input 
              v-model="form.filePath" 
              required 
              class="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-white placeholder-gray-500 transition-shadow" 
              placeholder="/tmp/daily_briefing.txt"
            >
          </div>
        </div>

        <div v-if="successMsg" class="text-green-400 text-sm bg-green-900/20 p-3 rounded-lg border border-green-800">
          ✓ {{ successMsg }}
        </div>
        <div v-if="errorMsg" class="text-red-400 text-sm bg-red-900/20 p-3 rounded-lg border border-red-800">
          ⚠ {{ errorMsg }}
        </div>

        <div class="flex justify-end pt-4">
          <button 
            type="submit" 
            :disabled="isLoading" 
            class="px-8 py-3 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg shadow-lg shadow-blue-900/20 transition-all flex items-center justify-center disabled:opacity-70 disabled:cursor-not-allowed"
          >
            <span v-if="isLoading" class="animate-spin mr-2">⚬</span>
            Save Configuration
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { setAlarm } from '../api/briefing'

const isLoading = ref(false)
const successMsg = ref('')
const errorMsg = ref('')

const form = reactive({
  city: 'Beijing',
  time: '08:30',
  filePath: '/tmp/daily_briefing.txt'
})

const handleSave = async () => {
  successMsg.value = ''
  errorMsg.value = ''
  isLoading.value = true
  
  try {
    const res: any = await setAlarm(form)
    // Based on the Java Controller: it returns a String directly
    successMsg.value = res || 'Daily briefing configured successfully!'
  } catch (err: any) {
    errorMsg.value = err.message || 'Failed to save configuration. Is Java server running?'
  } finally {
    isLoading.value = false
  }
}
</script>
