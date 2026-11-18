<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ value: number; size?: number }>(), { size: 74 })

const radius = computed(() => (props.size - 8) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const offset = computed(() => circumference.value * (1 - Math.min(100, Math.max(0, props.value)) / 100))
const text = computed(() => `${Math.round(props.value)}%`)
</script>

<template>
  <div class="ring" :style="{ width: size + 'px', height: size + 'px' }">
    <svg :width="size" :height="size">
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        fill="none"
        stroke="var(--border)"
        :stroke-width="5"
      />
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        fill="none"
        stroke="var(--accent)"
        :stroke-width="5"
        stroke-linecap="round"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="offset"
        style="transition: stroke-dashoffset 0.45s ease"
      />
    </svg>
    <div class="ring-label">{{ text }}</div>
  </div>
</template>
