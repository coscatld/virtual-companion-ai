/**
 * 通用 API 响应体，对应后端 Result<T>
 * code: 200 = 成功, 500 = 失败
 */
export interface ApiResult<T = unknown> {
  code: number
  message: string
  data: T
}
