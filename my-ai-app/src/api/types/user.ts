/**
 * 用户相关 DTO 类型定义
 * 对应后端 com.example.vr_gfriend.user.DTO.*
 */

// ────────────────────────────────
// 注册 Step1：基础账号信息
// POST /admin/user/register
// ────────────────────────────────
export interface RegisterStep1DTO {
  email: string    // 邮箱（必填，格式校验）
  phone: string    // 手机号（必填，1[3-9]\d{9}）
  password: string // 密码（必填，6-20 位）
}

// ────────────────────────────────
// 注册 Step2：用户画像
// POST /admin/user/complete-profile（需要 JWT）
// 注：userId 由后端从 JWT 中读取，前端无需传递
// ────────────────────────────────
export interface RegisterStep2DTO {
  username: string    // 用户名（max 50）
  nickname: string    // 昵称
  avatarUrl: string   // 头像 URL
  gender: 0 | 1 | 2 | 3 // 0未知 1男 2女 3其他
  birthday: string    // ISO 日期字符串，如 "2000-01-15"（过去的时间）
}

// ────────────────────────────────
// 登录 DTO
// POST /admin/user/login
// ────────────────────────────────
export interface LoginDTO {
  email: string
  phone: string
  password: string
}

// ────────────────────────────────
// AI 模板（从后端列表接口返回）
// GET /admin/user/templates（需要 JWT）
// ────────────────────────────────
export interface AITemplate {
  templateId: string     // 模板 ID，如 "1"
  name: string           // 模板名称，如 "夏心玲"
  tags: string[]         // 标签列表，如 ["温柔", "耐心"]
  interests: string      // 兴趣（后端为逗号拼接的字符串）
  // initPrompt 被 @JsonIgnore，不出现在返回值中
}

// ────────────────────────────────
// 应用模板 DTO
// POST /admin/user/use-template（需要 JWT）
// ────────────────────────────────
export interface TemplateSelectDTO {
  templateId: string   // 必填，选定的模板 ID
  aiName?: string      // 选填，用户自定义 AI 名字（为空则用模板默认）
}

// ────────────────────────────────
// 自定义 AI 创建 DTO
// POST /admin/user/customize（需要 JWT）
// ────────────────────────────────
export interface CustomCreateDTO {
  aiName: string               // 必填 AI 昵称
  personalityTags?: string[]   // 性格标签列表，如 ["高冷", "毒舌"]
  interests?: string[]         // 兴趣列表，如 ["编程", "游戏"]
  description?: string         // 可选：用户手写的描述文字
}
