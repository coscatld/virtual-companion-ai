import http from './http'
import type {
  Account, AITemplate, Companion, CustomCreateDTO, LoginDTO, RegisterStep1DTO,
  RegisterStep2DTO, TemplateSelectDTO,
} from './types/user'

const path = '/admin/user'

export const register = (data: RegisterStep1DTO) => http.post<unknown, string>(`${path}/register`, data)
export const login = (data: LoginDTO) => http.post<unknown, string>(`${path}/login`, data)
export const getAccount = () => http.get<unknown, Account>(`${path}/me`)
export const getCompanion = () => http.get<unknown, Companion | null>(`${path}/companion`)
export const completeProfile = (data: RegisterStep2DTO) => http.post(`${path}/complete-profile`, data)
export const getTemplates = () => http.get<unknown, AITemplate[]>(`${path}/templates`)
export const useTemplate = (data: TemplateSelectDTO) => http.post(`${path}/use-template`, data)
export const customizeAI = (data: CustomCreateDTO) => http.post(`${path}/customize`, data)
