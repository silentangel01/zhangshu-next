<script setup lang="ts">
import { computed, ref } from 'vue'

import type { OutlineItem, OutlineTreeNodeData } from '@/entities/outline/types'
import OutlineTreeNode from './OutlineTreeNode.vue'
import type { DropPosition } from './outlineDrag'

const props = defineProps<{
  items: OutlineItem[]
  selectedOutlineId: string | null
}>()

const emit = defineEmits<{
  select: [item: OutlineItem]
  reorder: [draggedId: string, targetId: string | null, position: DropPosition]
}>()

const draggedId = ref<string | null>(null)

const treeGroups = computed(() => buildOutlineTree(props.items))

function buildOutlineTree(items: OutlineItem[]): {
  roots: OutlineTreeNodeData[]
  orphanRoots: OutlineTreeNodeData[]
} {
  const nodes = new Map<string, OutlineTreeNodeData>()

  for (const item of items) {
    nodes.set(item.id, { item, children: [] })
  }

  const roots: OutlineTreeNodeData[] = []
  const orphanRoots: OutlineTreeNodeData[] = []

  for (const node of nodes.values()) {
    const parentId = node.item.parent_id
    const parent = parentId ? nodes.get(parentId) : null

    if (parent) {
      parent.children.push(node)
    } else if (parentId) {
      orphanRoots.push(node)
    } else {
      roots.push(node)
    }
  }

  sortTreeNodes(roots)
  sortTreeNodes(orphanRoots)
  return { roots, orphanRoots }
}

function sortTreeNodes(nodes: OutlineTreeNodeData[]) {
  nodes.sort((left, right) => compareOutlineItems(left.item, right.item))
  for (const node of nodes) {
    sortTreeNodes(node.children)
  }
}

function compareOutlineItems(left: OutlineItem, right: OutlineItem): number {
  if (left.order_index !== right.order_index) {
    return left.order_index - right.order_index
  }
  return new Date(left.created_at).getTime() - new Date(right.created_at).getTime()
}

function handleDragStart(id: string) {
  draggedId.value = id
}

function handleDragEnd() {
  draggedId.value = null
}

function handleDrop(targetId: string | null, position: DropPosition) {
  if (!draggedId.value) return
  emit('reorder', draggedId.value, targetId, position)
  draggedId.value = null
}
</script>

<template>
  <section class="outline-tree">
    <header class="tree-header">
      <h2>大纲树</h2>
    </header>

    <p v-if="items.length === 0" class="empty-state">暂无大纲内容。</p>

    <div v-else class="tree-groups">
      <ul v-if="treeGroups.roots.length" class="tree-list">
        <OutlineTreeNode
          v-for="node in treeGroups.roots"
          :key="node.item.id"
          :node="node"
          :depth="0"
          :selected-outline-id="selectedOutlineId"
          :dragged-id="draggedId"
          @select="emit('select', $event)"
          @drag-start="handleDragStart"
          @drag-end="handleDragEnd"
          @drop="handleDrop"
        />
      </ul>

      <section v-if="treeGroups.orphanRoots.length" class="orphan-group">
        <h3>未归类大纲</h3>
        <ul class="tree-list">
          <OutlineTreeNode
            v-for="node in treeGroups.orphanRoots"
            :key="node.item.id"
            :node="node"
            :depth="0"
            :selected-outline-id="selectedOutlineId"
            :dragged-id="draggedId"
            @select="emit('select', $event)"
            @drag-start="handleDragStart"
            @drag-end="handleDragEnd"
            @drop="handleDrop"
          />
        </ul>
      </section>
    </div>
  </section>
</template>

<style scoped>
.outline-tree {
  display: grid;
  gap: var(--zs-space-3);
}

.tree-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

h2,
h3 {
  margin: 0;
}

h2 {
  font-size: 1.1rem;
}

h3 {
  color: var(--zs-color-text-muted);
  font-size: 0.9rem;
}

.empty-state {
  margin: 0;
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-4);
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  text-align: center;
}

.tree-groups,
.orphan-group {
  display: grid;
  gap: var(--zs-space-2);
}

.orphan-group {
  border-top: 1px solid var(--zs-color-border-soft);
  padding-top: var(--zs-space-3);
}

.tree-list {
  display: grid;
  gap: var(--zs-space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
</style>
