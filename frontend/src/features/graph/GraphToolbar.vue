<script setup lang="ts">
export type GraphToolMode = 'select' | 'node' | 'edge' | 'pan'

defineProps<{
  mode: GraphToolMode
  showGrid: boolean
  snapToGrid: boolean
  cleanMode: boolean
  zoomPercent: number
  isLoading: boolean
}>()

const emit = defineEmits<{
  setMode: [mode: GraphToolMode]
  zoomIn: []
  zoomOut: []
  fitView: []
  resetView: []
  toggleGrid: []
  toggleSnap: []
  toggleClean: []
  refresh: []
}>()
</script>

<template>
  <nav class="graph-toolbar" aria-label="关系图工具栏">
    <div class="tool-group">
      <button type="button" :class="{ active: mode === 'select' }" @click="emit('setMode', 'select')">选择</button>
      <button type="button" :class="{ active: mode === 'node' }" @click="emit('setMode', 'node')">新建节点</button>
      <button type="button" :class="{ active: mode === 'edge' }" @click="emit('setMode', 'edge')">连线</button>
      <button type="button" :class="{ active: mode === 'pan' }" @click="emit('setMode', 'pan')">平移</button>
    </div>
    <div class="tool-group">
      <button type="button" title="放大" @click="emit('zoomIn')">放大</button>
      <button type="button" title="缩小" @click="emit('zoomOut')">缩小</button>
      <button type="button" @click="emit('fitView')">适应画布</button>
      <button type="button" @click="emit('resetView')">重置视图</button>
      <span class="zoom-readout">{{ zoomPercent }}%</span>
    </div>
    <div class="tool-group">
      <button type="button" :class="{ active: showGrid }" @click="emit('toggleGrid')">网格</button>
      <button type="button" :class="{ active: snapToGrid }" @click="emit('toggleSnap')">吸附</button>
      <button type="button" :class="{ active: cleanMode }" @click="emit('toggleClean')">纯净模式</button>
      <button type="button" :disabled="isLoading" @click="emit('refresh')">刷新</button>
    </div>
  </nav>
</template>

<style scoped>
.graph-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 8px;
  background: #ffffff;
}

.tool-group {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

button {
  min-height: 32px;
  border: 1px solid #d8dee9;
  border-radius: 7px;
  padding: 0 10px;
  background: #ffffff;
  color: #1f2937;
  font: inherit;
  font-size: 0.84rem;
  font-weight: 700;
  cursor: pointer;
}

button:hover,
button.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.zoom-readout {
  min-width: 48px;
  color: #64748b;
  font-size: 0.8rem;
  font-weight: 800;
  text-align: center;
}
</style>
