<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type { ChapterVersionListItem } from '@/entities/chapter-version/types'
import ChapterVersionPanel from '@/features/chapters/ChapterVersionPanel.vue'
import ChapterGraphCard from '@/features/graph/ChapterGraphCard.vue'
import ChapterContextSummary from '@/features/writing/ChapterContextSummary.vue'
import CreativeReminderPanel from '@/features/writing/CreativeReminderPanel.vue'
import ChapterTimelinePanel from '@/features/timeline/ChapterTimelinePanel.vue'

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

type AidTab =
  | 'overview'
  | 'outline'
  | 'characters'
  | 'settings'
  | 'graph'
  | 'timeline'
  | 'foreshadowing'
  | 'reminders'
  | 'versions'
type ContextKind =
  | 'overview'
  | 'outline'
  | 'characters'
  | 'settings'
  | 'graph'
  | 'timeline'
  | 'clues'
type LinkedContextKind = Exclude<ContextKind, 'overview'>

const activeTab = ref<AidTab>(
  isAidTab(props.initialActiveTab) ? props.initialActiveTab : 'overview',
)

const tabs: Array<{ id: AidTab; label: string }> = [
  { id: 'overview', label: '联动' },
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

watch(
  () => props.initialActiveTab,
  (tab) => {
    if (isAidTab(tab) && tab !== activeTab.value) {
      activeTab.value = tab
    }
  },
)

function setActiveTab(tab: AidTab) {
  activeTab.value = tab
  emit('activeTabChange', tab)
}

function selectLinkedContext(kind: LinkedContextKind) {
  setActiveTab(kind === 'clues' ? 'foreshadowing' : kind)
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
  return (
    value === 'overview' ||
    value === 'outline' ||
    value === 'characters' ||
    value === 'settings' ||
    value === 'graph' ||
    value === 'timeline' ||
    value === 'foreshadowing' ||
    value === 'reminders' ||
    value === 'versions'
  )
}
</script>

<template>
  <aside class="writing-aid-panel">
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

      <ChapterGraphCard
        v-else-if="activeTab === 'graph'"
        :project-id="projectId"
        :chapter-id="chapterId"
      />

      <ChapterTimelinePanel
        v-else-if="activeTab === 'timeline'"
        :project-id="projectId"
        :chapter-id="chapterId"
      />

      <ChapterContextSummary
        v-else
        :project-id="projectId"
        :chapter-id="chapterId"
        :kind="getContextKind(activeTab)!"
        @select-context="selectLinkedContext"
      />
    </section>
  </aside>
</template>

<style scoped>
.writing-aid-panel {
  display: grid;
  gap: var(--zs-space-2);
  min-height: 0;
  grid-template-rows: auto minmax(0, 1fr);
}

.state-message,
.status-message {
  margin: 0;
}

.tab-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  border-bottom: 1px solid var(--zs-color-border);
  padding: 0;
  margin: 0 calc(-1 * var(--zs-space-3));
}

.tab-list button {
  min-height: 34px;
  border: none;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  padding: 0 9px;
  background: transparent;
  color: var(--zs-color-text-muted);
  font: inherit;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition:
    color 0.15s,
    border-color 0.15s;
  margin-bottom: -1px;
}

.tab-list button:hover {
  color: var(--zs-color-text);
}

.tab-list button.active {
  color: var(--zs-color-primary);
  border-bottom-color: var(--zs-color-primary);
  font-weight: 700;
}

.tab-content {
  min-height: 0;
  overflow: auto;
  padding-top: var(--zs-space-2);
}

.state-message {
  border: 0;
  border-top: 1px solid var(--zs-color-border-soft);
  border-bottom: 1px solid var(--zs-color-border-soft);
  border-radius: 0;
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
