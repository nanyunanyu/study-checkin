import type { DayLog, DayTask, PlanItem, Review } from './types'

export const SUBJECTS = ['英语', '语文', '数学', '专业课', '网课', '练习', '背诵', '复盘', '休息', '其他']

const SUBJECT_KEY: Record<string, string> = {
  英语: 'eng',
  语文: 'chn',
  数学: 'math',
  专业课: 'major',
  网课: 'video',
  练习: 'practice',
  背诵: 'recite',
  复盘: 'review',
  休息: 'rest',
  其他: 'other'
}

export function subjectKey(subject: string): string {
  return SUBJECT_KEY[subject] || 'other'
}

export function defaultFocusMinutes(startTime: string, endTime: string, now = new Date()): number {
  const timePattern = /^(?:[01]\d|2[0-3]):[0-5]\d$/
  if (!timePattern.test(startTime) || !timePattern.test(endTime)) return 30
  const [startHour, startMinute] = startTime.split(':').map(Number)
  const [endHour, endMinute] = endTime.split(':').map(Number)
  const start = startHour * 60 + startMinute
  const end = endHour * 60 + endMinute
  const current = now.getHours() * 60 + now.getMinutes()
  if (start < current || end <= start) return 30
  return end - start
}

export const PROBLEM_OPTIONS = ['走神', '网课吸收不足', '错题未消化', '背诵不牢', '拖延', '其他']

export function pad(value: number): string {
  return String(value).padStart(2, '0')
}

export function dateToStr(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function todayStr(): string {
  return dateToStr(new Date())
}

export function parseDate(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, (month || 1) - 1, day || 1)
}

export function addDays(value: string, delta: number): string {
  const date = parseDate(value)
  date.setDate(date.getDate() + delta)
  return dateToStr(date)
}

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

export function weekdayCN(value: string): string {
  return WEEKDAYS[parseDate(value).getDay()]
}

export function humanDate(value: string): string {
  const date = parseDate(value)
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

export function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.round(seconds))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  if (hours > 0) return minutes ? `${hours} 小时 ${minutes} 分` : `${hours} 小时`
  if (minutes > 0) return `${minutes} 分钟`
  return total > 0 ? `${total} 秒` : '0 分钟'
}

export function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const secs = total % 60
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(secs)}` : `${pad(minutes)}:${pad(secs)}`
}

export function emptyReview(): Review {
  return { best: ['', ''], problems: [], other: '', priorities: ['', '', ''], adjustment: '' }
}

export function normalizeReview(input: any): Review {
  const base = emptyReview()
  if (!input || typeof input !== 'object') return base
  const best = Array.isArray(input.best) ? input.best.slice(0, 2) : []
  const priorities = Array.isArray(input.priorities)
    ? input.priorities.map((priority: any) => (typeof priority === 'string' ? priority : ''))
    : []
  while (priorities.length < 3) priorities.push('')
  return {
    best: [best[0] || '', best[1] || ''],
    problems: Array.isArray(input.problems) ? input.problems.filter((p: any) => typeof p === 'string') : [],
    other: typeof input.other === 'string' ? input.other : '',
    priorities,
    adjustment: typeof input.adjustment === 'string' ? input.adjustment : ''
  }
}

export function tasksFromPlan(plan: PlanItem[]): DayTask[] {
  return plan
    .filter((item) => item.active)
    .map((item) => ({
      id: item.id,
      startTime: item.startTime,
      endTime: item.endTime,
      title: item.title,
      subject: item.subject,
      note: item.note,
      done: false,
      focusSec: 0
    }))
}

export function computeCompletion(tasks: DayTask[]): number {
  if (!tasks.length) return 0
  const done = tasks.filter((task) => task.done).length
  return Math.round((done / tasks.length) * 1000) / 10
}

export function completionOf(log: DayLog): number {
  if (!log) return 0
  if (typeof log.completion === 'number' && log.completion > 0) return log.completion
  return computeCompletion(log.tasks || [])
}

export function completeDay(log: DayLog): number {
  return computeCompletion(log.tasks || [])
}

export function streakOf(days: Record<string, DayLog>, today: string): number {
  let cursor = today
  if (!(days[cursor]?.checkedIn || completionOf(days[cursor]) > 0)) {
    cursor = addDays(today, -1)
  }
  let streak = 0
  while (true) {
    const log = days[cursor]
    if (!log || !(log.checkedIn || completionOf(log) > 0)) break
    streak += 1
    cursor = addDays(cursor, -1)
    if (streak > 2000) break
  }
  return streak
}

export function checkinDaysOf(days: Record<string, DayLog>): number {
  return Object.values(days).filter((log) => log.checkedIn || completionOf(log) > 0).length
}

export function totalFocusOf(days: Record<string, DayLog>): number {
  return Object.values(days).reduce((sum, log) => sum + (log.focusSec || 0), 0)
}

export function monthCompletionOf(days: Record<string, DayLog>, today: string): number {
  const month = today.slice(0, 7)
  const values: number[] = []
  for (const [day, log] of Object.entries(days)) {
    if (!day.startsWith(month)) continue
    if (!log.tasks?.length) continue
    values.push(completionOf(log))
  }
  if (!values.length) return 0
  return Math.round((values.reduce((a, b) => a + b, 0) / values.length) * 10) / 10
}

export function exportFileName(username: string): string {
  return `学习打卡备份-${username}-${todayStr()}.json`
}

export function downloadJson(data: unknown, filename: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function uuid(): string {
  if (crypto && 'randomUUID' in crypto) return crypto.randomUUID().replace(/-/g, '')
  return Math.random().toString(16).slice(2) + Date.now().toString(16)
}
