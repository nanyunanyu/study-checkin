<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useThemeStore } from '../stores/theme'
import Icon from './Icon.vue'

withDefaults(defineProps<{ compact?: boolean }>(), { compact: false })

const theme = useThemeStore()
const open = ref(false)
const root = ref<HTMLElement | null>(null)
const options = computed(() => [
  ...theme.themes,
  { id: 'auto', label: '跟随系统', swatch: 'conic-gradient(#e8f7ee 0 25%,#e9f2fd 0 50%,#fdfaf2 0 75%,#1b2530 0)' }
])
const selected = computed(() => options.value.find((option) => option.id === theme.mode) || options.value[0])

function closeOnOutside(event: MouseEvent) {
  if (root.value && !root.value.contains(event.target as Node)) open.value = false
}

function closeOnEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') open.value = false
}

function select(id: string) {
  theme.setMode(id)
  open.value = false
}

onMounted(() => {
  document.addEventListener('click', closeOnOutside)
  document.addEventListener('keydown', closeOnEscape)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeOnOutside)
  document.removeEventListener('keydown', closeOnEscape)
})
</script>

<template>
  <div ref="root" class="theme-picker" :class="{ compact }">
    <button
      class="theme-trigger"
      type="button"
      :aria-label="`界面配色：${selected.label}`"
      :title="`当前配色：${selected.label}`"
      :aria-expanded="open"
      aria-haspopup="listbox"
      @click="open = !open"
    >
      <svg v-if="compact" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M8 4 3 7l2 5 3-1v9h8v-9l3 1 2-5-5-3a4 4 0 0 1-8 0Z" />
      </svg>
      <span v-if="!compact" class="theme-preview-swatch" :style="{ background: selected.swatch }" />
      <span v-if="!compact" class="theme-trigger-copy">
        <span class="theme-trigger-label">{{ selected.label }}</span>
        <span v-if="!compact" class="theme-trigger-hint">当前配色 · 已实时应用</span>
      </span>
      <Icon v-if="!compact" :name="open ? 'up' : 'down'" :size="15" />
    </button>

    <div v-if="open" class="theme-options" role="listbox" aria-label="选择配色方案">
      <button
        v-for="option in options"
        :key="option.id"
        class="theme-option"
        :class="{ active: theme.mode === option.id }"
        type="button"
        role="option"
        :aria-selected="theme.mode === option.id"
        @click="select(option.id)"
      >
        <span class="theme-option-swatch" :style="{ background: option.swatch }" />
        <span>{{ option.label }}</span>
        <Icon v-if="theme.mode === option.id" name="check" :size="15" />
      </button>
    </div>

    <div v-if="!compact" class="theme-live-preview" aria-live="polite">
      <div class="preview-window">
        <span class="preview-dot" />
        <span class="preview-line" />
        <span class="preview-accent" />
      </div>
      <span class="hint">页面效果预览</span>
    </div>
  </div>
</template>

<style scoped>
.theme-picker {
  position: relative;
  width: min(100%, 390px);
}

.theme-picker.compact {
  width: auto;
}

.theme-picker.compact .theme-trigger {
  width: 36px;
  height: 36px;
  min-height: 36px;
  justify-content: center;
  padding: 0;
  border-radius: 8px;
}

.theme-trigger {
  width: 100%;
  min-height: 56px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 9px 12px;
  text-align: left;
  color: var(--text);
  background: var(--surface-solid);
  border: 1px solid var(--border-strong);
  border-radius: 14px;
}

.theme-trigger:hover,
.theme-trigger:focus-visible {
  border-color: var(--accent);
  outline: none;
}

.theme-preview-swatch,
.theme-option-swatch {
  flex: none;
  border: 1px solid var(--border-strong);
  border-radius: 10px;
}

.theme-preview-swatch {
  width: 36px;
  height: 36px;
}

.theme-trigger-copy {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  gap: 1px;
}

.theme-trigger-label {
  font-size: 13px;
  font-weight: 600;
}

.theme-trigger-hint {
  color: var(--text-3);
  font-size: 11px;
}

.theme-options {
  position: absolute;
  z-index: 40;
  top: calc(100% + 7px);
  left: 0;
  right: 0;
  display: grid;
  gap: 4px;
  padding: 7px;
  background: var(--surface-solid);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: var(--shadow);
}

.theme-picker.compact .theme-options {
  right: 0;
  left: auto;
  width: 205px;
}

.theme-option {
  min-height: 44px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 9px;
  border-radius: 10px;
  text-align: left;
  color: var(--text-2);
  font-size: 13px;
}

.theme-option:hover,
.theme-option.active {
  background: var(--accent-soft);
  color: var(--accent-text);
}

.theme-option-swatch {
  width: 26px;
  height: 26px;
}

.theme-option :deep(svg) {
  margin-left: auto;
}

.theme-live-preview {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: 12px;
}

.preview-window {
  width: 74px;
  height: 36px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px;
  background: var(--surface-solid);
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  box-shadow: var(--shadow-soft);
}

.preview-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
}

.preview-line {
  width: 22px;
  height: 5px;
  border-radius: 5px;
  background: var(--surface-3);
}

.preview-accent {
  width: 13px;
  height: 13px;
  margin-left: auto;
  border-radius: 4px;
  background: var(--accent-soft);
  border: 1px solid var(--accent);
}

@media (max-width: 560px) {
  .theme-picker:not(.compact) {
    width: 100%;
  }

  .theme-picker:not(.compact) .theme-options {
    position: static;
    margin-top: 7px;
  }
}
</style>
