<script setup lang="ts">
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
  boundTypeChanged: []
  createFromBinding: [boundType: Exclude<GraphNodeBoundType, 'custom'>, boundId: string]
}>()

const nodeTypes: GraphNodeType[] = ['character', 'setting', 'clue', 'timeline_event', 'organization', 'location', 'custom']
const boundTypes: Array<GraphNodeBoundType | ''> = ['', 'character', 'setting', 'clue', 'timeline_event', 'custom']
const visibilityOptions: GraphVisibility[] = ['normal', 'subtle', 'hidden']
const relationTypes: GraphEdgeRelationType[] = ['relationship', 'conflict', 'ally', 'family', 'belongs_to', 'controls', 'clue_related', 'timeline_related', 'setting_related', 'cause', 'custom']
const directions: GraphEdgeDirection[] = ['undirected', 'directed']
const lineStyles: GraphEdgeLineStyle[] = ['solid', 'dashed', 'dotted', 'arc']

function getBindingList(
  options: Record<'character' | 'setting' | 'clue' | 'timeline_event', BindingOption[]>,
  boundType: GraphNodeBoundType | null,
) {
  if (!boundType || boundType === 'custom') {
    return []
  }
  return options[boundType]
}

function handleCreateFromBinding(boundType: Exclude<GraphNodeBoundType, 'custom'>, boundId: string) {
  emit('createFromBinding', boundType, boundId)
}
</script>

<template>
  <aside class="graph-inspector">
    <template v-if="selectedNode">
      <header>
        <p>节点详情</p>
        <h2>{{ selectedNode.title }}</h2>
      </header>
      <div class="form-grid">
        <label class="wide"><span>标题</span><input v-model.trim="nodeDraft.title" type="text" /></label>
        <label><span>类型</span><select v-model="nodeDraft.node_type"><option v-for="type in nodeTypes" :key="type" :value="type">{{ graphNodeTypeLabels[type] }}</option></select></label>
        <label>
          <span>绑定对象类型</span>
          <select v-model="nodeDraft.bound_type" @change="emit('boundTypeChanged')">
            <option v-for="type in boundTypes" :key="type || 'none'" :value="type || null">
              {{ type ? graphNodeBoundTypeLabels[type] : '未绑定' }}
            </option>
          </select>
        </label>
        <label v-if="nodeDraft.bound_type && nodeDraft.bound_type !== 'custom'" class="wide">
          <span>绑定对象</span>
          <select v-model="nodeDraft.bound_id">
            <option value="">请选择绑定对象</option>
            <option v-for="item in getBindingList(bindingOptions, nodeDraft.bound_type)" :key="item.id" :value="item.id">{{ item.label }}</option>
          </select>
        </label>
        <label v-else class="wide"><span>绑定对象</span><input v-model.trim="nodeDraft.bound_id" type="text" placeholder="可选" /></label>
        <p v-if="nodeDraft.bound_type && nodeDraft.bound_type !== 'custom' && !nodeDraft.bound_id" class="hint wide">请选择绑定对象</p>
        <label class="wide"><span>简介</span><textarea v-model="nodeDraft.summary" rows="4" /></label>
        <label><span>颜色</span><input v-model.trim="nodeDraft.color" type="text" placeholder="#4f7cff" /></label>
        <label><span>大小</span><select v-model.number="nodeDraft.size"><option :value="1">1</option><option :value="2">2</option><option :value="3">3</option></select></label>
        <label><span>可见性</span><select v-model="nodeDraft.visibility"><option v-for="item in visibilityOptions" :key="item" :value="item">{{ graphVisibilityLabels[item] }}</option></select></label>
        <label><span>x</span><input v-model.number="nodeDraft.x" type="number" /></label>
        <label><span>y</span><input v-model.number="nodeDraft.y" type="number" /></label>
      </div>
      <div class="actions">
        <button type="button" class="primary" :disabled="isSaving || !nodeDraft.title.trim()" @click="emit('saveNode')">保存</button>
        <button type="button" :disabled="!selectedNode.bound_type || !selectedNode.bound_id" @click="emit('openBound')">打开绑定资料</button>
        <button type="button" class="danger" :disabled="isSaving" @click="emit('deleteNode')">删除</button>
      </div>
    </template>

    <template v-else-if="selectedEdge">
      <header>
        <p>关系详情</p>
        <h2>{{ selectedEdge.label || graphEdgeRelationLabels[selectedEdge.relation_type] }}</h2>
      </header>
      <div class="form-grid">
        <label class="wide"><span>起点节点</span><select v-model="edgeDraft.from_node_id"><option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.title }}</option></select></label>
        <label class="wide"><span>终点节点</span><select v-model="edgeDraft.to_node_id"><option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.title }}</option></select></label>
        <label><span>关系类型</span><select v-model="edgeDraft.relation_type"><option v-for="type in relationTypes" :key="type" :value="type">{{ graphEdgeRelationLabels[type] }}</option></select></label>
        <label><span>方向</span><select v-model="edgeDraft.direction"><option v-for="item in directions" :key="item" :value="item">{{ graphEdgeDirectionLabels[item] }}</option></select></label>
        <label><span>强度</span><input v-model.number="edgeDraft.strength" min="1" max="5" type="number" /></label>
        <label><span>线条样式</span><select v-model="edgeDraft.line_style"><option v-for="item in lineStyles" :key="item" :value="item">{{ graphEdgeLineStyleLabels[item] }}</option></select></label>
        <label class="wide"><span>标签</span><input v-model.trim="edgeDraft.label" type="text" /></label>
        <label><span>可见性</span><select v-model="edgeDraft.visibility"><option v-for="item in visibilityOptions" :key="item" :value="item">{{ graphVisibilityLabels[item] }}</option></select></label>
        <label class="wide"><span>批注</span><textarea v-model="edgeDraft.note" rows="4" /></label>
      </div>
      <div class="actions">
        <button type="button" class="primary" :disabled="isSaving || edgeDraft.from_node_id === edgeDraft.to_node_id" @click="emit('saveEdge')">保存</button>
        <button type="button" class="danger" :disabled="isSaving" @click="emit('deleteEdge')">删除</button>
      </div>
    </template>

    <template v-else>
      <section class="placeholder">
        <h2>请选择节点或关系查看详情。</h2>
      </section>
    </template>

    <GraphBindingPanel :options="bindingOptions" @create-from-binding="handleCreateFromBinding" />
  </aside>
</template>

<style scoped>
.graph-inspector {
  display: grid;
  align-content: start;
  gap: 14px;
  min-width: 0;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 14px;
  background: #ffffff;
  overflow: auto;
}

header p,
header h2,
.placeholder h2,
.hint {
  margin: 0;
}

header p {
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 800;
}

header h2,
.placeholder h2 {
  margin-top: 4px;
  color: #111827;
  font-size: 1rem;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

label {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.wide {
  grid-column: 1 / -1;
}

span {
  color: #475569;
  font-size: 0.78rem;
  font-weight: 800;
}

input,
select,
textarea,
button {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  padding: 8px 10px;
  background: #ffffff;
  color: #111827;
  font: inherit;
  font-size: 0.84rem;
}

textarea {
  line-height: 1.6;
  resize: vertical;
}

.hint {
  color: #b45309;
  font-size: 0.8rem;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

button {
  width: auto;
  font-weight: 800;
  cursor: pointer;
}

button.primary {
  border-color: #2563eb;
  background: #2563eb;
  color: #ffffff;
}

button.danger {
  border-color: #fecaca;
  background: #fff1f2;
  color: #b42318;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.placeholder {
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 14px;
  background: #f8fafc;
}
</style>
