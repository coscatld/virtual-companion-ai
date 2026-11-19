import { onUnmounted, ref } from 'vue'
import { streamChat } from '../api/chatApi'
import { useUserStore } from '../stores/useUserStore'
import { useChatStore } from '../stores/useChatStore'

export function useChatStream() {
  const userStore = useUserStore()
  const chatStore = useChatStore()
  const isStreaming = ref(false)
  const error = ref('')
  let controller: AbortController | undefined

  async function send(message: string): Promise<void> {
    const text = message.trim()
    if (isStreaming.value || !text || !userStore.token) return

    const request = new AbortController()
    controller = request
    error.value = ''
    isStreaming.value = true
    chatStore.addMessage('user', text)
    const reply = chatStore.addMessage('ai', '', true)

    try {
      await streamChat(text, userStore.token, request.signal, (delta) => {
        chatStore.appendToMessage(reply, delta)
      })
    } catch (cause) {
      if (!request.signal.aborted) {
        error.value = cause instanceof Error ? cause.message : '对话服务暂时不可用。'
      }
    } finally {
      chatStore.finalizeMessage(reply)
      controller = undefined
      isStreaming.value = false
    }
  }

  function abort(): void {
    controller?.abort()
  }

  onUnmounted(abort)
  return { isStreaming, error, send, abort }
}
