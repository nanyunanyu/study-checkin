<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { useDataStore } from '../stores/data'
import { useToastStore } from '../stores/toast'
import { defaultFocusMinutes, todayStr, uuid } from '../utils'
import type { PlanItem } from '../types'
import Icon from '../components/Icon.vue'

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

function move(index: number, delta: number) {
  const target = index + delta
  if (target < 0 || target >= items.value.length) return
  const [item] = items.value.splice(index, 1)
  items.value.splice(target, 0, item)
  mark()
}

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

      <article v-for="(item, index) in items" :key="item.id" class="plan-item">
        <div class="plan-row">
          <div class="plan-time">
            <input v-model="item.startTime" class="plan-native-time" type="time" aria-label="开始时间" @input="mark" />
            <span class="hint">至</span>
            <input v-model="item.endTime" class="plan-native-time" type="time" aria-label="结束时间" @input="mark" />
          </div>
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
            <el-button circle text :disabled="index === 0" aria-label="上移" title="上移" @click="move(index, -1)"><Icon name="up" :size="14" /></el-button>
            <el-button circle text :disabled="index === items.length - 1" aria-label="下移" title="下移" @click="move(index, 1)"><Icon name="down" :size="14" /></el-button>
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
                <label>开始时间</label>
                <el-time-picker v-model="item.startTime" class="time-picker" format="HH:mm" value-format="HH:mm" placeholder="开始时间" :clearable="false" />
              </div>
              <div class="field">
                <label>结束时间</label>
                <el-time-picker v-model="item.endTime" class="time-picker" format="HH:mm" value-format="HH:mm" placeholder="结束时间" :clearable="false" />
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
  </div>
</template>
