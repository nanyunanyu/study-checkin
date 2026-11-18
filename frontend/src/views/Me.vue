<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { api } from '../api'
import { useAuthStore } from '../stores/auth'
import { useDataStore } from '../stores/data'
import { useTimerStore } from '../stores/timer'
import { useToastStore } from '../stores/toast'
import type { LearningSummary } from '../types'
import { downloadJson, exportFileName, formatDuration } from '../utils'
import PasswordModal from '../components/PasswordModal.vue'
import Icon from '../components/Icon.vue'

const auth = useAuthStore()
const data = useDataStore()
const timer = useTimerStore()
const toast = useToastStore()

const showPassword = ref(false)
const exporting = ref(false)
const importing = ref(false)
const importInput = ref<HTMLInputElement | null>(null)
const summary = ref<LearningSummary | null>(null)
const summaryError = ref(false)
let summaryRequest = 0

async function loadSummary() {
  const request = ++summaryRequest
  summaryError.value = false
  try {
    const result = await api.learningSummary()
    if (request === summaryRequest) summary.value = result
  } catch {
    if (request === summaryRequest) summaryError.value = true
  }
}

watch(() => data.savedAt, loadSummary, { immediate: true })

async function exportData() {
  exporting.value = true
  try {
    const payload = await api.exportData()
    downloadJson(payload, exportFileName(auth.user?.username || 'user'))
    toast.push('已导出备份文件', 'ok')
  } catch (err: any) {
    toast.push(err?.message || '导出失败', 'err')
  } finally {
    exporting.value = false
  }
}

async function onImportFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const text = await file.text()
    const parsed = JSON.parse(text)
    if (!Array.isArray(parsed.days)) {
      toast.push('文件格式不对，应为本应用导出的 JSON', 'err')
      return
    }
    await ElMessageBox.confirm(
      `将导入 ${parsed.days.length} 天记录，同一天的现有记录会被覆盖，计划与历史记录中的自定义分类会合并到当前账号。继续？`,
      '确认导入备份',
      { confirmButtonText: '继续导入', cancelButtonText: '取消', type: 'warning', customClass: 'redesign-message-box' }
    )
    importing.value = true
    const categoryNames = new Set<string>()
    const collectCategory = (name: unknown) => {
      if (typeof name === 'string' && name.trim()) categoryNames.add(name.trim())
    }
    if (Array.isArray(parsed.categories)) parsed.categories.forEach(collectCategory)
    if (Array.isArray(parsed.plan)) parsed.plan.forEach((item: any) => collectCategory(item?.subject))
    for (const log of parsed.days) {
      if (Array.isArray(log?.tasks)) log.tasks.forEach((task: any) => collectCategory(task?.subject))
    }
    if (categoryNames.size) await api.importCategories([...categoryNames])
    if (Array.isArray(parsed.plan) && parsed.plan.length) {
      await data.savePlan(parsed.plan)
    }
    for (const log of parsed.days) {
      if (!log?.day) continue
      await api.saveDay(log.day, {
        day: log.day,
        tasks: Array.isArray(log.tasks) ? log.tasks : [],
        review: log.review || {},
        focusSec: Number(log.focusSec) || 0,
        completion: Number(log.completion) || 0,
        checkedIn: Boolean(log.checkedIn)
      })
    }
    await data.load()
    void loadSummary()
    toast.push('导入完成', 'ok')
  } catch (err: any) {
    if (err !== 'cancel' && err !== 'close') toast.push(err?.message || '导入失败，请检查文件内容', 'err')
  } finally {
    importing.value = false
    input.value = ''
  }
}

function saveTimerConfig() {
  timer.saveConfig()
  toast.push('计时器设置已保存', 'ok')
}

function logout() {
  auth.signOut()
  toast.push('已退出登录', 'info')
}

function chooseImport() {
  importInput.value?.click()
}
</script>

<template>
  <div class="me-page">
    <header class="me-identity">
      <el-avatar :size="48">{{ (auth.user?.displayName || auth.user?.username || '?').slice(0, 1) }}</el-avatar>
      <div>
        <h1>{{ auth.user?.displayName || auth.user?.username }}</h1>
        <span class="hint">@{{ auth.user?.username }}</span>
      </div>
      <span class="tag" :class="{ 'tag-accent': auth.isSuperadmin }">{{ auth.isSuperadmin ? '超级管理员' : '学习者' }}</span>
    </header>

    <section class="me-overview" aria-labelledby="me-overview-title">
      <h2 id="me-overview-title">学习概览</h2>
      <dl class="me-metrics" :aria-busy="!summary && !summaryError">
        <div class="me-metric"><dt>累计打卡</dt><dd>{{ summary ? `${summary.checkinDays} 天` : '—' }}</dd></div>
        <div class="me-metric"><dt>连续打卡</dt><dd>{{ summary ? `${summary.streak} 天` : '—' }}</dd></div>
        <div class="me-metric"><dt>累计专注</dt><dd>{{ summary ? formatDuration(summary.totalFocusSec) : '—' }}</dd></div>
      </dl>
      <p v-if="summaryError" class="hint" role="status">学习概览暂时无法加载 <el-button text size="small" @click="loadSummary">重试</el-button></p>
    </section>

    <div class="me-settings">
    <section class="me-section me-timer-settings">
      <div class="card-head">
        <h2>番茄钟设置</h2>
        <div class="spacer" />
        <el-button size="small" type="primary" @click="saveTimerConfig">保存设置</el-button>
      </div>
      <div class="kpi-grid settings-config-grid">
        <div class="field">
          <label>专注（分钟）</label>
          <el-input-number v-model="timer.config.focusMin" aria-label="专注分钟数" :min="5" :max="180" :step="5" controls-position="right" />
        </div>
        <div class="field">
          <label>短休息</label>
          <el-input-number v-model="timer.config.breakMin" aria-label="短休息分钟数" :min="1" :max="60" controls-position="right" />
        </div>
        <div class="field">
          <label>长休息</label>
          <el-input-number v-model="timer.config.longBreakMin" aria-label="长休息分钟数" :min="5" :max="90" :step="5" controls-position="right" />
        </div>
        <div class="field">
          <label>几轮后长休</label>
          <el-input-number v-model="timer.config.roundsPerLong" aria-label="长休息轮数" :min="2" :max="8" controls-position="right" />
        </div>
      </div>
      <div class="settings-switch-row">
        <el-switch v-model="timer.config.autoBreak" aria-label="专注结束后自动开始休息" />
        <span>专注结束后自动开始休息</span>
      </div>
    </section>

    <section class="me-section me-backup">
      <div class="card-head">
        <h2>数据备份</h2>
      </div>
      <div class="row settings-data-actions" style="flex-wrap: wrap; gap: 8px">
        <el-button :loading="exporting" @click="exportData">
          <Icon name="download" :size="14" />
          {{ exporting ? '导出中…' : '导出 JSON 备份' }}
        </el-button>
        <input ref="importInput" type="file" accept="application/json" hidden @change="onImportFile" />
        <el-button :loading="importing" @click="chooseImport">导入备份</el-button>
      </div>
    </section>

    <section class="me-section me-security">
      <div class="card-head"><h2>账号安全</h2></div>
      <div class="me-actions">
        <el-button @click="showPassword = true"><Icon name="key" :size="14" />修改密码</el-button>
        <el-button type="danger" plain @click="logout">退出登录</el-button>
      </div>
    </section>
    </div>

    <PasswordModal v-if="showPassword" @close="showPassword = false" />
  </div>
</template>

<style scoped>
.me-page { display: grid; gap: 18px; }
.me-identity { display: flex; align-items: center; gap: 12px; min-width: 0; }
.me-identity > div { min-width: 0; overflow-wrap: anywhere; }
.me-identity .tag { flex-shrink: 0; }
h1, h2 { margin: 0; line-height: 1.3; }
h1 { font-size: 21px; }
h2 { font-size: 15px; }
.me-metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; margin: 8px 0 0; }
.me-metric { min-width: 0; padding: 10px 12px; border: 1px solid var(--border); border-top: 2px solid var(--accent); border-radius: 8px; background: var(--surface-solid); }
.me-metric dt { color: var(--text-3); font-size: 11px; }
.me-metric dd { margin: 2px 0 0; overflow-wrap: anywhere; font-size: 17px; font-weight: 650; font-variant-numeric: tabular-nums; }
.me-settings { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr); gap: 14px 22px; }
.me-section { min-width: 0; padding: 12px 0 7px; border-top: 1px solid var(--border); }
.me-section .card-head { margin-bottom: 10px; }
.me-timer-settings { grid-row: span 2; }
.settings-config-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.settings-config-grid :deep(.el-input-number) { width: 100%; }
.me-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.me-section :deep(.el-button + .el-button) { margin-left: 0; }
@media (max-width: 620px) {
  .me-settings { grid-template-columns: 1fr; gap: 6px; }
  .me-timer-settings { grid-row: auto; }
  .me-metrics { gap: 5px; }
  .me-metric { padding: 8px 6px; }
  .me-metric dd { font-size: 14px; }
}
</style>
