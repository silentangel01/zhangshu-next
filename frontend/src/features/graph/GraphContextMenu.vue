<script setup lang="ts">
import type { GraphEdge, GraphNode } from '@/entities/graph/types'

export type GraphContextMenuKind = 'canvas' | 'node' | 'edge'

defineProps<{
  visible: boolean
  kind: GraphContextMenuKind
  x: number
  y: number
  node: GraphNode | null
  edge: GraphEdge | null
}>()

const emit = defineEmits<{
  createNode: []
  fitView: []
  resetView: []
  editNode: []
  startEdge: []
  duplicateNode: []
  deleteNode: []
  openBound: []
  editEdge: []
  deleteEdge: []
}>()
</script>

<template>
  <div
    v-if="visible"
    class="context-menu"
    :style="{ left: `${x}px`, top: `${y}px` }"
    role="menu"
    @click.stop
  >
    <template v-if="kind === 'canvas'">
      <button type="button" @click="emit('createNode')">在此处新建节点</button>
      <button type="button" disabled>粘贴节点</button>
      <button type="button" @click="emit('fitView')">适应画布</button>
      <button type="button" @click="emit('resetView')">重置视图</button>
    </template>

    <template v-else-if="kind === 'node' && node">
      <button type="button" @click="emit('editNode')">编辑节点</button>
      <button type="button" @click="emit('startEdge')">从此节点连线</button>
      <button type="button" @click="emit('duplicateNode')">复制节点</button>
      <button type="button" class="danger" @click="emit('deleteNode')">删除节点</button>
      <button type="button" :disabled="!node.bound_type || !node.bound_id" @click="emit('openBound')">打开绑定资料</button>
    </template>

    <template v-else-if="kind === 'edge' && edge">
      <button type="button" @click="emit('editEdge')">编辑关系</button>
      <button type="button" class="danger" @click="emit('deleteEdge')">删除关系</button>
    </template>
  </div>
</template>

<style scoped>
.context-menu {
  position: fixed;
  z-index: 50;
  display: grid;
  min-width: 168px;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 6px;
  background: #ffffff;
  box-shadow: 0 18px 36px rgb(15 23 42 / 18%);
}

button {
  border: 0;
  border-radius: 6px;
  padding: 8px 10px;
  background: transparent;
  color: #111827;
  font: inherit;
  font-size: 0.86rem;
  text-align: left;
  cursor: pointer;
}

button:hover {
  background: #eff6ff;
  color: #1d4ed8;
}

button.danger {
  color: #b42318;
}

button:disabled {
  color: #94a3b8;
  cursor: not-allowed;
}
</style>
