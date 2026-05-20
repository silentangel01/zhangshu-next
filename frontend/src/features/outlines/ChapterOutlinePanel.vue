<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { listChapterOutlines } from '@/entities/outline/api'
import type { OutlineItem, OutlineTreeNodeData } from '@/entities/outline/types'
import ChapterOutlineNode from './ChapterOutlineNode.vue'

const props = defineProps<{
  projectId: string
  chapterId: string | null
  compact?: boolean
}>()

const outlines = ref<OutlineItem[]>([])
const isLoading = ref(false)
const errorMessage = ref('')

const outlineTree = computed(() => buildOutlineTree(outlines.value))

onMounted(() => {
  void refreshOutlines()
})

watch(
  () => props.chapterId,
  () => {
    void refreshOutlines()
  },
)

async function refreshOutlines() {
  if (!props.chapterId) {
    outlines.value = []
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    outlines.value = await listChapterOutlines(props.chapterId)
  } catch (error) {
    void error
    errorMessage.value = '加载章节细纲失败。'
  } finally {
    isLoading.value = false
  }
}

function buildOutlineTree(items: OutlineItem[]): OutlineTreeNodeData[] {
  const nodes = new Map<string, OutlineTreeNodeData>()

  for (const item of items) {
    nodes.set(item.id, { item, children: [] })
  }

  const roots: OutlineTreeNodeData[] = []
  for (const node of nodes.values()) {
    const parent = node.item.parent_id ? nodes.get(node.item.parent_id) : null
    if (parent) {
      parent.children.push(node)
    } else {
      roots.push(node)
    }
  }

  sortTreeNodes(roots)
  return roots
}

function sortTreeNodes(nodes: OutlineTreeNodeData[]) {
  nodes.sort((left, right) => {
    if (left.item.order_index !== right.item.order_index) {
      return left.item.order_index - right.item.order_index
    }
    return new Date(left.item.created_at).getTime() - new Date(right.item.created_at).getTime()
  })
  for (const node of nodes) {
    sortTreeNodes(node.children)
  }
}
</script>

<template>
  <aside class="chapter-outline-panel" :class="{ compact }">
    <header class="panel-header">
      <div>
        <p class="eyebrow">写作参考</p>
        <h2>当前章节细纲</h2>
      </div>
      <RouterLink class="open-link" :to="`/projects/${projectId}/outlines`">打开完整大纲</RouterLink>
    </header>

    <p v-if="isLoading" class="state-message">正在加载章节细纲……</p>
    <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    <p v-else-if="outlines.length === 0" class="state-message">暂无章节细纲。</p>

    <ul v-else class="outline-list">
      <ChapterOutlineNode
        v-for="node in outlineTree"
        :key="node.item.id"
        :node="node"
        :depth="0"
      />
    </ul>
  </aside>
</template>

<style scoped>
.chapter-outline-panel {
  display: grid;
  gap: 12px;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 16px;
  background: #fbfcfe;
}

.chapter-outline-panel.compact {
  border: 0;
  padding: 0;
  background: transparent;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.eyebrow {
  margin: 0 0 5px;
  color: #64748b;
  font-size: 0.75rem;
  font-weight: 800;
}

h2,
p {
  margin: 0;
}

h2 {
  font-size: 1rem;
}

.open-link {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 0 10px;
  background: #ffffff;
  color: #2563eb;
  font-size: 0.86rem;
  font-weight: 800;
  text-decoration: none;
}

.state-message,
.error-message {
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 14px;
  color: #64748b;
  text-align: center;
}

.error-message {
  border-color: #fecaca;
  color: #b42318;
}

.outline-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}
</style>
