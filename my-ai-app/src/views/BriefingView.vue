<script setup lang="ts">
import { useBriefingForm } from '../composables/useBriefingForm'

const { form, isLoading, successMessage, submitError, submitBriefing, loadSettings } = useBriefingForm()
</script>

<template>
  <main class="sheet narrow">
    <h1>每日简报</h1>
    <p class="muted">简报会按时生成。打开对话页即可查看最新一份。</p>
    <form class="fields" @submit.prevent="submitBriefing">
      <label>城市 <input v-model.trim="form.city" maxlength="100" required placeholder="例如：上海"></label>
      <label>服务时区的提醒时间 <input v-model.trim="form.cronExpression" required placeholder="08:30" aria-describedby="briefing-time"></label>
      <small id="briefing-time" class="muted">使用 24 小时格式，例如 08:30。已有 Cron 设置也可保留。</small>
      <label class="check"><input v-model="form.enabled" type="checkbox"> 启用每日简报</label>
      <p v-if="submitError" class="error" role="alert">{{ submitError }}</p>
      <p v-if="successMessage" role="status">{{ successMessage }}</p>
      <div class="actions">
        <button class="primary" type="submit" :disabled="isLoading">保存设置</button>
        <button type="button" :disabled="isLoading" @click="loadSettings">重新加载</button>
      </div>
    </form>
  </main>
</template>
