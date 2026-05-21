<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { listProjectCharacters } from '@/entities/character/api'
import type { Character } from '@/entities/character/types'
import { listProjectClues } from '@/entities/clue/api'
import type { Clue } from '@/entities/clue/types'
import {
  createGraphEdge,
  createGraphNode,
  deleteGraphEdge,
  deleteGraphNode,
  listGraphEdges,
  listGraphNodes,
  updateGraphEdge,
  updateGraphNode,
} from '@/entities/graph/api'
import type {
  GraphEdge,
  GraphEdgeCreatePayload,
  GraphNode,
  GraphNodeBoundType,
  GraphNodeCreatePayload,
  GraphNodeType,
  GraphVisibility,
} from '@/entities/graph/types'
import {
  graphEdgeRelationLabels,
  graphNodeBoundTypeLabels,
  graphNodeTypeLabels,
  graphVisibilityLabels,
} from '@/entities/graph/types'
import { getProject } from '@/entities/project/api'
import type { Project } from '@/entities/project/types'
import { listProjectSettings } from '@/entities/setting/api'
import type { SettingItem } from '@/entities/setting/types'
import { listProjectTimelineEvents } from '@/entities/timeline/api'
import type { TimelineEvent } from '@/entities/timeline/types'
import GraphCanvas from '@/features/graph/GraphCanvas.vue'
import GraphInspector, { type EdgeDraft, type NodeDraft } from '@/features/graph/GraphInspector.vue'
import GraphToolbar, { type GraphToolMode } from '@/features/graph/GraphToolbar.vue'
import type { BindingOption } from '@/features/graph/GraphBindingPanel.vue'

type Point = { x: number; y: number }
type BindingKey = 'character' | 'setting' | 'clue' | 'timeline_event'

const route = useRoute()
const router = useRouter()
const canvasRef = ref<InstanceType<typeof GraphCanvas> | null>(null)

const project = ref<Project | null>(null)
const nodes = ref<GraphNode[]>([])
const edges = ref<GraphEdge[]>([])
const characters = ref<Character[]>([])
const settings = ref<SettingItem[]>([])
const clues = ref<Clue[]>([])
const timelineEvents = ref<TimelineEvent[]>([])

const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const mode = ref<GraphToolMode>('select')
const showGrid = ref(true)
const snapToGrid = ref(true)
const cleanMode = ref(false)
const zoomPercent = ref(100)
const selectedNodeId = ref<string | null>(null)
const selectedEdgeId = ref<string | null>(null)

const filters = reactive({
  keyword: '',
  nodeType: '' as GraphNodeType | '',
  visibility: '' as GraphVisibility | '',
})

const nodeDraft = reactive<NodeDraft>({
  title: '',
  node_type: 'custom',
  bound_type: null,
  bound_id: '',
  summary: '',
  x: 0,
  y: 0,
  color: '',
  size: 1,
  visibility: 'normal',
})

const edgeDraft = reactive<EdgeDraft>({
  from_node_id: '',
  to_node_id: '',
  relation_type: 'relationship',
  direction: 'undirected',
  strength: 1,
  label: '',
  note: '',
  line_style: 'solid',
  visibility: 'normal',
})

const nodeTypes: GraphNodeType[] = ['character', 'setting', 'clue', 'timeline_event', 'organization', 'location', 'custom']
const visibilityOptions: GraphVisibility[] = ['normal', 'subtle', 'hidden']

const projectId = computed(() => {
  const value = route.params.projectId
  return (Array.isArray(value) ? value[0] : value) ?? ''
})

const nodeMap = computed(() => new Map(nodes.value.map((node) => [node.id, node] as const)))
const edgeMap = computed(() => new Map(edges.value.map((edge) => [edge.id, edge] as const)))
const selectedNode = computed(() => selectedNodeId.value ? nodeMap.value.get(selectedNodeId.value) ?? null : null)
const selectedEdge = computed(() => selectedEdgeId.value ? edgeMap.value.get(selectedEdgeId.value) ?? null : null)

const visibleNodes = computed(() => nodes.value.filter((node) => node.visibility !== 'hidden'))

const filteredNodes = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  return nodes.value
    .filter((node) => {
      if (filters.nodeType && node.node_type !== filters.nodeType) {
        return false
      }
      if (filters.visibility && node.visibility !== filters.visibility) {
        return false
      }
      if (!keyword) {
        return true
      }
      return [node.title, node.summary, node.bound_id ?? ''].some((value) => value.toLowerCase().includes(keyword))
    })
    .sort((left, right) => left.title.localeCompare(right.title, 'zh-Hans-CN'))
})

const bindingOptions = computed<Record<BindingKey, BindingOption[]>>(() => ({
  character: characters.value.map((item) => ({ id: item.id, label: item.name, summary: item.summary })),
  setting: settings.value.map((item) => ({ id: item.id, label: item.title, summary: item.summary })),
  clue: clues.value.map((item) => ({ id: item.id, label: item.title, summary: item.description })),
  timeline_event: timelineEvents.value.map((item) => ({ id: item.id, label: item.title, summary: item.description })),
}))

onMounted(() => {
  void loadAll()
})

watch(projectId, () => {
  clearSelection()
  void loadAll()
})

watch(selectedNode, (node) => {
  if (node) {
    applyNodeToDraft(node)
  }
})

watch(selectedEdge, (edge) => {
  if (edge) {
    applyEdgeToDraft(edge)
  }
})

async function loadAll() {
  if (!projectId.value) {
    return
  }
  isLoading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const [projectDetail, graphNodes, graphEdges] = await Promise.all([
      getProject(projectId.value),
      listGraphNodes(projectId.value),
      listGraphEdges(projectId.value),
    ])
    project.value = projectDetail
    nodes.value = graphNodes
    edges.value = graphEdges
    reconcileSelection()
    await loadBindingData()
  } catch (error) {
    void error
    errorMessage.value = '关系图加载失败，请稍后重试。'
  } finally {
    isLoading.value = false
  }
}

async function loadBindingData() {
  const [characterResult, settingResult, clueResult, timelineResult] = await Promise.allSettled([
    listProjectCharacters(projectId.value),
    listProjectSettings(projectId.value),
    listProjectClues(projectId.value),
    listProjectTimelineEvents(projectId.value),
  ])
  if (characterResult.status === 'fulfilled') {
    characters.value = characterResult.value
  }
  if (settingResult.status === 'fulfilled') {
    settings.value = settingResult.value
  }
  if (clueResult.status === 'fulfilled') {
    clues.value = clueResult.value
  }
  if (timelineResult.status === 'fulfilled') {
    timelineEvents.value = timelineResult.value
  }
}

function reconcileSelection() {
  if (selectedNodeId.value && !nodeMap.value.has(selectedNodeId.value)) {
    selectedNodeId.value = null
  }
  if (selectedEdgeId.value && !edgeMap.value.has(selectedEdgeId.value)) {
    selectedEdgeId.value = null
  }
}

function selectNode(node: GraphNode) {
  selectedNodeId.value = node.id
  selectedEdgeId.value = null
  applyNodeToDraft(node)
}

function selectEdge(edge: GraphEdge) {
  selectedEdgeId.value = edge.id
  selectedNodeId.value = null
  applyEdgeToDraft(edge)
}

function clearSelection() {
  selectedNodeId.value = null
  selectedEdgeId.value = null
}

function applyNodeToDraft(node: GraphNode) {
  nodeDraft.title = node.title
  nodeDraft.node_type = node.node_type
  nodeDraft.bound_type = node.bound_type
  nodeDraft.bound_id = node.bound_id ?? ''
  nodeDraft.summary = node.summary
  nodeDraft.x = Math.round(node.x)
  nodeDraft.y = Math.round(node.y)
  nodeDraft.color = node.color ?? ''
  nodeDraft.size = clamp(Math.round(node.size), 1, 3)
  nodeDraft.visibility = node.visibility
}

function applyEdgeToDraft(edge: GraphEdge) {
  edgeDraft.from_node_id = edge.from_node_id
  edgeDraft.to_node_id = edge.to_node_id
  edgeDraft.relation_type = edge.relation_type
  edgeDraft.direction = edge.direction
  edgeDraft.strength = edge.strength
  edgeDraft.label = edge.label
  edgeDraft.note = edge.note
  edgeDraft.line_style = edge.line_style
  edgeDraft.visibility = edge.visibility
}

async function createNodeAt(point: Point, overrides: Partial<GraphNodeCreatePayload> = {}) {
  const payload: GraphNodeCreatePayload = {
    title: overrides.title ?? '新节点',
    node_type: overrides.node_type ?? 'custom',
    bound_type: overrides.bound_type ?? null,
    bound_id: overrides.bound_id ?? null,
    summary: overrides.summary ?? '',
    x: safeCoordinate(point.x),
    y: safeCoordinate(point.y),
    color: overrides.color ?? null,
    size: overrides.size ?? 1,
    visibility: overrides.visibility ?? 'normal',
  }
  try {
    isSaving.value = true
    const node = await createGraphNode(projectId.value, payload)
    upsertNode(node)
    selectNode(node)
    mode.value = 'select'
    successMessage.value = '节点已创建'
    errorMessage.value = ''
  } catch (error) {
    void error
    errorMessage.value = '节点保存失败，请重试。'
  } finally {
    isSaving.value = false
  }
}

async function createEdgeBetween(fromNodeId: string, toNodeId: string) {
  if (fromNodeId === toNodeId) {
    return
  }
  const payload: GraphEdgeCreatePayload = {
    from_node_id: fromNodeId,
    to_node_id: toNodeId,
    relation_type: 'relationship',
    direction: 'undirected',
    strength: 1,
    label: '',
    note: '',
    line_style: 'solid',
    visibility: 'normal',
  }
  try {
    isSaving.value = true
    const edge = await createGraphEdge(projectId.value, payload)
    upsertEdge(edge)
    selectEdge(edge)
    mode.value = 'select'
    successMessage.value = '关系已创建'
    errorMessage.value = ''
  } catch (error) {
    void error
    errorMessage.value = '关系保存失败，请重试。'
  } finally {
    isSaving.value = false
  }
}

async function saveNodePosition(node: GraphNode, x: number, y: number, previous: Point) {
  const index = nodes.value.findIndex((item) => item.id === node.id)
  if (index === -1) {
    return
  }
  const current = nodes.value[index]
  if (!current) {
    return
  }
  const optimistic: GraphNode = { ...current, x: safeCoordinate(x), y: safeCoordinate(y) }
  nodes.value.splice(index, 1, optimistic)
  if (selectedNodeId.value === node.id) {
    applyNodeToDraft(optimistic)
  }
  try {
    const saved = await updateGraphNode(node.id, { x: optimistic.x, y: optimistic.y })
    upsertNode(saved)
    successMessage.value = '节点位置已保存'
    errorMessage.value = ''
  } catch (error) {
    void error
    nodes.value.splice(index, 1, { ...node, x: previous.x, y: previous.y })
    errorMessage.value = '节点位置保存失败，请重试'
  }
}

async function saveSelectedNode() {
  if (!selectedNode.value) {
    return
  }
  const title = nodeDraft.title.trim()
  if (!title) {
    errorMessage.value = '节点标题不能为空。'
    return
  }
  try {
    isSaving.value = true
    const saved = await updateGraphNode(selectedNode.value.id, {
      title,
      node_type: nodeDraft.node_type,
      bound_type: nodeDraft.bound_type,
      bound_id: nodeDraft.bound_id.trim() || null,
      summary: nodeDraft.summary,
      x: safeCoordinate(nodeDraft.x),
      y: safeCoordinate(nodeDraft.y),
      color: nodeDraft.color.trim() || null,
      size: clamp(Math.round(nodeDraft.size), 1, 3),
      visibility: nodeDraft.visibility,
    })
    upsertNode(saved)
    selectNode(saved)
    successMessage.value = '已保存'
    errorMessage.value = ''
  } catch (error) {
    void error
    errorMessage.value = '节点保存失败，请重试。'
  } finally {
    isSaving.value = false
  }
}

async function saveSelectedEdge() {
  if (!selectedEdge.value) {
    return
  }
  if (!edgeDraft.from_node_id || !edgeDraft.to_node_id || edgeDraft.from_node_id === edgeDraft.to_node_id) {
    errorMessage.value = '请选择不同的起点节点和终点节点。'
    return
  }
  try {
    isSaving.value = true
    const saved = await updateGraphEdge(selectedEdge.value.id, {
      from_node_id: edgeDraft.from_node_id,
      to_node_id: edgeDraft.to_node_id,
      relation_type: edgeDraft.relation_type,
      direction: edgeDraft.direction,
      strength: clamp(Math.round(edgeDraft.strength), 1, 5),
      label: edgeDraft.label,
      note: edgeDraft.note,
      line_style: edgeDraft.line_style,
      visibility: edgeDraft.visibility,
    })
    upsertEdge(saved)
    selectEdge(saved)
    successMessage.value = '已保存'
    errorMessage.value = ''
  } catch (error) {
    void error
    errorMessage.value = '关系保存失败，请重试。'
  } finally {
    isSaving.value = false
  }
}

async function deleteSelectedNode(node = selectedNode.value) {
  if (!node) {
    return
  }
  if (!window.confirm('确认删除该节点吗？相关关系也可能被删除或隐藏。')) {
    return
  }
  try {
    isSaving.value = true
    const deleted = await deleteGraphNode(node.id)
    nodes.value = nodes.value.filter((item) => item.id !== deleted.id)
    edges.value = edges.value.filter((edge) => edge.from_node_id !== deleted.id && edge.to_node_id !== deleted.id)
    clearSelection()
    successMessage.value = '节点已删除'
    errorMessage.value = ''
  } catch (error) {
    void error
    errorMessage.value = '节点保存失败，请重试。'
  } finally {
    isSaving.value = false
  }
}

async function deleteSelectedEdge(edge = selectedEdge.value) {
  if (!edge) {
    return
  }
  if (!window.confirm('确认删除该关系吗？')) {
    return
  }
  try {
    isSaving.value = true
    const deleted = await deleteGraphEdge(edge.id)
    edges.value = edges.value.filter((item) => item.id !== deleted.id)
    clearSelection()
    successMessage.value = '关系已删除'
    errorMessage.value = ''
  } catch (error) {
    void error
    errorMessage.value = '关系保存失败，请重试。'
  } finally {
    isSaving.value = false
  }
}

function duplicateNode(node: GraphNode) {
  void createNodeAt({ x: node.x + 40, y: node.y + 40 }, {
    title: `${node.title} 副本`,
    node_type: node.node_type,
    bound_type: node.bound_type,
    bound_id: node.bound_id,
    summary: node.summary,
    color: node.color,
    size: node.size,
    visibility: node.visibility,
  })
}

function createFromBinding(boundType: Exclude<GraphNodeBoundType, 'custom'>, boundId: string) {
  const option = bindingOptions.value[boundType].find((item) => item.id === boundId)
  if (!option) {
    errorMessage.value = '绑定对象不存在或已被删除。'
    return
  }
  const center = canvasRef.value?.getViewportCenter() ?? { x: 320, y: 220 }
  void createNodeAt(center, {
    title: option.label,
    node_type: boundType,
    bound_type: boundType,
    bound_id: option.id,
    summary: option.summary,
  })
}

function handleBoundTypeChanged() {
  if (!nodeDraft.bound_type || nodeDraft.bound_type === 'custom') {
    nodeDraft.bound_id = ''
    return
  }
  const valid = bindingOptions.value[nodeDraft.bound_type].some((item) => item.id === nodeDraft.bound_id)
  if (!valid) {
    nodeDraft.bound_id = ''
  }
}

function openBoundMaterial(node = selectedNode.value) {
  if (!node?.bound_type || !node.bound_id) {
    errorMessage.value = '绑定对象不存在或已被删除。'
    return
  }
  const routeMap: Partial<Record<GraphNodeBoundType, string>> = {
    character: `/projects/${projectId.value}/characters`,
    setting: `/projects/${projectId.value}/settings`,
    clue: `/projects/${projectId.value}/clues`,
    timeline_event: `/projects/${projectId.value}/timeline`,
  }
  const target = routeMap[node.bound_type]
  if (!target) {
    errorMessage.value = '该绑定类型暂无可打开的资料页。'
    return
  }
  void router.push(target).then(() => {
    window.setTimeout(() => {
      window.alert('已跳转到对应资料库，请在列表中查看绑定对象。')
    }, 0)
  })
}

function upsertNode(node: GraphNode) {
  const index = nodes.value.findIndex((item) => item.id === node.id)
  if (index === -1) {
    nodes.value.push(node)
  } else {
    nodes.value.splice(index, 1, node)
  }
}

function upsertEdge(edge: GraphEdge) {
  const index = edges.value.findIndex((item) => item.id === edge.id)
  if (index === -1) {
    edges.value.push(edge)
  } else {
    edges.value.splice(index, 1, edge)
  }
}

function safeCoordinate(value: number) {
  return clamp(Math.round(Number.isFinite(value) ? value : 0), -20000, 20000)
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}
</script>

<template>
  <main class="graph-page">
    <header class="page-header">
      <div>
        <RouterLink class="back-link" :to="`/projects/${projectId}`">返回写作页</RouterLink>
        <h1>关系图</h1>
        <p>用画布管理人物、设定、伏笔、时间轴事件之间的关系。</p>
        <span v-if="project">{{ project.title }}</span>
      </div>
    </header>

    <GraphToolbar
      :mode="mode"
      :show-grid="showGrid"
      :snap-to-grid="snapToGrid"
      :clean-mode="cleanMode"
      :zoom-percent="zoomPercent"
      :is-loading="isLoading"
      @set-mode="mode = $event"
      @zoom-in="canvasRef?.zoomIn()"
      @zoom-out="canvasRef?.zoomOut()"
      @fit-view="canvasRef?.fitView()"
      @reset-view="canvasRef?.resetView()"
      @toggle-grid="showGrid = !showGrid"
      @toggle-snap="snapToGrid = !snapToGrid"
      @toggle-clean="cleanMode = !cleanMode"
      @refresh="loadAll"
    />

    <p v-if="errorMessage" class="status error">{{ errorMessage }}</p>
    <p v-else-if="successMessage" class="status success">{{ successMessage }}</p>

    <section class="workspace">
      <aside class="left-panel">
        <header>
          <h2>节点列表</h2>
          <span>{{ filteredNodes.length }}</span>
        </header>
        <label><span>搜索</span><input v-model.trim="filters.keyword" type="search" placeholder="搜索标题、简介或绑定 ID" /></label>
        <label><span>类型筛选</span><select v-model="filters.nodeType"><option value="">全部类型</option><option v-for="type in nodeTypes" :key="type" :value="type">{{ graphNodeTypeLabels[type] }}</option></select></label>
        <label><span>可见性筛选</span><select v-model="filters.visibility"><option value="">全部可见性</option><option v-for="item in visibilityOptions" :key="item" :value="item">{{ graphVisibilityLabels[item] }}</option></select></label>
        <div class="node-list">
          <button
            v-for="node in filteredNodes"
            :key="node.id"
            type="button"
            :class="{ active: selectedNodeId === node.id, hidden: node.visibility === 'hidden' }"
            @click="selectNode(node)"
          >
            <strong>{{ node.title }}</strong>
            <small>
              {{ graphNodeTypeLabels[node.node_type] }}
              <span v-if="node.bound_type"> · {{ graphNodeBoundTypeLabels[node.bound_type] }}</span>
            </small>
          </button>
          <p v-if="filteredNodes.length === 0" class="empty-list">没有符合条件的节点。</p>
        </div>
      </aside>

      <GraphCanvas
        ref="canvasRef"
        :nodes="nodes"
        :edges="edges"
        :selected-node-id="selectedNodeId"
        :selected-edge-id="selectedEdgeId"
        :mode="mode"
        :show-grid="showGrid"
        :snap-to-grid="snapToGrid"
        :clean-mode="cleanMode"
        @select-node="selectNode"
        @select-edge="selectEdge"
        @clear-selection="clearSelection"
        @create-node="createNodeAt"
        @create-edge="createEdgeBetween"
        @save-node-position="saveNodePosition"
        @delete-node="deleteSelectedNode"
        @delete-edge="deleteSelectedEdge"
        @duplicate-node="duplicateNode"
        @open-bound="openBoundMaterial"
        @zoom-changed="zoomPercent = $event"
      />

      <GraphInspector
        :selected-node="selectedNode"
        :selected-edge="selectedEdge"
        :node-draft="nodeDraft"
        :edge-draft="edgeDraft"
        :nodes="visibleNodes"
        :binding-options="bindingOptions"
        :is-saving="isSaving"
        @save-node="saveSelectedNode"
        @delete-node="deleteSelectedNode"
        @save-edge="saveSelectedEdge"
        @delete-edge="deleteSelectedEdge"
        @open-bound="openBoundMaterial"
        @bound-type-changed="handleBoundTypeChanged"
        @create-from-binding="createFromBinding"
      />
    </section>
  </main>
</template>

<style scoped>
.graph-page {
  display: grid;
  gap: 12px;
  min-height: 100vh;
  box-sizing: border-box;
  padding: 18px;
  background: #f5f7fb;
  color: #111827;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.back-link {
  display: inline-flex;
  margin-bottom: 8px;
  color: #2563eb;
  font-size: 0.86rem;
  font-weight: 800;
  text-decoration: none;
}

h1,
h2,
p {
  margin: 0;
}

h1 {
  font-size: 1.7rem;
}

.page-header p {
  margin-top: 6px;
  color: #475569;
  line-height: 1.6;
}

.page-header span {
  display: inline-block;
  margin-top: 4px;
  color: #64748b;
  font-size: 0.86rem;
  font-weight: 700;
}

.status {
  border-radius: 8px;
  padding: 9px 12px;
  font-size: 0.86rem;
}

.status.error {
  background: #fef2f2;
  color: #b42318;
}

.status.success {
  background: #ecfdf5;
  color: #047857;
}

.workspace {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 340px;
  gap: 12px;
  min-height: calc(100vh - 180px);
}

.left-panel {
  display: grid;
  align-content: start;
  gap: 12px;
  min-width: 0;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
  overflow: auto;
}

.left-panel header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.left-panel h2 {
  font-size: 1rem;
}

.left-panel header span {
  border-radius: 999px;
  padding: 3px 8px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 0.76rem;
  font-weight: 800;
}

.left-panel label {
  display: grid;
  gap: 6px;
}

.left-panel label span {
  color: #475569;
  font-size: 0.78rem;
  font-weight: 800;
}

input,
select {
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

.node-list {
  display: grid;
  gap: 8px;
}

.node-list button {
  display: grid;
  gap: 4px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 9px 10px;
  background: #ffffff;
  color: #111827;
  text-align: left;
  cursor: pointer;
}

.node-list button:hover,
.node-list button.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.node-list button.hidden {
  opacity: 0.58;
}

.node-list strong {
  overflow: hidden;
  font-size: 0.86rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-list small,
.empty-list {
  color: #64748b;
  font-size: 0.76rem;
}

@media (max-width: 1240px) {
  .workspace {
    grid-template-columns: 240px minmax(0, 1fr);
  }

  .workspace > :last-child {
    grid-column: 1 / -1;
  }
}

@media (max-width: 860px) {
  .graph-page {
    padding: 12px;
  }

  .workspace {
    grid-template-columns: 1fr;
  }
}
</style>
