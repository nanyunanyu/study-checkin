<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useDataStore } from '../stores/data'
import { useTimerStore } from '../stores/timer'
import { useToastStore } from '../stores/toast'
import { formatClock, formatDuration, todayStr } from '../utils'
import Icon from './Icon.vue'

const timer = useTimerStore()
const data = useDataStore()
const toast = useToastStore()

const customMinutes = ref(30)
const widget = ref<HTMLElement>()
const modes = [{ id: 'pomo', label: '番茄钟' }, { id: 'up', label: '正计时' }, { id: 'down', label: '倒计时' }] as const
const canEnableNotifications = ref(typeof Notification !== 'undefined' && Notification.permission === 'default')

const todayTasks = computed(() => data.getDay(todayStr()).tasks)
const modeLabel = computed(() => {
  if (timer.state.mode === 'pomo') return timer.state.phase === 'focus' ? '番茄专注' : '番茄休息'
  return timer.state.mode === 'up' ? '正计时' : '倒计时'
})
const subLabel = computed(() => {
  if (timer.state.mode === 'pomo') {
    const minutes = timer.state.phase === 'focus' ? Math.round(timer.state.durationSec / 60) : timer.config.focusMin
    return `第 ${timer.state.round + 1} 轮 · 专注 ${minutes} 分 / 休息 ${timer.config.breakMin} 分`
  }
  if (timer.state.mode === 'down') return `共 ${Math.round(timer.state.durationSec / 60)} 分钟`
  return '自由计时，随时结束'
})

function bindTask(value: string) {
  const task = todayTasks.value.find((item) => item.id === value)
  timer.bindTask(task ? task.id : null, task ? task.title : '')
}

function startDown() {
  timer.setMode('down', customMinutes.value)
  timer.start()
}

function reportSettled(seconds: number) {
  if (seconds <= 0) {
    toast.push('本轮不足 5 秒，未计入专注时长', 'info')
    return
  }
  toast.push(`本次专注 ${formatDuration(seconds)} 已计入今日`, 'ok')
}

function handleReset() {
  reportSettled(timer.reset())
}

function handleMode(mode: 'pomo' | 'up' | 'down') {
  if (timer.state.mode === mode) return
  const seconds = timer.settle()
  timer.setMode(mode)
  if (seconds > 0) reportSettled(seconds)
}

async function askNotify() {
  const ok = await timer.requestNotifyPermission()
  canEnableNotifications.value = typeof Notification !== 'undefined' && Notification.permission === 'default'
  toast.push(ok ? '已开启计时结束通知' : '未获得通知权限，仍会有提示音', ok ? 'ok' : 'err')
}

function close(restoreFocus = false) {
  timer.panelOpen = false
  if (restoreFocus) void nextTick(() => widget.value?.querySelector('button')?.focus())
}

function open() {
  timer.panelOpen = true
  void nextTick(() => widget.value?.querySelector<HTMLButtonElement>('.timer-close')?.focus())
}

function outside(event: MouseEvent) {
  if (timer.panelOpen && widget.value && !event.composedPath().includes(widget.value)) close()
}

function escape(event: KeyboardEvent) {
  if (event.key === 'Escape' && !event.defaultPrevented && timer.panelOpen && !document.querySelector('dialog[open], .el-overlay-dialog')) {
    close(widget.value?.contains(document.activeElement))
  }
}

onMounted(() => {
  document.addEventListener('click', outside, true)
  document.addEventListener('keydown', escape)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', outside, true)
  document.removeEventListener('keydown', escape)
})
</script>

<template>
  <div ref="widget">
    <el-button
      v-if="!timer.panelOpen"
      class="timer-fab"
      :class="{ running: timer.state.running }"
      round
      aria-label="展开计时器"
      aria-expanded="false"
      @click="open"
    >
      <span v-if="timer.state.running" class="timer-dot" />
      <Icon name="timer" :size="16" />
      <span>{{ formatClock(timer.displaySeconds) }}</span>
    </el-button>

    <section v-else class="timer-panel timer-sheet" aria-label="专注计时器">
      <div class="row timer-header">
        <strong>专注计时</strong>
        <div class="spacer" />
        <el-button class="timer-close" circle text aria-label="收起计时器" @click="close(true)"><Icon name="close" :size="15" /></el-button>
      </div>

      <div class="timer-segments" role="group" aria-label="计时模式">
        <button v-for="mode in modes" :key="mode.id" type="button" :aria-pressed="timer.state.mode === mode.id" @click="handleMode(mode.id)">{{ mode.label }}</button>
      </div>

      <div class="timer-readout">
        <div class="timer-status">{{ modeLabel }} · {{ timer.state.running ? '计时中' : timer.elapsed > 0 ? '已暂停' : '待开始' }}</div>
        <div class="timer-clock">{{ formatClock(timer.displaySeconds) }}</div>
        <div class="timer-sub">{{ subLabel }}</div>
      </div>

      <div v-if="timer.state.mode === 'down'" class="timer-duration">
        <el-input-number
          v-model.number="customMinutes"
          aria-label="倒计时分钟数"
          :min="1"
          :max="600"
          :step="5"
          :disabled="timer.state.running"
          controls-position="right"
          @change="timer.setDuration($event || 30)"
        />
        <el-button size="small" type="primary" :disabled="timer.state.running" @click="startDown">应用并开始</el-button>
      </div>

      <label class="timer-task-field">绑定任务
        <select :value="timer.state.taskId || ''" @change="bindTask(($event.target as HTMLSelectElement).value)">
          <option value="">不绑定，仅计时</option>
          <option v-for="task in todayTasks" :key="task.id" :value="task.id">{{ task.startTime }} {{ task.title }}</option>
        </select>
      </label>

      <div class="row timer-actions">
        <el-button type="primary" style="flex: 1" @click="timer.toggle()">
          <Icon :name="timer.state.running ? 'pause' : 'play'" :size="15" />
          {{ timer.state.running ? '暂停' : '开始' }}
        </el-button>
        <el-button @click="handleReset">结束本轮</el-button>
      </div>

      <div class="row timer-footer">
        <span class="hint">本轮已专注 {{ formatClock(timer.elapsed) }}</span>
        <div class="spacer" />
        <el-button
          v-if="canEnableNotifications"
          size="small"
          text
          @click="askNotify"
        >
          开启结束通知
        </el-button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.timer-sheet { display: grid; gap: 9px; width: min(335px, calc(100vw - 24px)); max-height: calc(100dvh - 44px); overflow-y: auto; overscroll-behavior: contain; padding: 12px 14px; border-radius: 12px; }
.timer-header strong { font-size: 14px; }
.timer-header .timer-close { width: 30px; height: 30px; padding: 0; }
.timer-segments { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 2px; padding: 3px; border: 1px solid var(--border); border-radius: 7px; background: var(--surface-2); }
.timer-segments button { min-height: 29px; border-radius: 5px; color: var(--text-2); font-size: 12px; }
.timer-segments button[aria-pressed='true'] { color: var(--accent-text); background: var(--accent-soft); font-weight: 650; }
.timer-readout { padding: 8px 0; border-bottom: 1px solid var(--border); text-align: center; }
.timer-status { color: var(--accent-text); font-size: 12px; }
.timer-readout .timer-clock { margin: 1px 0; font-size: 42px; line-height: 1.1; letter-spacing: 0; }
.timer-readout .timer-sub { margin: 0; }
.timer-duration { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 7px; }
.timer-duration :deep(.el-input-number) { width: 100%; }
.timer-task-field { display: grid; gap: 4px; min-width: 0; color: var(--text-2); font-size: 12px; }
.timer-task-field select { min-width: 0; width: 100%; height: 34px; padding: 0 6px; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--surface-solid); color: var(--text); font: inherit; }
.timer-actions, .timer-footer { gap: 6px; }
.timer-actions .el-button, .timer-footer .el-button { margin: 0; }
@media (max-width: 820px) {
  .timer-sheet, .timer-fab { bottom: max(78px, calc(env(safe-area-inset-bottom) + 68px)); }
  .timer-sheet { max-height: calc(100dvh - max(90px, env(safe-area-inset-bottom) + 80px)); }
}
</style>
