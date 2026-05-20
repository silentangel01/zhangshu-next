<script setup lang="ts">
import { computed, ref } from 'vue'

import type { Chapter } from '@/entities/chapter/types'
import type { Volume } from '@/entities/volume/types'
import ContextMenu, { type ContextMenuItem } from '@/shared/ui/ContextMenu.vue'

const props = defineProps<{
  projectTitle: string
  volumes: Volume[]
  chapters: Chapter[]
  selectedChapterId: string | null
}>()

const emit = defineEmits<{
  selectChapter: [chapter: Chapter]
  createVolume: []
  createChapter: [volumeId: string | null]
  editVolume: [volume: Volume]
  deleteVolume: [volume: Volume]
  editChapter: [chapter: Chapter]
  deleteChapter: [chapter: Chapter]
}>()

type TreeMenuContext =
  | { target: 'root' }
  | { target: 'unassigned' }
  | { target: 'volume'; volume: Volume }
  | { target: 'chapter'; chapter: Chapter }

const contextMenu = ref<{
  visible: boolean
  x: number
  y: number
  context: TreeMenuContext
} | null>(null)

const expandedVolumeIds = ref<Record<string, boolean>>({})
const unassignedExpanded = ref(true)

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

function isVolumeExpanded(volumeId: string) {
  return expandedVolumeIds.value[volumeId] ?? true
}

function toggleVolume(volumeId: string) {
  expandedVolumeIds.value = {
    ...expandedVolumeIds.value,
    [volumeId]: !isVolumeExpanded(volumeId),
  }
}

function toggleUnassigned() {
  unassignedExpanded.value = !unassignedExpanded.value
}

function openRootMenu(event: MouseEvent) {
  openContextMenu(event, { target: 'root' })
}

function openUnassignedMenu(event: MouseEvent) {
  openContextMenu(event, { target: 'unassigned' })
}

function openVolumeMenu(event: MouseEvent, volume: Volume) {
  openContextMenu(event, { target: 'volume', volume })
}

function openChapterMenu(event: MouseEvent, chapter: Chapter) {
  openContextMenu(event, { target: 'chapter', chapter })
}

function openContextMenu(event: MouseEvent, context: TreeMenuContext) {
  event.preventDefault()
  event.stopPropagation()

  contextMenu.value = {
    visible: true,
    x: event.clientX + 2,
    y: event.clientY + 2,
    context,
  }
}

const menuItems = computed<ContextMenuItem[]>(() => {
  if (!contextMenu.value) {
    return []
  }

  switch (contextMenu.value.context.target) {
    case 'root':
      return [
        { id: 'create-volume', label: '新建分卷' },
        { id: 'create-chapter', label: '新建未分卷章节' },
      ]
    case 'unassigned':
      return [{ id: 'create-chapter', label: '新建章节' }]
    case 'volume':
      return [
        { id: 'create-chapter', label: '新建章节' },
        { id: 'edit-volume', label: '编辑分卷' },
        { id: 'delete-volume', label: '删除分卷', danger: true },
      ]
    case 'chapter':
      return [
        { id: 'edit-chapter', label: '编辑章节信息' },
        { id: 'delete-chapter', label: '删除章节', danger: true },
      ]
  }
})

function handleMenuSelect(item: ContextMenuItem) {
  if (!contextMenu.value) {
    return
  }

  const target = contextMenu.value.context

  switch (target.target) {
    case 'root':
      if (item.id === 'create-volume') {
        emit('createVolume')
      } else if (item.id === 'create-chapter') {
        emit('createChapter', null)
      }
      break
    case 'unassigned':
      if (item.id === 'create-chapter') {
        emit('createChapter', null)
      }
      break
    case 'volume':
      if (item.id === 'create-chapter') {
        emit('createChapter', target.volume.id)
      } else if (item.id === 'edit-volume') {
        emit('editVolume', target.volume)
      } else if (item.id === 'delete-volume') {
        emit('deleteVolume', target.volume)
      }
      break
    case 'chapter':
      if (item.id === 'edit-chapter') {
        emit('editChapter', target.chapter)
      } else if (item.id === 'delete-chapter') {
        emit('deleteChapter', target.chapter)
      }
      break
  }
}

function closeMenu() {
  contextMenu.value = null
}
</script>

<template>
  <nav class="chapter-tree" aria-label="章节树" @contextmenu.prevent="openRootMenu">
    <div class="tree-root">
      <div class="tree-row root-row">
        <span class="tree-label">{{ projectTitle }}</span>
      </div>

      <button
        type="button"
        class="tree-row create-row"
        @click="emit('createVolume')"
        @contextmenu.stop.prevent="openRootMenu"
      >
        + 新建分卷
      </button>
    </div>

    <section v-for="volume in sortedVolumes" :key="volume.id" class="tree-group">
      <button
        type="button"
        class="tree-row volume-row"
        :class="{ expanded: isVolumeExpanded(volume.id) }"
        @click="toggleVolume(volume.id)"
        @contextmenu.stop.prevent="openVolumeMenu($event, volume)"
      >
        <span class="disclosure">{{ isVolumeExpanded(volume.id) ? '▾' : '▸' }}</span>
        <span class="tree-label">{{ volume.title }}</span>
      </button>

      <button
        type="button"
        class="tree-row create-row child-row"
        @click="emit('createChapter', volume.id)"
        @contextmenu.stop.prevent="openVolumeMenu($event, volume)"
      >
        + 新建章节
      </button>

      <div v-if="isVolumeExpanded(volume.id)" class="tree-children">
        <button
          v-for="chapter in chaptersForVolume(volume.id)"
          :key="chapter.id"
          type="button"
          class="tree-row chapter-row child-row"
          :class="{ selected: chapter.id === selectedChapterId }"
          @click="emit('selectChapter', chapter)"
          @contextmenu.stop.prevent="openChapterMenu($event, chapter)"
        >
          <span class="tree-label">{{ chapter.title }}</span>
        </button>
      </div>
    </section>

    <section class="tree-group">
      <button
        type="button"
        class="tree-row volume-row"
        :class="{ expanded: unassignedExpanded }"
        @click="toggleUnassigned"
        @contextmenu.stop.prevent="openUnassignedMenu"
      >
        <span class="disclosure">{{ unassignedExpanded ? '▾' : '▸' }}</span>
        <span class="tree-label">未分卷章节</span>
      </button>

      <button
        type="button"
        class="tree-row create-row child-row"
        @click="emit('createChapter', null)"
        @contextmenu.stop.prevent="openUnassignedMenu"
      >
        + 新建章节
      </button>

      <div v-if="unassignedExpanded" class="tree-children">
        <button
          v-for="chapter in unassignedChapters"
          :key="chapter.id"
          type="button"
          class="tree-row chapter-row child-row"
          :class="{ selected: chapter.id === selectedChapterId }"
          @click="emit('selectChapter', chapter)"
          @contextmenu.stop.prevent="openChapterMenu($event, chapter)"
        >
          <span class="tree-label">{{ chapter.title }}</span>
        </button>
      </div>
    </section>

    <ContextMenu
      :visible="Boolean(contextMenu?.visible)"
      :x="contextMenu?.x ?? 0"
      :y="contextMenu?.y ?? 0"
      :items="menuItems"
      @close="closeMenu"
      @select="handleMenuSelect"
    />
  </nav>
</template>

<style scoped>
.chapter-tree {
  display: grid;
  gap: 4px;
}

.tree-root,
.tree-group {
  display: grid;
}

.tree-root {
  margin-bottom: 2px;
}

.tree-children {
  display: grid;
}

.tree-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  border: 0;
  border-radius: 6px;
  padding: 0 10px;
  background: transparent;
  color: #111827;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.tree-row:hover,
.tree-row:focus-visible {
  background: #f3f4f6;
  outline: none;
}

.root-row {
  min-height: 32px;
  color: #0f172a;
  font-weight: 800;
}

.create-row {
  min-height: 28px;
  color: #2563eb;
  font-size: 0.84rem;
  font-weight: 700;
}

.volume-row {
  min-height: 32px;
  color: #111827;
  font-weight: 700;
}

.chapter-row {
  min-height: 30px;
  color: #334155;
}

.child-row {
  padding-left: 28px;
}

.chapter-row.child-row {
  padding-left: 44px;
}

.selected {
  background: #eaf2ff;
  color: #1d4ed8;
}

.selected:hover,
.selected:focus-visible {
  background: #dde9ff;
}

.disclosure {
  display: inline-flex;
  width: 14px;
  flex: 0 0 auto;
  color: #64748b;
  font-size: 0.78rem;
  justify-content: center;
}

.tree-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
