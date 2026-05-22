<script setup lang="ts">
import { RouterLink } from 'vue-router'

export type GraphToolMode = 'select' | 'node' | 'edge' | 'pan'

defineProps<{
  mode: GraphToolMode
  showGrid: boolean
  snapToGrid: boolean
  cleanMode: boolean
  zoomPercent: number
  isLoading: boolean
  writingPageUrl: string
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
  <nav class="graph-toolbar" data-graph-toolbar="true" aria-label="关系图工具栏">
    <section class="toolbar-group" aria-label="工具">
      <span class="group-label">工具</span>
      <div class="button-row">
        <button type="button" :class="{ active: mode === 'select' }" @click="emit('setMode', 'select')">选择</button>
        <button type="button" :class="{ active: mode === 'node' }" @click="emit('setMode', 'node')">新建</button>
        <button type="button" :class="{ active: mode === 'edge' }" @click="emit('setMode', 'edge')">连线</button>
        <button type="button" :class="{ active: mode === 'pan' }" @click="emit('setMode', 'pan')">平移</button>
      </div>
    </section>

    <section class="toolbar-group" aria-label="视图">
      <span class="group-label">视图</span>
      <div class="button-row">
        <button type="button" title="放大" @click="emit('zoomIn')">放大</button>
        <button type="button" title="缩小" @click="emit('zoomOut')">缩小</button>
        <button type="button" @click="emit('fitView')">适应画布</button>
        <button type="button" @click="emit('resetView')">重置视图</button>
        <span class="zoom-readout">{{ zoomPercent }}%</span>
      </div>
    </section>

    <section class="toolbar-group" aria-label="显示">
      <span class="group-label">显示</span>
      <div class="button-row">
        <button type="button" class="toggle-button" :class="{ active: showGrid }" @click="emit('toggleGrid')">网格</button>
        <button type="button" class="toggle-button" :class="{ active: snapToGrid }" @click="emit('toggleSnap')">吸附</button>
        <button type="button" class="toggle-button" :class="{ active: cleanMode }" @click="emit('toggleClean')">清爽模式</button>
      </div>
    </section>

    <section class="toolbar-group" aria-label="操作">
      <span class="group-label">操作</span>
      <div class="button-row">
        <button type="button" :disabled="isLoading" @click="emit('refresh')">刷新</button>
        <RouterLink class="toolbar-link" :to="writingPageUrl">返回写作页</RouterLink>
      </div>
    </section>
  </nav>
</template>

<style scoped>
.graph-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--zs-space-2);
  align-items: stretch;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-2);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
}

.toolbar-group {
  display: grid;
  gap: 5px;
  align-content: start;
  border-right: 1px solid var(--zs-color-border-soft);
  padding-right: var(--zs-space-2);
}

.toolbar-group:last-child {
  border-right: 0;
  padding-right: 0;
}

.group-label {
  color: var(--zs-color-text-muted);
  font-size: 0.7rem;
  font-weight: 900;
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

button,
.toolbar-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 31px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 10px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 750;
  text-decoration: none;
  cursor: pointer;
}

button:hover,
button.active,
.toolbar-link:hover {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-primary);
}

.toggle-button {
  position: relative;
  padding-left: 26px;
}

.toggle-button::before {
  position: absolute;
  left: 9px;
  width: 10px;
  height: 10px;
  border: 1px solid var(--zs-color-text-faint);
  border-radius: 999px;
  background: var(--zs-color-surface);
  content: '';
}

.toggle-button.active::before {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary);
  box-shadow: inset 0 0 0 2px var(--zs-color-surface);
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.zoom-readout {
  min-width: 48px;
  border-radius: var(--zs-radius-sm);
  padding: 7px 8px;
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-text);
  font-size: 0.8rem;
  font-weight: 900;
  text-align: center;
}
</style>
