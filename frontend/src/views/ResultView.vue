<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import type { Analysis } from '../types'

const route = useRoute()
const analysis = ref<Analysis | null>(null)
const error = ref('')

onMounted(async () => {
  try {
    analysis.value = await api.analysis(Number(route.params.id))
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  }
})

const scoreColor = computed(() => {
  const s = analysis.value?.score ?? 0
  if (s >= 85) return '#16a34a'
  if (s >= 70) return '#4f46e5'
  if (s >= 55) return '#d97706'
  return '#dc2626'
})

const ringStyle = computed(() => {
  const pct = (analysis.value?.score ?? 0) / 100
  return {
    background: `conic-gradient(${scoreColor.value} ${pct * 360}deg, #eef0f4 0deg)`,
  }
})

const dimensions = computed(() => Object.values(analysis.value?.details.dimensions ?? {}))
</script>

<template>
  <div v-if="error" class="card">
    <div class="error-banner">{{ error }}</div>
  </div>

  <div v-else-if="!analysis" class="card">
    <p class="muted">加载中…</p>
  </div>

  <template v-else>
    <!-- 总览 -->
    <div class="card">
      <div class="result-head">
        <div class="score-ring" :style="ringStyle">
          <div class="score-ring-inner">
            <span class="score-num" :style="{ color: scoreColor }">{{ analysis.score }}</span>
            <span class="score-max">/ 100</span>
          </div>
        </div>
        <div>
          <span class="engine-badge" :class="analysis.engine">
            {{ analysis.engine === 'llm' ? 'AI 引擎分析' : '规则引擎分析' }}
          </span>
          <h2 style="margin: 0">{{ analysis.filename }}</h2>
          <p class="summary-text">{{ analysis.summary }}</p>
        </div>
      </div>
    </div>

    <!-- 维度得分 -->
    <div class="card">
      <h3 class="section-title">维度得分</h3>
      <div v-for="dim in dimensions" :key="dim.label" class="dim-row">
        <div class="dim-head">
          <span>{{ dim.label }}</span>
          <span class="dim-score">{{ dim.score }} / {{ dim.max }}</span>
        </div>
        <div class="progress">
          <div class="progress-bar" :style="{ width: `${(dim.score / dim.max) * 100}%` }"></div>
        </div>
        <div v-if="dim.detail" class="dim-detail">{{ dim.detail }}</div>
      </div>
    </div>

    <!-- 修改建议 -->
    <div v-if="analysis.details.suggestions.length" class="card">
      <h3 class="section-title">修改建议</h3>
      <ol class="suggestion-list">
        <li v-for="(s, i) in analysis.details.suggestions" :key="i">
          <span class="suggestion-idx">{{ i + 1 }}</span>
          <span>{{ s }}</span>
        </li>
      </ol>
    </div>

    <!-- 关键词 -->
    <div v-if="analysis.details.matched_keywords.length || analysis.details.missing_keywords.length" class="card">
      <h3 class="section-title">关键词匹配</h3>
      <div class="keyword-section">
        <h3>已覆盖（{{ analysis.details.matched_keywords.length }}）</h3>
        <div class="chip-group">
          <span v-for="k in analysis.details.matched_keywords" :key="k" class="chip">{{ k }}</span>
        </div>
      </div>
      <div v-if="analysis.details.missing_keywords.length" class="keyword-section">
        <h3>JD 要求但缺失（{{ analysis.details.missing_keywords.length }}）</h3>
        <div class="chip-group">
          <span v-for="k in analysis.details.missing_keywords" :key="k" class="chip missing">{{ k }}</span>
        </div>
      </div>
    </div>

    <!-- JD 与操作 -->
    <div v-if="analysis.job_description" class="card">
      <h3 class="section-title">目标岗位 JD</h3>
      <div class="jd-block">{{ analysis.job_description }}</div>
    </div>

    <div class="mt-4" style="display: flex; gap: 12px; flex-wrap: wrap">
      <router-link :to="`/chat/${analysis.id}/${analysis.resume_id}`" class="btn btn-primary">AI 对话追问</router-link>
      <router-link to="/upload" class="btn btn-ghost">再分析一份</router-link>
      <router-link to="/history" class="btn btn-ghost">查看历史记录</router-link>
    </div>
  </template>
</template>
