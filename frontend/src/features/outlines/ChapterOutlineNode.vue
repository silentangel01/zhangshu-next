<script setup lang="ts">
import type { OutlineTreeNodeData } from '@/entities/outline/types'
import {
  outlineImportanceLabels,
  outlineItemTypeLabels,
  outlineStatusLabels,
} from '@/entities/outline/types'

defineProps<{
  node: OutlineTreeNodeData
  depth: number
}>()
</script>

<template>
  <li class="outline-node" :style="{ '--depth': depth }">
    <article class="outline-card">
      <header>
        <h3>{{ node.item.title }}</h3>
        <span class="importance">{{ outlineImportanceLabels[node.item.importance] }}</span>
      </header>
      <p class="meta">
        {{ outlineItemTypeLabels[node.item.item_type] }} · {{ outlineStatusLabels[node.item.status] }}
      </p>
      <p v-if="node.item.content" class="content-preview">{{ node.item.content }}</p>
    </article>

    <ul v-if="node.children.length" class="child-list">
      <ChapterOutlineNode
        v-for="child in node.children"
        :key="child.item.id"
        :node="child"
        :depth="depth + 1"
      />
    </ul>
  </li>
</template>

<style scoped>
.outline-node {
  display: grid;
  gap: 8px;
  margin-left: calc(var(--depth) * 16px);
}

.child-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.outline-card {
  display: grid;
  gap: 8px;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: 8px;
  padding: 12px;
  background: var(--zs-color-surface);
}

.outline-card header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

h3,
p {
  margin: 0;
}

h3 {
  color: var(--zs-color-text);
  font-size: 0.95rem;
  line-height: 1.4;
}

.importance {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 3px 8px;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
  font-size: 0.75rem;
  font-weight: 800;
}

.meta {
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  font-weight: 800;
}

.content-preview {
  color: var(--zs-color-text);
  line-height: 1.7;
  white-space: pre-wrap;
}
</style>
