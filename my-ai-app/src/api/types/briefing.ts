/**
 * 日常播报 / 闹钟配置 DTO
 * 对应后端 com.example.vr_gfriend.Scheduler.DTO.UserAlarmProfileDTO
 */

// ────────────────────────────────
// 设置闹钟 DTO
// POST /api/briefing/set（需要 JWT）
// 注：userId 由后端从 JWT 中读取，前端无需传递
// 后端支持传 "08:30" 格式，会自动转为 Cron；
// 也可直接传完整 Cron 表达式（如 "0 30 8 * * ?"）
// ────────────────────────────────
export interface UserAlarmProfileDTO {
  city: string              // 城市名称，如 "Beijing"
  cronExpression: string    // "HH:mm" 格式字符串 或 完整 Cron 表达式
  scheduleFilePath: string  // 授权/任务文件路径
  enabled: boolean          // 是否开启该闹钟
}
