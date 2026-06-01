/**
 * Vue composable that ties the CloudSyncManager lifecycle to route changes.
 *
 * - Starts the manager when a project route is active.
 * - Stops the manager when leaving project routes.
 */

import { onUnmounted, watch } from 'vue'
import type { RouteLocationNormalizedLoaded } from 'vue-router'
import { useRoute } from 'vue-router'

import { cloudSyncManager } from './cloudSyncManager'

export function useCloudSyncLifecycle(): void {
  let route: RouteLocationNormalizedLoaded | undefined
  try {
    route = useRoute()
  } catch {
    // No router context available — skip.
    return
  }

  if (!route?.params) {
    return
  }

  function getProjectId(): string | null {
    const id = route!.params.projectId
    return typeof id === 'string' ? id : null
  }

  function syncWithRoute(): void {
    const projectId = getProjectId()
    if (projectId) {
      cloudSyncManager.start(projectId)
    } else {
      cloudSyncManager.stop()
    }
  }

  // Start/stop on route changes
  watch(
    () => route!.params.projectId,
    () => {
      syncWithRoute()
    },
    { immediate: true },
  )

  // Cleanup on unmount
  onUnmounted(() => {
    cloudSyncManager.stop()
  })
}
