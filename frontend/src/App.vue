<script setup lang="ts">
import ThemeSwitcher from '@/shared/theme/ThemeSwitcher.vue'
</script>

<template>
  <ThemeSwitcher class="app-theme-switcher" />
  <RouterView />
</template>

<style scoped>
.app-theme-switcher {
  position: fixed;
  top: var(--zs-space-4);
  right: var(--zs-space-4);
  z-index: 90;
  padding: var(--zs-space-1);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
}

@media (max-width: 720px) {
  .app-theme-switcher {
    top: auto;
    bottom: var(--zs-space-4);
    right: var(--zs-space-4);
  }
}
</style>
