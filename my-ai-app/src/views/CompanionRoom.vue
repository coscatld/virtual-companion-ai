<template>
  <div class="flex flex-col h-screen w-full bg-gray-900 overflow-hidden relative">
    
    <!-- 状态提示 -->
    <div v-if="wsStatus !== 'connected'" class="absolute top-6 left-1/2 -translate-x-1/2 z-50 bg-yellow-100 text-yellow-800 px-8 py-4 rounded-full text-2xl shadow-lg border border-yellow-300">
      {{ wsErrorMsg || '正在连接，请稍等...' }}
    </div>

    <!-- 3D 渲染区 -->
    <div class="flex-1 relative">
      <AvatarCanvas ref="avatarRef" />
    </div>

    <!-- 适老化字幕区 -->
    <div class="h-2/5 md:h-1/3 bg-black bg-opacity-80 p-6 flex flex-col justify-end relative shadow-[0_-15px_40px_rgba(0,0,0,0.6)]">
      
      <!-- AI 文本展示区 (大字体与高对比度文字) -->
      <div class="mb-4 flex-1 overflow-y-auto">
        <p class="text-white text-4xl leading-relaxed font-medium tracking-wide">
          {{ aiText || '很高兴见到您！想和我说点什么吗？' }}
        </p>
      </div>

      <!-- 用户状态/文本展示区 -->
      <div class="mb-6">
        <p class="text-yellow-400 text-3xl font-bold">
          <span v-if="isRecording">🗣️ </span>
          {{ userText }}
        </p>
      </div>

      <!-- 极简操作面板 -->
      <div class="flex justify-center items-center pb-8">
        <!-- 巨大的麦克风按钮绑定防误触 -->
        <button 
          @pointerdown="handlePointerDown"
          @pointerup="handlePointerUp"
          @pointerleave="handlePointerUp"
          class="relative w-40 h-40 rounded-full flex items-center justify-center transition-all duration-300 shadow-[0_0_20px_rgba(59,130,246,0.6)] select-none disabled:opacity-50 disabled:grayscale"
          :class="isRecording ? 'bg-red-500 scale-105 shadow-[0_0_40px_rgba(239,68,68,0.9)]' : 'bg-blue-600 hover:bg-blue-500'"
          :disabled="wsStatus !== 'connected'"
        >
          <div v-if="isRecording" class="absolute inset-0 rounded-full animate-ping bg-red-400 opacity-75"></div>
          <span class="text-7xl text-white relative z-10 select-none">{{ isRecording ? '⏹️' : '🎤' }}</span>
        </button>
        <p class="absolute bottom-2 text-gray-400 text-2xl font-medium tracking-widest mt-4 pointer-events-none">
          按住说话，松开发送
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import { useAudioStream } from '@/composables/useAudioStream';
import AvatarCanvas from '@/components/AvatarCanvas.vue'; 

const avatarRef = ref<InstanceType<typeof AvatarCanvas> | null>(null);

const {
  isRecording,
  wsStatus,
  wsErrorMsg,
  aiText,
  userText,
  mouthOpenness,
  connectWebSocket,
  startRecording,
  stopRecording
} = useAudioStream();

watch(mouthOpenness, (newVal) => {
  if (avatarRef.value && avatarRef.value.updateMouth) {
    avatarRef.value.updateMouth(newVal);
  }
});

let recordTimeout: number | null = null;
const MIN_RECORD_TIME = 800; // 最小录制防抖时间 800ms

const handlePointerDown = (e: PointerEvent) => {
  if (wsStatus.value !== 'connected' || isRecording.value) return;
  e.preventDefault();
  startRecording();
};

const handlePointerUp = () => {
  if (!isRecording.value) return;
  stopRecording();
};

onMounted(() => {
  connectWebSocket();
});
</script>
