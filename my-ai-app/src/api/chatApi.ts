/**
 * 流式对话 API — 使用原生 fetch（不使用 Axios）
 * 对应 GET /api/chat/stream?msg=<text>（SSE, text/event-stream）
 *
 * 后端 SSE 事件格式：
 *   id: <timestamp>
 *   event: message
 *   data: <delta_text>         ← 正常文字片段
 *   data: <delta_text>\n[END]  ← 最后一帧附带 [END] 标记
 *
 * 后端错误事件：
 *   event: error
 *   data: <error_message>
 */

const BASE_URL = 'http://localhost:8080'
const END_MARKER = '[END]'

/**
 * 创建 SSE 流式聊天连接
 *
 * @param msg      - 用户输入的消息文本
 * @param token    - JWT Token（由调用方从 Store 获取）
 * @param signal   - AbortController.signal，用于主动取消
 * @returns        - ReadableStreamDefaultReader<Uint8Array>，供上层逐行读取
 * @throws         - 当 HTTP 响应不是 2xx 时抛出 Error
 */
export async function createChatStream(
  msg: string,
  token: string,
  signal: AbortSignal,
): Promise<ReadableStreamDefaultReader<Uint8Array>> {
  const url = new URL(`${BASE_URL}/api/chat/stream`)
  url.searchParams.set('msg', msg)

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'text/event-stream',
    },
    signal,
  })

  if (!response.ok) {
    throw new Error(`SSE 连接失败：HTTP ${response.status}`)
  }
  if (!response.body) {
    throw new Error('浏览器不支持 ReadableStream，无法接收流式响应')
  }

  return response.body.getReader()
}

/**
 * 解析 SSE 行，提取 data 字段内容
 * 仅处理 "data: ..." 行，忽略 id/event/comment 行
 *
 * @param rawLine - SSE 协议中的单行文本
 * @returns       - 解析后的 { delta, isEnd } 或 null（非 data 行）
 */
export function parseSSELine(rawLine: string): { delta: string; isEnd: boolean } | null {
  const trimmed = rawLine.trim()
  if (!trimmed.startsWith('data:')) return null

  // 去除 "data:" 前缀和首尾空白
  const payload = trimmed.slice('data:'.length).trimStart()

  if (!payload || payload === '[DONE]') return null

  const isEnd = payload.endsWith(END_MARKER)
  // 去除末尾的 "[END]" 和前面可能的换行
  const delta = isEnd
    ? payload.slice(0, payload.length - END_MARKER.length).replace(/\n$/, '')
    : payload

  return { delta, isEnd }
}
