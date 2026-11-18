<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api'
import { useDataStore } from '../stores/data'
import { useToastStore } from '../stores/toast'
import { defaultFocusMinutes, todayStr, uuid } from '../utils'
import type { PlanItem } from '../types'
import Icon from '../components/Icon.vue'
import TimeRangePicker from '../components/TimeRangePicker.vue'

const data = useDataStore()
const toast = useToastStore()
const items = ref<PlanItem[]>([])
const dirty = ref(false)
const saving = ref(false)
const addOpen = ref(false)
const restoreOpen = ref(false)
const restoring = ref(false)
const expandedIds = ref(new Set<string>())
const drafts = ref<PlanItem[]>([])
const presets = ref<string[]>([])
const customCategories = ref<Array<{ id: number; name: string }>>([])
const categoryNames = computed(() => new Set([...presets.value, ...customCategories.value.map(({ name }) => name)]))
const categoriesOpen = ref(false)
const newCategoryName = ref('')
const categoryBusy = ref(false)
const editingCategoryId = ref<number | null>(null)
const editingCategoryName = ref('')
const editingTime = ref<PlanItem | null>(null)
const list = ref<HTMLElement>()
const drop = ref<{ id: string; after: boolean } | null>(null)
const dragId = ref<string | null>(null)
const sortAnnouncement = ref('')
let drag: { id: string; pointer: number; startY: number; y: number; handle: HTMLElement } | null = null
let frame = 0

function timeLabel(item: PlanItem) {
  if (!item.startTime && !item.endTime) return '设置时间'
  return `${item.startTime || '—'} 至 ${item.endTime || '—'}`
}

function applyTime(range: Pick<PlanItem, 'startTime' | 'endTime'>) {
  const item = editingTime.value
  if (!item) return
  if (item.startTime !== range.startTime || item.endTime !== range.endTime) {
    Object.assign(item, range)
    if (!addOpen.value) mark()
  }
  editingTime.value = null
}

async function loadCategories() {
  const result = await api.categories()
  presets.value = result.presets
  customCategories.value = result.custom
}

function clonePlan() {
  items.value = data.plan.map((item, index) => ({ ...item, focusMin: item.focusMin ?? null, sortOrder: index }))
  dirty.value = false
}

onMounted(() => {
  clonePlan()
  void loadCategories().catch((err: any) => toast.push(err?.message || '分类加载失败', 'err'))
})

function mark() {
  dirty.value = true
}

function blankItem(): PlanItem {
  return {
    id: uuid(),
    sortOrder: 0,
    startTime: '',
    endTime: '',
    title: '',
    subject: '其他',
    focusMin: null,
    note: '',
    active: true
  }
}

async function createCategory() {
  const name = newCategoryName.value.trim()
  if (!name || categoryBusy.value) return
  categoryBusy.value = true
  try {
    const created = await api.createCategory(name)
    customCategories.value.push(created)
    newCategoryName.value = ''
    toast.push(`已新增分类「${created.name}」`, 'ok')
  } catch (err: any) {
    toast.push(err?.message || '新增分类失败', 'err')
  } finally {
    categoryBusy.value = false
  }
}

function beginRename(category: { id: number; name: string }) {
  editingCategoryId.value = category.id
  editingCategoryName.value = category.name
}

async function saveCategoryName(category: { id: number; name: string }) {
  const name = editingCategoryName.value.trim()
  if (!name || categoryBusy.value) return
  categoryBusy.value = true
  try {
    const updated = await api.renameCategory(category.id, name)
    const rename = (item: PlanItem) => sameCategory(item.subject, category.name) ? { ...item, subject: updated.name } : item
    items.value = items.value.map(rename)
    drafts.value = drafts.value.map(rename)
    data.plan = data.plan.map(rename)
    if (data.reconcileToday()) data.touch(todayStr())
    customCategories.value = customCategories.value.map((item) => item.id === updated.id ? updated : item)
    editingCategoryId.value = null
    toast.push('分类已重命名，已同步到当前计划', 'ok')
  } catch (err: any) {
    toast.push(err?.message || '重命名失败', 'err')
  } finally {
    categoryBusy.value = false
  }
}

async function deleteCategory(category: { id: number; name: string }) {
  if (categoryBusy.value) return
  categoryBusy.value = true
  try {
    await api.deleteCategory(category.id)
    customCategories.value = customCategories.value.filter((item) => item.id !== category.id)
    toast.push(`已删除分类「${category.name}」`, 'ok')
  } catch (err: any) {
    toast.push(err?.message || '删除分类失败', 'err')
  } finally {
    categoryBusy.value = false
  }
}

function sameCategory(first: string, second: string) {
  return first.trim().toLowerCase() === second.trim().toLowerCase()
}

function categoryInPlan(name: string) {
  return [...data.plan, ...items.value].some((item) => sameCategory(item.subject, name))
}

function openAdd() {
  drafts.value = [blankItem()]
  addOpen.value = true
}

function addDraft() {
  if (items.value.length + drafts.value.length >= 200) {
    toast.push('计划最多支持 200 条', 'err')
    return
  }
  drafts.value.push(blankItem())
}

function removeDraft(index: number) {
  drafts.value.splice(index, 1)
  if (!drafts.value.length) drafts.value.push(blankItem())
}

function addDrafts() {
  if (items.value.length + drafts.value.length > 200) {
    toast.push('计划最多支持 200 条，请减少本次新增数量', 'err')
    return
  }
  if (drafts.value.some((item) => !item.title.trim())) {
    toast.push('请填写每条计划的任务内容', 'err')
    return
  }
  const added = drafts.value.map((item) => ({ ...item, id: uuid(), sortOrder: items.value.length }))
  items.value.push(...added)
  for (const item of added) expandedIds.value.add(item.id)
  expandedIds.value = new Set(expandedIds.value)
  mark()
  addOpen.value = false
  toast.push(`已新增 ${added.length} 条计划`, 'ok')
}

function toggleExpanded(id: string) {
  const next = new Set(expandedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedIds.value = next
}

function focusMinutes(item: PlanItem) {
  return item.focusMin ?? defaultFocusMinutes(item.startTime, item.endTime)
}

function remove(index: number) {
  items.value.splice(index, 1)
  mark()
}

function move(index: number, target: number) {
  if (index < 0 || target < 0 || target >= items.value.length || target === index) return
  const [item] = items.value.splice(index, 1)
  items.value.splice(target, 0, item)
  sortAnnouncement.value = `${item.title || '计划'}已移到第 ${target + 1} 项`
  mark()
}

function onSortKey(event: KeyboardEvent, id: string) {
  if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return
  event.preventDefault()
  const index = items.value.findIndex((item) => item.id === id)
  move(index, index + (event.key === 'ArrowUp' ? -1 : 1))
  const handle = event.currentTarget as HTMLElement
  requestAnimationFrame(() => {
    handle.focus({ preventScroll: true })
    handle.scrollIntoView({ block: 'nearest' })
  })
}

function startDrag(event: PointerEvent, id: string) {
  if (drag || !event.isPrimary || event.button !== 0 || items.value.length < 2 || saving.value) return
  const handle = event.currentTarget as HTMLElement
  handle.setPointerCapture(event.pointerId)
  drag = { id, pointer: event.pointerId, startY: event.clientY, y: event.clientY, handle }
}

function updateDrop() {
  if (!drag || !list.value) return
  const bounds = list.value.getBoundingClientRect()
  if (drag.y < bounds.top - 16 || drag.y > bounds.bottom + 16) {
    drop.value = null
    return
  }
  let id = ''
  for (const row of list.value.children as HTMLCollectionOf<HTMLElement>) {
    if (!row.dataset.itemId || row.dataset.itemId === drag.id) continue
    id = row.dataset.itemId
    const rect = row.getBoundingClientRect()
    if (drag.y < rect.top + rect.height / 2) {
      drop.value = { id, after: false }
      return
    }
  }
  drop.value = id ? { id, after: true } : null
}

function scrollWhileDragging() {
  if (!drag || !dragId.value) return
  const edge = 80
  const bottom = window.innerHeight - (window.matchMedia('(max-width: 820px)').matches ? 62 : 0)
  const speed = drag.y < edge ? -Math.min(18, (edge - drag.y) / 4)
    : drag.y > bottom - edge ? Math.min(18, (drag.y - bottom + edge) / 4) : 0
  if (speed) {
    window.scrollBy(0, speed)
    updateDrop()
  }
  frame = requestAnimationFrame(scrollWhileDragging)
}

function dragMove(event: PointerEvent) {
  if (!drag || event.pointerId !== drag.pointer) return
  drag.y = event.clientY
  if (!dragId.value) {
    if (Math.abs(drag.y - drag.startY) < 5) return
    dragId.value = drag.id
    frame = requestAnimationFrame(scrollWhileDragging)
  }
  updateDrop()
}

function resetDrag() {
  const previous = drag
  drag = null
  dragId.value = null
  drop.value = null
  cancelAnimationFrame(frame)
  if (previous?.handle.hasPointerCapture(previous.pointer)) previous.handle.releasePointerCapture(previous.pointer)
}

function finishDrag(event: PointerEvent) {
  if (!drag || event.pointerId !== drag.pointer) return
  const item = drag.id
  if (dragId.value) {
    drag.y = event.clientY
    updateDrop()
  }
  const target = drop.value
  resetDrag()
  if (target) {
    const from = items.value.findIndex(({ id }) => id === item)
    let to = items.value.findIndex(({ id }) => id === target.id) + (target.after ? 1 : 0)
    if (from < to) to--
    move(from, to)
  }
}

function cancelDrag(event: PointerEvent) {
  if (drag?.pointer === event.pointerId) resetDrag()
}

onBeforeUnmount(resetDrag)

async function save() {
  if (items.value.some((item) => !item.title.trim())) {
    toast.push('有任务名为空的条目，请填写或删除', 'err')
    return
  }
  saving.value = true
  try {
    await data.savePlan(items.value.map((item, index) => ({ ...item, sortOrder: index })))
    data.dropDayIfEmpty(todayStr())
    dirty.value = false
    toast.push('计划已保存，从今天起生效', 'ok')
  } catch (err: any) {
    toast.push(err?.message || '保存失败', 'err')
  } finally {
    saving.value = false
  }
}

async function restoreDefault() {
  restoring.value = true
  try {
    const result = await api.planTemplate()
    items.value = result.items.map((item, index) => ({ ...item, focusMin: item.focusMin ?? null, sortOrder: index }))
    expandedIds.value = new Set()
    mark()
    restoreOpen.value = false
    toast.push('已载入默认模板，记得点保存', 'info')
  } catch (err: any) {
    toast.push(err?.message || '加载失败', 'err')
  } finally {
    restoring.value = false
  }
}
</script>

<template>
  <div class="stack">
    <section class="card card-pad">
      <div class="card-head plan-head">
        <div class="card-title">计划表</div>
        <span class="hint">{{ items.length }} 个时间段</span>
        <div class="spacer" />
        <div class="plan-toolbar">
          <span v-if="dirty" class="tag">未保存</span>
          <el-button size="small" @click="categoriesOpen = true">管理分类</el-button>
          <el-button size="small" @click="restoreOpen = true">恢复默认</el-button>
          <el-button size="small" @click="openAdd"><Icon name="plus" :size="14" />新增计划表</el-button>
          <el-button size="small" type="primary" :loading="saving" :disabled="!dirty" @click="save">
            {{ saving ? '保存中…' : '保存' }}
          </el-button>
        </div>
      </div>

      <div v-if="!items.length" class="empty">还没有任何时间段，点「新增计划表」开始</div>

      <span class="sort-announcement" aria-live="polite">{{ sortAnnouncement }}</span>
      <div ref="list" class="plan-sort-list">
      <article v-for="(item, index) in items" :key="item.id" :data-item-id="item.id" class="plan-item" :class="{
        'plan-dragging': dragId === item.id, 'plan-drop-before': drop?.id === item.id && !drop.after, 'plan-drop-after': drop?.id === item.id && drop.after
      }">
        <button
          type="button" class="plan-grip" :aria-label="`排序：${item.title || `第 ${index + 1} 项`}`" title="拖动排序" aria-keyshortcuts="ArrowUp ArrowDown"
          @pointerdown="startDrag($event, item.id)" @pointermove="dragMove" @pointerup="finishDrag" @pointercancel="cancelDrag" @lostpointercapture="cancelDrag"
          @keydown="onSortKey($event, item.id)" @keydown.esc="resetDrag"
        ><span aria-hidden="true" /></button>
        <div class="plan-row">
          <button class="plan-time-button" type="button" :aria-label="`编辑计划时间：${item.title}`" @click="editingTime = item">{{ timeLabel(item) }}</button>
          <el-input v-model="item.title" placeholder="任务内容" @input="mark" />
          <select v-model="item.subject" class="plan-category-select plan-native-select" aria-label="计划类别" @change="mark">
            <option v-if="!categoryNames.has(item.subject)" :value="item.subject">{{ item.subject }}</option>
            <optgroup v-if="presets.length" label="预设分类">
              <option v-for="category in presets" :key="category" :value="category">{{ category }}</option>
            </optgroup>
            <optgroup v-if="customCategories.length" label="自定义分类">
              <option v-for="category in customCategories" :key="category.id" :value="category.name">{{ category.name }}</option>
            </optgroup>
          </select>
          <div class="plan-actions">
            <el-button circle text :aria-label="expandedIds.has(item.id) ? '收起详情' : '展开详情'" :aria-expanded="expandedIds.has(item.id)" title="详情" @click="toggleExpanded(item.id)">
              <Icon :name="expandedIds.has(item.id) ? 'up' : 'down'" :size="14" />
            </el-button>
            <el-button circle text type="danger" aria-label="删除" title="删除" @click="remove(index)"><Icon name="trash" :size="14" /></el-button>
          </div>
        </div>
        <div v-if="expandedIds.has(item.id)" class="plan-details">
          <div class="field plan-note-field">
            <label>备注</label>
            <el-input v-model="item.note" placeholder="补充说明（可选）" @input="mark" />
          </div>
          <div class="field focus-estimate-field">
            <label>预计专注</label>
            <div class="focus-estimate-control">
              <el-input-number :model-value="focusMinutes(item)" :min="1" :max="600" :step="5" aria-label="预计专注分钟" @update:model-value="item.focusMin = $event ?? 30; mark()" />
              <span class="hint">分钟</span>
              <el-button v-if="item.focusMin !== null" size="small" @click="item.focusMin = null; mark()">自动计算</el-button>
              <span v-else class="hint">按时段自动计算</span>
            </div>
          </div>
        </div>
      </article>
      </div>
    </section>

    <p class="hint" style="padding: 0 4px">
      保存后只影响今天及以后。每天的打卡记录是当时的快照，改计划不会动到历史数据。
    </p>

    <el-dialog v-model="addOpen" title="新增计划表" width="780px" class="plan-dialog" :close-on-click-modal="false" destroy-on-close>
        <p class="hint modal-description">可一次填写多条计划，新增后仍需点击页面上的“保存”使计划生效。</p>
        <div class="batch-list">
          <article v-for="(item, index) in drafts" :key="item.id" class="batch-item">
            <div class="batch-item-head">
              <strong>计划 {{ index + 1 }}</strong>
              <button v-if="drafts.length > 1" class="icon-btn" aria-label="移除此条" @click="removeDraft(index)"><Icon name="trash" :size="14" /></button>
            </div>
            <div class="batch-fields">
              <div class="field">
                <label>时间段</label>
                <button class="plan-time-button" type="button" :aria-label="`设置第 ${index + 1} 条计划的时间`" @click="editingTime = item">{{ timeLabel(item) }}</button>
              </div>
              <div class="field batch-title-field">
                <label>任务内容</label>
                <el-input v-model="item.title" placeholder="例如：完成英语阅读练习" />
              </div>
              <div class="field">
                <label>计划类别</label>
                <el-select v-model="item.subject" class="plan-category-select">
                  <el-option-group v-for="group in [{ label: '预设分类', options: presets }, { label: '自定义分类', options: customCategories.map((category) => category.name) }]" :key="group.label" :label="group.label">
                    <el-option v-for="category in group.options" :key="category" :label="category" :value="category" />
                  </el-option-group>
                </el-select>
              </div>
              <div class="field batch-note-field">
                <label>备注（可选）</label>
                <el-input v-model="item.note" placeholder="补充说明" />
              </div>
            </div>
            <div class="batch-focus hint">预计专注：{{ defaultFocusMinutes(item.startTime, item.endTime) }} 分钟（按时段自动计算）</div>
          </article>
        </div>
        <el-button class="add-another-btn" plain @click="addDraft"><Icon name="plus" :size="14" />再加一条</el-button>
        <template #footer>
          <div class="dialog-actions">
            <el-button @click="addOpen = false">取消</el-button>
            <el-button type="primary" @click="addDrafts">加入计划表</el-button>
          </div>
        </template>
    </el-dialog>

    <el-dialog v-model="categoriesOpen" title="管理计划分类" width="480px" class="category-dialog" :close-on-click-modal="false">
      <p class="hint category-help">自定义分类仅当前账号可见。重命名会同步当前计划，历史记录保留原名称。</p>
      <div class="category-create-row">
        <el-input v-model="newCategoryName" placeholder="输入新的自定义分类" maxlength="40" @keyup.enter="createCategory" />
        <el-button type="primary" :loading="categoryBusy" :disabled="!newCategoryName.trim()" @click="createCategory"><Icon name="plus" :size="14" />新增</el-button>
      </div>
      <div v-if="customCategories.length" class="category-manage-list">
        <div v-for="category in customCategories" :key="category.id" class="category-manage-row">
          <template v-if="editingCategoryId === category.id">
            <el-input v-model="editingCategoryName" maxlength="40" @keyup.enter="saveCategoryName(category)" />
            <el-button text type="primary" :loading="categoryBusy" @click="saveCategoryName(category)">保存</el-button>
            <el-button text @click="editingCategoryId = null">取消</el-button>
          </template>
          <template v-else>
            <span class="category-name">
              <span>{{ category.name }}</span>
              <small v-if="categoryInPlan(category.name)">当前计划使用中</small>
            </span>
            <el-button text type="primary" @click="beginRename(category)">重命名</el-button>
            <el-button
              text
              type="danger"
              :loading="categoryBusy"
              :disabled="categoryInPlan(category.name)"
              :title="categoryInPlan(category.name) ? '请先调整并保存当前计划的分类' : '删除分类'"
              @click="deleteCategory(category)"
            >删除</el-button>
          </template>
        </div>
      </div>
      <el-empty v-else description="还没有自定义分类" :image-size="56" />
      <template #footer><el-button @click="categoriesOpen = false">完成</el-button></template>
    </el-dialog>

    <el-dialog v-model="restoreOpen" title="恢复默认计划？" width="460px" class="confirm-dialog" :close-on-click-modal="false">
        <p class="hint">将用默认的 24 条计划替换当前编辑内容。历史打卡记录不受影响，载入后还需点击“保存”。</p>
        <template #footer>
          <div class="dialog-actions">
            <el-button :disabled="restoring" @click="restoreOpen = false">取消</el-button>
            <el-button type="primary" :loading="restoring" @click="restoreDefault">载入默认计划</el-button>
          </div>
        </template>
    </el-dialog>
    <TimeRangePicker v-if="editingTime" title="编辑计划时间" :start-time="editingTime.startTime" :end-time="editingTime.endTime" @confirm="applyTime" @cancel="editingTime = null" />
  </div>
</template>

<style scoped>
.plan-item { position: relative; padding-left: 33px; }
.plan-item.plan-dragging { opacity: .55; }
.plan-drop-before::before, .plan-drop-after::after { content: ''; position: absolute; z-index: 1; left: 7px; right: 5px; height: 2px; border-radius: 2px; background: var(--accent); }
.plan-drop-before::before { top: -1px; }
.plan-drop-after::after { bottom: -1px; }
.plan-grip { position: absolute; inset: 6px auto 6px 0; display: grid; place-items: center; width: 29px; color: var(--text-3); border-radius: 6px; cursor: grab; touch-action: none; user-select: none; }
.plan-grip span { width: 12px; height: 18px; background: radial-gradient(circle, currentColor 1.25px, transparent 1.6px) 0 0 / 6px 6px; }
.plan-grip:hover, .plan-grip:focus-visible { color: var(--accent-text); background: var(--accent-soft); }
.plan-dragging .plan-grip { cursor: grabbing; }
.plan-time-button { min-height: 34px; padding: 0 8px; white-space: nowrap; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--surface-solid); color: var(--text-2); font-size: 12px; font-variant-numeric: tabular-nums; }
.plan-time-button:hover { border-color: var(--accent); color: var(--accent-text); }
.plan-row { grid-template-columns: 113px minmax(0, 1fr) minmax(95px, 128px) auto; }
.sort-announcement { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
@media (max-width: 820px) {
  .plan-row { grid-template-columns: minmax(0, 1fr) auto auto; gap: 5px 6px; }
  .plan-row > .el-input { grid-column: 1 / -1; grid-row: 1; }
  .plan-row > .plan-time-button { grid-column: 1; grid-row: 2; justify-self: start; padding-inline: 6px; }
  .plan-row > .plan-category-select { grid-column: 2; grid-row: 2; width: clamp(61px, 19vw, 110px); padding-inline: 4px; font-size: 12px; }
  .plan-row > .plan-actions { grid-column: 3; grid-row: 2; }
  .plan-row .plan-actions :deep(.el-button) { width: 28px; height: 33px; }
  .plan-row > .plan-time-button, .plan-row > .plan-category-select { min-height: 32px; height: 32px; }
  .plan-item { padding-left: 25px; }
  .plan-grip { width: 22px; }
}
</style>
