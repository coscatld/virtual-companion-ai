<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-950 text-white p-4 relative overflow-hidden">
    <!-- Background Decor -->
    <div class="absolute inset-0 bg-gradient-to-br from-indigo-900/20 to-teal-900/20 z-0"></div>
    <div class="absolute top-10 left-10 w-96 h-96 bg-indigo-600 rounded-full mix-blend-multiply filter blur-3xl opacity-20"></div>

    <div class="relative z-10 w-full max-w-lg p-8 bg-gray-900/80 backdrop-blur-xl rounded-2xl border border-gray-800 shadow-2xl">
      <h2 class="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-teal-400 to-indigo-500 mb-6 text-center">Complete Your Profile</h2>
      <p class="text-gray-400 text-sm text-center mb-8">Personalize your virtual presence before entering the AI Hub.</p>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-1">Username</label>
          <input v-model="form.username" required class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-teal-500 outline-none text-white placeholder-gray-500" placeholder="e.g. johndoe">
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-1">Nickname</label>
          <input v-model="form.nickname" required class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-teal-500 outline-none text-white placeholder-gray-500" placeholder="Display name">
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-1">Gender</label>
            <select v-model.number="form.gender" class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-teal-500 outline-none text-white">
              <option value="0">Secret</option>
              <option value="1">Male</option>
              <option value="2">Female</option>
              <option value="3">Other</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-1">Birthday</label>
            <input v-model="form.birthday" type="date" class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-teal-500 outline-none text-white">
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-300 mb-1">Avatar URL (Optional)</label>
          <input v-model="form.avatarUrl" type="url" class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-teal-500 outline-none text-white placeholder-gray-500" placeholder="https://example.com/avatar.jpg">
        </div>

        <div v-if="errorMsg" class="text-red-400 text-sm">{{ errorMsg }}</div>

        <button type="submit" :disabled="isLoading" class="w-full mt-6 py-3 px-4 bg-gradient-to-r from-teal-500 to-indigo-600 hover:from-teal-400 hover:to-indigo-500 text-white font-medium rounded-lg shadow-lg transition-all flex justify-center items-center">
          <span v-if="isLoading" class="animate-spin mr-2">⚬</span>
          Enter the Hub
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { completeProfile } from '../api/auth'

const router = useRouter()
const isLoading = ref(false)
const errorMsg = ref('')

const form = reactive({
  username: '',
  nickname: '',
  gender: 0,
  birthday: '',
  avatarUrl: ''
})

const handleSubmit = async () => {
  errorMsg.value = ''
  isLoading.value = true
  try {
    await completeProfile(form)
    router.push('/dashboard')
  } catch (err: any) {
    errorMsg.value = err.message || 'Failed to update profile.'
  } finally {
    isLoading.value = false
  }
}
</script>
