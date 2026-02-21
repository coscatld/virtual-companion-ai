import request from './request'

// Template APIs
export const getTemplates = () => request.get('/admin/user/templates')
export const useTemplate = (data: any) => request.post('/admin/user/use-template', data)
export const customizeAI = (data: any) => request.post('/admin/user/customize', data)
