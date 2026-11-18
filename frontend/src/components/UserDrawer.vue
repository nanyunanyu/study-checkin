<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import type { DayLog, OverviewResponse } from '../types'
import { completionOf, formatDuration, humanDate, normalizeReview, todayStr, weekdayCN } from '../utils'
import Heatmap from './Heatmap.vue'
import RingProgress from './RingProgress.vue'

const props = defineProps<{ userId: number; name: string }>()
const emit = defineEmits<{ (event: 'close'): void }>()

const loading = ref(true)
const error = ref('')
const data = ref<OverviewResponse | null>(null)
const metric = ref<'completion' | 'focus'>('completion')

const daysMap = computed<Record<string, DayLog>>(() => {
  const map: Record<string, DayLog> = {}
  for (const log of data.value?.days || []) {
    map[log.day] = { ...log, review: normalizeReview(log.review) }
  }
  return map
})

const recent = computed(() =>
  [...(data.value?.days || [])]
    .filter((log) => log.checkedIn || completionOf(log) > 0)
    .slice(-6)
    .reverse()
)

onMounted(async () => {
  try {
    data.value = await api.adminOverview(props.userId)
  } catch (err: any) {
    error.value = err?.message || '加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="drawer-wrap">
    <div style="flex: 1" @click="emit('close')" />
    <aside class="drawer">
      <div class="row" style="margin-bottom: 4px">
        <div>
          <div class="card-title" style="font-size: 17px">{{ data?.user.displayName || name }}</div>
          <div class="hint">@{{ data?.user.username }}</div>
        </div>
        <div class="spacer" />
        <span class="tag tag-accent">只读</span>
        <button class="icon-btn" @click="emit('close')">✕</button>
      </div>

      <div v-if="loading" class="empty">加载中…</div>
      <div v-else-if="error" class="empty">{{ error }}</div>

      <div v-else-if="data" class="stack" style="margin-top: 14px">
        <div class="row" style="gap: 14px; align-items: center">
          <RingProgress :value="data.stats.todayCompletion" :size="64" />
          <div class="metrics" style="margin: 0; flex: 1; gap: 18px">
            <div class="metric">
              <div class="metric-value">{{ data.stats.streak }}</div>
              <div class="metric-label">连续打卡</div>
            </div>
            <div class="metric">
              <div class="metric-value">{{ data.stats.checkinDays }}</div>
              <div class="metric-label">累计打卡</div>
            </div>
            <div class="metric">
              <div class="metric-value">{{ formatDuration(data.stats.totalFocusSec) }}</div>
              <div class="metric-label">累计专注</div>
            </div>
          </div>
        </div>

        <div class="card card-pad">
          <div class="card-head">
            <div class="card-title">打卡热力图</div>
            <div class="spacer" />
            <el-radio-group v-model="metric" size="small" aria-label="热力图指标">
              <el-radio-button value="completion">完成率</el-radio-button>
              <el-radio-button value="focus">专注时长</el-radio-button>
            </el-radio-group>
          </div>
          <Heatmap :days="daysMap" :metric="metric" :today="todayStr()" />
        </div>

        <div class="card card-pad">
          <div class="card-head">
            <div class="card-title">最近复盘</div>
            <div class="spacer" />
            <span class="hint">共 {{ data.days.length }} 天记录</span>
          </div>
          <div v-if="!recent.length" class="empty">还没有打卡记录</div>
          <div v-else class="stack" style="gap: 12px">
            <div v-for="log in recent" :key="log.day" style="border-top: 1px solid var(--border); padding-top: 10px">
              <div class="row">
                <span style="font-size: 13px">{{ humanDate(log.day) }}</span>
                <span class="hint">{{ weekdayCN(log.day) }}</span>
                <div class="spacer" />
                <span class="tag">完成 {{ completionOf(log) }}%</span>
                <span class="tag">专注 {{ formatDuration(log.focusSec || 0) }}</span>
              </div>
              <div v-if="(log.review.best || []).filter(Boolean).length" class="hint" style="margin-top: 6px">
                有效：{{ (log.review.best || []).filter(Boolean).join('；') }}
              </div>
              <div v-if="(log.review.problems || []).length" class="hint" style="margin-top: 2px">
                问题：{{ (log.review.problems || []).join('、') }}{{ log.review.other ? `（${log.review.other}）` : '' }}
              </div>
              <div v-if="log.review.adjustment" class="hint" style="margin-top: 2px">调整：{{ log.review.adjustment }}</div>
            </div>
          </div>
        </div>

        <div class="card card-pad">
          <div class="card-head">
            <div class="card-title">当前计划表</div>
            <div class="spacer" />
            <span class="hint">{{ data.plan.length }} 项</span>
          </div>
          <div class="stack" style="gap: 4px">
            <div v-for="item in data.plan" :key="item.id" class="row" style="gap: 8px">
              <span class="task-time" style="width: 84px">{{ item.startTime }}</span>
              <span style="font-size: 12.5px">{{ item.title }}</span>
              <div class="spacer" />
              <span class="chip" :class="`subj-${item.subject}`">{{ item.subject }}</span>
            </div>
          </div>
          <div class="hint" style="margin-top: 10px">超级管理员只能查看，不能修改其他账号的数据</div>
        </div>
      </div>
    </aside>
  </div>
</template>
