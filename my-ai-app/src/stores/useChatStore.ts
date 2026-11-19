/**
 * 聊天消息列表状态管理
 * 与 useChatStream.ts 配合使用，负责存储和操作消息列表
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ChatMessage, MessageRole } from '../api/types/chat'

let _idCounter = 0
/** 生成本地消息 ID */
function genId(): string {
  return `msg_${Date.now()}_${_idCounter++}`
}

export const useChatStore = defineStore('chat', () => {
  // ───── State ─────

  /** 完整消息列表（用户消息 + AI 回复消息交替出现） */
  const messages = ref<ChatMessage[]>([])

  // ───── Actions ─────

  /**
   * 添加一条新消息到列表末尾
   * @param role    - 发送方：'user' 或 'ai'
   * @param content - 初始文本内容（AI 流式消息初始为空字符串）
   * @param streaming - 是否处于流式接收中，默认 false
   * @returns 新消息的 id（供后续 append 操作定位）
   */
  function addMessage(role: MessageRole, content: string, streaming = false): string {
    const id = genId()
    messages.value.push({
      id,
      role,
      content,
      streaming,
      timestamp: Date.now(),
    })
    return id
  }

  /**
   * 向指定 AI 消息追加内容（SSE 打字机效果核心操作）
   * @param id    - 目标消息的 id
   * @param delta - 本次 SSE 事件携带的文字片段
   */
  function appendToMessage(id: string, delta: string): void {
    const msg = messages.value.find((m) => m.id === id)
    if (msg) {
      msg.content += delta
    }
  }

  /**
   * 标记消息流结束（关闭打字机光标动画）
   * @param id - 目标消息的 id
   */
  function finalizeMessage(id: string): void {
    const msg = messages.value.find((m) => m.id === id)
    if (msg) {
      msg.streaming = false
    }
  }

  /**
   * 清空全部对话记录（开始新会话时调用）
   */
  function resetChat(): void {
    messages.value = []
  }

  return {
    // state（readonly 暴露）
    messages,
    // actions
    addMessage,
    appendToMessage,
    finalizeMessage,
    resetChat,
  }
})
