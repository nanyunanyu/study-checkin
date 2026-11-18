<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { api } from '../api'
import type { PlanItem, PlanVersion } from '../types'
import { defaultFocusMinutes } from '../utils'
import Icon from './Icon.vue'

const props = defineProps<{ dirty: boolean }>()
const emit = defineEmits<{ close: []; select: [items: PlanItem[]] }>()
const versions = ref<PlanVersion[]>([])
const cursor = ref<number | null>(null)
const listBusy = ref(false)
const listError = ref('')
const selected = ref<PlanVersion | null>(null)
const preview = ref<PlanItem[] | null>(null)
const previewError = ref('')
const previewTitle = ref<HTMLElement>()
const listRoot = ref<HTMLElement>()

const timeFormat = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23'
})

function formatVersion(version: PlanVersion) {
  return timeFormat.format(new Date(version.replacedAt))
}

async function loadList() {
  listBusy.value = true
  listError.value = ''
  try {
    const page = await api.planHistory(cursor.value ?? undefined)
    versions.value.push(...page.versions)
    cursor.value = page.nextBefore
  } catch (err) {
    listError.value = err instanceof Error ? err.message : '历史计划加载失败'
  } finally {
    listBusy.value = false
  }
}

async function openPreview(version: PlanVersion) {
  selected.value = version
  preview.value = null
  previewError.value = ''
  await nextTick()
  previewTitle.value?.focus()
  try {
    const result = await api.planVersion(version.id)
    if (selected.value === version) preview.value = result.items
  } catch (err) {
    if (selected.value === version) previewError.value = err instanceof Error ? err.message : '预览加载失败'
  }
}

async function backToList() {
  const id = selected.value?.id
  selected.value = null
  await nextTick()
  listRoot.value?.querySelector<HTMLButtonElement>(`[data-version-id="${id}"]`)?.focus()
}

async function selectVersion() {
  const items = preview.value
  if (!items) return
  if (props.dirty) {
    try {
      await ElMessageBox.confirm('当前有未保存的修改。载入这个版本会替换当前草稿。', '替换当前草稿？', {
        confirmButtonText: '替换草稿', cancelButtonText: '取消', type: 'warning'
      })
    } catch {
      return
    }
  }
  emit('select', items)
}

onMounted(loadList)
</script>

<template>
  <el-dialog :model-value="true" title="历史计划" width="580px" class="plan-dialog" :close-on-click-modal="false" @close="emit('close')">
    <template v-if="selected">
      <div class="version-head">
        <button type="button" class="version-back" aria-label="返回历史列表" title="返回历史列表" @click="backToList"><Icon name="left" :size="16" /></button>
        <div>
          <h3 ref="previewTitle" tabindex="-1">{{ formatVersion(selected) }} 的存档</h3>
          <span class="hint">{{ selected.itemCount }} 个时间段</span>
        </div>
      </div>

      <div v-if="previewError" class="history-state" role="alert">
        {{ previewError }} <el-button text type="primary" @click="openPreview(selected)">重试</el-button>
      </div>
      <div v-else-if="!preview" class="empty" role="status">正在加载预览…</div>
      <div v-else-if="!preview.length" class="empty">这个版本没有时间段</div>
      <ol v-else class="history-scroll version-tasks">
        <li v-for="item in preview" :key="item.id" class="version-task">
          <span class="version-time">{{ item.startTime || '—' }} 至 {{ item.endTime || '—' }}</span>
          <div class="version-task-copy">
            <strong>{{ item.title }}</strong>
            <span class="hint">{{ item.subject }} · {{ item.focusMin ?? defaultFocusMinutes(item.startTime, item.endTime) }} 分钟<span v-if="!item.active"> · 未启用</span></span>
            <span v-if="item.note" class="hint">{{ item.note }}</span>
          </div>
        </li>
      </ol>
    </template>

    <div v-else ref="listRoot">
      <div v-if="!listBusy && !listError && !versions.length" class="empty">暂无历史计划</div>
      <div class="history-scroll">
        <ol v-if="versions.length" class="version-list" aria-label="计划存档">
          <li v-for="version in versions" :key="version.id">
            <button type="button" class="version-row" :data-version-id="version.id" @click="openPreview(version)">
              <span><strong>{{ formatVersion(version) }} 的存档</strong><small class="hint">{{ version.itemCount }} 个时间段</small></span>
              <span class="version-open">预览 <Icon name="right" :size="13" /></span>
            </button>
          </li>
        </ol>
        <div v-if="listError" class="history-state" role="alert">
          {{ listError }} <el-button text type="primary" @click="loadList">重试</el-button>
        </div>
        <div v-else-if="listBusy" class="empty" role="status">正在加载历史计划…</div>
        <div v-else-if="cursor !== null" class="history-state">
          <el-button text type="primary" @click="loadList">加载更多</el-button>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-actions">
        <el-button @click="emit('close')">关闭</el-button>
        <el-button v-if="selected" type="primary" :disabled="!preview" @click="selectVersion">载入草稿</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.version-list, .version-tasks { list-style: none; margin: 0; padding: 0; }
.history-scroll { max-height: min(52dvh, 460px); overflow: auto; overscroll-behavior: contain; }
.version-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  padding: 10px 8px;
  border: 0;
  border-bottom: 1px solid var(--border);
  background: transparent;
  color: var(--text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.version-row:hover, .version-back:hover { background: var(--accent-soft); }
.version-row:focus-visible { outline-offset: -2px; }
.version-row small { display: block; margin-top: 2px; }
.version-open { display: inline-flex; align-items: center; gap: 2px; color: var(--accent-text); white-space: nowrap; }
.version-head { display: flex; align-items: center; gap: 8px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
.version-head h3 { margin: 0; color: var(--text); font-size: 14px; }
.version-back { display: grid; place-items: center; width: 36px; height: 36px; flex: none; border: 1px solid var(--border); border-radius: 8px; background: transparent; color: var(--text-2); cursor: pointer; }
.version-task { display: grid; grid-template-columns: 94px minmax(0, 1fr); gap: 8px; padding: 9px 2px; border-bottom: 1px solid var(--border); }
.version-time { color: var(--text-2); font-size: 12px; font-variant-numeric: tabular-nums; }
.version-task-copy { display: grid; gap: 2px; color: var(--text); overflow-wrap: anywhere; }
.history-state { padding: 8px; text-align: center; }
</style>
