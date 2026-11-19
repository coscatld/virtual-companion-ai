<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { getChatHistory } from '../api/chatApi'
import { useChatStore } from '../stores/useChatStore'
import { useUserStore } from '../stores/useUserStore'
import { useChatStream } from '../composables/useChatStream'
import { useVoice } from '../composables/useVoice'
import { useBriefingFeed } from '../composables/useBriefingFeed'

const user = useUserStore()
const chat = useChatStore()
const { isStreaming, error, send, abort } = useChatStream()
const voice = useVoice(() => user.token, (userText, text) => {
  if (userText) chat.addMessage('user', userText)
  if (text) chat.addMessage('ai', text)
})
const brief = ref('')
useBriefingFeed(() => user.token, (text) => { brief.value = text })
const draft = ref('')
const timeline = ref<HTMLElement>()
const isLoadingHistory = ref(!chat.messages.length)
const historyError = ref('')
const historyRequest = new AbortController()
const visibleMessages = computed(() => chat.messages.filter((message) => message.content || message.streaming))
const name = computed(() => user.companion?.name || '伴侣')
const status = computed(() => ({
  idle: isStreaming.value ? '正在回复' : '等待消息',
  requesting: '等待麦克风授权',
  recording: '正在录音',
  waiting: '正在处理语音',
})[voice.phase.value])

async function submit() {
  const message = draft.value.trim()
  if (!message || isLoadingHistory.value || voice.phase.value !== 'idle' || isStreaming.value) return
  draft.value = ''
  voice.error.value = ''
  await send(message)
}

function startRecording() {
  error.value = ''
  void voice.start()
}

function keyboard(event: KeyboardEvent) {
  if (event.shiftKey || event.isComposing) return
  event.preventDefault()
  void submit()
}

onMounted(async () => {
  if (!isLoadingHistory.value) return
  try {
    const recent = await getChatHistory(historyRequest.signal)
    if (historyRequest.signal.aborted || !user.token) return
    for (const message of recent) {
      chat.addMessage(message.role === 'assistant' ? 'ai' : 'user', message.content)
    }
  } catch {
    if (!historyRequest.signal.aborted) historyError.value = '暂时无法加载近期对话。'
  } finally {
    isLoadingHistory.value = false
  }
})
onUnmounted(() => historyRequest.abort())

watch(
  () => [chat.messages.length, chat.messages[chat.messages.length - 1]?.content],
  async () => {
    const list = timeline.value
    const follow = !list || list.scrollHeight - list.scrollTop - list.clientHeight < 100
    await nextTick()
    if (follow && list) list.scrollTop = list.scrollHeight
  },
)
</script>

<template>
  <main class="companion-room">
    <aside class="presence" :data-phase="voice.phase.value" :data-speaking="isStreaming">
      <div class="presence-copy">
        <h1>{{ name }}</h1>
        <p v-if="user.companion?.tags?.length">{{ user.companion.tags.join(' · ') }}</p>
      </div>
      <div class="signal" aria-hidden="true">
        <div class="orbit orbit-outside"></div>
        <div class="orbit orbit-inside"></div>
        <div class="signal-core"></div>
      </div>
      <div class="presence-status" role="status"><span></span>{{ status }}</div>
    </aside>
    <section class="conversation" aria-label="对话">
      <aside v-if="brief" class="briefing-note">
        <div class="actions split"><strong>每日简报</strong><button class="quiet" type="button" aria-label="关闭简报" @click="brief = ''">关闭</button></div>
        <p>{{ brief }}</p>
      </aside>
      <div ref="timeline" class="timeline">
        <div v-if="!visibleMessages.length" class="chat-empty">
          <p>{{ isLoadingHistory ? '正在加载对话…' : historyError || '今天想聊些什么？' }}</p>
        </div>
        <article v-for="message in visibleMessages" :key="message.id" class="turn" :data-role="message.role">
          <span>{{ message.role === 'user' ? '你' : name }}</span>
          <p>{{ message.content || '…' }}<i v-if="message.content && message.streaming" aria-label="正在生成"></i></p>
        </article>
      </div>
      <div class="composer">
        <p v-if="error || voice.error.value" class="error" role="alert">{{ error || voice.error.value }}</p>
        <audio v-if="voice.audioUrl.value" :key="voice.audioUrl.value" :src="voice.audioUrl.value" controls autoplay aria-label="播放伴侣语音回复"></audio>
        <form @submit.prevent="submit">
          <textarea v-model="draft" rows="2" maxlength="4000" aria-label="消息" placeholder="说说你的想法…" @keydown.enter="keyboard"></textarea>
          <div class="actions split">
            <div class="actions">
              <button v-if="voice.phase.value === 'idle'" type="button" :disabled="isStreaming || isLoadingHistory" @click="startRecording">录音</button>
              <button v-if="voice.phase.value === 'recording'" type="button" @click="voice.stop">发送语音</button>
              <button v-if="voice.phase.value !== 'idle'" class="quiet" type="button" @click="voice.cancel">取消语音</button>
            </div>
            <button v-if="isStreaming" type="button" @click="abort">停止回复</button>
            <button v-else class="primary" type="submit" :disabled="!draft.trim() || isLoadingHistory || voice.phase.value !== 'idle'">发送</button>
          </div>
        </form>
      </div>
    </section>
  </main>
</template>
