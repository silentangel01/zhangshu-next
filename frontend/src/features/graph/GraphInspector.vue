<script setup lang="ts">
import { reactive } from 'vue'

import type {
  GraphEdge,
  GraphEdgeDirection,
  GraphEdgeLineStyle,
  GraphEdgeRelationType,
  GraphNode,
  GraphNodeBoundType,
  GraphNodeType,
  GraphVisibility,
} from '@/entities/graph/types'
import {
  graphEdgeDirectionLabels,
  graphEdgeLineStyleLabels,
  graphEdgeRelationLabels,
  graphNodeBoundTypeLabels,
  graphNodeTypeLabels,
  graphVisibilityLabels,
} from '@/entities/graph/types'

import GraphBindingPanel, { type BindingOption } from './GraphBindingPanel.vue'

export interface NodeDraft {
  title: string
  node_type: GraphNodeType
  bound_type: GraphNodeBoundType | null
  bound_id: string
  summary: string
  x: number
  y: number
  width: number
  height: number
  color: string
  size: number
  visibility: GraphVisibility
}

export interface EdgeDraft {
  from_node_id: string
  to_node_id: string
  relation_type: GraphEdgeRelationType
  direction: GraphEdgeDirection
  strength: number
  label: string
  note: string
  line_style: GraphEdgeLineStyle
  visibility: GraphVisibility
}

defineProps<{
  selectedNode: GraphNode | null
  selectedEdge: GraphEdge | null
  nodeDraft: NodeDraft
  edgeDraft: EdgeDraft
  nodes: GraphNode[]
  bindingOptions: Record<'character' | 'setting' | 'clue' | 'timeline_event', BindingOption[]>
  isSaving: boolean
}>()

const emit = defineEmits<{
  saveNode: []
  deleteNode: []
  saveEdge: []
  deleteEdge: []
  openBound: []
  syncFromBound: []
  createMaterialFromNode: []
  boundTypeChanged: []
  boundSelectionChanged: []
  sizePresetChanged: []
  createFromBinding: [boundType: Exclude<GraphNodeBoundType, 'custom'>, boundId: string]
}>()

const nodeTypes: GraphNodeType[] = ['character', 'setting', 'clue', 'timeline_event', 'organization', 'location', 'custom']
const boundTypes: Array<GraphNodeBoundType | ''> = ['', 'character', 'setting', 'clue', 'timeline_event', 'custom']
const visibilityOptions: GraphVisibility[] = ['normal', 'subtle', 'hidden']
const relationTypes: GraphEdgeRelationType[] = ['relationship', 'conflict', 'ally', 'family', 'belongs_to', 'controls', 'clue_related', 'timeline_related', 'setting_related', 'cause', 'custom']
const directions: GraphEdgeDirection[] = ['undirected', 'directed']
const lineStyles: GraphEdgeLineStyle[] = ['solid', 'dashed', 'dotted', 'arc']
const reverseCreationLabels: Partial<Record<GraphNodeType, string>> = {
  character: '创建对应人物资料',
  setting: '创建对应设定',
  clue: '创建对应伏笔',
}

// ---------------------------------------------------------------------------
// Section collapse state (style & position collapsed by default)
// ---------------------------------------------------------------------------

const sectionOpen = reactive({
  description: true,
  binding: true,
  style: false,
  endpoints: true,
  relation: true,
})

function toggleSection(key: keyof typeof sectionOpen) {
  sectionOpen[key] = !sectionOpen[key]
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getBindingList(
  options: Record<'character' | 'setting' | 'clue' | 'timeline_event', BindingOption[]>,
  boundType: GraphNodeBoundType | null,
) {
  if (!boundType || boundType === 'custom') {
    return []
  }
  return options[boundType]
}

function canCreateMaterialFromNode(node: GraphNode) {
  return !node.bound_type && !node.bound_id && Boolean(reverseCreationLabels[node.node_type])
}

function handleCreateFromBinding(boundType: Exclude<GraphNodeBoundType, 'custom'>, boundId: string) {
  emit('createFromBinding', boundType, boundId)
}
</script>

<template>
  <aside class="graph-inspector" data-graph-inspector="true">
    <!-- ================================================================ -->
    <!-- NODE EDITING                                                     -->
    <!-- ================================================================ -->
    <template v-if="selectedNode">
      <header class="inspector-header">
        <div class="header-row">
          <span class="type-badge">{{ graphNodeTypeLabels[nodeDraft.node_type] }}</span>
        </div>
        <h2 class="node-title">{{ selectedNode.title }}</h2>
        <p v-if="nodeDraft.summary" class="node-summary">{{ nodeDraft.summary }}</p>
      </header>

      <!-- Description -->
      <section class="inspector-section">
        <button type="button" class="section-header" @click="toggleSection('description')">
          <span class="chevron" :class="{ open: sectionOpen.description }">▾</span>
          <span class="section-name">描述</span>
        </button>
        <Transition name="section-body">
          <div v-if="sectionOpen.description" class="section-body">
            <div class="form-grid">
              <label><span>类型</span><select v-model="nodeDraft.node_type"><option v-for="type in nodeTypes" :key="type" :value="type">{{ graphNodeTypeLabels[type] }}</option></select></label>
              <label><span>可见性</span><select v-model="nodeDraft.visibility"><option v-for="item in visibilityOptions" :key="item" :value="item">{{ graphVisibilityLabels[item] }}</option></select></label>
              <label class="wide"><span>简介</span><textarea v-model="nodeDraft.summary" rows="4" /></label>
            </div>
          </div>
        </Transition>
      </section>

      <!-- Binding -->
      <section class="inspector-section">
        <button type="button" class="section-header" @click="toggleSection('binding')">
          <span class="chevron" :class="{ open: sectionOpen.binding }">▾</span>
          <span class="section-name">绑定资料</span>
          <span v-if="nodeDraft.bound_type" class="section-count">已绑定</span>
        </button>
        <Transition name="section-body">
          <div v-if="sectionOpen.binding" class="section-body">
            <div class="form-grid">
              <label>
                <span>绑定类型</span>
                <select v-model="nodeDraft.bound_type" @change="emit('boundTypeChanged')">
                  <option v-for="type in boundTypes" :key="type || 'none'" :value="type || null">
                    {{ type ? graphNodeBoundTypeLabels[type] : '未绑定' }}
                  </option>
                </select>
              </label>
              <label v-if="nodeDraft.bound_type && nodeDraft.bound_type !== 'custom'" class="wide">
                <span>绑定对象</span>
                <select v-model="nodeDraft.bound_id" @change="emit('boundSelectionChanged')">
                  <option value="">请选择绑定对象</option>
                  <option v-for="item in getBindingList(bindingOptions, nodeDraft.bound_type)" :key="item.id" :value="item.id">{{ item.label }}</option>
                </select>
              </label>
              <label v-else class="wide"><span>绑定对象</span><input v-model.trim="nodeDraft.bound_id" type="text" placeholder="可选" /></label>
              <p v-if="nodeDraft.bound_type && nodeDraft.bound_type !== 'custom' && !nodeDraft.bound_id" class="hint wide">请选择绑定对象</p>
              <button
                v-if="nodeDraft.bound_type && nodeDraft.bound_type !== 'custom' && nodeDraft.bound_id"
                type="button"
                class="wide action-button"
                :disabled="isSaving"
                @click="emit('syncFromBound')"
              >
                从绑定资料同步
              </button>
              <button
                v-if="canCreateMaterialFromNode(selectedNode)"
                type="button"
                class="wide action-button"
                :disabled="isSaving || !nodeDraft.title.trim()"
                @click="emit('createMaterialFromNode')"
              >
                {{ reverseCreationLabels[selectedNode.node_type] }}
              </button>
            </div>
          </div>
        </Transition>
      </section>

      <!-- Style & Position (collapsed by default) -->
      <section class="inspector-section">
        <button type="button" class="section-header" @click="toggleSection('style')">
          <span class="chevron" :class="{ open: sectionOpen.style }">▾</span>
          <span class="section-name">样式与位置</span>
        </button>
        <Transition name="section-body">
          <div v-if="sectionOpen.style" class="section-body">
            <div class="form-grid">
              <label><span>颜色</span><input v-model.trim="nodeDraft.color" type="text" placeholder="#4f7cff" /></label>
              <label><span>大小预设</span><select v-model.number="nodeDraft.size" @change="emit('sizePresetChanged')"><option :value="1">1</option><option :value="2">2</option><option :value="3">3</option></select></label>
              <label><span>宽度</span><input v-model.number="nodeDraft.width" min="80" max="420" type="number" /></label>
              <label><span>高度</span><input v-model.number="nodeDraft.height" min="40" max="260" type="number" /></label>
              <label><span>X</span><input v-model.number="nodeDraft.x" type="number" /></label>
              <label><span>Y</span><input v-model.number="nodeDraft.y" type="number" /></label>
            </div>
          </div>
        </Transition>
      </section>

      <div class="inspector-actions">
        <button type="button" class="action-primary" :disabled="isSaving || !nodeDraft.title.trim()" @click="emit('saveNode')">保存</button>
        <button type="button" class="action-secondary" :disabled="!selectedNode.bound_type || !selectedNode.bound_id" @click="emit('openBound')">打开绑定资料</button>
        <button type="button" class="action-danger" :disabled="isSaving" @click="emit('deleteNode')">删除</button>
      </div>
    </template>

    <!-- ================================================================ -->
    <!-- EDGE EDITING                                                     -->
    <!-- ================================================================ -->
    <template v-else-if="selectedEdge">
      <header class="inspector-header">
        <div class="header-row">
          <span class="type-badge edge-badge">关系</span>
        </div>
        <h2 class="node-title">{{ selectedEdge.label || graphEdgeRelationLabels[selectedEdge.relation_type] }}</h2>
      </header>

      <!-- Endpoints -->
      <section class="inspector-section">
        <button type="button" class="section-header" @click="toggleSection('endpoints')">
          <span class="chevron" :class="{ open: sectionOpen.endpoints }">▾</span>
          <span class="section-name">端点</span>
        </button>
        <Transition name="section-body">
          <div v-if="sectionOpen.endpoints" class="section-body">
            <div class="form-grid">
              <label class="wide"><span>起点节点</span><select v-model="edgeDraft.from_node_id"><option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.title }}</option></select></label>
              <label class="wide"><span>终点节点</span><select v-model="edgeDraft.to_node_id"><option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.title }}</option></select></label>
            </div>
          </div>
        </Transition>
      </section>

      <!-- Relation Properties -->
      <section class="inspector-section">
        <button type="button" class="section-header" @click="toggleSection('relation')">
          <span class="chevron" :class="{ open: sectionOpen.relation }">▾</span>
          <span class="section-name">关系属性</span>
        </button>
        <Transition name="section-body">
          <div v-if="sectionOpen.relation" class="section-body">
            <div class="form-grid">
              <label><span>关系类型</span><select v-model="edgeDraft.relation_type"><option v-for="type in relationTypes" :key="type" :value="type">{{ graphEdgeRelationLabels[type] }}</option></select></label>
              <label><span>方向</span><select v-model="edgeDraft.direction"><option v-for="item in directions" :key="item" :value="item">{{ graphEdgeDirectionLabels[item] }}</option></select></label>
              <label><span>强度</span><input v-model.number="edgeDraft.strength" min="1" max="5" type="number" /></label>
              <label><span>线条样式</span><select v-model="edgeDraft.line_style"><option v-for="item in lineStyles" :key="item" :value="item">{{ graphEdgeLineStyleLabels[item] }}</option></select></label>
              <label class="wide"><span>标签</span><input v-model.trim="edgeDraft.label" type="text" /></label>
              <label><span>可见性</span><select v-model="edgeDraft.visibility"><option v-for="item in visibilityOptions" :key="item" :value="item">{{ graphVisibilityLabels[item] }}</option></select></label>
              <label class="wide"><span>批注</span><textarea v-model="edgeDraft.note" rows="4" /></label>
            </div>
          </div>
        </Transition>
      </section>

      <div class="inspector-actions">
        <button type="button" class="action-primary" :disabled="isSaving || edgeDraft.from_node_id === edgeDraft.to_node_id" @click="emit('saveEdge')">保存</button>
        <button type="button" class="action-danger" :disabled="isSaving" @click="emit('deleteEdge')">删除</button>
      </div>
    </template>

    <!-- ================================================================ -->
    <!-- EMPTY STATE                                                      -->
    <!-- ================================================================ -->
    <template v-else>
      <p class="empty-hint">选择画布上的节点或关系以编辑属性。</p>
      <GraphBindingPanel :options="bindingOptions" @create-from-binding="handleCreateFromBinding" />
    </template>
  </aside>
</template>

<style scoped>
/* =========================================================================
   Graph Inspector v2 — Professional writing-tool inspector
   ========================================================================= */

.graph-inspector {
  display: grid;
  align-content: start;
  gap: var(--zs-space-3);
  min-width: 0;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-3);
  background: var(--zs-color-surface);
  overflow: auto;
}

/* --- Header --- */

.inspector-header {
  display: grid;
  gap: 6px;
  padding-bottom: var(--zs-space-3);
  border-bottom: 1px solid var(--zs-color-border-soft);
}

.header-row {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
}

.type-badge {
  display: inline-flex;
  align-items: center;
  border-radius: var(--zs-radius-sm);
  padding: 2px 8px;
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-primary);
  font-size: 0.72rem;
  font-weight: 700;
}

.edge-badge {
  background: var(--zs-module-graph);
  color: #fff;
}

.node-title {
  margin: 0;
  color: var(--zs-color-text);
  font-size: 1.3rem;
  font-weight: 700;
  line-height: 1.3;
  word-break: break-word;
}

.node-summary {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.84rem;
  font-style: italic;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* --- Collapsible sections --- */

.inspector-section {
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  min-height: 36px;
  border: none;
  border-radius: 0;
  padding: 6px 10px;
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
  transition: background var(--zs-duration-fast) var(--zs-ease-standard);
}

.section-header:hover {
  background: var(--zs-color-surface-muted);
}

.chevron {
  display: inline-block;
  flex-shrink: 0;
  width: 14px;
  color: var(--zs-color-text-faint);
  font-size: 0.7rem;
  text-align: center;
  transition: transform 0.2s ease;
}

.chevron.open {
  transform: rotate(0deg);
}

.chevron:not(.open) {
  transform: rotate(-90deg);
}

.section-name {
  color: var(--zs-color-text);
  font-weight: 700;
}

.section-count {
  margin-left: auto;
  border-radius: var(--zs-radius-sm);
  padding: 1px 6px;
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-primary);
  font-size: 0.66rem;
  font-weight: 700;
}

/* Section body + form grid */

.section-body {
  padding: 10px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

/* --- Form fields --- */

label {
  display: grid;
  gap: 4px;
  min-width: 0;
}

label > span {
  color: var(--zs-color-text-faint);
  font-size: 0.74rem;
  font-weight: 700;
}

.wide {
  grid-column: 1 / -1;
}

input,
select,
textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 7px 10px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.84rem;
}

textarea {
  line-height: 1.7;
  resize: vertical;
}

input:focus,
select:focus,
textarea:focus {
  border-color: var(--zs-color-primary);
  outline: none;
}

.hint {
  margin: 0;
  color: var(--zs-color-warning);
  font-size: 0.78rem;
}

/* --- Action buttons within sections (sync, reverse create) --- */

.action-button {
  min-height: 32px;
  border-color: var(--zs-color-border) !important;
  background: var(--zs-color-surface) !important;
  color: var(--zs-color-primary) !important;
  font-weight: 600;
  cursor: pointer;
  transition:
    border-color var(--zs-duration-fast) var(--zs-ease-standard),
    background var(--zs-duration-fast) var(--zs-ease-standard);
}

.action-button:hover:not(:disabled) {
  border-color: var(--zs-color-primary) !important;
  background: var(--zs-color-primary-soft) !important;
}

/* --- Sticky action bar --- */

.inspector-actions {
  display: flex;
  gap: 8px;
  padding-top: var(--zs-space-3);
  border-top: 1px solid var(--zs-color-border-soft);
  position: sticky;
  bottom: 0;
  background: var(--zs-color-surface);
  z-index: 2;
}

.inspector-actions button {
  min-height: 34px;
  border-radius: var(--zs-radius-sm);
  padding: 0 12px;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}

.action-primary {
  border: 1px solid var(--zs-color-primary);
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.action-primary:hover:not(:disabled) {
  background: var(--zs-color-primary-hover);
  border-color: var(--zs-color-primary-hover);
}

.action-secondary {
  border: 1px solid var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.action-secondary:hover:not(:disabled) {
  border-color: var(--zs-color-border-strong);
  background: var(--zs-color-surface-soft);
}

.action-danger {
  border: 1px solid var(--zs-color-danger);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
}

.action-danger:hover:not(:disabled) {
  background: var(--zs-color-danger);
  color: var(--zs-color-on-primary);
}

.inspector-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

/* --- Empty state --- */

.empty-hint {
  margin: 0;
  padding: var(--zs-space-3) var(--zs-space-2);
  color: var(--zs-color-text-faint);
  font-size: 0.84rem;
  text-align: center;
}

/* --- Section body transition --- */

.section-body-expand-enter-active,
.section-body-expand-leave-active {
  transition:
    max-height 0.2s ease,
    opacity 0.15s ease,
    padding 0.2s ease;
  overflow: hidden;
}

.section-body-expand-enter-from,
.section-body-expand-leave-to {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.section-body-expand-enter-to,
.section-body-expand-leave-from {
  max-height: 600px;
  opacity: 1;
}
</style>
