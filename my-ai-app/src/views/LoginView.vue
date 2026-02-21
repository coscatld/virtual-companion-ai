<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-950 text-white relative overflow-hidden">
    <!-- Background Decor -->
    <div class="absolute inset-0 bg-gradient-to-br from-blue-900/20 to-purple-900/20 z-0"></div>
    <div class="absolute -top-40 -left-40 w-96 h-96 bg-blue-600 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"></div>
    <div class="absolute -bottom-40 -right-40 w-96 h-96 bg-purple-600 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>

    <div class="relative z-10 w-full max-w-md p-8 bg-gray-900/80 backdrop-blur-xl rounded-2xl border border-gray-800 shadow-2xl">
      <div class="flex flex-col items-center mb-8">
        <h1 class="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-500 mb-2">Virtual AI Hub</h1>
        <p class="text-gray-400 text-sm">Welcome back, please sign in to your AI companion.</p>
      </div>

      <!-- Tabs -->
      <div class="flex space-x-1 bg-gray-800 p-1 rounded-lg mb-6">
        <button 
          @click="isLogin = true" 
          :class="['flex-1 py-2 text-sm font-medium rounded-md transition-all', isLogin ? 'bg-gray-700 shadow text-white' : 'text-gray-400 hover:text-gray-200']">
          Login
        </button>
        <button 
          @click="isLogin = false" 
          :class="['flex-1 py-2 text-sm font-medium rounded-md transition-all', !isLogin ? 'bg-gray-700 shadow text-white' : 'text-gray-400 hover:text-gray-200']">
          Register
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-1" for="identifier">{{ isLogin ? 'Email or Phone' : 'Email' }}</label>
          <input 
            v-model="form.identifier" 
            id="identifier" 
            type="text" 
            required 
            class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition text-white placeholder-gray-500"
            :placeholder="isLogin ? 'Enter email or phone' : 'Enter email'"
          >
        </div>

        <div v-if="!isLogin">
          <label class="block text-sm font-medium text-gray-300 mb-1" for="phone">Phone (Optional)</label>
          <input 
            v-model="form.phone" 
            id="phone" 
            type="text" 
            class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition text-white placeholder-gray-500"
            placeholder="Enter phone number"
          >
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-300 mb-1" for="password">Password</label>
          <input 
            v-model="form.password" 
            id="password" 
            type="password" 
            required 
            class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition text-white placeholder-gray-500"
            placeholder="••••••••"
          >
        </div>

        <div v-if="errorMsg" class="text-red-400 text-sm py-1">
          {{ errorMsg }}
        </div>

        <button 
          type="submit" 
          :disabled="isLoading"
          class="w-full mt-6 py-3 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium rounded-lg shadow-lg hover:shadow-xl transition-all flex items-center justify-center disabled:opacity-70">
          <span v-if="isLoading" class="animate-spin mr-2">⚬</span>
          {{ isLogin ? 'Sign In' : 'Create Account' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/useAuth'
import { login, register } from '../api/auth'

const router = useRouter()
const authStore = useAuthStore()

const isLogin = ref(true)
const isLoading = ref(false)
const errorMsg = ref('')

const form = reactive({
  identifier: '', // used for email or phone in login, just email in register
  phone: '',      // used only in register
  password: ''
})

const handleSubmit = async () => {
  errorMsg.value = ''
  isLoading.value = true
  try {
    if (isLogin.value) {
      // Login flow: guess if it's email or phone
      const isEmail = form.identifier.includes('@')
      const payload: any = { password: form.password }
      if (isEmail) payload.email = form.identifier
      else payload.phone = form.identifier
      
      const res: any = await login(payload)
      authStore.setToken(res.data)
      // Check user registration stage if needed, but for now just go to dashboard
      // Or we can route to profile-setup if the user is new, but VR_Gfriend logic handles profile stage
      router.push('/dashboard')
    } else {
      // Register flow
      const payload = {
        email: form.identifier,
        phone: form.phone,
        password: form.password
      }
      const res: any = await register(payload)
      authStore.setToken(res.data)
      router.push('/profile-setup')
    }
  } catch (err: any) {
    errorMsg.value = err.message || 'An error occurred. Please try again.'
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
@keyframes blob {
  0% { transform: translate(0px, 0px) scale(1); }
  33% { transform: translate(30px, -50px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
  100% { transform: translate(0px, 0px) scale(1); }
}
.animate-blob {
  animation: blob 7s infinite;
}
.animation-delay-2000 {
  animation-delay: 2s;
}
</style>
