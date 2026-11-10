<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const file = ref<File | null>(null)
const jd = ref('')
const error = ref('')
const uploading = ref(false)

const router = useRouter()

function onPick(e: Event) {
  const input = e.target as HTMLInputElement
  file.value = input.files?.[0] ?? null
  error.value = ''
}

async function onAnalyze() {
  error.value = ''
  if (!file.value) {
    error.value = '请先选择简历文件（支持 PDF / TXT）'
    return
  }
  uploading.value = true
  try {
    const resume = await api.uploadResume(file.value)
    const analysis = await api.analyze(resume.id, jd.value.trim())
    router.push(`/result/${analysis.id}`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '分析失败，请重试'
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div>
    <div class="card">
      <h2>上传简历</h2>
      <p class="sub">上传 PDF 简历；粘贴目标岗位 JD 可获得针对性的匹配分析（可选）</p>

      <div v-if="error" class="error-banner">{{ error }}</div>

      <label class="drop-zone" :class="{ 'has-file': file }">
        <input type="file" accept=".pdf,.txt" style="display: none" @change="onPick" />
        <template v-if="file">
          <div style="font-size: 28px">📄</div>
          <p class="file-name">{{ file.name }}</p>
          <p class="muted">点击可重新选择</p>
        </template>
        <template v-else>
          <div style="font-size: 28px">⬆️</div>
          <p>点击选择简历文件（PDF / TXT，不超过 5MB）</p>
        </template>
      </label>

      <div class="field mt-3">
        <label for="jd">目标岗位 JD（可选）</label>
        <textarea
          id="jd"
          v-model="jd"
          class="textarea"
          rows="7"
          placeholder="粘贴你要投递的岗位描述，分析将计算简历与岗位的关键词匹配度…"
        ></textarea>
      </div>

      <button class="btn btn-primary btn-block" :disabled="uploading" @click="onAnalyze">
        {{ uploading ? '解析分析中…（首次分析约需几秒）' : '开始诊断' }}
      </button>
    </div>

    <p class="muted mt-3" style="text-align: center">
      未配置大模型 API 时使用内置规则引擎评分；配置后自动切换 AI 深度分析。
    </p>
  </div>
</template>
