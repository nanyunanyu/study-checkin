<script setup lang="ts">
import { useToastStore } from '../stores/toast'

const toast = useToastStore()
</script>

<template>
  <div class="toast-stack">
    <div v-for="item in toast.items" :key="item.id" class="toast" :class="item.kind">
      {{ item.text }}
    </div>
  </div>
</template>
