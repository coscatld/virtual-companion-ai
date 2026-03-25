/**
 * ⚡ useChatStream — 流式对话核心 Hook
 *
 * 功能：
 *  - 调用 chatApi.createChatStream 发起 SSE 连接
 *  - 逐行解析 SSE 协议，通过 useChatStore.appendToMessage 实现打字机效果
 *  - 主动取消：调用 abort() 或组件卸载时自动中止连接
 *  - 断线/超时自动重试（指数退避，最多 MAX_RETRIES 次）
 *  - 错误事件（event: error）直接终止并抛出
 */
import { ref, onUnmounted } from 'vue'
import { createChatStream, parseSSELine } from '../api/chatApi'
import { useUserStore } from '../stores/useUserStore'
import { useChatStore } from '../stores/useChatStore'
import { onApiError } from '../api/http'

// 最大重试次数
const MAX_RETRIES = 3
// 初始退避延迟（ms），每次重试翻倍
const BASE_RETRY_DELAY_MS = 1000

export function useChatStream() {
  const userStore = useUserStore()
  const chatStore = useChatStore()

  /** 是否正在进行流式接收 */
  const isStreaming = ref(false)

  /**
   * 当前活跃的 AbortController
   * abort() 公开方法 和 组件卸载 都会调用它
   */
  let controller: AbortController | null = null

  /**
   * 内部流式读取循环
   * @param msg           - 本次发送的用户消息文本
   * @param aiMessageId   - 预先创建的 AI 消息 ID（供追加文字）
   * @param retryCount    - 当前重试次数
   */
  async function _readStream(
    msg: string,
    aiMessageId: string,
    retryCount = 0,
  ): Promise<void> {
    // 每次（重）连接都创建新的 AbortController
    controller = new AbortController()
    const decoder = new TextDecoder('utf-8')
    let reader: ReadableStreamDefaultReader<Uint8Array> | null = null
    // 用于拼接跨 chunk 的不完整行
    let buffer = ''

    try {
      reader = await createChatStream(
        msg,
        userStore.token ?? '',
        controller.signal,
      )

      // ── 流式读取主循环 ──
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        // 将 Uint8Array 解码为字符串并追加到 buffer
        buffer += decoder.decode(value, { stream: true })

        // 按行拆分（SSE 协议以 \n 分隔字段，以 \n\n 分隔事件）
        const lines = buffer.split('\n')
        // 最后一个元素可能是不完整的行，保留在 buffer 中
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          // 检测后端发来的 error 事件行
          if (line.trim() === 'event: error') {
            throw new Error('后端 SSE 发送了 error 事件')
          }

          const parsed = parseSSELine(line)
          if (!parsed) continue

          const { delta, isEnd } = parsed

          // 追加文字到 AI 消息（打字机效果）
          if (delta) {
            chatStore.appendToMessage(aiMessageId, delta)
          }

          // 检测结束标记
          if (isEnd) {
            chatStore.finalizeMessage(aiMessageId)
            isStreaming.value = false
            return
          }
        }
      }

      // 流自然结束（done = true，但没收到 [END]）
      chatStore.finalizeMessage(aiMessageId)
      isStreaming.value = false
    } catch (error: unknown) {
      // AbortError：主动取消，不重试
      if (error instanceof DOMException && error.name === 'AbortError') {
        chatStore.finalizeMessage(aiMessageId)
        isStreaming.value = false
        return
      }

      // 其他错误：尝试重试
      if (retryCount < MAX_RETRIES) {
        const delay = BASE_RETRY_DELAY_MS * Math.pow(2, retryCount)
        console.warn(
          `[useChatStream] 连接中断，${delay}ms 后第 ${retryCount + 1} 次重试...`,
          error,
        )
        await new Promise((resolve) => setTimeout(resolve, delay))
        return _readStream(msg, aiMessageId, retryCount + 1)
      }

      // 超过最大重试次数，终止并通知 UI
      const errMsg = error instanceof Error ? error.message : '流式对话连接失败'
      onApiError(`${errMsg}（已重试 ${MAX_RETRIES} 次）`)
      chatStore.finalizeMessage(aiMessageId)
      isStreaming.value = false
    } finally {
      // 确保 reader 始终被释放
      try {
        reader?.releaseLock()
      } catch {
        // ignore
      }
    }
  }

  /**
   * 发送用户消息并启动流式接收
   * @param msg - 用户输入的消息文本
   */
  async function send(msg: string): Promise<void> {
    if (isStreaming.value) return // 防止并发请求

    const trimmed = msg.trim()
    if (!trimmed) return

    // 1. 添加用户消息气泡
    chatStore.addMessage('user', trimmed)

    // 2. 添加空白 AI 消息占位（streaming = true，UI 展示光标）
    const aiMsgId = chatStore.addMessage('ai', '', true)

    isStreaming.value = true

    // 3. 启动流式读取（不 await，让 UI 保持响应）
    _readStream(trimmed, aiMsgId)
  }

  /**
   * 主动中止当前流（用户点击"停止生成"按钮）
   */
  function abort(): void {
    controller?.abort()
    controller = null
  }

  // 组件卸载时自动中止，防止内存泄漏
  onUnmounted(() => {
    abort()
  })

  return {
    /** 响应式消息列表（直接来自 chatStore） */
    messages: chatStore.messages,
    /** 是否正在流式接收 */
    isStreaming,
    /** 发送消息 */
    send,
    /** 主动中止流 */
    abort,
  }
}
