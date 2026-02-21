import request from './request'

// Auth APIs
export const login = (data: any) => request.post('/admin/user/login', data)
export const register = (data: any) => request.post('/admin/user/register', data)
export const completeProfile = (data: any) => request.post('/admin/user/complete-profile', data)
