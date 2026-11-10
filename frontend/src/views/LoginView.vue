<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

async function onSubmit() {
  error.value = ''
  if (!email.value || !password.value) {
    error.value = '请输入邮箱和密码'
    return
  }
  loading.value = true
  try {
    await auth.login(email.value.trim(), password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/upload'
    router.push(redirect)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="card auth-card">
    <h2>登录</h2>
    <p class="sub">登录后上传简历，获取 AI 诊断报告</p>

    <div v-if="error" class="error-banner">{{ error }}</div>

    <form @submit.prevent="onSubmit">
      <div class="field">
        <label for="email">邮箱</label>
        <input id="email" v-model="email" type="email" class="input" placeholder="you@example.com" autocomplete="email" />
      </div>
      <div class="field">
        <label for="password">密码</label>
        <input id="password" v-model="password" type="password" class="input" placeholder="至少 6 位" autocomplete="current-password" />
      </div>
      <button class="btn btn-primary btn-block" :disabled="loading">
        {{ loading ? '登录中…' : '登 录' }}
      </button>
    </form>

    <p class="form-footer">
      还没有账号？<router-link to="/register">立即注册</router-link>
    </p>
  </div>
</template>
