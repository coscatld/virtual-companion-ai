/**
 * 用户模块 API 请求函数
 * 对应后端 Usercontroller（路径前缀：/admin/user）
 * 所有函数均有 try/catch，错误向上抛出让调用方（Store / Composable）决定如何处理
 */
import http from './http'
import type {
  RegisterStep1DTO,
  RegisterStep2DTO,
  LoginDTO,
  AITemplate,
  TemplateSelectDTO,
  CustomCreateDTO,
} from './types/user'

// ────────────────────────────────
// 1. 注册 Step1 — 基础账号
//    返回 JWT Token 字符串
// ────────────────────────────────
export async function register(dto: RegisterStep1DTO): Promise<string> {
  try {
    // 响应拦截器已解包，data 直接是 token 字符串
    const token = await http.post<string>('/admin/user/register', dto)
    return token as unknown as string
  } catch (error) {
    throw error
  }
}

// ────────────────────────────────
// 2. 注册 Step2 — 填写用户画像
//    需要已登录（JWT）
// ────────────────────────────────
export async function completeProfile(dto: RegisterStep2DTO): Promise<string> {
  try {
    const msg = await http.post<string>('/admin/user/complete-profile', dto)
    return msg as unknown as string
  } catch (error) {
    throw error
  }
}

// ────────────────────────────────
// 3. 登录
//    返回 JWT Token 字符串
// ────────────────────────────────
export async function login(dto: LoginDTO): Promise<string> {
  try {
    const token = await http.post<string>('/admin/user/login', dto)
    return token as unknown as string
  } catch (error) {
    throw error
  }
}

// ────────────────────────────────
// 4. 获取 AI 模板列表
//    需要已登录（JWT）
// ────────────────────────────────
export async function getTemplates(): Promise<AITemplate[]> {
  try {
    const list = await http.get<AITemplate[]>('/admin/user/templates')
    return list as unknown as AITemplate[]
  } catch (error) {
    throw error
  }
}

// ────────────────────────────────
// 5. 应用选定模板
//    需要已登录（JWT）
// ────────────────────────────────
export async function useTemplate(dto: TemplateSelectDTO): Promise<string> {
  try {
    const msg = await http.post<string>('/admin/user/use-template', dto)
    return msg as unknown as string
  } catch (error) {
    throw error
  }
}

// ────────────────────────────────
// 6. 创建自定义 AI
//    需要已登录（JWT）
// ────────────────────────────────
export async function customizeAI(dto: CustomCreateDTO): Promise<string> {
  try {
    const msg = await http.post<string>('/admin/user/customize', dto)
    return msg as unknown as string
  } catch (error) {
    throw error
  }
}
