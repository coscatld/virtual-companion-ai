/**
 * useBriefingForm — 日常播报设置表单逻辑
 *
 * 管理表单字段的响应式状态、校验逻辑和提交到后端
 *
 * 使用方式（在 Vue 组件中）：
 *   const { form, errors, isLoading, submitBriefing, resetForm } = useBriefingForm()
 */
import { reactive, ref } from 'vue'
import { setAlarm } from '../api/briefingApi'
import type { UserAlarmProfileDTO } from '../api/types/briefing'

// ── 时间格式校验正则（HH:mm，00:00~23:59） ──
const TIME_REGEX = /^([01]\d|2[0-3]):([0-5]\d)$/

export function useBriefingForm() {
  // ─── 表单字段（响应式） ───
  const form = reactive<UserAlarmProfileDTO>({
    city: '',
    cronExpression: '',   // 用户在 UI 填写 "HH:mm" 格式，后端自动转 Cron
    scheduleFilePath: '',
    enabled: true,
  })

  // ─── 字段级错误消息（为空字符串表示无错误） ───
  const errors = reactive({
    city: '',
    cronExpression: '',
    scheduleFilePath: '',
  })

  /** 提交中状态 */
  const isLoading = ref(false)

  /** 提交成功的服务器确认消息 */
  const successMessage = ref<string | null>(null)

  /** 提交失败的全局错误 */
  const submitError = ref<string | null>(null)

  // ─── 前端校验 ───
  function validate(): boolean {
    let valid = true

    if (!form.city.trim()) {
      errors.city = '城市名称不能为空'
      valid = false
    } else {
      errors.city = ''
    }

    if (!form.cronExpression.trim()) {
      errors.cronExpression = '请输入提醒时间'
      valid = false
    } else if (
      !TIME_REGEX.test(form.cronExpression) &&
      // 同时允许直接传 Cron 表达式（包含空格）
      !form.cronExpression.includes(' ')
    ) {
      errors.cronExpression = '时间格式不正确，请使用 HH:mm（如 08:30）'
      valid = false
    } else {
      errors.cronExpression = ''
    }

    if (!form.scheduleFilePath.trim()) {
      errors.scheduleFilePath = '授权文件路径不能为空'
      valid = false
    } else {
      errors.scheduleFilePath = ''
    }

    return valid
  }

  // ─── 提交表单 ───
  async function submitBriefing(): Promise<void> {
    successMessage.value = null
    submitError.value = null

    if (!validate()) return

    isLoading.value = true
    try {
      const msg = await setAlarm({ ...form })
      successMessage.value = msg
      // TODO: 触发 UI Toast：Toast.success(msg)
    } catch (e: unknown) {
      submitError.value = e instanceof Error ? e.message : '设置失败，请重试'
      // TODO: 触发 UI Toast：Toast.error(submitError.value)
    } finally {
      isLoading.value = false
    }
  }

  // ─── 重置表单 ───
  function resetForm(): void {
    form.city = ''
    form.cronExpression = ''
    form.scheduleFilePath = ''
    form.enabled = true
    errors.city = ''
    errors.cronExpression = ''
    errors.scheduleFilePath = ''
    successMessage.value = null
    submitError.value = null
  }

  return {
    form,          // 双向绑定到 v-model
    errors,        // 字段错误，绑定到校验提示文字
    isLoading,     // 控制提交按钮 loading 状态
    successMessage,// 成功提示
    submitError,   // 失败提示
    submitBriefing,
    resetForm,
  }
}
