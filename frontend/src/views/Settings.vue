<script setup lang="ts">
import { ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { api } from '../api'
import { useAuthStore } from '../stores/auth'
import { useDataStore } from '../stores/data'
import { useTimerStore } from '../stores/timer'
import { useToastStore } from '../stores/toast'
import { downloadJson, exportFileName } from '../utils'
import ThemePicker from '../components/ThemePicker.vue'
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
      `将导入 ${parsed.days.length} 天记录，同一天的现有记录会被覆盖。继续？`,
      '确认导入备份',
      { confirmButtonText: '继续导入', cancelButtonText: '取消', type: 'warning', customClass: 'redesign-message-box' }
    )
    importing.value = true
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
  <div class="stack">
    <section class="card card-pad">
      <div class="card-head">
        <div class="card-title">账号</div>
        <div class="spacer" />
        <span class="tag" :class="{ 'tag-accent': auth.isSuperadmin }">
          {{ auth.isSuperadmin ? '超级管理员' : '普通用户' }}
        </span>
      </div>
      <div class="row settings-account-row" style="gap: 14px">
        <el-avatar :size="46">
          {{ (auth.user?.displayName || auth.user?.username || '?').slice(0, 1) }}
        </el-avatar>
        <div>
          <div style="font-size: 15px">{{ auth.user?.displayName || auth.user?.username }}</div>
          <div class="hint">@{{ auth.user?.username }}</div>
        </div>
        <div class="spacer" />
        <el-button @click="showPassword = true">修改密码</el-button>
      </div>
    </section>

    <section class="card card-pad">
      <div class="card-head">
        <div class="card-title">界面配色</div>
        <div class="spacer" />
        <span class="hint">选择后立即生效，保存在本机</span>
      </div>
      <ThemePicker />
    </section>

    <section class="card card-pad">
      <div class="card-head">
        <div class="card-title">番茄钟设置</div>
        <div class="spacer" />
        <el-button type="primary" @click="saveTimerConfig">保存设置</el-button>
      </div>
      <div class="kpi-grid settings-config-grid">
        <div class="field">
          <label>专注（分钟）</label>
          <el-input-number v-model="timer.config.focusMin" :min="5" :max="180" :step="5" controls-position="right" />
        </div>
        <div class="field">
          <label>短休息</label>
          <el-input-number v-model="timer.config.breakMin" :min="1" :max="60" controls-position="right" />
        </div>
        <div class="field">
          <label>长休息</label>
          <el-input-number v-model="timer.config.longBreakMin" :min="5" :max="90" :step="5" controls-position="right" />
        </div>
        <div class="field">
          <label>几轮后长休</label>
          <el-input-number v-model="timer.config.roundsPerLong" :min="2" :max="8" controls-position="right" />
        </div>
      </div>
      <div class="settings-switch-row">
        <el-switch v-model="timer.config.autoBreak" />
        <span>专注结束后自动开始休息</span>
      </div>
    </section>

    <section class="card card-pad">
      <div class="card-head">
        <div class="card-title">数据</div>
        <div class="spacer" />
        <span class="hint">{{ Object.keys(data.days).length }} 天记录 · {{ data.plan.length }} 条计划</span>
      </div>
      <div class="row settings-data-actions" style="flex-wrap: wrap; gap: 8px">
        <el-button :loading="exporting" @click="exportData">
          <Icon name="download" :size="14" />
          {{ exporting ? '导出中…' : '导出 JSON 备份' }}
        </el-button>
        <input ref="importInput" type="file" accept="application/json" hidden @change="onImportFile" />
        <el-button :loading="importing" @click="chooseImport">导入备份</el-button>
        <div class="spacer" />
        <el-button type="danger" plain @click="logout">退出登录</el-button>
      </div>
      <p class="hint" style="margin: 12px 0 0">
        数据保存在应用自己的数据库里。建议每周导出一次备份，换设备或误删时可以用导入恢复。
      </p>
    </section>

    <p class="hint" style="text-align: center; padding: 4px">专升本 · 每日学习打卡 · 数据归属 {{ auth.user?.username }}</p>

    <PasswordModal v-if="showPassword" @close="showPassword = false" />
  </div>
</template>
