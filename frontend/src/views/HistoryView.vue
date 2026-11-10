<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import type { Analysis } from '../types'

const list = ref<Analysis[]>([])
const loading = ref(true)
const router = useRouter()

onMounted(async () => {
  try {
    list.value = await api.analyses()
  } finally {
    loading.value = false
  }
})

function scoreStyle(score: number) {
  const color = score >= 85 ? '#16a34a' : score >= 70 ? '#4f46e5' : score >= 55 ? '#d97706' : '#dc2626'
  return { color, background: `${color}1a` }
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}
</script>

<template>
  <div class="card">
    <h2>分析历史</h2>
    <p class="sub">共 {{ list.length }} 条记录</p>

    <p v-if="loading" class="muted">加载中…</p>

    <div v-else-if="!list.length" class="empty-state">
      <div class="icon">📋</div>
      <p>还没有分析记录</p>
      <router-link to="/upload" class="btn btn-primary btn-sm mt-2">去上传简历</router-link>
    </div>

    <div v-else>
      <div v-for="item in list" :key="item.id" class="history-item" @click="router.push(`/result/${item.id}`)">
        <div class="history-score" :style="scoreStyle(item.score)">{{ item.score }}</div>
        <div class="history-main">
          <p class="history-title">{{ item.filename }}</p>
          <p class="history-meta">
            {{ formatTime(item.created_at) }}
            · {{ item.engine === 'llm' ? 'AI 引擎' : '规则引擎' }}
            <template v-if="item.job_description"> · 含 JD 匹配</template>
          </p>
        </div>
        <span class="muted">›</span>
      </div>
    </div>
  </div>
</template>
