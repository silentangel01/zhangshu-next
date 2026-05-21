<script setup lang="ts">
import type { GraphEdge, GraphNode } from '@/entities/graph/types'

interface EdgeRenderItem {
  edge: GraphEdge
  fromNode: GraphNode
  toNode: GraphNode
  path: string
  labelX: number
  labelY: number
}

defineProps<{
  edges: EdgeRenderItem[]
  selectedEdgeId: string | null
  cleanMode: boolean
  width: number
  height: number
  previewPath: string
}>()

const emit = defineEmits<{
  selectEdge: [edge: GraphEdge]
  contextMenu: [event: MouseEvent, edge: GraphEdge]
}>()
</script>

<template>
  <svg class="graph-edge-overlay" :viewBox="`0 0 ${width} ${height}`" :width="width" :height="height">
    <defs>
      <marker id="graph-arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
        <path d="M0,0 L0,6 L9,3 z" fill="currentColor" />
      </marker>
    </defs>

    <g
      v-for="item in edges"
      :key="item.edge.id"
      class="edge-group"
      data-graph-edge="true"
      :class="[item.edge.visibility, { selected: selectedEdgeId === item.edge.id }]"
      @dblclick.stop="emit('selectEdge', item.edge)"
      @contextmenu.prevent.stop="emit('contextMenu', $event, item.edge)"
    >
      <path
        class="edge-hit"
        data-graph-edge="true"
        :d="item.path"
        @click.stop="emit('selectEdge', item.edge)"
        @dblclick.stop="emit('selectEdge', item.edge)"
      />
      <path
        class="edge-line"
        data-graph-edge="true"
        :class="[item.edge.line_style, { selected: selectedEdgeId === item.edge.id }]"
        :d="item.path"
        :stroke-width="Math.max(1.4, Math.min(5, item.edge.strength))"
        :marker-end="item.edge.direction === 'directed' ? 'url(#graph-arrow)' : undefined"
        @dblclick.stop="emit('selectEdge', item.edge)"
      />
      <text
        v-if="item.edge.label && (!cleanMode || selectedEdgeId === item.edge.id)"
        class="edge-label"
        :x="item.labelX"
        :y="item.labelY"
        text-anchor="middle"
      >
        {{ item.edge.label }}
      </text>
    </g>

    <path v-if="previewPath" class="preview-line" :d="previewPath" />
  </svg>
</template>

<style scoped>
.graph-edge-overlay {
  position: absolute;
  inset: 0;
  overflow: visible;
  pointer-events: none;
}

.edge-group {
  color: #64748b;
  pointer-events: auto;
}

.edge-group.subtle {
  opacity: 0.48;
}

.edge-group.selected {
  color: #2563eb;
  opacity: 1;
}

.edge-hit,
.edge-line,
.preview-line {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.edge-hit {
  stroke: transparent;
  stroke-width: 14;
  cursor: pointer;
}

.edge-line {
  stroke: currentColor;
}

.edge-line.dashed {
  stroke-dasharray: 9 7;
}

.edge-line.dotted {
  stroke-dasharray: 2 8;
}

.edge-line.selected {
  filter: drop-shadow(0 0 4px rgb(37 99 235 / 45%));
}

.edge-label {
  fill: #0f172a;
  font-size: 12px;
  font-weight: 800;
  paint-order: stroke;
  stroke: #ffffff;
  stroke-linejoin: round;
  stroke-width: 4px;
  pointer-events: none;
}

.preview-line {
  stroke: #2563eb;
  stroke-dasharray: 8 6;
  stroke-width: 2;
  pointer-events: none;
}
</style>
