import { onMounted, reactive, ref } from 'vue'
import { getSettings, setAlarm } from '../api/briefingApi'
import type { UserAlarmProfileDTO } from '../api/types/briefing'

export function useBriefingForm() {
  const form = reactive<UserAlarmProfileDTO>({ city: '', cronExpression: '08:30', enabled: true })
  const isLoading = ref(false)
  const successMessage = ref('')
  const submitError = ref('')

  async function run(action: () => Promise<void>) {
    if (isLoading.value) return
    isLoading.value = true
    successMessage.value = ''
    submitError.value = ''
    try {
      await action()
    } catch (cause) {
      submitError.value = cause instanceof Error ? cause.message : '简报设置暂时无法连接。'
    } finally {
      isLoading.value = false
    }
  }

  function loadSettings() {
    return run(async () => {
      const saved = await getSettings()
      if (!saved) return
      form.city = saved.city
      form.enabled = saved.enabled
      form.cronExpression = saved.cronExpression
    })
  }

  function submitBriefing() {
    return run(async () => {
      successMessage.value = (await setAlarm({ ...form })) || '简报设置已保存。'
    })
  }

  onMounted(loadSettings)
  return { form, isLoading, successMessage, submitError, submitBriefing, loadSettings }
}
