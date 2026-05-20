<script setup lang="ts">
import { computed, ref } from 'vue'

import type { OutlineItem, OutlineTreeNodeData } from '@/entities/outline/types'
import {
  outlineImportanceLabels,
  outlineItemTypeLabels,
  outlineStatusLabels,
} from '@/entities/outline/types'

const props = defineProps<{
  node: OutlineTreeNodeData
  selectedOutlineId: string | null
  depth: number
}>()

const emit = defineEmits<{
  select: [item: OutlineItem]
}>()

const isExpanded = ref(true)
const hasChildren = computed(() => props.node.children.length > 0)

function handleToggle() {
  if (hasChildren.value) {
    isExpanded.value = !isExpanded.value
  }
}
</script>

<template>
  <li class="tree-item">
    <div class="node-row" :style="{ '--depth': depth }">
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

      <button
        class="tree-node"
        type="button"
        :class="{ active: node.item.id === selectedOutlineId }"
        @click="emit('select', node.item)"
      >
        <span class="node-title">{{ node.item.title }}</span>
        <span class="node-meta">
          {{ outlineItemTypeLabels[node.item.item_type] }} ·
          {{ outlineStatusLabels[node.item.status] }} ·
          {{ outlineImportanceLabels[node.item.importance] }}
        </span>
      </button>
    </div>

    <ul v-if="hasChildren && isExpanded" class="child-list">
      <OutlineTreeNode
        v-for="child in node.children"
        :key="child.item.id"
        :node="child"
        :depth="depth + 1"
        :selected-outline-id="selectedOutlineId"
        @select="emit('select', $event)"
      />
    </ul>
  </li>
</template>

<style scoped>
.tree-item {
  display: grid;
  gap: 8px;
}

.node-row {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 6px;
  align-items: stretch;
  margin-left: calc(var(--depth) * 22px);
}

.child-list {
  display: grid;
  gap: 8px;
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
  border-radius: 6px;
  background: #eef2ff;
  color: #3730a3;
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
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 10px 12px;
  background: #ffffff;
  color: #111827;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.tree-node.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.node-title {
  font-weight: 800;
  line-height: 1.4;
}

.node-meta {
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.4;
}
</style>
