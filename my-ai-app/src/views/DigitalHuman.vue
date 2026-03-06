<template>
  <div class="relative w-screen h-screen bg-gray-900 overflow-hidden font-sans select-none">
    
    <!-- 1. 核心视觉区：全屏沉浸式 3D 数字人画布 -->
    <div class="absolute inset-0 z-0">
      <AvatarCanvas ref="avatarCanvasRef" modelUrl="/models/avatar.vrm" />
    </div>

    <!-- 2. 画中画（PIP）：本地摄像头捕获区 -->
    <!-- 支持拖拽可用 vueuse/useDraggable 扩展，此处使用绝对定位居右下角演示基础框架 -->
    <div 
         class="absolute bottom-28 right-6 w-36 h-48 md:w-48 md:h-64 bg-black rounded-2xl shadow-2xl border-2 border-gray-700 overflow-hidden z-20 cursor-move transition-transform hover:scale-105">
      <video 
        ref="localVideoRef" 
        class="w-full h-full object-cover transform scale-x-[-1]" 
        autoplay 
        playsinline 
        muted
        v-show="isVideoEnabled">
      </video>
      <!-- 未开启摄像头时的占位符 -->
      <div v-show="!isVideoEnabled" class="w-full h-full flex flex-col items-center justify-center bg-gray-800 text-gray-400">
        <span class="text-3xl mb-2">📷</span>
        <span class="text-sm font-medium">摄像头未开启</span>
      </div>
    </div>

    <!-- 3. 全局字幕层 (位于屏幕正下方) -->
    <div class="absolute bottom-32 left-0 right-0 z-10 flex justify-center pointer-events-none px-4">
      <div class="bg-black bg-opacity-60 backdrop-blur-md px-6 py-4 rounded-xl max-w-3xl w-full text-center shadow-lg transition-all">
        <p class="text-2xl md:text-3xl font-bold text-white tracking-wider leading-relaxed">
          {{ aiSubtitle || '你好，我是你的虚拟伴侣！您可以打开麦克风跟我聊天哦。' }}
        </p>
      </div>
    </div>

    <!-- 4. 底部交互与控制栏 -->
    <div class="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-black/80 to-transparent z-30 flex items-center justify-center gap-6 px-6">
      
      <!-- 报错提示 Toast -->
      <div v-if="errorMsg" class="absolute -top-12 bg-red-500 text-white px-4 py-2 rounded-lg text-sm shadow-lg">
        {{ errorMsg }}
      </div>

      <!-- 硬件授权与开关组 -->
      <button 
        @click="startDevices(true, true)"
        v-if="!isVideoEnabled && !isAudioEnabled"
        class="bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-full font-bold text-lg shadow-lg flex items-center gap-2 transition-all">
        <span class="text-xl">🚀</span> 开启音视频陪护模式
      </button>

      <!-- 细分控制 (仅在授权后显示) -->
      <template v-else>
        <button 
          @click="toggleAudio"
          class="w-14 h-14 rounded-full flex items-center justify-center transition-all"
          :class="isAudioEnabled ? 'bg-green-500 text-white hover:bg-green-400' : 'bg-gray-600 text-gray-300 hover:bg-gray-500'">
          <span class="text-2xl">{{ isAudioEnabled ? '🎤' : '🔇' }}</span>
        </button>

        <!-- 模拟连麦按键 -->
        <button 
          @click="handleCallStart"
          class="bg-red-500 hover:bg-red-400 text-white px-10 py-3 rounded-full font-bold text-xl shadow-lg border-2 border-red-400 flex items-center gap-3 transition-transform active:scale-95">
          <span class="text-2xl" :class="wsStatus === 'connected' ? 'animate-pulse' : ''">📞</span> 
          {{ wsStatus === 'connected' ? '正在陪伴通话中...' : '开始连线' }}
        </button>

        <button 
          @click="toggleVideo"
          class="w-14 h-14 rounded-full flex items-center justify-center transition-all"
          :class="isVideoEnabled ? 'bg-blue-500 text-white hover:bg-blue-400' : 'bg-gray-600 text-gray-300 hover:bg-gray-500'">
          <span class="text-2xl">{{ isVideoEnabled ? '📹' : '📴' }}</span>
        </button>
      </template>

    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import AvatarCanvas from '@/components/AvatarCanvas.vue'
import { useMediaDevices } from '@/composables/useMediaDevices'
import { useAvatarWS } from '@/composables/useAvatarWS'

// 1. 获取 3D Canvas 子组件引用，以便调用更新口型等方法
const avatarCanvasRef = ref<InstanceType<typeof AvatarCanvas> | null>(null)

// 2. 初始化硬件控制 Composable
const localVideoRef = ref<HTMLVideoElement | null>(null)
const { 
  videoStream, 
  isVideoEnabled, 
  isAudioEnabled, 
  errorMsg, 
  startDevices, 
  toggleAudio, 
  toggleVideo 
} = useMediaDevices()

// 监听 VideoStream 绑定到原生的 <video> 标签中
watch(videoStream, (newStream) => {
  if (localVideoRef.value && newStream) {
    localVideoRef.value.srcObject = newStream
  }
})

// 3. 初始化 WebSocket 连接 Composable
const { 
  wsStatus, 
  aiSubtitle, 
  onBlendShapeUpdate, 
  connect 
} = useAvatarWS()

// 挂载后端下发的面部控制指令到 3D Canvas 上
onBlendShapeUpdate.value = (shapeName: string, value: number) => {
  if (avatarCanvasRef.value && shapeName === 'aa') {
    // 假设后端传过来的是 'aa'，直接映射更新嘴巴张开度
    avatarCanvasRef.value.updateMouth(value)
  }
}

// 模拟点击连线
const handleCallStart = () => {
  if (wsStatus.value !== 'connected') {
    connect() // 核心功能：连接后端指令 WS
  }
}

onMounted(() => {
  // Mount 逻辑可以留空，由用户主动点击获取硬件流
})
</script>

<style scoped>
/* 一些特定的防止双击缩放的设定 */
* {
  touch-action: pan-y;
}
</style>
