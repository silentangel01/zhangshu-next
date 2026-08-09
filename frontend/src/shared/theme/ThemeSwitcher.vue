<script setup lang="ts">
import { ref, onMounted } from 'vue'

import { type AppTheme, applyAppTheme, readAppTheme, writeAppTheme } from './appTheme'

const THEME_OPTIONS: { value: AppTheme; label: string }[] = [
  { value: 'default', label: '默认' },
  { value: 'eye-care', label: '护眼' },
  { value: 'dark', label: '黑夜' },
]

const currentTheme = ref<AppTheme>('default')

onMounted(() => {
  currentTheme.value = readAppTheme()
})

function selectTheme(theme: AppTheme) {
  currentTheme.value = theme
  applyAppTheme(theme)
  writeAppTheme(theme)
}
</script>

<template>
  <div class="theme-switcher" role="group" aria-label="全局主题">
    <button
      v-for="option in THEME_OPTIONS"
      :key="option.value"
      type="button"
      class="theme-option"
      :class="{ active: currentTheme === option.value }"
      :aria-pressed="currentTheme === option.value"
      @click="selectTheme(option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.theme-switcher {
  display: inline-flex;
  gap: 0;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface);
  overflow: hidden;
}

.theme-option {
  min-height: 28px;
  border: none;
  border-right: 1px solid var(--zs-color-border-soft);
  border-radius: 0;
  padding: 0 10px;
  background: transparent;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    background var(--zs-duration-fast) var(--zs-ease-standard),
    color var(--zs-duration-fast) var(--zs-ease-standard);
}

.theme-option:last-child {
  border-right: 0;
}

.theme-option:hover {
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-text);
}

.theme-option.active {
  background: var(--zs-color-surface);
  color: var(--zs-color-primary);
  box-shadow: inset 0 -2px 0 var(--zs-color-primary);
}

.theme-option:focus-visible {
  outline: none;
  box-shadow: var(--zs-shadow-focus);
}
</style>
