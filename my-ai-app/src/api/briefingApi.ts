/**
 * 日常播报 / 闹钟模块 API 请求函数
 * 对应后端 DailyBriefingController（路径前缀：/api/briefing）
 */
import http from './http'
import type { UserAlarmProfileDTO } from './types/briefing'

// ────────────────────────────────
// 1. 设置闹钟播报配置
//    POST /api/briefing/set（需要 JWT）
//    入参：{city, cronExpression("HH:mm" 或 Cron), scheduleFilePath, enabled}
//    返回：后端确认文字
// ────────────────────────────────
export async function setAlarm(dto: UserAlarmProfileDTO): Promise<string> {
  try {
    const msg = await http.post<string>('/api/briefing/set', dto)
    return msg as unknown as string
  } catch (error) {
    throw error
  }
}

// ────────────────────────────────
// 2. 手动触发测试播报（流式）
//    GET /api/briefing/test/{userId}
//    注意：该接口返回 Flux<String>（纯文本流），不是 SSE，
//          使用 responseType: 'text' 直接拿拼接好的字符串
// ────────────────────────────────
export async function triggerTestBriefing(userId: string): Promise<string> {
  try {
    // 该接口不走 JSON 响应体解包，直接拿 text
    const response = await http.get<string>(`/api/briefing/test/${userId}`, {
      responseType: 'text',
    })
    return response as unknown as string
  } catch (error) {
    throw error
  }
}
