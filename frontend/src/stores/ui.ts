import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ViewName = 'today' | 'plan' | 'stats' | 'admin' | 'settings'

export const useUiStore = defineStore('ui', () => {
  const view = ref<ViewName>('today')
  const focusDate = ref<string | null>(null)

  function openDay(day: string) {
    focusDate.value = day
    go('today')
  }

  function go(next: ViewName) {
    view.value = next
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
  }

  return { view, focusDate, openDay, go }
})
