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
    <RouterView v-slot="{ Component, route }">
      <Transition name="route-view" mode="out-in">
        <div :key="route.path" class="route-stage">
          <component :is="Component" />
        </div>
      </Transition>
    </RouterView>
  </div>
</template>

<style scoped>
.app-root {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  --top-bar-clearance: calc(var(--banner-height, 0px) + 56px);
  --top-bar-width: 220px;
}

.route-stage {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.route-view-enter-active {
  transition:
    opacity var(--zs-duration-normal) var(--zs-ease-emphasized),
    transform var(--zs-duration-normal) var(--zs-ease-emphasized);
}

.route-view-leave-active {
  transition:
    opacity var(--zs-duration-fast) var(--zs-ease-standard),
    transform var(--zs-duration-fast) var(--zs-ease-standard);
}

.route-view-enter-from {
  opacity: 0;
  transform: translateY(5px);
}

.route-view-leave-to {
  opacity: 0;
  transform: translateY(-3px);
}

.app-top-bar {
  position: fixed;
  top: calc(var(--banner-height, 0px) + var(--zs-space-4));
  right: var(--zs-space-4);
  z-index: 90;
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  padding: 0;
  border: 0;
  background: transparent;
  transition: top var(--zs-duration-slow) var(--zs-ease-emphasized);
}

@media (max-width: 720px) {
  .app-top-bar {
    top: auto;
    bottom: var(--zs-space-4);
    right: var(--zs-space-4);
  }
}
</style>
