<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useUserStore } from './stores/useUserStore'
import { useChatStore } from './stores/useChatStore'
import './style.css'

const router = useRouter()
const user = useUserStore()
const chat = useChatStore()

function signOut() {
  user.clearUser()
  chat.resetChat()
  void router.replace('/login')
}

function reload() {
  window.location.reload()
}
</script>

<template>
  <div class="site">
    <header class="masthead">
      <RouterLink class="brand" to="/chat">GA<span>伴侣</span></RouterLink>
      <nav v-if="user.isLoggedIn" aria-label="主导航">
        <RouterLink v-if="user.companion" to="/chat">对话</RouterLink>
        <RouterLink v-if="user.companion" to="/settings/briefing">每日简报</RouterLink>
        <button class="quiet" type="button" @click="signOut">退出</button>
      </nav>
    </header>
    <main v-if="user.accountError" class="sheet narrow">
      <h1>账户连接中断</h1>
      <p role="alert">{{ user.accountError }}</p>
      <button class="primary" type="button" @click="reload">重新连接</button>
    </main>
    <RouterView v-else />
  </div>
</template>
