/**
 * 聊天相关类型定义
 * 用于 SSE 流式对话的消息列表管理
 */

/** 消息角色 */
export type MessageRole = 'user' | 'ai'

/** 聊天消息实体 */
export interface ChatMessage {
  /** 消息唯一 ID（前端生成，用于列表 key） */
  id: string
  /** 发送方角色 */
  role: MessageRole
  /** 消息文本内容（AI 消息在流式过程中逐步追加） */
  content: string
  /**
   * 是否正在流式接收中（打字机动画控制标志）
   * true: 正在接收 SSE 切片，UI 展示光标动画
   * false: 流已完成或为用户消息
   */
  streaming: boolean
  /** 消息创建时间戳（ms） */
  timestamp: number
}

/** SSE 事件的解析结果 */
export interface SSEParsedEvent {
  /** 后端发送的文字 delta */
  delta: string
  /** 是否为结束标记（后端在末尾追加 [END]） */
  isEnd: boolean
}
