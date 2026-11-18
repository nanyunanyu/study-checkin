<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api'
import { useAuthStore } from '../stores/auth'
import { useToastStore } from '../stores/toast'

const props = defineProps<{ force?: boolean }>()
const emit = defineEmits<{ (event: 'close'): void }>()

const auth = useAuthStore()
const toast = useToastStore()

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const submitting = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  if (newPassword.value.length < 8) {
    error.value = '新密码至少 8 位'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    error.value = '两次输入的新密码不一致'
    return
  }
  submitting.value = true
  try {
    await api.changePassword(oldPassword.value, newPassword.value)
    if (auth.user) auth.setUser({ ...auth.user, mustChangePassword: false })
    toast.push('密码已修改', 'ok')
    emit('close')
  } catch (err: any) {
    error.value = err?.message || '修改失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="true"
    :title="props.force ? '首次登录，请修改密码' : '修改密码'"
    width="460px"
    :show-close="!props.force"
    :close-on-click-modal="!props.force"
    :close-on-press-escape="!props.force"
    @close="!props.force && emit('close')"
  >
      <el-form label-position="top" class="password-form">
        <div class="field">
          <label>当前密码</label>
          <el-input v-model="oldPassword" type="password" show-password autocomplete="current-password" />
        </div>
        <div class="field">
          <label>新密码（至少 8 位）</label>
          <el-input v-model="newPassword" type="password" show-password autocomplete="new-password" />
        </div>
        <div class="field">
          <label>确认新密码</label>
          <el-input v-model="confirmPassword" type="password" show-password autocomplete="new-password" @keyup.enter="submit" />
        </div>
      </el-form>
      <el-alert v-if="error" class="password-error" :title="error" type="error" :closable="false" show-icon />
      <template #footer>
        <div class="dialog-actions">
          <el-button v-if="!props.force" @click="emit('close')">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submit">确认修改</el-button>
        </div>
      </template>
  </el-dialog>
</template>

<style scoped>
.password-form {
  display: grid;
  gap: 13px;
}

.password-form .field > label {
  display: block;
  margin-bottom: 6px;
}

.password-error {
  margin-top: 12px;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
