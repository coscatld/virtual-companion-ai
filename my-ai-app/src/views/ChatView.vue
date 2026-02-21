<template>
  <div class="flex flex-col h-full bg-gray-900 border border-gray-700 rounded-xl overflow-hidden shadow-2xl relative">
    
    <!-- Header -->
    <header class="h-16 flex items-center justify-between px-6 bg-gray-800 border-b border-gray-700 shrink-0">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-500 to-purple-500 p-0.5">
          <img src="https://via.placeholder.com/150/000000/FFFFFF?text=AI" class="w-full h-full rounded-full object-cover">
        </div>
        <div>
          <h2 class="font-bold text-lg text-white">AI Companion</h2>
          <div class="flex items-center text-xs text-green-400">
            <span class="w-2 h-2 rounded-full bg-green-500 mr-2"></span> Online
          </div>
        </div>
      </div>
      <button @click="clearChat" class="text-gray-400 hover:text-white text-sm transition-colors">
        Clear Chat
      </button>
    </header>

    <!-- Message Area -->
    <div 
      class="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth bg-gray-900 message-area" 
      ref="messageArea"
    >
      <div v-if="messages.length === 0" class="flex flex-col items-center justify-center h-full text-gray-500 space-y-4">
        <div class="w-16 h-16 rounded-full bg-gray-800 flex items-center justify-center border border-gray-700">
          <svg class="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path></svg>
        </div>
        <p>Send a message to start chatting</p>
      </div>

      <div 
        v-for="(msg, index) in messages" 
        :key="index"
        :class="['flex', msg.role === 'user' ? 'justify-end' : 'justify-start']"
      >
        <div 
          :class="[
            'max-w-[80%] rounded-2xl px-5 py-3 shadow-sm', 
            msg.role === 'user' 
              ? 'bg-blue-600 text-white rounded-br-none' 
              : 'bg-gray-800 text-gray-100 rounded-bl-none border border-gray-700'
          ]"
        >
          <div class="whitespace-pre-wrap leading-relaxed">{{ msg.content }}</div>
        </div>
      </div>

      <!-- Typing Indicator -->
      <div v-if="isTyping" class="flex justify-start">
        <div class="bg-gray-800 border border-gray-700 rounded-2xl rounded-bl-none px-5 py-4 flex space-x-2">
          <div class="w-2 h-2 rounded-full bg-gray-500 animate-bounce"></div>
          <div class="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style="animation-delay: 0.2s"></div>
          <div class="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style="animation-delay: 0.4s"></div>
        </div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="p-4 bg-gray-800 border-t border-gray-700 shrink-0">
      <form @submit.prevent="sendMessage" class="relative flex items-center">
        <input 
          v-model="inputMsg" 
          type="text" 
          placeholder="Type your message..." 
          class="w-full bg-gray-900 border border-gray-700 text-white rounded-full pl-6 pr-14 py-3 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all shadow-inner"
          :disabled="isTyping"
        >
        <button 
          type="submit" 
          :disabled="!inputMsg.trim() || isTyping" 
          class="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-blue-600 hover:bg-blue-500 text-white rounded-full transition-all disabled:opacity-50 disabled:hover:bg-blue-600 flex items-center justify-center"
        >
          <svg class="w-5 h-5 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { streamChat } from '../api/chat'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const inputMsg = ref('')
const messages = ref<Message[]>([])
const isTyping = ref(false)
const messageArea = ref<HTMLElement | null>(null)

let abortStream: (() => void) | null = null

const scrollToBottom = async () => {
  await nextTick()
  if (messageArea.value) {
    messageArea.value.scrollTop = messageArea.value.scrollHeight
  }
}

const sendMessage = async () => {
  const text = inputMsg.value.trim()
  if (!text) return

  // Push user message
  messages.value.push({ role: 'user', content: text })
  inputMsg.value = ''
  isTyping.value = true
  scrollToBottom()

  // Initialize the placeholder for the assistant's reply
  const assistantIndex = messages.value.length
  messages.value.push({ role: 'assistant', content: '' })
  
  const req = streamChat(
    text,
    (chunk) => {
      isTyping.value = false
      messages.value[assistantIndex].content += chunk
      scrollToBottom()
    },
    (err) => {
      isTyping.value = false
      messages.value[assistantIndex].content += '\n\n[Error: Connection Interrupted]'
      abortStream = null
      scrollToBottom()
    },
    () => {
      isTyping.value = false
      abortStream = null
      scrollToBottom()
    }
  )

  abortStream = req.abort
}

const clearChat = () => {
  if (abortStream) abortStream()
  messages.value = []
  isTyping.value = false
}

// Ensure load scroll
onMounted(() => scrollToBottom())
</script>

<style scoped>
/* Custom Scrollbar for Chat Area */
.message-area::-webkit-scrollbar {
  width: 6px;
}
.message-area::-webkit-scrollbar-track {
  background: transparent;
}
.message-area::-webkit-scrollbar-thumb {
  background-color: #4B5563;
  border-radius: 10px;
}
</style>
