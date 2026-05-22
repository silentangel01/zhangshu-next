<script setup lang="ts">
import { computed, ref } from 'vue'

import type { Chapter, ChapterReorderItem, ReorderChaptersPayload } from '@/entities/chapter/types'
import type { Volume } from '@/entities/volume/types'
import ContextMenu, { type ContextMenuItem } from '@/shared/ui/ContextMenu.vue'

const props = defineProps<{
  projectTitle: string
  volumes: Volume[]
  chapters: Chapter[]
  selectedChapterId: string | null
  isReordering?: boolean
}>()

const emit = defineEmits<{
  selectChapter: [chapter: Chapter]
  createVolume: []
  createChapter: [volumeId: string | null]
  editVolume: [volume: Volume]
  deleteVolume: [volume: Volume]
  editChapter: [chapter: Chapter]
  deleteChapter: [chapter: Chapter]
  reorderChapters: [payload: ReorderChaptersPayload]
}>()

type TreeMenuContext =
  | { target: 'root' }
  | { target: 'unassigned' }
  | { target: 'volume'; volume: Volume }
  | { target: 'chapter'; chapter: Chapter }

type DropTarget =
  | { target: 'volume'; volumeId: string | null }
  | { target: 'chapter'; chapterId: string; position: 'before' | 'after' }

const contextMenu = ref<{
  visible: boolean
  x: number
  y: number
  context: TreeMenuContext
} | null>(null)

const expandedVolumeIds = ref<Record<string, boolean>>({})
const unassignedExpanded = ref(true)
const draggingChapterId = ref<string | null>(null)
const dropTarget = ref<DropTarget | null>(null)

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

function handleChapterClick(chapter: Chapter) {
  emit('selectChapter', chapter)
}

function handleChapterKeydown(event: KeyboardEvent, chapter: Chapter) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    emit('selectChapter', chapter)
  }
}

function handleDragStart(event: DragEvent, chapter: Chapter) {
  if (props.isReordering) {
    event.preventDefault()
    return
  }

  event.dataTransfer?.setData('text/plain', chapter.id)
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }

  draggingChapterId.value = chapter.id
  dropTarget.value = null
  closeMenu()
}

function handleDragEnd() {
  draggingChapterId.value = null
  dropTarget.value = null
}

function getChapterById(chapterId: string) {
  return props.chapters.find((chapter) => chapter.id === chapterId) ?? null
}

function getGroupedChapters() {
  const groups = new Map<string | null, Chapter[]>()

  for (const volume of sortedVolumes.value) {
    groups.set(volume.id, chaptersForVolume(volume.id))
  }

  groups.set(null, [...unassignedChapters.value])
  return groups
}

function resolveChapterDropTarget(event: DragEvent, chapter: Chapter): DropTarget | null {
  const draggedChapterId = draggingChapterId.value
  if (!draggedChapterId || props.isReordering) {
    return null
  }

  const draggedChapter = getChapterById(draggedChapterId)
  if (!draggedChapter || draggedChapter.id === chapter.id) {
    return null
  }

  const currentTarget = event.currentTarget as HTMLElement | null
  const rect = currentTarget?.getBoundingClientRect()
  if (!rect) {
    return null
  }

  const position = event.clientY < rect.top + rect.height / 2 ? 'before' : 'after'
  return { target: 'chapter', chapterId: chapter.id, position }
}

function isSameDropTarget(left: DropTarget | null, right: DropTarget | null) {
  if (!left || !right) {
    return false
  }

  if (left.target !== right.target) {
    return false
  }

  if (left.target === 'volume' && right.target === 'volume') {
    return left.volumeId === right.volumeId
  }

  if (left.target === 'chapter' && right.target === 'chapter') {
    return left.chapterId === right.chapterId && left.position === right.position
  }

  return false
}

function handleVolumeDragOver(event: DragEvent, volumeId: string | null) {
  if (!draggingChapterId.value || props.isReordering) {
    return
  }

  event.preventDefault()
  const nextTarget: DropTarget = { target: 'volume', volumeId }
  if (!isSameDropTarget(dropTarget.value, nextTarget)) {
    dropTarget.value = nextTarget
  }
}

function handleVolumeDrop(event: DragEvent, volumeId: string | null) {
  if (!draggingChapterId.value || props.isReordering) {
    return
  }

  event.preventDefault()
  requestReorder({ target: 'volume', volumeId })
}

function handleChapterDragOver(event: DragEvent, chapter: Chapter) {
  const nextTarget = resolveChapterDropTarget(event, chapter)
  if (!nextTarget) {
    return
  }

  event.preventDefault()
  if (!isSameDropTarget(dropTarget.value, nextTarget)) {
    dropTarget.value = nextTarget
  }
}

function handleChapterDrop(event: DragEvent, chapter: Chapter) {
  if (!draggingChapterId.value || props.isReordering) {
    return
  }

  const nextTarget = resolveChapterDropTarget(event, chapter)
  if (!nextTarget) {
    return
  }

  event.preventDefault()
  requestReorder(nextTarget)
}

function clearDropTarget() {
  dropTarget.value = null
}

function requestReorder(target: DropTarget) {
  const payload = buildReorderPayload(target)
  if (!payload?.items.length) {
    return
  }

  emit('reorderChapters', payload)
  clearDropTarget()
  draggingChapterId.value = null
}

function buildReorderPayload(target: DropTarget): ReorderChaptersPayload | null {
  const draggedChapterId = draggingChapterId.value
  if (!draggedChapterId) {
    return null
  }

  const draggedChapter = getChapterById(draggedChapterId)
  if (!draggedChapter) {
    return null
  }

  const sourceVolumeId =
    draggedChapter.volume_id && activeVolumeIds.value.has(draggedChapter.volume_id)
      ? draggedChapter.volume_id
      : null
  const targetChapterVolumeId = target.target === 'chapter' ? getChapterById(target.chapterId)?.volume_id : null
  const targetVolumeId =
    target.target === 'volume'
      ? target.volumeId
      : targetChapterVolumeId && activeVolumeIds.value.has(targetChapterVolumeId)
        ? targetChapterVolumeId
        : null

  const originalGroups = getGroupedChapters()
  const workingGroups = new Map<string | null, Chapter[]>(
    [...originalGroups.entries()].map(([key, chapters]) => [key, [...chapters]]),
  )

  const sourceGroup = workingGroups.get(sourceVolumeId)
  const targetGroup = workingGroups.get(targetVolumeId)

  if (!sourceGroup || !targetGroup) {
    return null
  }

  const sourceBefore = sourceGroup.map((chapter) => chapter.id)
  const targetBefore = sourceVolumeId === targetVolumeId ? sourceBefore : targetGroup.map((chapter) => chapter.id)
  const draggedIndex = sourceGroup.findIndex((chapter) => chapter.id === draggedChapterId)

  if (draggedIndex === -1) {
    return null
  }

  sourceGroup.splice(draggedIndex, 1)

  let insertIndex = targetGroup.length
  if (target.target === 'chapter') {
    if (target.chapterId === draggedChapterId) {
      return null
    }

    const anchorIndex = targetGroup.findIndex((chapter) => chapter.id === target.chapterId)
    if (anchorIndex === -1) {
      return null
    }

    insertIndex = target.position === 'after' ? anchorIndex + 1 : anchorIndex
  }

  targetGroup.splice(insertIndex, 0, draggedChapter)

  const sourceAfter = (workingGroups.get(sourceVolumeId) ?? []).map((chapter) => chapter.id)
  const targetAfter = (workingGroups.get(targetVolumeId) ?? []).map((chapter) => chapter.id)

  if (sourceVolumeId === targetVolumeId) {
    if (sourceBefore.join('|') === sourceAfter.join('|')) {
      return null
    }
  } else if (sourceBefore.join('|') === sourceAfter.join('|') && targetBefore.join('|') === targetAfter.join('|')) {
    return null
  }

  const affectedGroupIds = new Set<string | null>([sourceVolumeId, targetVolumeId])
  const items: ChapterReorderItem[] = []

  for (const volume of sortedVolumes.value) {
    if (!affectedGroupIds.has(volume.id)) {
      continue
    }

    const group = workingGroups.get(volume.id) ?? []
    group.forEach((chapter, index) => {
      items.push({
        chapter_id: chapter.id,
        volume_id: volume.id,
        order_index: index,
      })
    })
  }

  if (affectedGroupIds.has(null)) {
    const group = workingGroups.get(null) ?? []
    group.forEach((chapter, index) => {
      items.push({
        chapter_id: chapter.id,
        volume_id: null,
        order_index: index,
      })
    })
  }

  return { items }
}

function isDraggingChapter(chapterId: string) {
  return draggingChapterId.value === chapterId
}

function isDropBefore(chapterId: string) {
  return dropTarget.value?.target === 'chapter' && dropTarget.value.chapterId === chapterId && dropTarget.value.position === 'before'
}

function isDropAfter(chapterId: string) {
  return dropTarget.value?.target === 'chapter' && dropTarget.value.chapterId === chapterId && dropTarget.value.position === 'after'
}

function isVolumeDropTarget(volumeId: string | null) {
  return dropTarget.value?.target === 'volume' && dropTarget.value.volumeId === volumeId
}
</script>

<template>
  <nav class="chapter-tree" aria-label="章节树" @contextmenu.prevent="openRootMenu">
    <div class="tree-root">
      <div class="tree-row root-row">
        <span class="tree-label">{{ projectTitle }}</span>
      </div>

    </div>

    <section v-for="volume in sortedVolumes" :key="volume.id" class="tree-group">
      <button
        type="button"
        class="tree-row volume-row"
        :class="{ expanded: isVolumeExpanded(volume.id), 'drop-target': isVolumeDropTarget(volume.id) }"
        @click="toggleVolume(volume.id)"
        @contextmenu.stop.prevent="openVolumeMenu($event, volume)"
        @dragover.prevent="handleVolumeDragOver($event, volume.id)"
        @drop.prevent="handleVolumeDrop($event, volume.id)"
      >
        <span class="disclosure">{{ isVolumeExpanded(volume.id) ? '▾' : '▸' }}</span>
        <span class="tree-label">{{ volume.title }}</span>
      </button>

      <div v-if="isVolumeExpanded(volume.id)" class="tree-children">
        <div
          v-for="chapter in chaptersForVolume(volume.id)"
          :key="chapter.id"
          class="tree-row chapter-row child-row"
          :class="{
            selected: chapter.id === selectedChapterId,
            dragging: isDraggingChapter(chapter.id),
            'drop-before': isDropBefore(chapter.id),
            'drop-after': isDropAfter(chapter.id),
          }"
          role="button"
          tabindex="0"
          @click="handleChapterClick(chapter)"
          @keydown.enter.prevent="handleChapterKeydown($event, chapter)"
          @keydown.space.prevent="handleChapterKeydown($event, chapter)"
          @contextmenu.stop.prevent="openChapterMenu($event, chapter)"
          @dragover.prevent="handleChapterDragOver($event, chapter)"
          @drop.prevent="handleChapterDrop($event, chapter)"
        >
          <span
            class="drag-handle"
            :class="{ disabled: isReordering }"
            draggable="true"
            aria-label="拖动章节"
            @click.stop.prevent
            @dragstart="handleDragStart($event, chapter)"
            @dragend="handleDragEnd"
          >
            ⋮⋮
          </span>
          <span class="tree-label">{{ chapter.title }}</span>
        </div>
        <button
          type="button"
          class="tree-row create-row child-row"
          @click="emit('createChapter', volume.id)"
          @contextmenu.stop.prevent="openVolumeMenu($event, volume)"
          @dragover.prevent="handleVolumeDragOver($event, volume.id)"
          @drop.prevent="handleVolumeDrop($event, volume.id)"
        >
          + 新建章节
        </button>
      </div>
    </section>

    <section class="tree-group">
      <button
        type="button"
        class="tree-row volume-row"
        :class="{ expanded: unassignedExpanded, 'drop-target': isVolumeDropTarget(null) }"
        @click="toggleUnassigned"
        @contextmenu.stop.prevent="openUnassignedMenu"
        @dragover.prevent="handleVolumeDragOver($event, null)"
        @drop.prevent="handleVolumeDrop($event, null)"
      >
        <span class="disclosure">{{ unassignedExpanded ? '▾' : '▸' }}</span>
        <span class="tree-label">未分卷章节</span>
      </button>

      <div v-if="unassignedExpanded" class="tree-children">
        <div
          v-for="chapter in unassignedChapters"
          :key="chapter.id"
          class="tree-row chapter-row child-row"
          :class="{
            selected: chapter.id === selectedChapterId,
            dragging: isDraggingChapter(chapter.id),
            'drop-before': isDropBefore(chapter.id),
            'drop-after': isDropAfter(chapter.id),
          }"
          role="button"
          tabindex="0"
          @click="handleChapterClick(chapter)"
          @keydown.enter.prevent="handleChapterKeydown($event, chapter)"
          @keydown.space.prevent="handleChapterKeydown($event, chapter)"
          @contextmenu.stop.prevent="openChapterMenu($event, chapter)"
          @dragover.prevent="handleChapterDragOver($event, chapter)"
          @drop.prevent="handleChapterDrop($event, chapter)"
        >
          <span
            class="drag-handle"
            :class="{ disabled: isReordering }"
            draggable="true"
            aria-label="拖动章节"
            @click.stop.prevent
            @dragstart="handleDragStart($event, chapter)"
            @dragend="handleDragEnd"
          >
            ⋮⋮
          </span>
          <span class="tree-label">{{ chapter.title }}</span>
        </div>
        <button
          type="button"
          class="tree-row create-row child-row"
          @click="emit('createChapter', null)"
          @contextmenu.stop.prevent="openUnassignedMenu"
          @dragover.prevent="handleVolumeDragOver($event, null)"
          @drop.prevent="handleVolumeDrop($event, null)"
        >
          + 新建章节
        </button>
      </div>
    </section>

    <button
      type="button"
      class="tree-row create-row volume-create-row"
      @click="emit('createVolume')"
      @contextmenu.stop.prevent="openRootMenu"
    >
      + 新建分卷
    </button>

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
  background: #f8fafc;
  outline: none;
}

.root-row {
  min-height: 32px;
  color: #0f172a;
  font-weight: 800;
}

.create-row {
  min-height: 28px;
  border: 1px solid #dbeafe;
  background: #f8fbff;
  color: #2563eb;
  font-size: 0.84rem;
  font-weight: 700;
}

.volume-create-row {
  margin-top: 6px;
  border-style: dashed;
}

.volume-row {
  min-height: 32px;
  color: #111827;
  font-weight: 700;
}

.volume-row.drop-target {
  background: #eef6ff;
}

.chapter-row {
  position: relative;
  min-height: 30px;
  color: #334155;
  user-select: none;
}

.chapter-row.selected {
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 800;
}

.chapter-row.selected:hover,
.chapter-row.selected:focus-visible {
  background: #eaf2ff;
}

.chapter-row.dragging {
  opacity: 0.55;
}

.chapter-row.drop-before::before,
.chapter-row.drop-after::after {
  content: '';
  position: absolute;
  left: 40px;
  right: 10px;
  height: 2px;
  border-radius: 999px;
  background: #2563eb;
}

.chapter-row.drop-before::before {
  top: -1px;
}

.chapter-row.drop-after::after {
  bottom: -1px;
}

.child-row {
  padding-left: 28px;
}

.chapter-row.child-row {
  padding-left: 20px;
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

.drag-handle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  flex: 0 0 auto;
  color: #94a3b8;
  font-size: 0.8rem;
  letter-spacing: 0;
  opacity: 0.3;
  cursor: grab;
}

.chapter-row:hover .drag-handle,
.chapter-row:focus-within .drag-handle {
  opacity: 0.8;
}

.drag-handle.disabled {
  cursor: not-allowed;
}
</style>
