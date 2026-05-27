<script setup lang="ts">
const version = import.meta.env.VITE_APP_VERSION
  || (typeof __ZHANGSHU_APP_VERSION__ !== 'undefined' ? __ZHANGSHU_APP_VERSION__ : 'dev')
</script>

<template>
  <div class="version-panel">
    <span class="version-label">软件版本</span>
    <span class="version-value">v{{ version }}</span>
  </div>
</template>

<style scoped>
.version-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--zs-space-3) var(--zs-space-4);
  background: var(--zs-color-surface-soft);
  border-radius: var(--zs-radius-sm);
}

.version-label {
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
}

.version-value {
  font-weight: 600;
  font-size: 0.9rem;
  font-family: monospace;
}
</style>
