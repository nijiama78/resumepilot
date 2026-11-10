<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()

onMounted(() => {
  if (auth.isLoggedIn && !auth.user) {
    auth.fetchMe()
  }
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <router-link to="/" class="brand">
        <span class="brand-mark">RP</span>
        <span class="brand-name">ResumePilot</span>
        <span class="brand-tag">AI 简历诊断</span>
      </router-link>
      <nav v-if="auth.isLoggedIn" class="nav">
        <router-link to="/upload" class="nav-link">上传分析</router-link>
        <router-link to="/history" class="nav-link">历史记录</router-link>
        <router-link to="/dashboard" class="nav-link">Dashboard</router-link>
        <span v-if="auth.user" class="nav-user">{{ auth.user.email }}</span>
        <button class="btn btn-ghost" @click="auth.logout(); $router.push('/login')">退出</button>
      </nav>
      <nav v-else class="nav">
        <router-link to="/login" class="nav-link">登录</router-link>
        <router-link to="/register" class="btn btn-primary btn-sm">注册</router-link>
      </nav>
    </header>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>
