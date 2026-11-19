import http from './http'
import type { UserAlarmProfileDTO } from './types/briefing'

export type Briefing = { text: string; generatedAt: string }

export function setAlarm(settings: UserAlarmProfileDTO): Promise<string> {
  return http.post<unknown, string>('/api/briefing/set', settings)
}

export function getSettings(): Promise<UserAlarmProfileDTO | null> {
  return http.get<unknown, UserAlarmProfileDTO | null>('/api/briefing/settings')
}

export function getLatestBriefing(): Promise<Briefing | null> {
  return http.get<unknown, Briefing | null>('/api/briefing/latest')
}
