import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { completeProfile, customizeAI, getTemplates, useTemplate } from '../api/userApi'
import type { AITemplate, CustomCreateDTO, RegisterStep2DTO, TemplateSelectDTO } from '../api/types/user'
import { useUserStore } from '../stores/useUserStore'

export function useOnboarding() {
  const router = useRouter()
  const user = useUserStore()
  const needsProfile = computed(() => user.account?.registerStage === 0)
  const isLoading = ref(false)
  const error = ref('')
  const templates = ref<AITemplate[]>([])

  async function submit(action: () => Promise<unknown>): Promise<void> {
    if (isLoading.value) return
    isLoading.value = true
    error.value = ''
    try {
      await action()
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '暂时无法保存，请重试。'
    } finally {
      isLoading.value = false
    }
  }

  async function loadTemplates(): Promise<void> {
    templates.value = await getTemplates()
  }

  function submitProfile(profile: RegisterStep2DTO): Promise<void> {
    return submit(async () => {
      await completeProfile(profile)
      await user.loadAccount(true)
      await loadTemplates()
    })
  }

  function saveCompanion(save: () => Promise<unknown>): Promise<void> {
    return submit(async () => {
      await save()
      await user.loadAccount(true)
      await router.replace('/chat')
    })
  }

  onMounted(() => { if (!needsProfile.value) void submit(loadTemplates) })

  return {
    needsProfile, isLoading, error, templates, submitProfile,
    refreshTemplates: () => submit(loadTemplates),
    applyTemplate: (data: TemplateSelectDTO) => saveCompanion(() => useTemplate(data)),
    createCustom: (data: CustomCreateDTO) => saveCompanion(() => customizeAI(data)),
  }
}
