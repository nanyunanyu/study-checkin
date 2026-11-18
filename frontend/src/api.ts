import type { DayLog, LearningSummary, OverviewResponse, PlanCategoriesResponse, PlanCategory, PlanItem, PlanVersion, StateResponse, User } from './types'

const TOKEN_KEY = 'study.token'
const USER_KEY = 'study.user'

export class ApiError extends Error {
  status: number
  constructor(message: string, status = 0) {
    super(message)
    this.status = status
  }
}

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function getCachedUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

export function cacheUser(user: User | null): void {
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
  else localStorage.removeItem(USER_KEY)
}

let unauthorizedHandler: (() => void) | null = null
export function onUnauthorized(fn: () => void): void {
  unauthorizedHandler = fn
}

const FIELD_LABEL: Record<string, string> = {
  username: '账号',
  password: '密码',
  newPassword: '新密码',
  displayName: '显示名',
  title: '任务内容'
}

/** 把 Pydantic 的英文校验信息翻译成人话，避免用户看到 "String should have at least 8 characters" */
function friendlyValidation(issue: any): string {
  const field = Array.isArray(issue?.loc) ? String(issue.loc[issue.loc.length - 1]) : ''
  const label = FIELD_LABEL[field] || '输入内容'
  const type = String(issue?.type || '')
  const ctx = issue?.ctx || {}
  if (type === 'string_too_short') return `${label}至少 ${ctx.min_length ?? 1} 位`
  if (type === 'string_too_long') return `${label}不能超过 ${ctx.max_length ?? 64} 位`
  if (type === 'missing') return `请填写${label}`
  if (type === 'string_type') return `${label}格式不正确`
  return issue?.msg ? `${label}${issue.msg}` : '提交的内容不合法'
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown } = {}
): Promise<T> {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) {
    // 托管平台的网关会用自己的 JWT 覆盖 Authorization 头，所以令牌走自定义头 X-Token；
    // Authorization 一并带上，方便本地直连或其它环境。
    headers['X-Token'] = token
    headers.Authorization = `Bearer ${token}`
  }
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(path, {
      method: options.method || 'GET',
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body)
    })
  } catch {
    throw new ApiError('网络连接失败，请检查网络后重试')
  }

  if (response.status === 401 && !path.startsWith('/api/login')) {
    clearToken()
    unauthorizedHandler?.()
    throw new ApiError('登录已失效，请重新登录', 401)
  }

  const text = await response.text()
  let data: any = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = { detail: text }
    }
  }

  if (!response.ok) {
    const detail = data?.detail
    let message = '请求失败，请稍后重试'
    if (typeof detail === 'string') message = detail
    else if (Array.isArray(detail) && detail[0]) message = friendlyValidation(detail[0])
    throw new ApiError(message, response.status)
  }

  return data as T
}

export interface LoginResult {
  token: string
  expiresAt: string
  user: User
}

export const api = {
  login: (username: string, password: string) =>
    request<LoginResult>('/api/login', { method: 'POST', body: { username, password } }),

  logout: () => request<{ ok: boolean }>('/api/logout', { method: 'POST' }),

  me: () => request<User>('/api/me'),

  changePassword: (oldPassword: string, newPassword: string) =>
    request<{ ok: boolean }>('/api/password', { method: 'POST', body: { oldPassword, newPassword } }),

  state: () => request<StateResponse>('/api/state'),
  learningSummary: () => request<LearningSummary>('/api/learning-summary'),

  categories: () => request<PlanCategoriesResponse>('/api/categories'),

  importCategories: (names: string[]) =>
    request<PlanCategoriesResponse>('/api/categories/import', { method: 'POST', body: { names } }),

  createCategory: (name: string) =>
    request<PlanCategory>('/api/categories', { method: 'POST', body: { name } }),

  renameCategory: (id: number, name: string) =>
    request<PlanCategory>(`/api/categories/${id}`, { method: 'PATCH', body: { name } }),

  deleteCategory: (id: number) =>
    request<{ ok: boolean }>(`/api/categories/${id}`, { method: 'DELETE' }),

  planTemplate: () => request<{ items: PlanItem[] }>('/api/plan/template'),
  planHistory: (before?: number) => request<{ versions: PlanVersion[]; nextBefore: number | null }>(
    before == null ? '/api/plan/history' : `/api/plan/history?before=${before}`
  ),
  planVersion: (id: number) => request<{ items: PlanItem[] }>(`/api/plan/history/${id}`),

  savePlan: (items: PlanItem[]) =>
    request<{ plan: PlanItem[] }>('/api/plan', {
      method: 'PUT',
      body: {
        items: items.map((item) => ({
          id: item.id,
          startTime: item.startTime || '',
          endTime: item.endTime || '',
          title: item.title,
          subject: item.subject,
          focusMin: item.focusMin,
          note: item.note || '',
          active: item.active
        }))
      }
    }),

  saveDay: (day: string, log: DayLog) =>
    request<DayLog>(`/api/day/${day}`, {
      method: 'PUT',
      body: {
        tasks: log.tasks,
        review: log.review,
        focusSec: log.focusSec,
        checkedIn: log.checkedIn
      }
    }),

  exportData: () => request<any>('/api/export'),

  adminUsers: () => request<{ users: User[] }>('/api/admin/users'),

  adminCreateUser: (payload: {
    username: string
    password: string
    displayName?: string
    mustChangePassword?: boolean
  }) => request<User>('/api/admin/users', { method: 'POST', body: payload }),

  adminPatchUser: (
    id: number,
    payload: { displayName?: string; status?: string; role?: string }
  ) => request<User>(`/api/admin/users/${id}`, { method: 'PATCH', body: payload }),

  adminResetPassword: (id: number, newPassword: string, mustChangePassword: boolean) =>
    request<{ ok: boolean }>(`/api/admin/users/${id}/password`, {
      method: 'POST',
      body: { newPassword, mustChangePassword }
    }),

  adminDeleteUser: (id: number) =>
    request<{ ok: boolean }>(`/api/admin/users/${id}`, { method: 'DELETE' }),

  adminOverview: (id: number) => request<OverviewResponse>(`/api/admin/users/${id}/overview`)
}
