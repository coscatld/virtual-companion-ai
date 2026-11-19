import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getAccount, getCompanion } from '../api/userApi'
import type { Account, Companion } from '../api/types/user'

const TOKEN_KEY = 'vr_token'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY))
  const account = ref<Account | null>(null)
  const companion = ref<Companion | null>(null)
  const accountError = ref('')
  const isLoggedIn = computed(() => Boolean(token.value))
  let hydratedToken: string | null = null
  let pending: { token: string; request: Promise<void> } | undefined

  function setToken(value: string): void {
    localStorage.setItem(TOKEN_KEY, value)
    token.value = value
    hydratedToken = null
    account.value = null
    companion.value = null
    accountError.value = ''
  }

  function clearUser(): void {
    localStorage.removeItem(TOKEN_KEY)
    token.value = null
    account.value = null
    companion.value = null
    hydratedToken = null
    accountError.value = ''
  }

  async function loadAccount(force = false): Promise<void> {
    const current = token.value
    if (!current || (!force && hydratedToken === current)) return
    if (pending?.token === current) return pending.request

    const request = Promise.all([getAccount(), getCompanion()])
      .then(([nextAccount, nextCompanion]) => {
        if (token.value !== current) return
        account.value = nextAccount
        companion.value = nextCompanion
        hydratedToken = current
        accountError.value = ''
      })
      .finally(() => {
        if (pending?.request === request) pending = undefined
      })
    pending = { token: current, request }
    return request
  }

  return { token, account, companion, accountError, isLoggedIn, setToken, clearUser, loadAccount }
})
