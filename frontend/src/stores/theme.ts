import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

export interface ThemeOption {
  id: string
  label: string
  swatch: string
}

export const THEMES: ThemeOption[] = [
  { id: 'mint', label: '淡绿渐变', swatch: 'linear-gradient(135deg,#e8f7ee,#c9ebd7)' },
  { id: 'sky', label: '淡蓝渐变', swatch: 'linear-gradient(135deg,#e9f2fd,#c6dcf7)' },
  { id: 'cream', label: '乳白', swatch: 'linear-gradient(135deg,#fdfaf2,#f0e6d2)' },
  { id: 'white', label: '纯白', swatch: 'linear-gradient(135deg,#ffffff,#eef1f6)' },
  { id: 'dark', label: '夜间', swatch: 'linear-gradient(135deg,#1b2530,#0e141b)' }
]

const STORAGE_KEY = 'study.theme'
const VALID = new Set([...THEMES.map((item) => item.id), 'auto'])

export const useThemeStore = defineStore('theme', () => {
  const saved = localStorage.getItem(STORAGE_KEY) || 'sky'
  const mode = ref(VALID.has(saved) ? saved : 'sky')
  const prefersDark = ref(window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false)

  const resolved = computed(() => (mode.value === 'auto' ? (prefersDark.value ? 'dark' : 'mint') : mode.value))
  const isDark = computed(() => resolved.value === 'dark')

  function apply() {
    document.documentElement.dataset.theme = resolved.value
    document.documentElement.classList.toggle('dark', isDark.value)
    const meta = document.querySelector('meta[name="theme-color"]')
    if (meta) {
      meta.setAttribute('content', isDark.value ? '#101b29' : resolved.value === 'sky' ? '#f5f9fe' : '#f5f9fe')
    }
  }

  function setMode(next: string) {
    mode.value = VALID.has(next) ? next : 'sky'
    localStorage.setItem(STORAGE_KEY, mode.value)
  }

  const media = window.matchMedia?.('(prefers-color-scheme: dark)')
  media?.addEventListener?.('change', (event) => {
    prefersDark.value = event.matches
  })

  watch(resolved, apply, { immediate: true })

  return { mode, resolved, isDark, themes: THEMES, setMode, apply }
})
