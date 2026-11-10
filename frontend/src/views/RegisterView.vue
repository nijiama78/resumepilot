<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const email = ref('')
const password = ref('')
const password2 = ref('')
const error = ref('')
const loading = ref(false)

const auth = useAuthStore()
const router = useRouter()

async function onSubmit() {
  error.value = ''
  if (!email.value || !password.value) {
    error.value = '请输入邮箱和密码'
    return
  }
  if (password.value.length < 6) {
    error.value = '密码至少 6 位'
    return
  }
  if (password.value !== password2.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  try {
    await auth.register(email.value.trim(), password.value)
    router.push('/upload')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '注册失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="card auth-card">
    <h2>注册</h2>
    <p class="sub">创建账号，开始诊断你的简历</p>

    <div v-if="error" class="error-banner">{{ error }}</div>

    <form @submit.prevent="onSubmit">
      <div class="field">
        <label for="email">邮箱</label>
        <input id="email" v-model="email" type="email" class="input" placeholder="you@example.com" autocomplete="email" />
      </div>
      <div class="field">
        <label for="password">密码</label>
        <input id="password" v-model="password" type="password" class="input" placeholder="至少 6 位" autocomplete="new-password" />
      </div>
      <div class="field">
        <label for="password2">确认密码</label>
        <input id="password2" v-model="password2" type="password" class="input" placeholder="再次输入密码" autocomplete="new-password" />
      </div>
      <button class="btn btn-primary btn-block" :disabled="loading">
        {{ loading ? '注册中…' : '注 册' }}
      </button>
    </form>

    <p class="form-footer">
      已有账号？<router-link to="/login">直接登录</router-link>
    </p>
  </div>
</template>
