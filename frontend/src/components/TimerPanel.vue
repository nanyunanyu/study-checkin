<script setup lang="ts">
import { computed, ref } from 'vue'
import { useDataStore } from '../stores/data'
import { useTimerStore } from '../stores/timer'
import { useToastStore } from '../stores/toast'
import { formatClock, formatDuration, todayStr } from '../utils'
import Icon from './Icon.vue'

const timer = useTimerStore()
const data = useDataStore()
const toast = useToastStore()

const customMinutes = ref(30)

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
  toast.push(ok ? '已开启计时结束通知' : '未获得通知权限，仍会有提示音', ok ? 'ok' : 'err')
}

function close() {
  timer.panelOpen = false
}
</script>

<template>
  <div>
    <el-button
      v-if="!timer.panelOpen"
      class="timer-fab"
      :class="{ running: timer.state.running }"
      round
      @click="timer.panelOpen = true"
    >
      <span v-if="timer.state.running" class="timer-dot" />
      <Icon name="timer" :size="16" />
      <span>{{ formatClock(timer.displaySeconds) }}</span>
    </el-button>

    <el-card v-else class="timer-panel" shadow="always">
      <div class="row" style="margin-bottom: 6px">
        <el-tag size="small" effect="plain">{{ modeLabel }}</el-tag>
        <div class="spacer" />
        <el-button circle text aria-label="收起计时器" @click="close"><Icon name="close" :size="15" /></el-button>
      </div>

      <div class="timer-clock">{{ formatClock(timer.displaySeconds) }}</div>
      <div class="timer-sub">{{ subLabel }}</div>

      <el-button-group class="timer-modes">
        <el-button :type="timer.state.mode === 'pomo' ? 'primary' : 'default'" @click="handleMode('pomo')">番茄钟</el-button>
        <el-button :type="timer.state.mode === 'up' ? 'primary' : 'default'" @click="handleMode('up')">正计时</el-button>
        <el-button :type="timer.state.mode === 'down' ? 'primary' : 'default'" @click="handleMode('down')">倒计时</el-button>
      </el-button-group>

      <div v-if="timer.state.mode === 'down'" class="row" style="margin-bottom: 10px">
        <span class="hint">分钟数</span>
        <el-input-number
          v-model.number="customMinutes"
          min="1"
          max="600"
          :step="5"
          controls-position="right"
          @change="timer.setDuration($event || 30)"
        />
        <el-button size="small" type="primary" :disabled="timer.state.running" @click="startDown">应用并开始</el-button>
      </div>

      <div class="timer-task-select">
        <label>绑定任务（专注时长计入该任务）</label>
        <el-select :model-value="timer.state.taskId || ''" @change="bindTask">
          <el-option label="不绑定，仅计时" value="" />
          <el-option v-for="task in todayTasks" :key="task.id" :label="`${task.startTime} ${task.title}`" :value="task.id" />
        </el-select>
      </div>

      <div class="row" style="gap: 8px">
        <el-button type="primary" style="flex: 1" @click="timer.toggle()">
          <Icon :name="timer.state.running ? 'pause' : 'play'" :size="15" />
          {{ timer.state.running ? '暂停' : '开始' }}
        </el-button>
        <el-button @click="handleReset">结束本轮</el-button>
      </div>

      <div class="row" style="margin-top: 12px">
        <span class="hint">本轮已专注 {{ formatClock(timer.elapsed) }}</span>
        <div class="spacer" />
        <el-button
          v-if="typeof Notification !== 'undefined' && Notification.permission !== 'granted'"
          size="small"
          @click="askNotify"
        >
          开启结束通知
        </el-button>
      </div>
    </el-card>
  </div>
</template>
