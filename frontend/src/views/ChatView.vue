<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, chatStream } from '../api'
import type { Analysis } from '../types'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const route = useRoute()
const resumeId = Number(route.params.resumeId)
const analysis = ref<Analysis | null>(null)
const error = ref('')

const messages = ref<Message[]>([])
const input = ref('')
const sending = ref(false)
const listEl = ref<HTMLElement | null>(null)

const quickQuestions = [
  '我的项目经历怎么改更好？',
  '针对这个 JD 我还缺什么技能？',
  '简历开头怎么写更吸引人？',
]

onMounted(async () => {
  try {
    analysis.value = await api.analysis(Number(route.params.analysisId))
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  }
})

async function scrollBottom() {
  await nextTick()
  listEl.value?.scrollTo({ top: listEl.value.scrollHeight })
}

async function send(text?: string) {
  const question = (text ?? input.value).trim()
  if (!question || sending.value) return

  messages.value.push({ role: 'user', content: question })
  input.value = ''
  sending.value = true
  const assistant: Message = { role: 'assistant', content: '' }
  messages.value.push(assistant)
  await scrollBottom()

  try {
    await chatStream(resumeId, question, (token) => {
      assistant.content += token + '\n'
      scrollBottom()
    })
  } catch (e) {
    assistant.content = e instanceof Error ? e.message : '请求失败'
  } finally {
    sending.value = false
    await scrollBottom()
  }
}
</script>

<template>
  <div class="card chat-card">
    <h2>AI 对话式诊断</h2>
    <p class="sub">
      基于简历「{{ analysis?.filename ?? '…' }}」追问，RAG 检索相关片段后流式生成建议
      <template v-if="analysis"> · 当前评分 {{ analysis.score }}/100</template>
    </p>

    <div v-if="error" class="error-banner">{{ error }}</div>

    <div ref="listEl" class="chat-list">
      <div v-if="!messages.length" class="chat-empty">
        <p class="muted">试试这些常见问题：</p>
        <div class="chip-group" style="justify-content: center">
          <button
            v-for="q in quickQuestions"
            :key="q"
            class="chip chip-btn"
            :disabled="sending"
            @click="send(q)"
          >
            {{ q }}
          </button>
        </div>
      </div>

      <div
        v-for="(m, i) in messages"
        :key="i"
        class="chat-msg"
        :class="m.role"
      >
        <div class="chat-bubble">{{ m.content }}</div>
      </div>

      <div v-if="sending && messages[messages.length - 1]?.content === ''" class="chat-msg assistant">
        <div class="chat-bubble chat-typing">思考中…</div>
      </div>
    </div>

    <div class="chat-input-row">
      <input
        v-model="input"
        class="input"
        placeholder="继续追问，例如：实习经历那段怎么量化成果？"
        :disabled="sending"
        @keyup.enter="send()"
      />
      <button class="btn btn-primary" :disabled="sending || !input.trim()" @click="send()">
        {{ sending ? '生成中…' : '发送' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-card {
  display: flex;
  flex-direction: column;
}

.chat-list {
  height: 420px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 14px;
  background: #fafbfd;
}

.chat-empty {
  text-align: center;
  padding-top: 100px;
}

.chip-btn {
  cursor: pointer;
  font-family: inherit;
  background: #eef2ff;
  color: var(--primary);
  border: 1px solid #c7d2fe;
}

.chip-btn:hover:not(:disabled) {
  background: #e0e7ff;
}

.chat-msg {
  display: flex;
  margin-bottom: 12px;
}

.chat-msg.user {
  justify-content: flex-end;
}

.chat-bubble {
  max-width: 78%;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.7;
  border-radius: 12px;
  padding: 10px 14px;
}

.chat-msg.user .chat-bubble {
  background: var(--primary);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.chat-msg.assistant .chat-bubble {
  background: #fff;
  border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
}

.chat-typing {
  color: var(--muted);
  font-style: italic;
}

.chat-input-row {
  display: flex;
  gap: 10px;
}

.chat-input-row .input {
  flex: 1;
}
</style>
