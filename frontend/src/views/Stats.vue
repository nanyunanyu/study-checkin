<script setup lang="ts">
import { computed, ref } from 'vue'
import { useDataStore } from '../stores/data'
import { useUiStore } from '../stores/ui'
import Heatmap from '../components/Heatmap.vue'
import {
  addDays,
  checkinDaysOf,
  completionOf,
  formatDuration,
  monthCompletionOf,
  streakOf,
  subjectKey,
  todayStr,
  totalFocusOf
} from '../utils'

const data = useDataStore()
const ui = useUiStore()

const today = todayStr()
const metric = ref<'completion' | 'focus'>('completion')

const streak = computed(() => streakOf(data.days, today))
const monthCompletion = computed(() => monthCompletionOf(data.days, today))
const totalFocus = computed(() => totalFocusOf(data.days))
const checkins = computed(() => checkinDaysOf(data.days))

const subjectStats = computed(() => {
  const map: Record<string, { focus: number; total: number; done: number }> = {}
  for (const log of Object.values(data.days)) {
    for (const task of log.tasks || []) {
      const key = task.subject || '其他'
      if (!map[key]) map[key] = { focus: 0, total: 0, done: 0 }
      map[key].focus += task.focusSec || 0
      map[key].total += 1
      if (task.done) map[key].done += 1
    }
  }
  return Object.entries(map)
    .map(([subject, stat]) => ({
      subject,
      focus: stat.focus,
      total: stat.total,
      completion: stat.total ? (stat.done / stat.total) * 100 : 0
    }))
    .filter((item) => item.total > 0)
    .sort((a, b) => b.focus - a.focus || b.completion - a.completion)
})

const trend = computed(() => {
  const points: { day: string; value: number }[] = []
  for (let index = 29; index >= 0; index -= 1) {
    const day = addDays(today, -index)
    const log = data.days[day]
    points.push({ day, value: log ? completionOf(log) : 0 })
  }
  return points
})

const linePath = computed(() => {
  const width = 640
  const height = 118
  const pad = 6
  const total = trend.value.length - 1 || 1
  return trend.value
    .map((point, index) => {
      const x = pad + (index / total) * (width - pad * 2)
      const y = height - pad - (Math.min(100, point.value) / 100) * (height - pad * 2)
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
})

const areaPath = computed(() => `${linePath.value} L634,118 L6,118 Z`)

const trendAverage = computed(() => {
  const values = trend.value.map((point) => point.value)
  if (!values.length) return 0
  return Math.round((values.reduce((a, b) => a + b, 0) / values.length) * 10) / 10
})
</script>

<template>
  <div class="stack">
    <dl class="stats-summary" aria-label="学习统计概览">
      <div>
        <dt>连续打卡</dt>
        <dd>{{ streak }} 天</dd>
      </div>
      <div>
        <dt>本月平均完成率</dt>
        <dd>{{ monthCompletion }}%</dd>
      </div>
      <div>
        <dt>累计专注</dt>
        <dd>{{ formatDuration(totalFocus) }}</dd>
      </div>
      <div>
        <dt>累计打卡天数</dt>
        <dd>{{ checkins }} 天</dd>
      </div>
    </dl>

    <section class="card card-pad">
      <div class="card-head">
        <div class="card-title">打卡热力图</div>
        <span class="hint">最近一年</span>
        <div class="spacer" />
        <el-radio-group v-model="metric" size="small" aria-label="热力图指标">
          <el-radio-button value="completion">按完成率</el-radio-button>
          <el-radio-button value="focus">按专注时长</el-radio-button>
        </el-radio-group>
      </div>
      <Heatmap :days="data.days" :metric="metric" :today="today" @select="ui.openDay" />
    </section>

    <section class="card card-pad">
      <div class="card-head">
        <div class="card-title">近 30 天完成率</div>
        <span class="hint">平均 {{ trendAverage }}%</span>
        <div class="spacer" />
        <span class="hint">{{ trend[0]?.day.slice(5) }} → {{ trend[trend.length - 1]?.day.slice(5) }}</span>
      </div>
      <svg viewBox="0 0 640 118" style="width: 100%; height: 118px" preserveAspectRatio="none">
        <line x1="6" y1="6" x2="634" y2="6" stroke="var(--border)" stroke-width="1" />
        <line x1="6" y1="59" x2="634" y2="59" stroke="var(--border)" stroke-width="1" stroke-dasharray="3 4" />
        <line x1="6" y1="112" x2="634" y2="112" stroke="var(--border)" stroke-width="1" />
        <path :d="areaPath" fill="var(--accent-soft)" />
        <path :d="linePath" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linejoin="round" />
      </svg>
    </section>

    <section class="card card-pad">
      <div class="card-head">
        <div class="card-title">科目分布</div>
        <div class="spacer" />
        <span class="hint">完成率 / 专注时长</span>
      </div>
      <div v-if="!subjectStats.length" class="empty">还没有数据，先去今日页打个卡</div>
      <div v-for="item in subjectStats" :key="item.subject" class="bar-row" :class="`subj-${subjectKey(item.subject)}`">
        <span style="font-size: 12.5px">{{ item.subject }}</span>
        <div class="bar-track">
          <div class="bar-fill" :style="{ width: `${item.completion}%` }" />
        </div>
        <span class="bar-value">{{ Math.round(item.completion) }}% · {{ Math.round(item.focus / 60) }}分</span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.stats-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-solid);
}

.stats-summary > div {
  min-width: 0;
  padding: 9px 14px;
}

.stats-summary > div + div {
  border-inline-start: 1px solid var(--border);
}

.stats-summary dt {
  color: var(--text-3);
  font-size: 12px;
  line-height: 1.4;
}

.stats-summary dd {
  margin: 2px 0 0;
  color: var(--text);
  font-size: 18px;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

@media (max-width: 560px) {
  .stats-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .stats-summary > div { padding: 7px 11px; }
  .stats-summary > div:nth-child(odd) { border-inline-start: 0; }
  .stats-summary > div:nth-child(n + 3) { border-top: 1px solid var(--border); }
  .stats-summary dd { font-size: 16px; }
}
</style>
