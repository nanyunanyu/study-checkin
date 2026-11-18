export interface User {
  id: number
  username: string
  displayName: string
  role: 'superadmin' | 'user'
  status?: 'active' | 'disabled'
  mustChangePassword: boolean
  createdAt?: string
  lastLoginAt?: string | null
  todayCompletion?: number
  todayCheckedIn?: boolean
  streak?: number
  checkinDays?: number
  totalFocusSec?: number
}

export interface PlanItem {
  id: string
  sortOrder: number
  startTime: string
  endTime: string
  title: string
  subject: string
  /** null means derive the estimate from the current time range */
  focusMin: number | null
  note: string
  active: boolean
}

export interface PlanVersion {
  id: number
  replacedAt: string
  itemCount: number
}

export interface PlanCategory {
  id: number
  name: string
}

export interface PlanCategoriesResponse {
  presets: string[]
  custom: PlanCategory[]
}

export interface DayTask {
  id: string
  startTime: string
  endTime: string
  timeOverridden?: boolean
  title: string
  subject: string
  note: string
  done: boolean
  focusSec: number
}

export interface Review {
  best: string[]
  problems: string[]
  other: string
  priorities: string[]
  adjustment: string
}

export interface DayLog {
  day: string
  tasks: DayTask[]
  review: Review
  focusSec: number
  completion: number
  checkedIn: boolean
  updatedAt?: string
}

export interface StateResponse {
  user: Pick<User, 'id' | 'username' | 'displayName' | 'role' | 'mustChangePassword'>
  plan: PlanItem[]
  days: DayLog[]
}

export interface OverviewResponse {
  user: User
  stats: LearningSummary & { todayCompletion: number; todayCheckedIn: boolean }
  plan: PlanItem[]
  days: DayLog[]
  readonly: boolean
}

export interface LearningSummary {
  streak: number
  checkinDays: number
  totalFocusSec: number
}
