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
import TimeRangePicker from '../components/TimeRangePicker.vue'
import Icon from '../components/Icon.vue'

const data = useDataStore()
const timer = useTimerStore()
const toast = useToastStore()
const ui = useUiStore()

const date = ref(todayStr())
const editingTask = ref<DayTask | null>(null)
const savingTime = ref(false)
const timeError = ref('')
const retryRestore = ref(false)

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

watch(date, () => { editingTask.value = null })

function editTime(task: DayTask) {
  if (!isToday.value) return
  timeError.value = ''
  retryRestore.value = false
  editingTask.value = task
}

async function saveTime(range: Pick<DayTask, 'startTime' | 'endTime'> | null) {
  if (!editingTask.value || !isToday.value || savingTime.value) return
  if (retryRestore.value) range = null
  retryRestore.value = range === null
  savingTime.value = true
  timeError.value = ''
  try {
    await data.setTodayTaskTime(editingTask.value.id, range)
    editingTask.value = null
    toast.push(range ? '已保存今日时间' : '已恢复计划时间', 'ok')
  } catch (err: any) {
    timeError.value = err?.message || '保存失败，请重试'
  } finally {
    savingTime.value = false
  }
}

function timeLabel(task: DayTask) {
  if (task.startTime && task.endTime && task.startTime !== task.endTime) return `${task.startTime}–${task.endTime}`
  return task.startTime || task.endTime || '未设时间'
}

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
  <div class="stack today-page">
    <section class="card today-overview" aria-label="学习概览">
      <div class="today-date-line">
        <div class="today-date-copy">
          <h1>{{ humanDate(date) }}</h1>
          <span class="hint">{{ weekdayCN(date) }}<span v-if="isToday"> · 今天</span></span>
        </div>
        <div class="today-date-tools">
          <el-button circle text aria-label="前一天" @click="shift(-1)"><Icon name="left" :size="16" /></el-button>
          <el-button circle text aria-label="后一天" @click="shift(1)"><Icon name="right" :size="16" /></el-button>
          <el-date-picker
            v-model="date"
            type="date"
            format="MM/DD"
            value-format="YYYY-MM-DD"
            :clearable="false"
            :editable="false"
            size="small"
            aria-label="选择日期"
          />
        </div>
        <el-button v-if="!isToday" size="small" text @click="gotoToday">回到今天</el-button>
      </div>

      <div class="today-progress-line">
        <div class="today-progress">
          <div class="today-completion">
            <RingProgress :value="completion" :size="29" />
            <div><strong>{{ doneCount }}/{{ total }}</strong><small>任务完成</small></div>
          </div>
          <div><strong>{{ streak }} 天</strong><small>连续打卡</small></div>
          <div><strong>{{ focusText }}</strong><small>当日专注</small></div>
        </div>
        <el-button class="today-checkin" size="small" :type="checkedIn ? 'success' : 'primary'" @click="toggleCheckIn">
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

          <button v-if="isToday" type="button" class="task-time task-time-button" :class="{ 'time-overridden': task.timeOverridden }" :aria-label="`编辑时间：${task.title}`" @click="editTime(task)">{{ timeLabel(task) }}</button>
          <span v-else class="task-time">{{ timeLabel(task) }}</span>

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
    <TimeRangePicker
      v-if="editingTask"
      title="编辑今日时间"
      :start-time="editingTask.startTime"
      :end-time="editingTask.endTime"
      :can-restore="editingTask.timeOverridden"
      :busy="savingTime"
      :error="timeError"
      @confirm="saveTime"
      @restore="saveTime(null)"
      @cancel="editingTask = null"
    />
  </div>
</template>

<style scoped>
.today-page { gap: 12px; }
.today-overview { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px 18px; padding: 12px 16px; }
.today-date-line, .today-date-copy, .today-date-tools, .today-progress-line, .today-progress, .today-completion { display: flex; align-items: center; }
.today-date-line { gap: 7px; flex-wrap: wrap; }
.today-date-copy { gap: 7px; }
.today-date-copy h1 { margin: 0; color: var(--text); font-size: 18px; line-height: 1.2; }
.today-date-tools { gap: 2px; }
.today-date-tools :deep(.el-button) { width: 30px; height: 34px; margin: 0; padding: 0; }
.today-date-tools :deep(.el-date-editor) { width: 76px; }
.today-date-tools :deep(.el-input__wrapper) { min-height: 32px; padding: 0 6px; }
.today-progress-line { gap: 10px; }
.today-progress { gap: 14px; min-width: 0; }
.today-progress strong, .today-progress small { display: block; line-height: 1.35; }
.today-progress strong { font-size: 13px; font-variant-numeric: tabular-nums; }
.today-progress small { color: var(--text-3); font-size: 11px; }
.today-completion { gap: 6px; }
.today-checkin { height: 34px; flex: none; padding-inline: 9px; }
.task-time-button { min-height: 32px; padding: 0 5px; border: 1px solid var(--border); border-radius: 6px; color: var(--text-2); background: var(--surface-2); text-align: center; }
.task-time-button:hover, .task-time-button.time-overridden { color: var(--accent-text); border-color: var(--accent); background: var(--accent-soft); }
@media (max-width: 560px) {
  .today-overview { padding: 10px 11px; gap: 8px; }
  .today-date-copy h1 { font-size: 16px; }
  .today-progress-line { width: 100%; justify-content: space-between; gap: 6px; border-top: 1px solid var(--border); padding-top: 8px; }
  .today-progress { gap: 9px; }
  .today-completion :deep(.ring) { display: none; }
  .today-page .task-play.el-button.is-circle { width: 34px; height: 34px; }
  .today-page .task-time { width: fit-content; }
}
</style>
