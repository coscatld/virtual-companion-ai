<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { login, register } from '../api/userApi'
import { useUserStore } from '../stores/useUserStore'

const props = defineProps<{ creating?: boolean }>()
const router = useRouter()
const user = useUserStore()
const form = reactive({ email: '', phone: '', password: '' })
const error = ref('')
const busy = ref(false)

async function submit() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    const token = await (props.creating ? register(form) : login(form))
    user.setToken(token)
    await router.replace(props.creating ? '/onboarding' : '/chat')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '暂时无法连接，请重试。'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="sheet narrow">
    <h1>{{ creating ? '创建账户' : '登录 GA' }}</h1>
    <form class="fields" @submit.prevent="submit">
      <label>邮箱 <input v-model.trim="form.email" type="email" autocomplete="email" required></label>
      <label>手机号码 <input v-model.trim="form.phone" type="tel" inputmode="numeric" autocomplete="tel" pattern="1[3-9][0-9]{9}" required></label>
      <label>密码 <input v-model="form.password" type="password" :autocomplete="creating ? 'new-password' : 'current-password'" :minlength="creating ? 6 : undefined" :maxlength="creating ? 20 : undefined" required></label>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button class="primary" :disabled="busy" type="submit">{{ busy ? '请稍候…' : creating ? '注册' : '登录' }}</button>
    </form>
    <p v-if="creating" class="muted">已有账户？ <RouterLink to="/login">登录</RouterLink></p>
    <p v-else class="muted">第一次来？ <RouterLink to="/register">创建账户</RouterLink></p>
  </main>
</template>
