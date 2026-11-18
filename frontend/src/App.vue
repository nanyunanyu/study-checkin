<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { onUnauthorized } from './api'
import { useAuthStore } from './stores/auth'
import { useDataStore } from './stores/data'
import { useThemeStore } from './stores/theme'
import { useTimerStore } from './stores/timer'
import { useToastStore } from './stores/toast'
import { useUiStore } from './stores/ui'
import { loginDestination, type ViewName } from './router'
import { todayStr } from './utils'

import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import TimerPanel from './components/TimerPanel.vue'
import ToastStack from './components/ToastStack.vue'
import PasswordModal from './components/PasswordModal.vue'
import Icon from './components/Icon.vue'
import ThemePicker from './components/ThemePicker.vue'
import PageScrollActions from './components/PageScrollActions.vue'

const auth = useAuthStore()
const data = useDataStore()
const timer = useTimerStore()
const toast = useToastStore()
const ui = useUiStore()
const theme = useThemeStore()
const route = useRoute()
const router = useRouter()

const tabs = computed<Array<{ id: ViewName; label: string; icon: string }>>(() => {
  const list: Array<{ id: ViewName; label: string; icon: string }> = [
    { id: 'today', label: '今日', icon: 'today' },
    { id: 'plan', label: '计划', icon: 'plan' },
    { id: 'stats', label: '统计', icon: 'stats' }
  ]
  if (auth.isSuperadmin) list.push({ id: 'admin', label: '后台', icon: 'admin' })
  list.push({ id: 'me', label: '我的', icon: 'user' })
  return list
})

const initial = computed(() => (auth.user?.displayName || auth.user?.username || '?').slice(0, 1))
const showForcePassword = computed(() => Boolean(auth.user?.mustChangePassword))
const activeLabel = computed(() => tabs.value.find((tab) => tab.id === route.name)?.label || '今日')

let tickHandle = 0

onUnauthorized(() => {
  auth.signOut()
  toast.push('登录已失效，请重新登录', 'err')
})

timer.onFinish((seconds, taskId) => {
  if (seconds < 5) return
  data.addFocus(todayStr(), taskId, seconds)
})

onMounted(() => {
  theme.apply()
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
    ui.focusDate = null
  }
)

watch(
  () => auth.isLoggedIn,
  async (loggedIn) => {
    if (!loggedIn) {
      if (route.name !== 'login') void router.replace({ name: 'login' })
      return
    }
    if (route.name === 'login') void router.replace(loginDestination(route, auth.isSuperadmin))
    if (!data.loaded) {
      try {
        await data.load()
      } catch (err: any) {
        toast.push(err?.message || '数据加载失败', 'err')
      }
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="app">
    <template v-if="route.name === 'login'">
      <RouterView />
    </template>

    <template v-else-if="auth.isLoggedIn">
      <div class="app-shell">
        <aside class="sidebar">
          <RouterLink class="brand brand-link" :to="{ name: 'today' }">
            <span class="brand-icon"><Icon name="today" :size="20" /></span>
            <span class="brand-copy">学习打卡<span class="brand-en">DAILY STUDY JOURNAL</span></span>
          </RouterLink>
          <div class="nav-label">学习空间</div>
          <nav class="side-nav" aria-label="主导航">
            <RouterLink
              v-for="tab in tabs"
              :key="tab.id"
              :class="{ selected: route.name === tab.id }"
              :to="{ name: tab.id }"
            >
              <Icon :name="tab.icon" :size="18" />
              <span>{{ tab.label }}</span>
              <span v-if="route.name === tab.id" class="nav-indicator" />
            </RouterLink>
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
              <RouterView />
              <PageScrollActions v-if="route.name === 'today' || route.name === 'plan'" />
            </template>
          </section>
        </main>

        <nav class="tabbar" aria-label="手机导航">
          <RouterLink
            v-for="tab in tabs"
            :key="tab.id"
            :class="{ active: route.name === tab.id }"
            :to="{ name: tab.id }"
          >
            <Icon :name="tab.icon" :size="19" />
            <span>{{ tab.label }}</span>
          </RouterLink>
        </nav>
      </div>

      <TimerPanel />
    </template>

    <PasswordModal v-if="showForcePassword" force @close="() => undefined" />
    <ToastStack />
  </div>
</template>
