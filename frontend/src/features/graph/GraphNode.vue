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
  character: 'var(--zs-module-character)',
  setting: 'var(--zs-module-setting)',
  clue: 'var(--zs-module-clue)',
  timeline_event: 'var(--zs-module-timeline)',
  organization: 'var(--zs-color-danger)',
  location: 'var(--zs-color-info)',
  custom: 'var(--zs-color-text-muted)',
}

function getAccentColor() {
  return props.node.color?.trim() || fallbackColors[props.node.node_type]
}
</script>

<template>
  <button
    class="graph-node"
    data-graph-node="true"
    :class="[`type-${node.node_type}`, `size-${node.size}`, node.visibility, { selected, dragging }]"
    :style="{ '--node-accent': getAccentColor() }"
    type="button"
    @pointerdown.stop="emit('pointerDown', $event, node)"
    @click.stop="emit('clickNode', $event, node)"
    @dblclick.stop="emit('clickNode', $event, node)"
    @contextmenu.prevent.stop="emit('contextMenu', $event, node)"
  >
    <span class="node-title">{{ node.title }}</span>
    <span class="node-meta">
      <span class="type-badge">{{ graphNodeTypeLabels[node.node_type] }}</span>
      <span v-if="node.bound_type && node.bound_id" class="bound-badge">已绑定</span>
    </span>
    <span v-if="!cleanMode && node.summary" class="node-summary">{{ node.summary }}</span>
  </button>
</template>

<style scoped>
.graph-node {
  position: relative;
  display: grid;
  gap: 5px;
  width: 100%;
  height: 100%;
  min-height: 0;
  border: 1px solid color-mix(in srgb, var(--node-accent) 42%, var(--zs-color-border));
  border-left: 5px solid var(--node-accent);
  border-radius: var(--zs-radius-md);
  padding: 10px 12px;
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
  color: var(--zs-color-text);
  text-align: left;
  cursor: grab;
  touch-action: none;
}

.graph-node::before {
  position: absolute;
  inset: 0;
  z-index: -1;
  border-radius: inherit;
  background: color-mix(in srgb, var(--node-accent) 8%, var(--zs-color-surface));
  content: '';
}

.graph-node:hover,
.graph-node.selected {
  border-color: var(--zs-color-primary);
  box-shadow: var(--zs-shadow-focus), 0 12px 24px rgb(31 42 46 / 11%);
}

.graph-node.dragging {
  cursor: grabbing;
  opacity: 0.86;
}

.graph-node.subtle {
  opacity: 0.58;
}

.graph-node.size-2 {
  min-height: 0;
}

.graph-node.size-3 {
  min-height: 0;
}

.graph-node.type-character {
  align-content: center;
  border-left-width: 1px;
  border-radius: 999px;
  padding: 18px;
  text-align: center;
}

.graph-node.type-setting {
  border-radius: 12px;
}

.graph-node.type-clue {
  border-left-width: 1px;
  border-radius: 14px;
  clip-path: polygon(50% 0, 100% 50%, 50% 100%, 0 50%);
  padding: 24px 28px;
  text-align: center;
}

.graph-node.type-timeline_event {
  border-left-width: 1px;
  border-radius: 999px;
  align-content: center;
}

.graph-node.type-organization {
  border-left-width: 1px;
  clip-path: polygon(12% 0, 88% 0, 100% 50%, 88% 100%, 12% 100%, 0 50%);
  padding-inline: 20px;
  text-align: center;
}

.graph-node.type-location {
  border-radius: 8px 18px 8px 8px;
}

.node-title {
  overflow: hidden;
  color: var(--zs-color-text);
  font-size: 0.92rem;
  font-weight: 900;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  align-items: center;
  justify-content: flex-start;
}

.type-character .node-meta,
.type-clue .node-meta,
.type-organization .node-meta {
  justify-content: center;
}

.type-badge,
.bound-badge {
  border-radius: 999px;
  padding: 2px 7px;
  background: color-mix(in srgb, var(--node-accent) 12%, var(--zs-color-surface));
  color: var(--node-accent);
  font-size: 0.7rem;
  font-weight: 900;
}

.bound-badge {
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-text-muted);
}

.node-summary {
  display: -webkit-box;
  overflow: hidden;
  color: var(--zs-color-text-muted);
  font-size: 0.75rem;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
</style>
