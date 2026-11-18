<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { pad } from '../utils'

const props = defineProps<{ startTime: string; endTime: string; title: string; canRestore?: boolean; busy?: boolean; error?: string }>()
const emit = defineEmits<{
  confirm: [range: { startTime: string; endTime: string }]
  restore: []
  cancel: []
}>()

const format = /^(?:[01]\d|2[0-3]):[0-5]\d$/
const dialog = ref<HTMLDialogElement>()
const start = ref(props.startTime)
const end = ref(props.endTime)
const active = ref<'start' | 'end'>('start')
const hourWheel = ref<HTMLElement>()
const minuteWheel = ref<HTMLElement>()
const validation = ref('')
const rowHeight = 40
const wheels = [
  { label: '小时', steps: 24, el: hourWheel },
  { label: '分钟', steps: 60, el: minuteWheel }
]

function current() {
  return active.value === 'start' ? start : end
}

function parts() {
  const value = current().value
  return format.test(value) ? value.split(':').map(Number) : [0, 0]
}

function align() {
  const values = parts()
  wheels.forEach(({ el }, index) => {
    if (el.value) el.value.scrollTop = values[index] * rowHeight
  })
}

function setPart(index: number, value: number) {
  const next = parts()
  next[index] = Math.max(0, Math.min(wheels[index].steps - 1, value))
  current().value = `${pad(next[0])}:${pad(next[1])}`
  validation.value = ''
}

function onWheelKey(event: KeyboardEvent, index: number) {
  const value = parts()[index]
  const max = wheels[index].steps - 1
  const targets: Record<string, number> = { ArrowUp: value + 1, ArrowDown: value - 1, Home: 0, End: max }
  if (!(event.key in targets)) return
  event.preventDefault()
  choosePart(index, targets[event.key])
}

function choosePart(index: number, value: number) {
  setPart(index, value)
  const wheel = wheels[index].el.value
  if (wheel) wheel.scrollTop = parts()[index] * rowHeight
}

function readWheel(event: Event, index: number) {
  const value = Math.round((event.target as HTMLElement).scrollTop / rowHeight)
  if (value !== parts()[index]) setPart(index, value)
}

function submit() {
  if (props.busy) return
  const startTime = start.value.trim()
  const endTime = end.value.trim()
  if ([startTime, endTime].some((time) => time && !format.test(time))) {
    validation.value = '请输入 24 小时制时间，例如 08:30。'
    return
  }
  emit('confirm', { startTime, endTime })
}

function dismiss() {
  if (!props.busy) emit('cancel')
}

watch(active, align, { flush: 'post' })
onMounted(() => {
  dialog.value?.showModal()
  align()
})
</script>

<template>
  <Teleport to="body">
    <dialog ref="dialog" class="time-range-dialog" aria-labelledby="time-range-title" @cancel.prevent="dismiss" @click.self="dismiss">
      <form class="time-range-body" @submit.prevent="submit">
        <h2 id="time-range-title">{{ title }}</h2>
        <div class="time-range-desktop">
          <label>开始<input v-model="start" maxlength="5" placeholder="HH:mm" @input="validation = ''" /></label>
          <span aria-hidden="true">至</span>
          <label>结束<input v-model="end" maxlength="5" placeholder="HH:mm" @input="validation = ''" /></label>
        </div>
        <div class="time-range-mobile">
          <div class="time-range-targets">
            <button type="button" :aria-pressed="active === 'start'" @click="active = 'start'">开始 <strong>{{ start || '未设置' }}</strong></button>
            <button type="button" :aria-pressed="active === 'end'" @click="active = 'end'">结束 <strong>{{ end || '未设置' }}</strong></button>
          </div>
          <div class="time-wheel-grid" :class="{ 'time-wheel-empty': !current().value }">
            <div v-for="({ label, steps, el }, index) in wheels" :key="label" class="time-wheel-column">
              <span>{{ label }}</span>
              <div
                :ref="(node) => { el.value = node as HTMLElement }"
                class="time-wheel"
                tabindex="0"
                role="spinbutton"
                :aria-label="label"
                :aria-valuemin="0"
                :aria-valuemax="steps - 1"
                :aria-valuenow="parts()[index]"
                @scroll="readWheel($event, index)"
                @keydown="onWheelKey($event, index)"
              >
                <div v-for="n in steps" :key="n" class="time-wheel-number" aria-hidden="true" @click="choosePart(index, n - 1)">{{ pad(n - 1) }}</div>
              </div>
            </div>
          </div>
          <button type="button" class="time-clear" @click="current().value = ''; align()">清除{{ active === 'start' ? '开始' : '结束' }}时间</button>
        </div>
        <p v-if="validation || error" class="time-range-error" role="alert">{{ validation || error }}</p>
        <div class="time-range-actions">
          <el-button v-if="canRestore" text :disabled="busy" @click="emit('restore')">恢复计划时间</el-button>
          <span class="spacer" />
          <el-button :disabled="busy" @click="dismiss">取消</el-button>
          <el-button type="primary" native-type="submit" :loading="busy">{{ error ? '重试保存' : '确定' }}</el-button>
        </div>
      </form>
    </dialog>
  </Teleport>
</template>

<style scoped>
.time-range-dialog {
  width: min(420px, calc(100vw - 28px));
  max-height: calc(100dvh - 24px);
  padding: 0;
  color: var(--text);
  background: var(--surface-solid);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: var(--shadow);
}
.time-range-dialog::backdrop { background: rgb(10 20 30 / 44%); }
.time-range-body { padding: 18px; }
h2 { margin: 0 0 16px; font-size: 16px; }
.time-range-desktop { display: grid; grid-template-columns: 1fr auto 1fr; align-items: end; gap: 10px; }
.time-range-desktop label { display: grid; gap: 5px; color: var(--text-2); }
.time-range-desktop > span { padding-bottom: 8px; color: var(--text-3); }
.time-range-desktop input { width: 100%; min-width: 0; padding: 8px 10px; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--surface-solid); color: var(--text); font: inherit; font-variant-numeric: tabular-nums; }
.time-range-mobile { display: none; }
.time-range-actions { display: flex; align-items: center; gap: 6px; margin-top: 18px; }
.time-range-actions .el-button { margin: 0; }
.time-range-error { margin: 10px 0 0; color: var(--el-color-danger); font-size: 13px; }
@media (max-width: 820px), (pointer: coarse) {
  .time-range-dialog { inset: auto 0 0; margin: 0 auto; width: min(100%, 480px); max-width: 100%; border-radius: 16px 16px 0 0; }
  .time-range-body { padding: 16px 16px max(16px, env(safe-area-inset-bottom)); }
  .time-range-desktop { display: none; }
  .time-range-mobile { display: grid; gap: 8px; }
  .time-range-targets, .time-wheel-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .time-range-targets button { display: flex; justify-content: space-between; align-items: center; gap: 6px; min-height: 40px; padding: 0 9px; border: 1px solid var(--border); border-radius: 8px; color: var(--text-2); background: var(--surface-2); }
  .time-range-targets button[aria-pressed='true'] { background: var(--accent-soft); color: var(--accent-text); border-color: var(--accent); }
  .time-range-targets strong { font-variant-numeric: tabular-nums; }
  .time-wheel-column { position: relative; display: grid; text-align: center; color: var(--text-3); font-size: 12px; }
  .time-wheel-column::before { content: ''; position: absolute; inset: auto 8px 60px; height: 40px; border-radius: 8px; background: var(--accent-soft); pointer-events: none; }
  .time-wheel { position: relative; height: 160px; padding-block: 60px; overflow-y: auto; overscroll-behavior: contain; scroll-snap-type: y mandatory; scrollbar-width: none; mask-image: linear-gradient(transparent, black 37%, black 63%, transparent); }
  .time-wheel::-webkit-scrollbar { display: none; }
  .time-wheel-number { display: grid; place-items: center; height: 40px; scroll-snap-align: center; color: var(--text); font-size: 24px; font-variant-numeric: tabular-nums; cursor: pointer; }
  .time-wheel-empty .time-wheel-column::before { background: var(--surface-2); }
  .time-clear { justify-self: center; min-height: 32px; color: var(--text-2); font-size: 12px; }
  .time-range-actions { margin-top: 10px; }
}
</style>
