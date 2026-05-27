<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  hint?: string
}>()
</script>

<template>
  <div class="stat-tile">
    <div class="stat-label">{{ label }}</div>
    <div class="stat-value">{{ value }}</div>
    <div v-if="hint" class="stat-hint">{{ hint }}</div>
  </div>
</template>

<style scoped>
.stat-tile {
  background: var(--ca-surface);
  border: 1px solid var(--ca-border);
  border-radius: var(--ca-radius);
  padding: var(--ca-space-4) var(--ca-space-5);
  box-shadow: var(--ca-shadow);
}
.stat-label {
  font-size: 12px;
  color: var(--ca-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--ca-space-1);
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
}
.stat-hint {
  font-size: 12px;
  color: var(--ca-text-muted);
  margin-top: var(--ca-space-1);
}
</style>
