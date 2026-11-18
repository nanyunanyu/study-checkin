<script setup lang="ts">
import { computed } from 'vue'
import type { DayLog } from '../types'
import { completionOf, dateToStr, formatDuration, humanDate, parseDate } from '../utils'

const props = defineProps<{
  days: Record<string, DayLog>
  metric: 'completion' | 'focus'
  today: string
}>()
const emit = defineEmits<{ (event: 'select', day: string): void }>()

const WEEKS = 53

interface Cell {
  day: string
  level: number
  value: number
  future: boolean
  isToday: boolean
}

const cells = computed<Cell[]>(() => {
  const end = parseDate(props.today)
  const weekStart = new Date(end)
  weekStart.setDate(end.getDate() - end.getDay())
  const start = new Date(weekStart)
  start.setDate(weekStart.getDate() - (WEEKS - 1) * 7)

  const list: Cell[] = []
  for (let index = 0; index < WEEKS * 7; index += 1) {
    const cursor = new Date(start)
    cursor.setDate(start.getDate() + index)
    const day = dateToStr(cursor)
    const log = props.days[day]
    const future = day > props.today
    let value = 0
    if (log && !future) {
      value = props.metric === 'completion' ? completionOf(log) : log.focusSec || 0
    }
    let level = 0
    if (value > 0) {
      if (props.metric === 'completion') {
        level = value < 25 ? 1 : value < 50 ? 2 : value < 75 ? 3 : 4
      } else {
        level = value < 1800 ? 1 : value < 5400 ? 2 : value < 10800 ? 3 : 4
      }
    }
    list.push({ day, level, value, future, isToday: day === props.today })
  }
  return list
})

function tooltip(cell: Cell): string {
  if (cell.future) return `${humanDate(cell.day)} · 还没到`
  const log = props.days[cell.day]
  if (!log || (!cell.value && !log.focusSec)) return `${humanDate(cell.day)} · 未打卡`
  return `${humanDate(cell.day)} · 完成率 ${completionOf(log)}% · 专注 ${formatDuration(log.focusSec || 0)}`
}
</script>

<template>
  <div>
    <div class="heat-scroll">
      <div class="heat-grid">
        <div
          v-for="cell in cells"
          :key="cell.day"
          class="heat-cell"
          :class="{ today: cell.isToday }"
          :data-level="cell.level"
          :title="tooltip(cell)"
          @click="emit('select', cell.day)"
        />
      </div>
    </div>
    <div class="heat-legend">
      <span>{{ metric === 'completion' ? '少' : '短' }}</span>
      <span class="sw" style="background: var(--heat-0)" />
      <span class="sw" style="background: var(--heat-1)" />
      <span class="sw" style="background: var(--heat-2)" />
      <span class="sw" style="background: var(--heat-3)" />
      <span class="sw" style="background: var(--heat-4)" />
      <span>{{ metric === 'completion' ? '多' : '长' }}</span>
      <span style="margin-left: auto">
        {{ metric === 'completion' ? '按当天完成率着色' : '按当天专注时长着色' }}
      </span>
    </div>
  </div>
</template>
