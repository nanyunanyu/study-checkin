import { defineStore } from 'pinia'
import { ref } from 'vue'
import { router } from '../router'

export const useUiStore = defineStore('ui', () => {
  const focusDate = ref<string | null>(null)

  function openDay(day: string) {
    focusDate.value = day
    void router.push({ name: 'today' })
  }

  return { focusDate, openDay }
})
