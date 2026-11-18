<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useDataStore } from '../stores/data'
import { useTimerStore } from '../stores/timer'
import { useToastStore } from '../stores/toast'
import { useUiStore } from '../stores/ui'
import {
  addDays,
  completionOf,
  defaultFocusMinutes,
  formatDuration,
  humanDate,
  streakOf,
  subjectKey,
  todayStr,
  weekdayCN
} from '../utils'
import type { DayTask, Review } from '../types'
import RingProgress from '../components/RingProgress.vue'
import ReviewCard from '../components/ReviewCard.vue'
import Icon from '../components/Icon.vue'

const data = useDataStore()
const timer = useTimerStore()
const toast = useToastStore()
const ui = useUiStore()

const date = ref(todayStr())

watch(
  () => ui.focusDate,
  (value) => {
    if (!value) return
    date.value = value
    ui.focusDate = null
  },
  { immediate: true }
)

const log = computed(() => data.getDay(date.value))
const isToday = computed(() => date.value === todayStr())
const streak = computed(() => streakOf(data.days, todayStr()))
const doneCount = computed(() => log.value.tasks.filter((task) => task.done).length)
const total = computed(() => log.value.tasks.length)
const completion = computed(() => completionOf(log.value))
const checkedIn = computed(() => Boolean(log.value.checkedIn))
const focusText = computed(() => formatDuration(log.value.focusSec || 0))

function shift(delta: number) {
  date.value = addDays(date.value, delta)
}

function gotoToday() {
  date.value = todayStr()
}

function toggle(task: DayTask) {
  data.toggleTask(date.value, task.id)
}

function toggleCheckIn() {
  const next = !checkedIn.value
  if (next && doneCount.value === 0) {
    toast.push('先勾选至少一项任务，再打卡', 'err')
    return
  }
  data.setCheckedIn(date.value, next)
  toast.push(next ? '今日打卡完成' : '已取消打卡', next ? 'ok' : 'info')
}

function onReview(patch: Partial<Review>) {
  data.updateReview(date.value, patch)
}

function startFocus(task: DayTask) {
  timer.panelOpen = true
  if (timer.state.taskId === task.id && timer.state.running) return
  // Settle the previous task before rebinding so its focus time keeps the right owner.
  timer.setMode('pomo')
  timer.bindTask(task.id, task.title)
  const planned = data.plan.find((item) => item.id === task.id)
  timer.setDuration(planned?.focusMin ?? defaultFocusMinutes(task.startTime, task.endTime))
  timer.start()
  toast.push(`开始专注：${task.title}`, 'ok')
}
</script>

<template>
  <div class="stack">
    <div class="view-heading">
      <div>
        <span class="eyebrow">YOUR DAILY RHYTHM</span>
        <h1>今日学习</h1>
        <p>按自己的节奏，一点点完成计划。</p>
      </div>
    </div>
    <section class="card today-head">
      <div class="date-block">
        <div class="row" style="gap: 6px">
          <el-button circle text aria-label="前一天" @click="shift(-1)"><Icon name="left" :size="16" /></el-button>
          <div>
            <div class="date-big">{{ humanDate(date) }}</div>
            <div class="hint">{{ weekdayCN(date) }}<span v-if="isToday"> · 今天</span></div>
          </div>
          <el-button circle text aria-label="后一天" @click="shift(1)"><Icon name="right" :size="16" /></el-button>
        </div>
      </div>

      <div class="today-date-controls">
        <el-date-picker
          v-model="date"
          type="date"
          format="YYYY年MM月DD日"
          value-format="YYYY-MM-DD"
          :clearable="false"
          :editable="false"
          aria-label="选择日期"
        />
        <el-button v-if="!isToday" @click="gotoToday">回到今天</el-button>
      </div>

      <div class="metrics">
        <div class="metric-cluster">
          <RingProgress :value="completion" :size="66" />
          <div class="metric">
            <div class="metric-value">{{ doneCount }}/{{ total }}</div>
            <div class="metric-label">任务完成</div>
          </div>
        </div>
        <div class="metric metric-tile">
          <div class="metric-value">{{ streak }} 天</div>
          <div class="metric-label">连续打卡</div>
        </div>
        <div class="metric metric-tile">
          <div class="metric-value">{{ focusText }}</div>
          <div class="metric-label">当日专注</div>
        </div>
        <el-button class="checkin-action" :type="checkedIn ? 'success' : 'primary'" @click="toggleCheckIn">
          <Icon v-if="checkedIn" name="check" :size="15" />
          {{ checkedIn ? '已打卡' : '完成打卡' }}
        </el-button>
      </div>
    </section>

    <section class="card">
      <div class="card-head" style="padding: 18px 22px 10px; margin: 0">
        <div class="card-title">时间表</div>
        <span class="hint">{{ doneCount }} / {{ total }} 已完成</span>
        <div class="spacer" />
        <el-tag v-if="data.pending > 0" size="small" type="warning" effect="plain">保存中…</el-tag>
        <el-tag v-else-if="data.savedAt" size="small" type="success" effect="plain">已保存</el-tag>
      </div>

      <div class="task-list">
        <div
          v-for="task in log.tasks"
          :key="task.id"
          class="task-row"
          :class="{ done: task.done, 'active-task': timer.state.taskId === task.id }"
        >
          <el-checkbox class="task-checkbox" :model-value="task.done" :aria-label="`完成任务：${task.title}`" @change="toggle(task)" />

          <span class="task-time">
            {{ task.startTime }}<span v-if="task.endTime && task.endTime !== task.startTime">–{{ task.endTime }}</span>
          </span>

          <div class="task-main">
            <span class="task-title">{{ task.title }}</span>
            <span class="chip" :class="`subj-${subjectKey(task.subject)}`">{{ task.subject }}</span>
            <span v-if="task.focusSec > 0" class="task-focus">专注 {{ formatDuration(task.focusSec) }}</span>
            <span v-if="task.note" class="task-note">{{ task.note }}</span>
          </div>

          <el-button class="task-play" type="primary" plain circle aria-label="开始专注" title="开始专注" @click="startFocus(task)"><Icon name="play" :size="14" /></el-button>
        </div>

        <el-empty v-if="!log.tasks.length" description="计划表还是空的，去「计划」页添加第一个时间段" />
      </div>
    </section>

    <ReviewCard :review="log.review" @update="onReview" />
  </div>
</template>
