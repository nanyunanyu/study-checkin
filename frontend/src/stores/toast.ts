import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ToastItem {
  id: number
  text: string
  kind: 'info' | 'ok' | 'err'
}

let seq = 0

export const useToastStore = defineStore('toast', () => {
  const items = ref<ToastItem[]>([])

  function push(text: string, kind: ToastItem['kind'] = 'info', duration = 2600) {
    const id = ++seq
    items.value = [...items.value, { id, text, kind }]
    window.setTimeout(() => {
      items.value = items.value.filter((item) => item.id !== id)
    }, duration)
  }

  return { items, push }
})
