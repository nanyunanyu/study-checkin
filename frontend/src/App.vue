<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { onUnauthorized } from './api'
import { useAuthStore } from './stores/auth'
import { useDataStore } from './stores/data'
import { useThemeStore } from './stores/theme'
import { useTimerStore } from './stores/timer'
import { useToastStore } from './stores/toast'
import { useUiStore, type ViewName } from './stores/ui'
import { todayStr } from './utils'

import Login from './views/Login.vue'
import Today from './views/Today.vue'
import Plan from './views/Plan.vue'
import Stats from './views/Stats.vue'
import Admin from './views/Admin.vue'
import Settings from './views/Settings.vue'
import TimerPanel from './components/TimerPanel.vue'
import ToastStack from './components/ToastStack.vue'
import PasswordModal from './components/PasswordModal.vue'
import Icon from './components/Icon.vue'
import ThemePicker from './components/ThemePicker.vue'

const auth = useAuthStore()
const data = useDataStore()
const timer = useTimerStore()
const toast = useToastStore()
const ui = useUiStore()
const theme = useThemeStore()

const tabs = computed<Array<{ id: ViewName; label: string; icon: string }>>(() => {
  const list: Array<{ id: ViewName; label: string; icon: string }> = [
    { id: 'today', label: '今日', icon: 'today' },
    { id: 'plan', label: '计划', icon: 'plan' },
    { id: 'stats', label: '统计', icon: 'stats' }
  ]
  if (auth.isSuperadmin) list.push({ id: 'admin', label: '后台', icon: 'admin' })
  list.push({ id: 'settings', label: '设置', icon: 'settings' })
  return list
})

const initial = computed(() => (auth.user?.displayName || auth.user?.username || '?').slice(0, 1))
const showForcePassword = computed(() => Boolean(auth.user?.mustChangePassword))
const activeLabel = computed(() => tabs.value.find((tab) => tab.id === ui.view)?.label || '今日')

let tickHandle = 0

onUnauthorized(() => {
  auth.signOut()
  toast.push('登录已失效，请重新登录', 'err')
})

timer.onFinish((seconds, taskId) => {
  if (seconds < 5) return
  data.addFocus(todayStr(), taskId, seconds)
})

onMounted(async () => {
  theme.apply()
  await auth.restore()
  if (auth.isLoggedIn) {
    try {
      await data.load()
    } catch (err: any) {
      toast.push(err?.message || '数据加载失败', 'err')
    }
  }
  tickHandle = window.setInterval(() => timer.tick(), 500)
})

onBeforeUnmount(() => {
  if (tickHandle) window.clearInterval(tickHandle)
})

// 账号换了（退出、换号登录）就先把上一个账号的数据清干净，
// 否则新账号会拿旧计划生成当天的任务快照，写进自己的记录里。
watch(
  () => auth.user?.id ?? null,
  () => {
    timer.reset(false)
    data.reset()
    ui.go('today')
  }
)

watch(
  () => auth.isLoggedIn,
  async (loggedIn) => {
    if (!loggedIn) {
      ui.go('today')
      return
    }
    if (!data.loaded) {
      try {
        await data.load()
      } catch (err: any) {
        toast.push(err?.message || '数据加载失败', 'err')
      }
    }
  }
)
</script>

<template>
  <div class="app">
    <template v-if="!auth.isLoggedIn">
      <Login />
    </template>

    <template v-else>
      <div class="app-shell">
        <aside class="sidebar">
          <button class="brand brand-link" @click="ui.go('today')">
            <span class="brand-icon"><Icon name="today" :size="20" /></span>
            <span class="brand-copy">学习打卡<span class="brand-en">DAILY STUDY JOURNAL</span></span>
          </button>
          <div class="nav-label">学习空间</div>
          <nav class="side-nav" aria-label="主导航">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              :class="{ selected: ui.view === tab.id }"
              :aria-current="ui.view === tab.id ? 'page' : undefined"
              @click="ui.go(tab.id)"
            >
              <Icon :name="tab.icon" :size="18" />
              <span>{{ tab.label }}</span>
              <span v-if="ui.view === tab.id" class="nav-indicator" />
            </button>
          </nav>
          <div class="sidebar-footer">
            <div class="local-box"><span class="dot" /> 每天进步一点</div>
            <div class="sidebar-user">
              <el-avatar :size="34">{{ initial }}</el-avatar>
              <div class="sidebar-user-copy">
                <strong>{{ auth.user?.displayName || auth.user?.username }}</strong>
                <span>{{ auth.isSuperadmin ? '超级管理员' : '学习者' }}</span>
              </div>
            </div>
          </div>
        </aside>

        <main class="main-pane">
          <header class="topbar">
            <div class="breadcrumb">我的学习 <span>/</span> <strong>{{ activeLabel }}</strong></div>
            <div class="top-meta">
              <ThemePicker compact />
              <span class="top-meta-name">{{ auth.user?.displayName || auth.user?.username }}</span>
              <el-avatar :size="32">{{ initial }}</el-avatar>
            </div>
          </header>

          <section class="page-content">
            <div v-if="data.loading || !data.loaded" class="loading-panel">
              <el-skeleton :rows="5" animated />
            </div>
            <template v-else>
              <Today v-if="ui.view === 'today'" />
              <Plan v-else-if="ui.view === 'plan'" />
              <Stats v-else-if="ui.view === 'stats'" />
              <Admin v-else-if="ui.view === 'admin'" />
              <Settings v-else />
            </template>
          </section>
        </main>

        <nav class="tabbar" aria-label="手机导航">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            :class="{ active: ui.view === tab.id }"
            :aria-current="ui.view === tab.id ? 'page' : undefined"
            @click="ui.go(tab.id)"
          >
            <Icon :name="tab.icon" :size="19" />
            <span>{{ tab.label }}</span>
          </button>
        </nav>
      </div>

      <TimerPanel />
    </template>

    <PasswordModal v-if="showForcePassword" force @close="() => undefined" />
    <ToastStack />
  </div>
</template>
