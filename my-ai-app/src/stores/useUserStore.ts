/**
 * 用户身份与 AI 伴侣 Profile 状态管理
 * - Token 持久化到 localStorage（key: 'vr_token'）
 * - 提供鉴权相关的 getter 和 action
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AITemplate } from '../api/types/user'

export const useUserStore = defineStore('user', () => {
  // ───── State ─────

  /** JWT Token，初始从 localStorage 恢复 */
  const token = ref<string | null>(localStorage.getItem('vr_token'))

  /**
   * 用户 ID，由后端注册/登录响应后解析 JWT 获得
   * 简化处理：直接存储，无需前端解析 JWT
   */
  const userId = ref<string | null>(localStorage.getItem('vr_userId'))

  /** 当前 AI 伴侣的模板/Profile 信息（应用模板或自定义后设置） */
  const aiProfile = ref<AITemplate | null>(
    (() => {
      const stored = localStorage.getItem('vr_aiProfile')
      return stored ? (JSON.parse(stored) as AITemplate) : null
    })(),
  )

  // ───── Getters ─────

  /** 是否已登录（有 Token） */
  const isLoggedIn = computed(() => !!token.value)

  /** 是否已完成 AI 伴侣选择（进入聊天页的前置条件） */
  const hasAiProfile = computed(() => !!aiProfile.value)

  // ───── Actions ─────

  /**
   * 保存 Token（登录/注册成功后调用）
   * @param newToken - 后端返回的 JWT 字符串
   * @param uid      - 对应用户 ID
   */
  function setToken(newToken: string, uid: string): void {
    token.value = newToken
    userId.value = uid
    localStorage.setItem('vr_token', newToken)
    localStorage.setItem('vr_userId', uid)
  }

  /**
   * 设置 AI 伴侣 Profile（应用模板或自定义完成后调用）
   * @param profile - AITemplate 对象（可从 getTemplates 列表中取得）
   */
  function setAiProfile(profile: AITemplate): void {
    aiProfile.value = profile
    localStorage.setItem('vr_aiProfile', JSON.stringify(profile))
  }

  /**
   * 退出登录，清空所有状态和本地存储
   */
  function clearUser(): void {
    token.value = null
    userId.value = null
    aiProfile.value = null
    localStorage.removeItem('vr_token')
    localStorage.removeItem('vr_userId')
    localStorage.removeItem('vr_aiProfile')
  }

  return {
    // state
    token,
    userId,
    aiProfile,
    // getters
    isLoggedIn,
    hasAiProfile,
    // actions
    setToken,
    setAiProfile,
    clearUser,
  }
})
