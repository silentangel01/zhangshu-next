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
  gap: var(--zs-space-2);
}

.node-row {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: var(--zs-space-1);
  align-items: stretch;
  margin-left: calc(var(--depth) * 22px);
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
  cursor: pointer;
}

.tree-node.active {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
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
