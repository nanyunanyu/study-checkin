<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { api } from '../api'
import { useAuthStore } from '../stores/auth'
import { useToastStore } from '../stores/toast'
import type { User } from '../types'
import UserDrawer from '../components/UserDrawer.vue'
import Icon from '../components/Icon.vue'

const auth = useAuthStore()
const toast = useToastStore()

const users = ref<User[]>([])
const loading = ref(false)
const error = ref('')

const showCreate = ref(false)
const form = ref({ username: '', password: '', displayName: '', mustChangePassword: true })
const creating = ref(false)
const createError = ref('')

const resetTarget = ref<User | null>(null)
const resetForm = ref({ password: '', mustChangePassword: true })
const resetting = ref(false)

const drawerUser = ref<User | null>(null)

const totalUsers = computed(() => users.value.length)
const activeUsers = computed(() => users.value.filter((user) => user.status !== 'disabled').length)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await api.adminUsers()
    users.value = result.users
  } catch (err: any) {
    error.value = err?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)

function openCreate() {
  form.value = { username: '', password: '', displayName: '', mustChangePassword: true }
  createError.value = ''
  showCreate.value = true
}

async function submitCreate() {
  if (creating.value) return
  createError.value = ''
  if (form.value.username.trim().length < 4) {
    createError.value = '账号至少 4 位'
    return
  }
  if (form.value.password.length < 8) {
    createError.value = '初始密码至少 8 位'
    return
  }
  creating.value = true
  try {
    const created = await api.adminCreateUser({
      username: form.value.username.trim(),
      password: form.value.password,
      displayName: form.value.displayName.trim() || undefined,
      mustChangePassword: form.value.mustChangePassword
    })
    toast.push(`账号 ${created.username} 已创建`, 'ok')
    showCreate.value = false
    await load()
  } catch (err: any) {
    createError.value = err?.message || '创建失败'
  } finally {
    creating.value = false
  }
}

async function toggleStatus(user: User) {
  const next = user.status === 'disabled' ? 'active' : 'disabled'
  const label = next === 'disabled' ? '停用' : '启用'
  if (next === 'disabled') {
    try {
      await ElMessageBox.confirm(`停用 ${user.username} 后该账号将立即退出登录，确定吗？`, '停用账号', { type: 'warning', confirmButtonText: '确认停用', cancelButtonText: '取消' })
    } catch { return }
  }
  try {
    await api.adminPatchUser(user.id, { status: next })
    toast.push(`已${label} ${user.username}`, 'ok')
    await load()
  } catch (err: any) {
    toast.push(err?.message || '操作失败', 'err')
  }
}

async function submitReset() {
  if (!resetTarget.value) return
  if (resetForm.value.password.length < 8) {
    toast.push('新密码至少 8 位', 'err')
    return
  }
  resetting.value = true
  try {
    await api.adminResetPassword(resetTarget.value.id, resetForm.value.password, resetForm.value.mustChangePassword)
    toast.push('密码已重置，该账号需重新登录', 'ok')
    resetTarget.value = null
  } catch (err: any) {
    toast.push(err?.message || '重置失败', 'err')
  } finally {
    resetting.value = false
  }
}

async function removeUser(user: User) {
  try {
    await ElMessageBox.prompt(`删除会同时清空该账号的全部打卡记录，且无法恢复。请输入账号「${user.username}」确认删除。`, '删除账号', {
      type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消', inputPlaceholder: '请输入账号名称',
      inputValidator: (value: string) => value.trim() === user.username || '输入的账号不一致'
    })
  } catch { return }
  try {
    await api.adminDeleteUser(user.id)
    toast.push(`已删除 ${user.username}`, 'ok')
    await load()
  } catch (err: any) {
    toast.push(err?.message || '删除失败', 'err')
  }
}

function lastLogin(value?: string | null) {
  if (!value) return '从未登录'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="stack">
    <section class="card card-pad">
      <div class="card-head">
        <div class="card-title">账号管理</div>
        <span class="hint">共 {{ totalUsers }} 个账号，{{ activeUsers }} 个启用中</span>
        <div class="spacer" />
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" @click="openCreate"><Icon name="plus" :size="14" />新建账号</el-button>
      </div>
      <div v-if="error" class="empty">{{ error }}</div>
      <div v-else class="admin-list" v-loading="loading">
        <article v-for="user in users" :key="user.id" class="admin-user">
          <div class="admin-user-main">
            <el-avatar :size="40">{{ (user.displayName || user.username).slice(0, 1) }}</el-avatar>
            <div><strong>{{ user.displayName || user.username }}</strong><div class="hint">@{{ user.username }}</div></div>
            <el-tag size="small" :type="user.role === 'superadmin' ? 'primary' : 'info'" effect="light">{{ user.role === 'superadmin' ? '超级管理员' : '普通用户' }}</el-tag>
            <el-tag size="small" :type="user.status === 'disabled' ? 'danger' : 'success'" effect="light">{{ user.status === 'disabled' ? '已停用' : '正常' }}</el-tag>
          </div>
          <div class="admin-user-meta"><span>今日完成 {{ Math.round(user.todayCompletion || 0) }}%</span><span>连续打卡 {{ user.streak || 0 }} 天</span><span>最近登录 {{ lastLogin(user.lastLoginAt) }}</span></div>
          <div class="admin-user-actions">
            <el-button text type="primary" @click="drawerUser = user">查看</el-button>
            <el-button text @click="resetTarget = user; resetForm = { password: '', mustChangePassword: true }">重置密码</el-button>
            <el-button text :disabled="user.id === auth.user?.id" @click="toggleStatus(user)">{{ user.status === 'disabled' ? '启用' : '停用' }}</el-button>
            <el-button text type="danger" :disabled="user.id === auth.user?.id" @click="removeUser(user)">删除</el-button>
          </div>
        </article>
        <div v-if="!loading && !users.length" class="empty">暂无账号</div>
      </div>
    </section>
    <p class="hint" style="padding: 0 4px">只有超级管理员能创建账号。停用账号会立即踢下线，删除会一并清空其全部打卡记录。</p>
    <el-dialog v-model="showCreate" title="新建账号" width="480px" class="responsive-dialog">
      <div class="stack" style="gap: 14px">
        <div class="field"><label>账号（4–32 位字母、数字、下划线）</label><el-input v-model="form.username" placeholder="例如 xiaoming2027" /></div>
        <div class="field"><label>初始密码（至少 8 位）</label><el-input v-model="form.password" type="password" show-password placeholder="建议告知对方后立即修改" /></div>
        <div class="field"><label>显示名（可选）</label><el-input v-model="form.displayName" placeholder="例如 小明" /></div>
        <el-checkbox v-model="form.mustChangePassword">要求首次登录修改密码</el-checkbox>
        <div v-if="createError" class="login-error">{{ createError }}</div>
      </div>
      <template #footer><el-button @click="showCreate = false">取消</el-button><el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button></template>
    </el-dialog>
    <el-dialog :model-value="!!resetTarget" :title="`重置 ${resetTarget?.username || ''} 的密码`" width="480px" class="responsive-dialog" @update:model-value="!$event && (resetTarget = null)">
      <div class="stack" style="gap: 14px">
        <div class="field"><label>新密码（至少 8 位）</label><el-input v-model="resetForm.password" type="password" show-password /></div>
        <el-checkbox v-model="resetForm.mustChangePassword">要求该账号下次登录时修改密码</el-checkbox>
        <p class="hint" style="margin: 0">重置后该账号的所有设备都会被登出。</p>
      </div>
      <template #footer><el-button @click="resetTarget = null">取消</el-button><el-button type="primary" :loading="resetting" @click="submitReset">确认重置</el-button></template>
    </el-dialog>
    <UserDrawer v-if="drawerUser" :user-id="drawerUser.id" :name="drawerUser.displayName || drawerUser.username" @close="drawerUser = null" />
  </div>
</template>
