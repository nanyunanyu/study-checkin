<script setup lang="ts">
import { onMounted, ref } from 'vue'
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

function clonePlan() {
  items.value = data.plan.map((item, index) => ({ ...item, focusMin: item.focusMin ?? null, sortOrder: index }))
  dirty.value = false
}

onMounted(clonePlan)

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
        <span v-if="dirty" class="tag">未保存</span>
        <el-button size="small" @click="restoreOpen = true">恢复默认</el-button>
        <el-button size="small" @click="openAdd"><Icon name="plus" :size="14" />新增计划表</el-button>
        <el-button size="small" type="primary" :loading="saving" :disabled="!dirty" @click="save">
          {{ saving ? '保存中…' : '保存' }}
        </el-button>
      </div>

      <div v-if="!items.length" class="empty">还没有任何时间段，点「新增计划表」开始</div>

      <article v-for="(item, index) in items" :key="item.id" class="plan-item">
        <div class="plan-row">
          <div class="plan-time">
            <el-time-picker v-model="item.startTime" class="time-picker" format="HH:mm" value-format="HH:mm" placeholder="开始" :clearable="false" @change="mark" />
            <span class="hint">至</span>
            <el-time-picker v-model="item.endTime" class="time-picker" format="HH:mm" value-format="HH:mm" placeholder="结束" :clearable="false" @change="mark" />
          </div>
          <el-input v-model="item.title" placeholder="任务内容" @input="mark" />
          <el-input v-model="item.subject" placeholder="自定义类别" aria-label="计划类别" @input="mark" />
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
                <label>自定义类别</label>
                <el-input v-model="item.subject" placeholder="例如：英语、复习" />
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
