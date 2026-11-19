import { apiBase } from './endpoints'
import http from './http'

type HistoryMessage = { role: 'user' | 'assistant'; content: string }

export function getChatHistory(signal: AbortSignal): Promise<HistoryMessage[]> {
  return http.get<unknown, HistoryMessage[]>('/api/chat/history', { signal })
}

export async function streamChat(
  message: string,
  token: string,
  signal: AbortSignal,
  onDelta: (text: string) => void,
): Promise<void> {
  const response = await fetch(`${apiBase}/api/chat/stream`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message }),
    signal,
  })

  if (response.status === 401) throw new Error('登录已过期，请重新登录。')
  if (!response.ok || !response.body) throw new Error(`无法连接对话服务（${response.status}）。`)

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let pending = ''
  let event = 'message'
  let data: string[] = []

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) throw new Error('回复中途断开，可以重新发送消息。')
      pending += value
      let end = pending.indexOf('\n')
      while (end !== -1) {
        const line = pending.slice(0, end).replace(/\r$/, '')
        pending = pending.slice(end + 1)
        if (line === '') {
          const text = data.join('\n')
          if (event === 'error') throw new Error(text || '对话服务暂时不可用。')
          if (event === 'done') return
          if (event === 'message' && data.length) onDelta(text)
          event = 'message'
          data = []
        } else if (line.startsWith('event:')) {
          event = line.slice(6).replace(/^ /, '')
        } else if (line.startsWith('data:')) {
          data.push(line.slice(5).replace(/^ /, ''))
        } else if (line === 'data') {
          data.push('')
        }
        end = pending.indexOf('\n')
      }
    }
  } finally {
    await reader.cancel().catch(() => undefined)
    reader.releaseLock()
  }
}
