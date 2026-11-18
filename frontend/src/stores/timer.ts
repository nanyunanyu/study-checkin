import { defineStore } from 'pinia'
import { computed, reactive, ref } from 'vue'

export type TimerMode = 'pomo' | 'up' | 'down'
export type TimerPhase = 'focus' | 'break'

export interface TimerConfig {
  focusMin: number
  breakMin: number
  longBreakMin: number
  roundsPerLong: number
  autoBreak: boolean
}

interface TimerState {
  mode: TimerMode
  phase: TimerPhase
  running: boolean
  startedAt: number
  base: number
  durationSec: number
  taskId: string | null
  taskTitle: string
  round: number
}

const STATE_KEY = 'study.timer.state'
const CONFIG_KEY = 'study.timer.config'

function loadConfig(): TimerConfig {
  try {
    const raw = localStorage.getItem(CONFIG_KEY)
    if (raw) return { ...defaultConfig(), ...JSON.parse(raw) }
  } catch {
    /* ignore */
  }
  return defaultConfig()
}

function defaultConfig(): TimerConfig {
  return { focusMin: 25, breakMin: 5, longBreakMin: 15, roundsPerLong: 4, autoBreak: true }
}

function loadState(): TimerState {
  const fallback: TimerState = {
    mode: 'pomo',
    phase: 'focus',
    running: false,
    startedAt: 0,
    base: 0,
    durationSec: 25 * 60,
    taskId: null,
    taskTitle: '',
    round: 0
  }
  try {
    const raw = localStorage.getItem(STATE_KEY)
    if (!raw) return fallback
    const parsed = JSON.parse(raw)
    const wasRunning = Boolean(parsed.running)
    let base = wasRunning
      ? Number(parsed.base || 0) + Math.max(0, (Date.now() - Number(parsed.startedAt || Date.now())) / 1000)
      : Number(parsed.base) || 0

    const mode: TimerMode = parsed.mode === 'up' || parsed.mode === 'down' ? parsed.mode : 'pomo'
    const durationSec = Number(parsed.durationSec) || 0
    let running = wasRunning
    // 关掉页面很久之后再打开：倒计时/番茄钟不追认，直接放弃这一轮
    if (running && mode !== 'up' && durationSec > 0 && base >= durationSec) {
      running = false
      base = 0
    }

    return {
      ...fallback,
      ...parsed,
      mode,
      durationSec,
      running,
      base,
      startedAt: Date.now()
    }
  } catch {
    return fallback
  }
}

export const useTimerStore = defineStore('timer', () => {
  const config = reactive<TimerConfig>(loadConfig())
  const state = reactive<TimerState>(loadState())
  const tickNow = ref(Date.now())
  const finished = ref(false)
  const panelOpen = ref(false)

  const listeners: Array<(seconds: number, taskId: string | null, phase: TimerPhase) => void> = []
  function onFinish(fn: (seconds: number, taskId: string | null, phase: TimerPhase) => void) {
    listeners.push(fn)
  }

  const elapsed = computed(() => {
    const running = state.running ? Math.max(0, (tickNow.value - state.startedAt) / 1000) : 0
    return state.base + running
  })

  const remaining = computed(() => Math.max(0, state.durationSec - elapsed.value))

  const displaySeconds = computed(() => (state.mode === 'up' ? elapsed.value : remaining.value))

  const progress = computed(() => {
    if (state.mode === 'up') return Math.min(1, (elapsed.value % 3600) / 3600)
    if (!state.durationSec) return 0
    return Math.min(1, elapsed.value / state.durationSec)
  })

  const isFocus = computed(() => state.phase === 'focus')

  function persist() {
    try {
      localStorage.setItem(
        STATE_KEY,
        JSON.stringify({ ...state, base: elapsed.value, running: state.running, startedAt: Date.now() })
      )
    } catch {
      /* ignore */
    }
  }

  function persistConfig() {
    localStorage.setItem(CONFIG_KEY, JSON.stringify(config))
  }

  function beep() {
    try {
      const Ctx = window.AudioContext || (window as any).webkitAudioContext
      if (!Ctx) return
      const ctx = new Ctx()
      const gain = ctx.createGain()
      gain.gain.value = 0.0001
      gain.connect(ctx.destination)
      const notes = [880, 1174, 1396]
      notes.forEach((freq, index) => {
        const osc = ctx.createOscillator()
        osc.type = 'sine'
        osc.frequency.value = freq
        osc.connect(gain)
        const start = ctx.currentTime + index * 0.18
        gain.gain.setValueAtTime(0.0001, start)
        gain.gain.exponentialRampToValueAtTime(0.25, start + 0.02)
        gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.16)
        osc.start(start)
        osc.stop(start + 0.18)
      })
      setTimeout(() => ctx.close(), 1200)
    } catch {
      /* ignore */
    }
  }

  function notify(title: string, body: string) {
    beep()
    if ('Notification' in window && Notification.permission === 'granted') {
      try {
        new Notification(title, { body })
      } catch {
        /* ignore */
      }
    }
  }

  async function requestNotifyPermission() {
    if (!('Notification' in window)) return false
    if (Notification.permission === 'granted') return true
    if (Notification.permission === 'denied') return false
    const result = await Notification.requestPermission()
    return result === 'granted'
  }

  function start() {
    if (state.running) return
    finished.value = false
    state.startedAt = Date.now()
    state.base = Number(state.base) || 0
    if (state.mode !== 'up' && state.durationSec <= 0) {
      state.durationSec = config.focusMin * 60
    }
    state.running = true
    tickNow.value = Date.now()
    persist()
  }

  function pause() {
    if (!state.running) return
    state.base = elapsed.value
    state.running = false
    persist()
  }

  function toggle() {
    if (state.running) pause()
    else start()
  }

  /**
   * 结束当前这一轮并结算专注时长。
   * 正计时不会自然结束，番茄钟也可能被用户中途停掉，
   * 这些情况下已经专注的时间必须记到当天，否则用户的专注时长会凭空消失。
   * 返回结算的秒数（不足 5 秒视为误触，不记录）。
   */
  function settle(): number {
    const seconds = state.phase === 'focus' ? Math.round(elapsed.value) : 0
    state.running = false
    state.base = 0
    if (seconds >= 5) {
      listeners.forEach((fn) => fn(seconds, state.taskId, 'focus'))
    }
    persist()
    return seconds >= 5 ? seconds : 0
  }

  function reset(keepTask = true) {
    const recorded = settle()
    state.phase = 'focus'
    finished.value = false
    if (state.mode === 'pomo') state.durationSec = config.focusMin * 60
    if (!keepTask) {
      state.taskId = null
      state.taskTitle = ''
    }
    persist()
    return recorded
  }

  function setMode(mode: TimerMode, minutes?: number) {
    settle()
    state.mode = mode
    state.phase = 'focus'
    finished.value = false
    if (mode === 'pomo') state.durationSec = config.focusMin * 60
    else if (mode === 'down') state.durationSec = Math.max(1, minutes || 30) * 60
    else state.durationSec = 0
    persist()
  }

  function setDuration(minutes: number) {
    const safe = Math.min(600, Math.max(1, Math.round(minutes)))
    state.durationSec = safe * 60
    if (!state.running) state.base = 0
    persist()
  }

  function bindTask(taskId: string | null, taskTitle = '') {
    state.taskId = taskId
    state.taskTitle = taskTitle
    persist()
  }

  function finishPhase() {
    const seconds = Math.round(elapsed.value)
    const phase = state.phase
    const taskId = state.taskId
    state.running = false
    state.base = 0
    finished.value = true

    if (phase === 'focus') {
      listeners.forEach((fn) => fn(seconds, taskId, 'focus'))
      if (state.mode === 'pomo') {
        state.round += 1
        if (config.autoBreak) {
          state.phase = 'break'
          const isLong = state.round % Math.max(1, config.roundsPerLong) === 0
          state.durationSec = (isLong ? config.longBreakMin : config.breakMin) * 60
          start()
          notify('专注结束，休息一下', `休息 ${isLong ? config.longBreakMin : config.breakMin} 分钟`)
        } else {
          state.phase = 'break'
          state.durationSec = config.breakMin * 60
          notify('专注结束', '点开始进入休息')
        }
      } else {
        notify('计时完成', `本次专注 ${Math.round(seconds / 60)} 分钟`)
      }
    } else {
      state.phase = 'focus'
      state.durationSec = config.focusMin * 60
      notify('休息结束', '准备开始下一轮专注')
    }
    persist()
  }

  function tick() {
    if (!state.running) return
    tickNow.value = Date.now()
    if (state.mode !== 'up' && elapsed.value >= state.durationSec - 0.5) {
      finishPhase()
    }
  }

  function saveConfig() {
    config.focusMin = Math.min(180, Math.max(5, Math.round(config.focusMin) || 25))
    config.breakMin = Math.min(60, Math.max(1, Math.round(config.breakMin) || 5))
    config.longBreakMin = Math.min(90, Math.max(5, Math.round(config.longBreakMin) || 15))
    config.roundsPerLong = Math.min(8, Math.max(2, Math.round(config.roundsPerLong) || 4))
    persistConfig()
  }

  return {
    state,
    config,
    tickNow,
    elapsed,
    remaining,
    displaySeconds,
    progress,
    isFocus,
    finished,
    panelOpen,
    onFinish,
    start,
    pause,
    toggle,
    settle,
    reset,
    setMode,
    setDuration,
    bindTask,
    tick,
    saveConfig,
    requestNotifyPermission
  }
})
