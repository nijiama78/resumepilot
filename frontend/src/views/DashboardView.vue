<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  Filler,
  Legend,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  RadarController,
  RadialLinearScale,
  Tooltip,
} from 'chart.js'
import { api } from '../api'
import type { Analysis } from '../types'

Chart.register(
  BarController,
  BarElement,
  CategoryScale,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  RadarController,
  RadialLinearScale,
  Filler,
  Legend,
  Tooltip,
)

const list = ref<Analysis[]>([])
const loading = ref(true)
const error = ref('')

// 按时间正序（旧 → 新）
const chronological = computed(() =>
  [...list.value].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()),
)

const latest = computed(() => chronological.value[chronological.value.length - 1])

// 最新一次分析的五维得分（折算成百分制）
const latestDims = computed(() => {
  if (!latest.value) return []
  return Object.values(latest.value.details.dimensions).map((d) => ({
    label: d.label,
    pct: d.max > 0 ? Math.round((d.score / d.max) * 100) : 0,
  }))
})

// 所有含 JD 的分析中，缺失关键词出现频次（短板优先级排序）
const missingStats = computed(() => {
  const counter = new Map<string, number>()
  for (const item of list.value) {
    for (const kw of item.details.missing_keywords) {
      counter.set(kw, (counter.get(kw) ?? 0) + 1)
    }
  }
  return [...counter.entries()]
    .map(([keyword, count]) => ({ keyword, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10)
})

const latestAvgDim = computed(() => {
  if (!latestDims.value.length) return null
  return Math.round(latestDims.value.reduce((s, d) => s + d.pct, 0) / latestDims.value.length)
})

function shortTime(iso: string): string {
  return new Date(iso).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
}

const CHART_TEXT = '#6b7280'
const CHART_GRID = '#eef0f4'

let trendChart: Chart | null = null
let radarChart: Chart | null = null
let gapChart: Chart | null = null

function renderCharts() {
  trendChart?.destroy()
  radarChart?.destroy()
  gapChart?.destroy()
  trendChart = null
  radarChart = null
  gapChart = null

  const items = chronological.value

  // 1. 评分趋势折线图
  const trendEl = document.getElementById('chart-trend') as HTMLCanvasElement | null
  if (trendEl && items.length >= 2) {
    trendChart = new Chart(trendEl, {
      type: 'line',
      data: {
        labels: items.map((i) => shortTime(i.created_at)),
        datasets: [
          {
            label: '总分',
            data: items.map((i) => i.score),
            borderColor: '#4f46e5',
            backgroundColor: 'rgba(79, 70, 229, 0.12)',
            fill: true,
            tension: 0.35,
            pointRadius: 4,
            pointBackgroundColor: '#4f46e5',
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          y: { min: 0, max: 100, ticks: { color: CHART_TEXT }, grid: { color: CHART_GRID } },
          x: { ticks: { color: CHART_TEXT }, grid: { display: false } },
        },
        plugins: { legend: { display: false } },
      },
    })
  }

  // 2. 最新分析五维雷达图
  const radarEl = document.getElementById('chart-radar') as HTMLCanvasElement | null
  if (radarEl && latestDims.value.length) {
    radarChart = new Chart(radarEl, {
      type: 'radar',
      data: {
        labels: latestDims.value.map((d) => d.label),
        datasets: [
          {
            label: '得分（%）',
            data: latestDims.value.map((d) => d.pct),
            borderColor: '#7c3aed',
            backgroundColor: 'rgba(124, 58, 237, 0.18)',
            pointBackgroundColor: '#7c3aed',
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          r: {
            min: 0,
            max: 100,
            ticks: { display: false },
            grid: { color: CHART_GRID },
            angleLines: { color: CHART_GRID },
            pointLabels: { color: '#1f2937', font: { size: 12 } },
          },
        },
        plugins: { legend: { display: false } },
      },
    })
  }

  // 3. 短板关键词频次横向条形图
  const gapEl = document.getElementById('chart-gap') as HTMLCanvasElement | null
  if (gapEl && missingStats.value.length) {
    gapChart = new Chart(gapEl, {
      type: 'bar',
      data: {
        labels: missingStats.value.map((s) => s.keyword),
        datasets: [
          {
            label: '缺失次数',
            data: missingStats.value.map((s) => s.count),
            backgroundColor: 'rgba(220, 38, 38, 0.75)',
            borderRadius: 6,
          },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        scales: {
          x: { min: 0, ticks: { stepSize: 1, color: CHART_TEXT }, grid: { color: CHART_GRID } },
          y: { ticks: { color: '#1f2937' }, grid: { display: false } },
        },
        plugins: { legend: { display: false } },
      },
    })
  }
}

onMounted(async () => {
  try {
    list.value = await api.analyses()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
    renderCharts()
  }
})

onBeforeUnmount(() => {
  trendChart?.destroy()
  radarChart?.destroy()
  gapChart?.destroy()
})
</script>

<template>
  <div>
    <div class="card">
      <h2>诊断 Dashboard</h2>
      <p class="sub">评分趋势 · 维度画像 · 技能短板，全部来自你的历史分析记录</p>

      <p v-if="loading" class="muted">加载中…</p>
      <div v-else-if="error" class="error-banner">{{ error }}</div>

      <div v-else-if="!list.length" class="empty-state">
        <div class="icon">📊</div>
        <p>还没有分析数据，先去做一次简历诊断</p>
        <router-link to="/upload" class="btn btn-primary btn-sm mt-2">去上传简历</router-link>
      </div>

      <template v-else>
        <div class="stat-row">
          <div class="stat-box">
            <div class="stat-num">{{ list.length }}</div>
            <div class="stat-label">分析次数</div>
          </div>
          <div class="stat-box">
            <div class="stat-num">{{ latest?.score ?? '-' }}</div>
            <div class="stat-label">最新评分</div>
          </div>
          <div class="stat-box">
            <div class="stat-num">
              {{ Math.round(chronological.reduce((s, i) => s + i.score, 0) / chronological.length) }}
            </div>
            <div class="stat-label">平均分</div>
          </div>
          <div class="stat-box">
            <div class="stat-num">{{ latestAvgDim ?? '-' }}</div>
            <div class="stat-label">最新均维</div>
          </div>
        </div>
      </template>
    </div>

    <template v-if="!loading && !error && list.length">
      <div v-if="chronological.length >= 2" class="card">
        <h3 class="section-title">评分趋势</h3>
        <div class="chart-wrap"><canvas id="chart-trend" /></div>
        <p class="muted mt-2">改过简历后再来分析，看分数涨没涨。</p>
      </div>

      <div v-if="latestDims.length" class="card">
        <h3 class="section-title">最新分析 · 五维画像（{{ latest?.filename }}）</h3>
        <div class="chart-wrap chart-wrap-radar"><canvas id="chart-radar" /></div>
      </div>

      <div v-if="missingStats.length" class="card">
        <h3 class="section-title">技能短板 Top {{ missingStats.length }}</h3>
        <p class="sub">历次 JD 匹配中反复缺失的关键词，按出现频次排序</p>
        <div class="chart-wrap"><canvas id="chart-gap" /></div>
      </div>

      <div v-if="chronological.length < 2 && !missingStats.length" class="card">
        <p class="muted">目前只有 1 条分析记录。多分析几次（尤其是带 JD 的），这里会出现趋势图和短板统计。</p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.stat-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.stat-box {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  text-align: center;
}

.stat-num {
  font-size: 26px;
  font-weight: 800;
  color: var(--primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: var(--muted);
  margin-top: 2px;
}

.chart-wrap {
  position: relative;
  height: 280px;
}

.chart-wrap-radar {
  height: 320px;
  max-width: 460px;
  margin: 0 auto;
}
</style>
