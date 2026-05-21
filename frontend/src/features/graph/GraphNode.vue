<script setup lang="ts">
import type { GraphNode } from '@/entities/graph/types'
import { graphNodeTypeLabels } from '@/entities/graph/types'

const props = defineProps<{
  node: GraphNode
  selected: boolean
  dragging: boolean
  cleanMode: boolean
}>()

const emit = defineEmits<{
  pointerDown: [event: PointerEvent, node: GraphNode]
  clickNode: [event: MouseEvent, node: GraphNode]
  contextMenu: [event: MouseEvent, node: GraphNode]
}>()

const fallbackColors: Record<GraphNode['node_type'], string> = {
  character: '#4f7cff',
  setting: '#0f9f88',
  clue: '#d97706',
  timeline_event: '#7c3aed',
  organization: '#ef4444',
  location: '#0891b2',
  custom: '#64748b',
}

function getAccentColor() {
  return props.node.color?.trim() || fallbackColors[props.node.node_type]
}
</script>

<template>
  <button
    class="graph-node"
    :class="[`size-${node.size}`, node.visibility, { selected, dragging }]"
    :style="{ '--node-accent': getAccentColor() }"
    type="button"
    @pointerdown.stop="emit('pointerDown', $event, node)"
    @click.stop="emit('clickNode', $event, node)"
    @contextmenu.prevent.stop="emit('contextMenu', $event, node)"
  >
    <span class="node-title">{{ node.title }}</span>
    <span class="node-meta">
      {{ graphNodeTypeLabels[node.node_type] }}
      <span v-if="node.bound_type && node.bound_id"> · 已绑定</span>
    </span>
    <span v-if="!cleanMode && node.summary" class="node-summary">{{ node.summary }}</span>
  </button>
</template>

<style scoped>
.graph-node {
  display: grid;
  gap: 4px;
  width: 172px;
  min-height: 76px;
  border: 1px solid #cbd5e1;
  border-left: 5px solid var(--node-accent);
  border-radius: 8px;
  padding: 10px 12px;
  background: #ffffff;
  box-shadow: 0 8px 18px rgb(15 23 42 / 8%);
  color: #111827;
  text-align: left;
  cursor: grab;
  touch-action: none;
}

.graph-node:hover,
.graph-node.selected {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgb(37 99 235 / 14%), 0 12px 24px rgb(15 23 42 / 12%);
}

.graph-node.dragging {
  cursor: grabbing;
  opacity: 0.86;
}

.graph-node.subtle {
  opacity: 0.62;
}

.graph-node.size-2 {
  width: 202px;
  min-height: 88px;
}

.graph-node.size-3 {
  width: 232px;
  min-height: 102px;
}

.node-title {
  overflow: hidden;
  color: #0f172a;
  font-size: 0.9rem;
  font-weight: 800;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-meta {
  color: #2563eb;
  font-size: 0.75rem;
  font-weight: 700;
}

.node-summary {
  display: -webkit-box;
  overflow: hidden;
  color: #475569;
  font-size: 0.75rem;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
</style>
