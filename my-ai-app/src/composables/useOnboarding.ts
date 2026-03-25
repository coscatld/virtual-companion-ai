/**
 * useOnboarding — 多步注册入场流状态机
 *
 * 步骤流转：
 *   STEP_1_REGISTER
 *     → STEP_2_PROFILE
 *       → STEP_3_CHOOSE_AI
 *         ├─ (选模板) → STEP_3A_USE_TEMPLATE → DONE
 *         └─ (自定义) → STEP_3B_CUSTOMIZE    → DONE
 *
 * 使用方式（在 Vue 组件中）：
 *   const { step, isLoading, error, submitStep1, submitStep2, applyTemplate, createCustom } = useOnboarding()
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/useUserStore'
import { register, completeProfile, getTemplates, useTemplate, customizeAI } from '../api/userApi'
import type {
  RegisterStep1DTO,
  RegisterStep2DTO,
  AITemplate,
  TemplateSelectDTO,
  CustomCreateDTO,
} from '../api/types/user'

// ── 步骤枚举 ──
export type OnboardingStep =
  | 'STEP_1_REGISTER'
  | 'STEP_2_PROFILE'
  | 'STEP_3_CHOOSE_AI'
  | 'STEP_3A_USE_TEMPLATE'
  | 'STEP_3B_CUSTOMIZE'
  | 'DONE'

export function useOnboarding() {
  const router = useRouter()
  const userStore = useUserStore()

  /** 当前所在步骤 */
  const step = ref<OnboardingStep>('STEP_1_REGISTER')

  /** 接口请求中状态（控制按钮 loading 动画） */
  const isLoading = ref(false)

  /** 当前错误信息（为 null 表示无错误） */
  const error = ref<string | null>(null)

  /** 可供 Step3 展示的模板列表 */
  const templateList = ref<AITemplate[]>([])

  // ─────────────────────────────────────────────
  // Step 1：注册账号
  // ─────────────────────────────────────────────
  async function submitStep1(dto: RegisterStep1DTO): Promise<void> {
    isLoading.value = true
    error.value = null
    try {
      // register() 返回 JWT Token
      const token = await register(dto)
      // 临时存入 Store（userId 由后端解析，此处用 email 作占位，实际项目可解析 JWT）
      userStore.setToken(token, dto.email)
      step.value = 'STEP_2_PROFILE'
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '注册失败'
    } finally {
      isLoading.value = false
    }
  }

  // ─────────────────────────────────────────────
  // Step 2：完善用户画像
  // ─────────────────────────────────────────────
  async function submitStep2(dto: RegisterStep2DTO): Promise<void> {
    isLoading.value = true
    error.value = null
    try {
      await completeProfile(dto)
      // 顺带拉取模板列表，供 Step 3 展示
      templateList.value = await getTemplates()
      step.value = 'STEP_3_CHOOSE_AI'
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '画像填写失败'
    } finally {
      isLoading.value = false
    }
  }

  // ─────────────────────────────────────────────
  // Step 3A：应用选定模板
  // ─────────────────────────────────────────────
  async function applyTemplate(dto: TemplateSelectDTO): Promise<void> {
    isLoading.value = true
    error.value = null
    step.value = 'STEP_3A_USE_TEMPLATE'
    try {
      await useTemplate(dto)
      // 从模板列表中找到对应 profile，存入 Store
      const selected = templateList.value.find((t) => t.templateId === dto.templateId)
      if (selected) {
        userStore.setAiProfile({
          ...selected,
          // 如果用户自定义了名字，覆盖模板名
          name: dto.aiName?.trim() || selected.name,
        })
      }
      step.value = 'DONE'
      // 跳转到聊天页
      await router.replace('/chat')
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '应用模板失败'
      step.value = 'STEP_3_CHOOSE_AI' // 回退到选择步骤
    } finally {
      isLoading.value = false
    }
  }

  // ─────────────────────────────────────────────
  // Step 3B：自定义创建 AI
  // ─────────────────────────────────────────────
  async function createCustom(dto: CustomCreateDTO): Promise<void> {
    isLoading.value = true
    error.value = null
    step.value = 'STEP_3B_CUSTOMIZE'
    try {
      await customizeAI(dto)
      // 自定义 AI 没有 templateId，构造一个占位 Profile
      userStore.setAiProfile({
        templateId: 'custom',
        name: dto.aiName,
        tags: dto.personalityTags ?? [],
        interests: (dto.interests ?? []).join(','),
      })
      step.value = 'DONE'
      await router.replace('/chat')
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '自定义 AI 创建失败'
      step.value = 'STEP_3_CHOOSE_AI'
    } finally {
      isLoading.value = false
    }
  }

  return {
    step,
    isLoading,
    error,
    templateList,
    submitStep1,
    submitStep2,
    applyTemplate,
    createCustom,
  }
}
