<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'

import ChapterCharacterPanel from '@/features/characters/ChapterCharacterPanel.vue'
import ChapterCluePanel from '@/features/clues/ChapterCluePanel.vue'
import ChapterGraphCard from '@/features/graph/ChapterGraphCard.vue'
import ChapterOutlinePanel from '@/features/outlines/ChapterOutlinePanel.vue'
import ChapterSettingPanel from '@/features/settings/ChapterSettingPanel.vue'
import ChapterTimelinePanel from '@/features/timeline/ChapterTimelinePanel.vue'
import ChapterVersionPanel from '@/features/chapters/ChapterVersionPanel.vue'
import type { ChapterVersionListItem } from '@/entities/chapter-version/types'

const props = defineProps<{
  projectId: string
  chapterId: string | null
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
}>()

type AidTab = 'outline' | 'characters' | 'settings' | 'graph' | 'timeline' | 'foreshadowing' | 'versions'

const activeTab = ref<AidTab>('outline')

const tabs: Array<{ id: AidTab; label: string }> = [
  { id: 'outline', label: '大纲' },
  { id: 'characters', label: '人物' },
  { id: 'settings', label: '设定' },
  { id: 'graph', label: '关系图' },
  { id: 'timeline', label: '时间轴' },
  { id: 'foreshadowing', label: '伏笔' },
  { id: 'versions', label: '版本' },
]

const manageAllLinks: Partial<Record<Exclude<AidTab, 'graph' | 'versions'>, string>> = {
  outline: `/projects/${props.projectId}/outlines`,
  characters: `/projects/${props.projectId}/characters`,
  settings: `/projects/${props.projectId}/settings`,
  timeline: `/projects/${props.projectId}/timeline`,
  foreshadowing: `/projects/${props.projectId}/clues`,
}

const manageAllLink = computed(() => {
  if (activeTab.value === 'graph' || activeTab.value === 'versions') {
    return ''
  }
  return manageAllLinks[activeTab.value] ?? ''
})

const showManageAllLink = computed(() => manageAllLink.value !== '' && activeTab.value !== 'timeline')

const versionsTabMessage = computed(() => {
  if (props.versionMessage) {
    return props.versionMessage
  }
  return ''
})
</script>

<template>
  <aside class="writing-aid-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">写作资料与辅助</p>
        <h2>资料面板</h2>
      </div>
    </header>

    <nav class="tab-list" aria-label="写作资料分类">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </nav>

    <section class="tab-content">
      <template v-if="activeTab === 'outline'">
        <p v-if="!chapterId" class="state-message">请选择章节后查看写作资料。</p>
        <ChapterOutlinePanel
          v-else
          :project-id="projectId"
          :chapter-id="chapterId"
          compact
        />
      </template>

      <ChapterCharacterPanel
        v-else-if="activeTab === 'characters'"
        :project-id="projectId"
        :chapter-id="chapterId"
      />

      <ChapterSettingPanel
        v-else-if="activeTab === 'settings'"
        :project-id="projectId"
        :chapter-id="chapterId"
      />

      <ChapterTimelinePanel
        v-else-if="activeTab === 'timeline'"
        :project-id="projectId"
        :chapter-id="chapterId"
      />

      <ChapterCluePanel
        v-else-if="activeTab === 'foreshadowing'"
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
    </section>

    <footer v-if="showManageAllLink" class="panel-footer">
      <RouterLink class="manage-link" :to="manageAllLink">管理全部</RouterLink>
    </footer>
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

.panel-header {
  display: grid;
  gap: 10px;
}

.eyebrow,
h2,
.state-message,
.status-message {
  margin: 0;
}

.eyebrow {
  color: #64748b;
  font-size: 0.75rem;
  font-weight: 800;
}

h2 {
  color: #111827;
  font-size: 1.05rem;
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

.panel-footer {
  display: flex;
  justify-content: flex-end;
}

.manage-link {
  color: #2563eb;
  font-size: 0.82rem;
  font-weight: 800;
  text-decoration: none;
}

.graph-link {
  justify-self: end;
}
</style>
