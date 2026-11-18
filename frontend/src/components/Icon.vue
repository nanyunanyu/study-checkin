<script setup lang="ts">
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Calendar,
  Check,
  CircleCheck,
  Close,
  DataAnalysis,
  Delete,
  Download,
  Key,
  List,
  Moon,
  Plus,
  Setting,
  Sunny,
  Timer,
  VideoPause,
  VideoPlay
} from '@element-plus/icons-vue'

withDefaults(defineProps<{ name: string; size?: number }>(), { size: 18 })

const icons: Record<string, unknown> = {
  today: Calendar,
  plan: List,
  stats: DataAnalysis,
  admin: CircleCheck,
  settings: Setting,
  play: VideoPlay,
  pause: VideoPause,
  close: Close,
  plus: Plus,
  up: ArrowUp,
  down: ArrowDown,
  trash: Delete,
  key: Key,
  timer: Timer,
  download: Download,
  check: Check,
  moon: Moon,
  sun: Sunny,
  left: ArrowLeft,
  right: ArrowRight
}
</script>

<template>
  <el-icon :size="size" aria-hidden="true"><component :is="icons[name] || CircleCheck" /></el-icon>
</template>
