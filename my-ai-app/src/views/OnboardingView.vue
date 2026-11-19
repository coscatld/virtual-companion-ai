<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useOnboarding } from '../composables/useOnboarding'
import type { RegisterStep2DTO } from '../api/types/user'

const { needsProfile, isLoading, error, templates, submitProfile, refreshTemplates, applyTemplate, createCustom } = useOnboarding()
const profile = reactive<RegisterStep2DTO>({ username: '', nickname: '', avatarUrl: '', gender: 0, birthday: '' })
const custom = reactive({ aiName: '', tags: '', interests: '', description: '' })
const selected = ref('')
const chosenName = ref('')
const mode = ref<'template' | 'custom'>('template')

function list(value: string): string[] {
  return value.split(/[,，]/).map((item) => item.trim()).filter(Boolean)
}
</script>

<template>
  <main class="sheet">
    <h1>{{ needsProfile ? '个人资料' : '设置你的伴侣' }}</h1>
    <form v-if="needsProfile" class="fields" @submit.prevent="submitProfile(profile)">
      <div class="field-pair">
        <label>用户名 <input v-model.trim="profile.username" maxlength="50" required></label>
        <label>昵称 <input v-model.trim="profile.nickname" maxlength="50" required></label>
      </div>
      <label>头像网址（可选） <input v-model.trim="profile.avatarUrl" type="url" maxlength="500" placeholder="https://…"></label>
      <div class="field-pair">
        <label>性别
          <select v-model="profile.gender"><option :value="0">不公开</option><option :value="1">男</option><option :value="2">女</option><option :value="3">其他</option></select>
        </label>
        <label>生日 <input v-model="profile.birthday" type="date" required></label>
      </div>
      <button class="primary" type="submit" :disabled="isLoading">下一步</button>
    </form>
    <template v-else>
      <div class="actions mode">
        <button type="button" :aria-pressed="mode === 'template'" @click="mode = 'template'">选用模板</button>
        <button type="button" :aria-pressed="mode === 'custom'" @click="mode = 'custom'">自定义伴侣</button>
      </div>
      <form v-if="mode === 'template'" class="fields" @submit.prevent="applyTemplate({ templateId: selected, aiName: chosenName })">
        <div class="template-grid">
          <label v-for="template in templates" :key="template.templateId" class="template-option">
            <input v-model="selected" type="radio" name="template" :value="template.templateId">
            <strong>{{ template.name }}</strong>
            <span class="muted">{{ template.tags.join(' · ') }}</span>
          </label>
        </div>
        <button v-if="!templates.length && !isLoading" type="button" @click="refreshTemplates">重新加载模板</button>
        <label>伴侣名字（可选） <input v-model.trim="chosenName" maxlength="50"></label>
        <button class="primary" type="submit" :disabled="!selected || isLoading">使用这个模板</button>
      </form>
      <form v-else class="fields" @submit.prevent="createCustom({ aiName: custom.aiName, personalityTags: list(custom.tags), interests: list(custom.interests), description: custom.description })">
        <label>名字 <input v-model.trim="custom.aiName" maxlength="50" required></label>
        <label>性格 <input v-model="custom.tags" maxlength="240" placeholder="用逗号分隔，例如：温和，好奇"></label>
        <label>兴趣 <input v-model="custom.interests" maxlength="240" placeholder="用逗号分隔，例如：音乐，旅行"></label>
        <label>希望如何相处 <textarea v-model.trim="custom.description" maxlength="2000" rows="3"></textarea></label>
        <button class="primary" type="submit" :disabled="isLoading">创建伴侣</button>
      </form>
    </template>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
  </main>
</template>
