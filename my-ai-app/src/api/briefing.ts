import request from './request'

// Briefing APIs
export const setAlarm = (data: any) => request.post('/api/briefing/set', data)
