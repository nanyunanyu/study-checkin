import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, cacheUser, clearToken, getCachedUser, getToken, setToken } from '../api'
import type { User } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(getCachedUser())
  const token = ref<string>(getToken())
  const ready = ref(false)
  const submitting = ref(false)
  const error = ref('')

  const isLoggedIn = computed(() => Boolean(token.value && user.value))
  const isSuperadmin = computed(() => user.value?.role === 'superadmin')

  async function login(username: string, password: string) {
    submitting.value = true
    error.value = ''
    try {
      const result = await api.login(username.trim(), password)
      token.value = result.token
      setToken(result.token)
      user.value = result.user
      cacheUser(result.user)
      return result.user
    } catch (err: any) {
      error.value = err?.message || '登录失败'
      throw err
    } finally {
      submitting.value = false
    }
  }

  async function restore() {
    if (!token.value) {
      ready.value = true
      return
    }
    try {
      const me = await api.me()
      user.value = me
      cacheUser(me)
    } catch (err: any) {
      // 只有令牌确实失效（401）才登出；网络抖动或服务端 5xx 时保留登录态，
      // 否则一次偶发失败就会把用户踢回登录页，还得重新输密码。
      if (err?.status === 401 || err?.status === 403) {
        token.value = ''
        user.value = null
        clearToken()
      }
    } finally {
      ready.value = true
    }
  }

  function setUser(next: User | null) {
    user.value = next
    cacheUser(next)
  }

  function signOut() {
    api.logout().catch(() => undefined)
    token.value = ''
    user.value = null
    clearToken()
  }

  return { user, token, ready, submitting, error, isLoggedIn, isSuperadmin, login, restore, signOut, setUser }
})
