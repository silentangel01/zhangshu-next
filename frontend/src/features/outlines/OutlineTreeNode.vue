<script setup lang="ts">
import { computed, ref } from 'vue'

import type { OutlineItem, OutlineTreeNodeData } from '@/entities/outline/types'
import {
  outlineImportanceLabels,
  outlineItemTypeLabels,
  outlineStatusLabels,
} from '@/entities/outline/types'
import type { DropPosition } from './outlineDrag'

const props = withDefaults(
  defineProps<{
    node: OutlineTreeNodeData
    selectedOutlineId: string | null
    depth: number
    draggedId?: string | null
  }>(),
  {
    draggedId: null,
  },
)

const emit = defineEmits<{
  select: [item: OutlineItem]
  dragStart: [id: string]
  dragEnd: []
  drop: [targetId: string | null, position: DropPosition]
}>()

const isExpanded = ref(true)
const hasChildren = computed(() => props.node.children.length > 0)
const dropZone = ref<DropPosition | null>(null)
const isDragOver = ref(false)

function handleToggle() {
  if (hasChildren.value) {
    isExpanded.value = !isExpanded.value
  }
}

function handleDragStart(event: DragEvent) {
  event.dataTransfer?.setData('text/plain', props.node.item.id)
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
  emit('dragStart', props.node.item.id)
}

function handleDragEnd() {
  dropZone.value = null
  isDragOver.value = false
  emit('dragEnd')
}

function handleDragOver(event: DragEvent) {
  if (!props.draggedId || props.draggedId === props.node.item.id) return
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }

  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const y = event.clientY - rect.top
  const height = rect.height
  const ratio = y / height

  if (ratio < 0.25) {
    dropZone.value = 'before'
  } else if (ratio > 0.75) {
    dropZone.value = 'after'
  } else {
    dropZone.value = 'inside'
  }
  isDragOver.value = true
}

function handleDragLeave() {
  dropZone.value = null
  isDragOver.value = false
}

function handleDrop(event: DragEvent) {
  event.preventDefault()
  if (!props.draggedId || !dropZone.value) return
  if (props.draggedId === props.node.item.id) return

  emit('drop', props.node.item.id, dropZone.value)
  dropZone.value = null
  isDragOver.value = false
}
</script>

<template>
  <li class="tree-item">
    <div
      class="node-row"
      :class="{
        'drop-before': dropZone === 'before',
        'drop-after': dropZone === 'after',
        'drop-inside': dropZone === 'inside',
      }"
      :style="{ '--depth': depth }"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
    >
      <button
        v-if="hasChildren"
        class="toggle-button"
        type="button"
        :aria-label="isExpanded ? '收起子条目' : '展开子条目'"
        @click.stop="handleToggle"
      >
        {{ isExpanded ? '▼' : '▶' }}
      </button>
      <span v-else class="toggle-spacer" aria-hidden="true"></span>

      <div
        class="tree-node"
        draggable="true"
        :class="{
          active: node.item.id === selectedOutlineId,
          dragging: node.item.id === draggedId,
        }"
        role="button"
        tabindex="0"
        @click="emit('select', node.item)"
        @keydown.enter="emit('select', node.item)"
        @dragstart="handleDragStart"
        @dragend="handleDragEnd"
      >
        <span class="node-title">{{ node.item.title }}</span>
        <span class="node-meta">
          {{ outlineItemTypeLabels[node.item.item_type] }} ·
          {{ outlineStatusLabels[node.item.status] }} ·
          {{ outlineImportanceLabels[node.item.importance] }}
        </span>
      </div>
    </div>

    <ul v-if="hasChildren && isExpanded" class="child-list">
      <OutlineTreeNode
        v-for="child in node.children"
        :key="child.item.id"
        :node="child"
        :depth="depth + 1"
        :selected-outline-id="selectedOutlineId"
        :dragged-id="draggedId"
        @select="emit('select', $event)"
        @drag-start="(id) => emit('dragStart', id)"
        @drag-end="emit('dragEnd')"
        @drop="(targetId, position) => emit('drop', targetId, position)"
      />
    </ul>
  </li>
</template>

<style scoped>
.tree-item {
  display: grid;
  gap: var(--zs-space-2);
}

.node-row {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: var(--zs-space-1);
  align-items: stretch;
  margin-left: calc(var(--depth) * 22px);
  border-radius: var(--zs-radius-md);
  transition: box-shadow 0.15s;
}

.node-row.drop-before {
  box-shadow: inset 0 3px 0 0 var(--zs-color-primary);
}

.node-row.drop-after {
  box-shadow: inset 0 -3px 0 0 var(--zs-color-primary);
}

.node-row.drop-inside {
  box-shadow: inset 0 0 0 2px var(--zs-color-primary);
}

.child-list {
  display: grid;
  gap: var(--zs-space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.toggle-button,
.toggle-spacer {
  width: 24px;
}

.toggle-button {
  border: 0;
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-primary);
  font: inherit;
  font-size: 0.78rem;
  font-weight: 800;
  cursor: pointer;
}

.toggle-spacer {
  display: block;
}

.tree-node {
  display: grid;
  gap: 5px;
  width: 100%;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: 10px 12px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  text-align: left;
  cursor: grab;
}

.tree-node:active {
  cursor: grabbing;
}

.tree-node.active {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
}

.tree-node.dragging {
  opacity: 0.4;
}

.node-title {
  font-weight: 800;
  line-height: 1.4;
}

.node-meta {
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  line-height: 1.4;
}
</style>
