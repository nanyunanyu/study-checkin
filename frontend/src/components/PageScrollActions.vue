<script setup lang="ts">
import { Bottom, Top } from '@element-plus/icons-vue'

function jump(toBottom: boolean) {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  window.scrollTo({
    top: toBottom ? document.scrollingElement?.scrollHeight ?? 0 : 0,
    behavior: reducedMotion ? 'instant' : 'smooth'
  })
}
</script>

<template>
  <div class="page-scroll-actions" role="group" aria-label="页面滚动">
    <button type="button" aria-label="回到顶部" title="回到顶部" @click="jump(false)"><el-icon :size="17" aria-hidden="true"><Top /></el-icon></button>
    <button type="button" aria-label="跳转底部" title="跳转底部" @click="jump(true)"><el-icon :size="17" aria-hidden="true"><Bottom /></el-icon></button>
  </div>
</template>

<style scoped>
.page-scroll-actions {
  position: fixed;
  z-index: 79;
  left: 16px;
  bottom: 133px;
  display: flex;
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  background: var(--surface-solid);
  box-shadow: 0 8px 20px -12px rgba(35, 70, 105, .45);
}
.page-scroll-actions button {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  padding: 0;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--text-2);
  cursor: pointer;
}
.page-scroll-actions button:hover { color: var(--accent-text); background: var(--accent-soft); }
@media (min-width: 821px) and (max-width: 1040px) {
  .page-scroll-actions { left: 18px; bottom: 72px; flex-direction: column; }
}
@media (max-width: 820px) {
  .page-scroll-actions { left: 12px; bottom: max(78px, calc(env(safe-area-inset-bottom) + 68px)); }
  .page-scroll-actions button { width: 42px; }
}
</style>
