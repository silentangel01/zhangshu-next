<script setup lang="ts">
import GlobalAnnouncementBanner from '@/features/announcements/GlobalAnnouncementBanner.vue'
import NotificationBell from '@/features/announcements/NotificationBell.vue'
import FeedbackEntryButton from '@/features/feedback/FeedbackEntryButton.vue'
import ThemeSwitcher from '@/shared/theme/ThemeSwitcher.vue'
import { useCloudSyncLifecycle } from '@/features/cloud/useCloudSyncLifecycle'

useCloudSyncLifecycle()
</script>

<template>
  <div class="app-root">
    <GlobalAnnouncementBanner />
    <div class="app-top-bar">
      <NotificationBell />
      <ThemeSwitcher />
    </div>
    <FeedbackEntryButton />
    <RouterView />
  </div>
</template>

<style scoped>
.app-root {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  --top-bar-clearance: calc(var(--banner-height, 0px) + 64px);
}

.app-top-bar {
  position: fixed;
  top: calc(var(--banner-height, 0px) + var(--zs-space-4));
  right: var(--zs-space-4);
  z-index: 90;
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  padding: var(--zs-space-1);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
  transition: top 0.3s ease;
}

@media (max-width: 720px) {
  .app-top-bar {
    top: auto;
    bottom: var(--zs-space-4);
    right: var(--zs-space-4);
  }
}
</style>
