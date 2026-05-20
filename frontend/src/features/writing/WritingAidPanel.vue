<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'

import ChapterCharacterPanel from '@/features/characters/ChapterCharacterPanel.vue'
import ChapterOutlinePanel from '@/features/outlines/ChapterOutlinePanel.vue'

const props = defineProps<{
  projectId: string
  chapterId: string | null
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

const placeholders: Record<Exclude<AidTab, 'outline' | 'characters'>, string> = {
  settings: '设定集模块将在后续版本实现',
  graph: '关系图模块将在后续版本实现',
  timeline: '时间轴模块将在后续版本实现',
  foreshadowing: '伏笔模块将在后续版本实现',
  versions: '版本历史仍在正文编辑区下方查看，后续会整理到这里。',
}

const placeholderText = computed(() => {
  if (activeTab.value === 'outline' || activeTab.value === 'characters') {
    return ''
  }
  return placeholders[activeTab.value]
})
</script>

<template>
  <aside class="writing-aid-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">写作资料与辅助</p>
        <h2>资料面板</h2>
      </div>
      <RouterLink class="outline-link" :to="`/projects/${projectId}/outlines`">打开完整大纲</RouterLink>
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
        <p v-if="!props.chapterId" class="state-message">请选择章节后查看写作辅助资料。</p>
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

      <p v-else class="state-message">{{ placeholderText }}</p>
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

.panel-header {
  display: grid;
  gap: 10px;
}

.eyebrow,
h2,
.state-message {
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

.outline-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 0 10px;
  background: #ffffff;
  color: #2563eb;
  font-size: 0.86rem;
  font-weight: 800;
  text-decoration: none;
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
</style>
