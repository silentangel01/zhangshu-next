<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { ChapterVersionListItem } from '@/entities/chapter-version/types'
import ChapterVersionPanel from '@/features/chapters/ChapterVersionPanel.vue'
import ChapterContextSummary from '@/features/writing/ChapterContextSummary.vue'
import CreativeReminderPanel from '@/features/writing/CreativeReminderPanel.vue'

const props = defineProps<{
  projectId: string
  chapterId: string | null
  initialActiveTab: AidTab | null
  versions: ChapterVersionListItem[]
  versionErrorMessage: string
  versionMessage: string
  versionIsLoading: boolean
  versionIsBusy: boolean
}>()

const emit = defineEmits<{
  createSnapshot: []
  viewVersion: [versionId: string]
  restoreVersion: [versionId: string]
  activeTabChange: [tab: AidTab]
}>()

type AidTab = 'outline' | 'characters' | 'settings' | 'graph' | 'timeline' | 'foreshadowing' | 'reminders' | 'versions'
type ContextKind = 'outline' | 'characters' | 'settings' | 'graph' | 'timeline' | 'clues'

const activeTab = ref<AidTab>(isAidTab(props.initialActiveTab) ? props.initialActiveTab : 'outline')

const tabs: Array<{ id: AidTab; label: string }> = [
  { id: 'outline', label: '大纲' },
  { id: 'characters', label: '人物' },
  { id: 'settings', label: '设定' },
  { id: 'graph', label: '关系' },
  { id: 'timeline', label: '时间' },
  { id: 'foreshadowing', label: '伏笔' },
  { id: 'reminders', label: '提醒' },
  { id: 'versions', label: '版本' },
]

const versionsTabMessage = computed(() => props.versionMessage || '')

watch(() => props.initialActiveTab, (tab) => {
  if (isAidTab(tab) && tab !== activeTab.value) {
    activeTab.value = tab
  }
})

function setActiveTab(tab: AidTab) {
  activeTab.value = tab
  emit('activeTabChange', tab)
}

function getContextKind(tab: AidTab): ContextKind | null {
  if (tab === 'versions' || tab === 'reminders') {
    return null
  }
  if (tab === 'foreshadowing') {
    return 'clues'
  }
  return tab
}

function isAidTab(value: unknown): value is AidTab {
  return value === 'outline'
    || value === 'characters'
    || value === 'settings'
    || value === 'graph'
    || value === 'timeline'
    || value === 'foreshadowing'
    || value === 'reminders'
    || value === 'versions'
}
</script>

<template>
  <aside class="writing-aid-panel">
    <h3 class="panel-title">写作资料</h3>
    <nav class="tab-list" aria-label="写作资料分类">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        :class="{ active: activeTab === tab.id }"
        @click="setActiveTab(tab.id)"
      >
        {{ tab.label }}
      </button>
    </nav>

    <section class="tab-content">
      <CreativeReminderPanel
        v-if="activeTab === 'reminders'"
        :project-id="projectId"
        :chapter-id="chapterId"
      />

      <section v-else-if="activeTab === 'versions'" class="versions-tab">
        <p v-if="!chapterId" class="state-message">请选择章节后查看版本历史。</p>
        <template v-else>
          <p v-if="versionsTabMessage" class="status-message">{{ versionsTabMessage }}</p>
          <ChapterVersionPanel
            :versions="versions"
            :is-loading="versionIsLoading"
            :error-message="versionErrorMessage"
            :is-busy="versionIsBusy"
            @create-snapshot="emit('createSnapshot')"
            @view-version="emit('viewVersion', $event)"
            @restore-version="emit('restoreVersion', $event)"
          />
        </template>
      </section>

      <ChapterContextSummary
        v-else
        :project-id="projectId"
        :chapter-id="chapterId"
        :kind="getContextKind(activeTab)!"
      />
    </section>
  </aside>
</template>

<style scoped>
.writing-aid-panel {
  display: grid;
  gap: var(--zs-space-2);
  min-height: 0;
}

.panel-title {
  margin: 0;
  color: var(--zs-color-text-faint);
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.state-message,
.status-message {
  margin: 0;
}

.tab-list {
  display: flex;
  flex-wrap: wrap;
  gap: 1px;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  overflow: hidden;
  background: var(--zs-color-border-soft);
}

.tab-list button {
  min-height: 28px;
  border: none;
  border-radius: 0;
  padding: 0 var(--zs-space-2);
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  font: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}

.tab-list button:hover {
  color: var(--zs-color-text);
  background: var(--zs-color-surface-soft);
}

.tab-list button.active {
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-primary);
}

.tab-content {
  min-height: 0;
  overflow: auto;
}

.state-message {
  border: 1px dashed var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-3);
  color: var(--zs-color-text-muted);
  font-size: 0.86rem;
  line-height: 1.6;
  text-align: center;
}

.status-message {
  margin-bottom: 10px;
  color: var(--zs-color-text);
  font-size: 0.9rem;
  font-weight: 700;
}
</style>
