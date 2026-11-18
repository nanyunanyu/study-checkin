import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api'
import type { DayLog, PlanItem, User } from '../types'
import { completeDay, emptyReview, normalizeReview, tasksFromPlan, todayStr } from '../utils'

export const useDataStore = defineStore('data', () => {
  const plan = ref<PlanItem[]>([])
  const days = ref<Record<string, DayLog>>({})
  const loaded = ref(false)
  const loading = ref(false)
  const pending = ref(0)
  const savedAt = ref<number | null>(null)
  const error = ref('')

  const timers: Record<string, number> = {}

  function indexDays(list: DayLog[]) {
    const map: Record<string, DayLog> = {}
    for (const log of list) {
      map[log.day] = {
        ...log,
        review: normalizeReview(log.review),
        tasks: Array.isArray(log.tasks) ? log.tasks : []
      }
    }
    days.value = map
  }

  let inflight: Promise<User | null> | null = null

  async function load() {
    // 登录瞬间可能被多处同时触发（挂载 + 登录状态监听），复用同一次请求，
    // 免得两次响应互相覆盖、或和切账号时的 reset 交错。
    if (inflight) return inflight
    loading.value = true
    error.value = ''
    inflight = (async () => {
      try {
        const state = await api.state()
        plan.value = state.plan
        indexDays(state.days)
        if (reconcileToday()) {
          void saveDay(todayStr()).catch(() => undefined)
        }
        loaded.value = true
        return state.user
      } catch (err: any) {
        error.value = err?.message || '加载失败'
        throw err
      } finally {
        loading.value = false
        inflight = null
      }
    })()
    return inflight
  }

  function emptyDay(day: string): DayLog {
    return {
      day,
      tasks: tasksFromPlan(plan.value),
      review: emptyReview(),
      focusSec: 0,
      completion: 0,
      checkedIn: false
    }
  }

  function getDay(day: string, create = true): DayLog {
    const existing = days.value[day]
    if (existing) return existing
    // 还没加载完（或刚切换账号）时不要凭空造一条当天记录：
    // 那时 plan 可能还是上一个账号的，会在本账号里写出一份错误的任务快照。
    if (!create || !loaded.value) return emptyDay(day)
    const fresh = emptyDay(day)
    days.value = { ...days.value, [day]: fresh }
    return fresh
  }

  /** 切换账号 / 退出登录时清空，避免上一个账号的计划和数据被带到下一个账号 */
  function reset() {
    for (const key of Object.keys(timers)) {
      window.clearTimeout(timers[key])
      delete timers[key]
    }
    plan.value = []
    days.value = {}
    loaded.value = false
    loading.value = false
    pending.value = 0
    savedAt.value = null
    error.value = ''
    inflight = null
  }

  async function saveDay(day: string) {
    const log = days.value[day]
    if (!log) return
    pending.value += 1
    try {
      const saved = await api.saveDay(day, log)
      const current = days.value[day]
      days.value = {
        ...days.value,
        [day]: {
          ...current,
          ...saved,
          review: normalizeReview(saved.review)
        }
      }
      savedAt.value = Date.now()
    } catch (err: any) {
      error.value = err?.message || '保存失败'
      throw err
    } finally {
      pending.value -= 1
    }
  }

  function touch(day: string, immediate = false) {
    if (timers[day]) window.clearTimeout(timers[day])
    if (immediate) {
      void saveDay(day).catch(() => undefined)
      return
    }
    timers[day] = window.setTimeout(() => {
      delete timers[day]
      void saveDay(day).catch(() => undefined)
    }, 800)
  }

  function recalc(day: string) {
    const log = days.value[day]
    if (!log) return
    // 只重算完成率；打卡由用户点「完成打卡」单独控制，不能因为勾了任务就自动算作已打卡
    log.completion = completeDay(log)
  }

  /**
   * 把「今天」的任务表对齐到当前计划：计划里新增的补上，删掉的移除，
   * 已勾选 / 已专注的状态按任务 id 保留。历史日期是快照，一律不动。
   * 这样才真正兑现「保存后从今天起生效」，也避免当天记录变成空表后无法恢复。
   */
  function reconcileToday(): boolean {
    if (!plan.value.length) return false
    const log = days.value[todayStr()]
    if (!log) return false

    const previous = new Map(log.tasks.map((task) => [task.id, task]))
    const next = plan.value
      .filter((item) => item.active !== false)
      .map((item) => {
        const old = previous.get(item.id)
        return {
          id: item.id,
          startTime: item.startTime,
          endTime: item.endTime,
          title: item.title,
          subject: item.subject,
          note: old?.note ?? item.note ?? '',
          done: old?.done ?? false,
          focusSec: old?.focusSec ?? 0
        }
      })
    if (!next.length) return false

    const unchanged =
      next.length === log.tasks.length &&
      next.every((task, index) => {
        const old = log.tasks[index]
        return (
          old &&
          old.id === task.id &&
          old.title === task.title &&
          old.startTime === task.startTime &&
          old.endTime === task.endTime &&
          old.subject === task.subject &&
          old.done === task.done
        )
      })
    if (unchanged) return false

    log.tasks = next
    log.completion = completeDay(log)
    return true
  }

  function toggleTask(day: string, taskId: string) {
    const log = getDay(day)
    const task = log.tasks.find((item) => item.id === taskId)
    if (!task) return
    task.done = !task.done
    recalc(day)
    touch(day)
  }

  function addFocus(day: string, taskId: string | null, seconds: number) {
    if (seconds <= 0) return
    const log = getDay(day)
    log.focusSec = (log.focusSec || 0) + seconds
    if (taskId) {
      const task = log.tasks.find((item) => item.id === taskId)
      if (task) task.focusSec = (task.focusSec || 0) + seconds
    }
    recalc(day)
    touch(day)
  }

  function setCheckedIn(day: string, value: boolean) {
    const log = getDay(day)
    log.checkedIn = value
    touch(day, true)
  }

  function updateReview(day: string, patch: Partial<DayLog['review']>) {
    const log = getDay(day)
    log.review = { ...log.review, ...patch }
    touch(day)
  }

  async function savePlan(items: PlanItem[]) {
    const result = await api.savePlan(items)
    plan.value = result.plan
    if (reconcileToday()) {
      await saveDay(todayStr()).catch(() => undefined)
    }
    return result.plan
  }

  function dropDayIfEmpty(day: string) {
    const log = days.value[day]
    if (!log) return
    // 只有「一条任务都没有」的空壳记录才丢弃，避免把刚对齐好的任务表一起删掉
    if (log.tasks.length > 0 || log.checkedIn || log.focusSec) return
    const next = { ...days.value }
    delete next[day]
    days.value = next
  }

  function focusToday(seconds: number, taskId: string | null) {
    addFocus(todayStr(), taskId, seconds)
  }

  return {
    plan,
    days,
    loaded,
    loading,
    pending,
    savedAt,
    error,
    load,
    getDay,
    reset,
    saveDay,
    touch,
    toggleTask,
    addFocus,
    setCheckedIn,
    updateReview,
    savePlan,
    recalc,
    reconcileToday,
    dropDayIfEmpty,
    focusToday
  }
})
