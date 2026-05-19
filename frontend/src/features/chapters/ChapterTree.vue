<script setup lang="ts">
import { computed } from 'vue'

import type { Chapter, ChapterStatus } from '@/entities/chapter/types'
import type { Volume } from '@/entities/volume/types'

const props = defineProps<{
  volumes: Volume[]
  chapters: Chapter[]
  selectedChapterId: string | null
}>()

const emit = defineEmits<{
  selectChapter: [chapter: Chapter]
  editVolume: [volume: Volume]
  deleteVolume: [volume: Volume]
  editChapter: [chapter: Chapter]
  deleteChapter: [chapter: Chapter]
}>()

const sortedVolumes = computed(() =>
  [...props.volumes].sort((left, right) => {
    if (left.order_index !== right.order_index) {
      return left.order_index - right.order_index
    }

    return new Date(left.created_at).getTime() - new Date(right.created_at).getTime()
  }),
)

const activeVolumeIds = computed(() => new Set(props.volumes.map((volume) => volume.id)))

const unassignedChapters = computed(() =>
  sortChapters(
    props.chapters.filter(
      (chapter) => !chapter.volume_id || !activeVolumeIds.value.has(chapter.volume_id),
    ),
  ),
)

function chaptersForVolume(volumeId: string): Chapter[] {
  return sortChapters(props.chapters.filter((chapter) => chapter.volume_id === volumeId))
}

function sortChapters(chapters: Chapter[]): Chapter[] {
  return [...chapters].sort((left, right) => {
    if (left.order_index !== right.order_index) {
      return left.order_index - right.order_index
    }

    return new Date(left.created_at).getTime() - new Date(right.created_at).getTime()
  })
}

function getStatusLabel(status: ChapterStatus): string {
  const labels: Record<ChapterStatus, string> = {
    draft: '草稿',
    writing: '写作中',
    revised: '已修订',
    completed: '已完成',
  }

  return labels[status]
}
</script>

<template>
  <nav class="chapter-tree" aria-label="章节树">
    <section v-for="volume in sortedVolumes" :key="volume.id" class="tree-section">
      <header class="tree-section-header">
        <div>
          <h3>{{ volume.title }}</h3>
          <span>排序 {{ volume.order_index }}</span>
        </div>
        <div class="tree-actions">
          <button type="button" @click="emit('editVolume', volume)">编辑</button>
          <button class="danger-action" type="button" @click="emit('deleteVolume', volume)">删除</button>
        </div>
      </header>

      <ul v-if="chaptersForVolume(volume.id).length" class="chapter-list">
        <li v-for="chapter in chaptersForVolume(volume.id)" :key="chapter.id">
          <button
            class="chapter-button"
            :class="{ selected: chapter.id === selectedChapterId }"
            type="button"
            @click="emit('selectChapter', chapter)"
          >
            <span>{{ chapter.title }}</span>
            <small>{{ getStatusLabel(chapter.status) }} - v{{ chapter.version }}</small>
          </button>
          <div class="chapter-actions">
            <button type="button" @click="emit('editChapter', chapter)">编辑信息</button>
            <button class="danger-action" type="button" @click="emit('deleteChapter', chapter)">
              删除
            </button>
          </div>
        </li>
      </ul>

      <p v-else class="empty-note">此分卷暂无章节。</p>
    </section>

    <section class="tree-section">
      <header class="tree-section-header">
        <div>
          <h3>未分卷章节</h3>
          <span>{{ unassignedChapters.length }} 个章节</span>
        </div>
      </header>

      <ul v-if="unassignedChapters.length" class="chapter-list">
        <li v-for="chapter in unassignedChapters" :key="chapter.id">
          <button
            class="chapter-button"
            :class="{ selected: chapter.id === selectedChapterId }"
            type="button"
            @click="emit('selectChapter', chapter)"
          >
            <span>{{ chapter.title }}</span>
            <small>{{ getStatusLabel(chapter.status) }} - v{{ chapter.version }}</small>
          </button>
          <div class="chapter-actions">
            <button type="button" @click="emit('editChapter', chapter)">编辑信息</button>
            <button class="danger-action" type="button" @click="emit('deleteChapter', chapter)">
              删除
            </button>
          </div>
        </li>
      </ul>

      <p v-else class="empty-note">暂无未分卷章节。</p>
    </section>
  </nav>
</template>

<style scoped>
.chapter-tree {
  display: grid;
  gap: 14px;
}

.tree-section {
  border: 1px solid #d8dee9;
  border-radius: 8px;
  background: #ffffff;
}

.tree-section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 14px;
  border-bottom: 1px solid #edf0f5;
}

h3 {
  margin: 0 0 4px;
  color: #111827;
  font-size: 0.98rem;
}

.tree-section-header span,
.empty-note,
small {
  color: #64748b;
  font-size: 0.82rem;
}

.tree-actions,
.chapter-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chapter-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 12px;
  list-style: none;
}

.chapter-list li {
  display: grid;
  gap: 6px;
}

.chapter-button {
  display: grid;
  gap: 4px;
  width: 100%;
  min-height: 46px;
  border: 1px solid #d8dee9;
  border-radius: 6px;
  padding: 9px 10px;
  background: #ffffff;
  color: #111827;
  text-align: left;
}

.chapter-button.selected {
  border-color: #2563eb;
  background: #eff6ff;
}

button {
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  background: #ffffff;
  color: #374151;
  font: inherit;
  font-size: 0.78rem;
  font-weight: 800;
  cursor: pointer;
}

.tree-actions button,
.chapter-actions button {
  min-height: 28px;
  padding: 0 8px;
}

.danger-action {
  border-color: #fecaca;
  color: #b42318;
}

.empty-note {
  margin: 0;
  padding: 12px 14px;
}
</style>
