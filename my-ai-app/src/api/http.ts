/**
 * Axios 全局实例封装
 * - 自动注入 JWT Token（Bearer）
 * - 统一解包 ApiResult<T>，非 200 自动抛出带 message 的 Error
 * - 预留 UI Toast 触发口（见 onApiError）
 */
import axios, { type AxiosInstance, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import type { ApiResult } from './types/apiResult'
import { apiBase } from './endpoints'

export class HttpError extends Error {
  readonly status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.status = status
  }
}

// ────────────────────────────────
// Toast 触发口
// 替换此函数以接入实际 UI Toast 组件（如 Element Plus、Vant）
// ────────────────────────────────
export function onApiError(message: string): void {
  // TODO: 接入 UI 通知，例如：ElMessage.error(message)
  console.error(`[API Error] ${message}`)
}

// ────────────────────────────────
// Axios 实例
// ────────────────────────────────
const http: AxiosInstance = axios.create({
  baseURL: apiBase,
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
})

// ── 请求拦截器：注入 JWT ──
http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('vr_token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// ── 响应拦截器：解包 ApiResult ──
http.interceptors.response.use(
  (response: AxiosResponse<ApiResult<unknown>>) => {
    const result = response.data
    if (typeof result !== 'object' || result === null || !('code' in result)) {
      return response.data as unknown as AxiosResponse<unknown>
    }
    if (result.code !== 200) {
      onApiError(result.message)
      return Promise.reject(new Error(result.message))
    }
    // 直接返回解包后的 data，调用方无需再取 .data
    return result.data as unknown as AxiosResponse<unknown>
  },
  (error: unknown) => {
    const msg = axios.isAxiosError(error) && error.response?.status === 401
      ? '登录已过期，请重新登录。'
      : axios.isAxiosError(error) && typeof error.response?.data?.message === 'string'
        ? error.response.data.message
        : error instanceof Error ? error.message : '网络异常，请检查连接后重试'
    onApiError(msg)
    return Promise.reject(new HttpError(msg, axios.isAxiosError(error) ? error.response?.status : undefined))
  },
)

export default http
