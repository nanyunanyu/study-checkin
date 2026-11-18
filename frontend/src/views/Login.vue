<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import ThemePicker from '../components/ThemePicker.vue'
import Icon from '../components/Icon.vue'

const auth = useAuthStore()
const username = ref('')
const password = ref('')

async function submit() {
  if (!username.value.trim() || !password.value) {
    auth.error = '请输入账号和密码'
    return
  }
  try {
    await auth.login(username.value, password.value)
  } catch {
    /* 错误信息由 store 维护 */
  }
}
</script>

<template>
  <div class="login-wrap">
    <el-card class="login-card" shadow="never">
      <div class="login-brand">
        <span class="brand-icon"><Icon name="today" :size="21" /></span>
        <div>
          <strong>学习打卡</strong>
          <span>DAILY STUDY JOURNAL</span>
        </div>
      </div>

      <div class="login-title">欢迎回来</div>
      <div class="login-sub">登录后继续完成今天的学习计划</div>

      <form class="login-form" @submit.prevent="submit">
        <el-form-item label="账号">
          <el-input v-model="username" autocomplete="username" placeholder="请输入账号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" show-password autocomplete="current-password" placeholder="请输入密码" @keyup.enter="submit" />
        </el-form-item>
        <el-alert v-if="auth.error" class="login-alert" :title="auth.error" type="error" :closable="false" show-icon />
        <el-button class="login-submit" type="primary" native-type="submit" :loading="auth.submitting" block>
          {{ auth.submitting ? '正在登录' : '登录' }}
        </el-button>
      </form>

      <el-divider content-position="left">界面配色</el-divider>
      <ThemePicker />
      <p class="login-footnote">账号由管理员创建 · 不支持自助注册</p>
    </el-card>
  </div>
</template>

<style scoped>
.login-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 26px;
}

.login-brand > div {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.login-brand strong {
  font-size: 15px;
  font-weight: 650;
}

.login-brand span:not(.brand-icon) {
  color: var(--text-3);
  font-size: 8px;
  letter-spacing: 1.3px;
}

.login-form {
  margin-top: 21px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.login-form :deep(.el-form-item__label) {
  color: var(--text-2);
  font-size: 12px;
}

.login-alert {
  margin: 2px 0 13px;
}

.login-submit {
  height: 44px;
  margin-top: 3px;
  font-weight: 600;
}

.login-footnote {
  margin: 18px 0 0;
  color: var(--text-3);
  font-size: 10.5px;
  text-align: center;
}
</style>
