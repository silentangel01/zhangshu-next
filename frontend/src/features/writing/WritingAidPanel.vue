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
  { id: 'graph', label: '关系图' },
  { id: 'timeline', label: '时间轴' },
  { id: 'foreshadowing', label: '伏笔' },
  { id: 'reminders', label: '创作提醒' },
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
  gap: 14px;
  min-height: 0;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 16px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgb(20 24 31 / 6%);
}

.state-message,
.status-message {
  margin: 0;
}

.tab-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tab-list button {
  min-height: 32px;
  border: 1px solid #d8dee9;
  border-radius: 999px;
  padding: 0 10px;
  background: #fbfcfe;
  color: #374151;
  font: inherit;
  font-size: 0.85rem;
  font-weight: 800;
  cursor: pointer;
}

.tab-list button.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

.tab-content {
  min-height: 0;
  overflow: auto;
}

.state-message {
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 14px;
  color: #64748b;
  line-height: 1.6;
  text-align: center;
}

.status-message {
  margin-bottom: 10px;
  color: #0f172a;
  font-size: 0.9rem;
  font-weight: 700;
}
</style>
