<template>
  <div class="min-h-screen bg-gray-50 flex flex-col items-center justify-between py-8 px-4 font-sans select-none">
    
    <!-- 头部状态栏 -->
    <header class="w-full max-w-2xl bg-white rounded-3xl shadow-sm p-4 text-center border-b-4" 
            :class="connectionStatusColor">
      <h1 class="text-3xl font-bold text-gray-800 tracking-wider">知己陪伴</h1>
      <p class="text-lg mt-2 font-medium" :class="connectionStatusTextColor">
        {{ connectionStatusText }}
      </p>
    </header>

    <!-- 中间：数字人展示区 -->
    <main class="flex-1 w-full max-w-2xl flex flex-col items-center justify-center my-8 relative">
      <!-- 虚拟人占位符 -->
      <div class="relative w-64 h-64 md:w-80 md:h-80 rounded-full bg-blue-100 border-8 border-white shadow-lg overflow-hidden flex items-center justify-center transition-all duration-300"
           :style="{ transform: `scale(${1 + mouthOpenness * 0.15})` }">
        
        <!-- 这里是将来替换 Live2D/3D 模型的地方，目前用简笔画代替 -->
        <div class="text-9xl relative t-2">
          👨‍🦳
          <!-- 动态模拟嘴巴张合度 (根据音量大小调节高度) -->
          <div class="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-red-400 rounded-full transition-all duration-75"
               :style="{ 
                 width: `${20 + mouthOpenness * 40}px`,
                 height: `${10 + mouthOpenness * 30}px`,
                 opacity: isPlaying ? 1 : 0
               }">
          </div>
        </div>

        <!-- 听音乐/听说话的波纹效果 -->
        <div v-if="isPlaying || isRecording" 
             class="absolute inset-0 rounded-full border-4 border-blue-400 opacity-50 animate-ping">
        </div>
      </div>

      <!-- 字幕与状态展示区 -->
      <div class="mt-8 bg-white w-full p-6 rounded-3xl shadow-sm border-2 border-gray-100 min-h-[140px] flex flex-col justify-center">
        <!-- 用户说的话 -->
        <p v-if="userText && !isPlaying" class="text-2xl text-gray-500 font-medium mb-2 opacity-80 border-l-4 border-gray-300 pl-4">
          您说: {{ userText }}
        </p>

        <!-- AI 说的话 -->
        <p class="text-3xl text-gray-900 font-bold leading-relaxed border-l-4 border-blue-500 pl-4 mt-2 transition-all">
          <span v-if="aiText">{{ aiText }}</span>
          <span v-else-if="!isRecording && !userText" class="text-gray-400">你好，我是你的专属陪伴...</span>
          <span v-else-if="isRecording" class="text-blue-500 animate-pulse">正在全神贯注听您讲...</span>
          <span v-else class="text-blue-400 animate-pulse">伴侣正在思考怎么回答您...</span>
        </p>
      </div>
    </main>

    <!-- 底部：巨大的语音交互控制区 -->
    <footer class="w-full max-w-2xl mb-4">
      <button 
        @touchstart.prevent="startRecording"
        @mousedown.prevent="startRecording"
        @touchend.prevent="stopRecording"
        @mouseup.prevent="stopRecording"
        @mouseleave.prevent="stopRecording"
        class="w-full h-32 md:h-40 rounded-full shadow-xl flex items-center justify-center text-4xl md:text-5xl font-bold tracking-widest text-white transition-all transform active:scale-95 touch-none"
        :class="isRecording ? 'bg-red-500 hover:bg-red-600 shadow-red-200' : 'bg-blue-500 hover:bg-blue-600 shadow-blue-200'"
        :disabled="wsStatus !== 'connected'"
      >
        <span v-if="isRecording" class="flex items-center gap-4 animate-pulse">
          <span class="text-5xl">🛑</span> 松开结束
        </span>
        <span v-else class="flex items-center gap-4">
          <span class="text-5xl">🎤</span> 按住说话
        </span>
      </button>
      
      <p class="text-center mt-6 text-xl text-gray-500 font-medium tracking-wide">
        长按上方大按钮对我说话，松开手指发送
      </p>
    </footer>

  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue';
import { useAudioStream } from '@/composables/useAudioStream';

const {
  isRecording,
  isPlaying,
  wsStatus,
  wsErrorMsg,
  aiText,
  userText,
  mouthOpenness,
  connectWebSocket,
  startRecording,
  stopRecording
} = useAudioStream();

// 根据连接状态智能切换颜色和提示文字，适老化设计需要极强视觉对比
const connectionStatusColor = computed(() => {
  switch (wsStatus.value) {
    case 'connected': return 'border-green-400';
    case 'error': return 'border-red-400 bg-red-50';
    case 'connecting': return 'border-yellow-400 bg-yellow-50';
    default: return 'border-gray-300';
  }
});

const connectionStatusTextColor = computed(() => {
  switch (wsStatus.value) {
    case 'connected': return 'text-green-600';
    case 'error': return 'text-red-600';
    case 'connecting': return 'text-yellow-600';
    default: return 'text-gray-500';
  }
});

const connectionStatusText = computed(() => {
  switch (wsStatus.value) {
    case 'connected': return '✅ 网络已连接，可以开始聊天咯';
    case 'error': return '❌ ' + (wsErrorMsg.value || '网络中断，正在尝试重新连接...');
    case 'connecting': return '⏳ 正在连接网络，请稍等...';
    default: return '🔌 离线状态';
  }
});

onMounted(() => {
  // 页面挂载时自动建立长连接
  connectWebSocket();
});
</script>

<style scoped>
/* 阻止移动端长按选中文本和呼出菜单，保证按住说话按钮的体验 */
button {
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  user-select: none;
  touch-action: none;
}
</style>
