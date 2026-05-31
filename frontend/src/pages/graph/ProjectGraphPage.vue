<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { createCharacter, listProjectCharacters } from '@/entities/character/api'
import type { Character } from '@/entities/character/types'
import { createClue, listProjectClues } from '@/entities/clue/api'
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
  graphNodeBoundTypeLabels,
  graphNodeTypeLabels,
  graphVisibilityLabels,
} from '@/entities/graph/types'
import { getProject } from '@/entities/project/api'
import type { Project } from '@/entities/project/types'
import { createSetting, listProjectSettings } from '@/entities/setting/api'
import type { SettingItem } from '@/entities/setting/types'
import { listProjectTimelineEvents } from '@/entities/timeline/api'
import type { TimelineEvent } from '@/entities/timeline/types'
import type { BindingOption } from '@/features/graph/GraphBindingPanel.vue'
import GraphCanvas, { type GraphViewportState } from '@/features/graph/GraphCanvas.vue'
import GraphInspector, { type EdgeDraft, type NodeDraft } from '@/features/graph/GraphInspector.vue'
import GraphToolbar, { type GraphToolMode } from '@/features/graph/GraphToolbar.vue'
import { safeReadJson, safeWriteJson } from '@/shared/storage/localWorkspaceState'
import { cloudSyncManager } from '@/features/cloud/cloudSyncManager'

type Point = { x: number; y: number }
type BindingKey = 'character' | 'setting' | 'clue' | 'timeline_event'
type ReverseMaterialType = 'character' | 'setting' | 'clue'

interface BoundSyncData {
  nodeType: GraphNodeType
  title: string
  summary: string
}

interface GraphViewState extends GraphViewportState {
  showGrid: boolean
  snapToGrid: boolean
  cleanMode: boolean
}

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
let graphViewSaveTimer: number | null = null

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
  width: 160,
  height: 72,
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
const modeLabels: Record<GraphToolMode, string> = {
  select: '选择',
  node: '新建节点',
  edge: '连线',
  pan: '平移',
}

const projectId = computed(() => {
  const value = route.params.projectId
  return (Array.isArray(value) ? value[0] : value) ?? ''
})

const graphViewStorageKey = computed(() => `zhangshu:graph:view:${projectId.value}`)

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
  restoreGraphViewState()
  void loadAll()
})

onBeforeUnmount(() => {
  if (graphViewSaveTimer !== null) {
    window.clearTimeout(graphViewSaveTimer)
  }
  saveGraphViewState()
})

watch(projectId, () => {
  clearSelection()
  restoreGraphViewState()
  void loadAll()
})

watch([showGrid, snapToGrid, cleanMode], () => {
  saveGraphViewState()
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
    await nextTick()
    applyStoredGraphViewport()
    focusRouteNode()
  } catch (error) {
    void error
    errorMessage.value = '关系图加载失败，请稍后重试。'
  } finally {
    isLoading.value = false
  }
}

function restoreGraphViewState() {
  const stored = readValidGraphViewState()
  if (!stored) {
    showGrid.value = true
    snapToGrid.value = true
    cleanMode.value = false
    zoomPercent.value = 100
    return
  }
  showGrid.value = stored.showGrid
  snapToGrid.value = stored.snapToGrid
  cleanMode.value = stored.cleanMode
  zoomPercent.value = Math.round(stored.zoom * 100)
  void nextTick(() => {
    applyStoredGraphViewport()
  })
}

function applyStoredGraphViewport() {
  const stored = readValidGraphViewState()
  if (!stored) {
    return
  }
  canvasRef.value?.applyViewportState({
    panX: stored.panX,
    panY: stored.panY,
    zoom: stored.zoom,
  })
}

function scheduleGraphViewStateSave(_viewport?: GraphViewportState) {
  if (graphViewSaveTimer !== null) {
    window.clearTimeout(graphViewSaveTimer)
  }
  graphViewSaveTimer = window.setTimeout(() => {
    graphViewSaveTimer = null
    saveGraphViewState()
  }, 200)
}

function saveGraphViewState(viewport = canvasRef.value?.getViewportState()) {
  if (!projectId.value || !viewport) {
    return
  }
  safeWriteJson(graphViewStorageKey.value, {
    panX: viewport.panX,
    panY: viewport.panY,
    zoom: viewport.zoom,
    showGrid: showGrid.value,
    snapToGrid: snapToGrid.value,
    cleanMode: cleanMode.value,
  } satisfies GraphViewState)
}

function readValidGraphViewState() {
  const state = safeReadJson<Partial<GraphViewState> | null>(graphViewStorageKey.value, null)
  if (!state) {
    return null
  }
  if (!isFiniteNumber(state.panX) || !isFiniteNumber(state.panY) || !isFiniteNumber(state.zoom)) {
    return null
  }
  if (state.zoom < 0.25 || state.zoom > 2.5) {
    return null
  }
  if (typeof state.showGrid !== 'boolean' || typeof state.snapToGrid !== 'boolean' || typeof state.cleanMode !== 'boolean') {
    return null
  }
  return state as GraphViewState
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
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

function selectNodeFromList(node: GraphNode) {
  selectNode(node)
  canvasRef.value?.centerOnNode(node.id)
}

function focusRouteNode() {
  const focusNodeId = Array.isArray(route.query.focusNodeId)
    ? route.query.focusNodeId[0]
    : route.query.focusNodeId
  if (!focusNodeId) {
    return
  }
  const node = nodes.value.find((item) => item.id === focusNodeId)
  if (!node) {
    errorMessage.value = '未找到对应关系图节点'
    return
  }
  selectNode(node)
  canvasRef.value?.centerOnNode(node.id)
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
  nodeDraft.width = Math.round(getNodeWidth(node))
  nodeDraft.height = Math.round(getNodeHeight(node))
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
    width: safeNodeWidth(overrides.width ?? presetNodeSize(overrides.size ?? 1).width),
    height: safeNodeHeight(overrides.height ?? presetNodeSize(overrides.size ?? 1).height),
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
    cloudSyncManager.notifyDirty(projectId.value)
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
    cloudSyncManager.notifyDirty(projectId.value)
  } catch (error) {
    void error
    errorMessage.value = '关系保存失败，请重试。'
  } finally {
    isSaving.value = false
  }
}

async function saveNodePosition(node: GraphNode, x: number, y: number, previous: Point) {
  const index = nodes.value.findIndex((item) => item.id === node.id)
  const current = nodes.value[index]
  if (index === -1 || !current) {
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
    cloudSyncManager.notifyDirty(projectId.value)
  } catch (error) {
    void error
    nodes.value.splice(index, 1, { ...node, x: previous.x, y: previous.y })
    errorMessage.value = '节点位置保存失败，请重试'
  }
}

async function saveNodeSize(node: GraphNode, width: number, height: number, previous: { width: number; height: number }) {
  const index = nodes.value.findIndex((item) => item.id === node.id)
  const current = nodes.value[index]
  if (index === -1 || !current) {
    return
  }
  const optimistic: GraphNode = { ...current, width: safeNodeWidth(width), height: safeNodeHeight(height) }
  nodes.value.splice(index, 1, optimistic)
  if (selectedNodeId.value === node.id) {
    applyNodeToDraft(optimistic)
  }
  try {
    const saved = await updateGraphNode(node.id, { width: optimistic.width, height: optimistic.height })
    upsertNode(saved)
    successMessage.value = '节点大小已保存'
    errorMessage.value = ''
    cloudSyncManager.notifyDirty(projectId.value)
  } catch (error) {
    void error
    nodes.value.splice(index, 1, { ...node, width: previous.width, height: previous.height })
    errorMessage.value = '节点大小保存失败，请重试'
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
  const boundType = nodeDraft.bound_type
  const boundId = nodeDraft.bound_id.trim()
  if (boundType && boundType !== 'custom' && boundId) {
    const duplicate = findExistingBoundNode(boundType, boundId)
    if (duplicate && duplicate.id !== selectedNode.value.id) {
      selectNode(duplicate)
      canvasRef.value?.centerOnNode(duplicate.id)
      errorMessage.value = '该绑定资料已存在关系图节点，已打开现有节点。'
      return
    }
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
      width: safeNodeWidth(nodeDraft.width),
      height: safeNodeHeight(nodeDraft.height),
      color: nodeDraft.color.trim() || null,
      size: clamp(Math.round(nodeDraft.size), 1, 3),
      visibility: nodeDraft.visibility,
    })
    upsertNode(saved)
    selectNode(saved)
    successMessage.value = '已保存'
    errorMessage.value = ''
    cloudSyncManager.notifyDirty(projectId.value)
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
    cloudSyncManager.notifyDirty(projectId.value)
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
  const nodeId = node.id
  if (!window.confirm('确认删除该节点吗？相关关系也可能被删除或隐藏。')) {
    return
  }
  try {
    isSaving.value = true
    await deleteGraphNode(nodeId)
    if (selectedNodeId.value === nodeId) {
      clearSelection()
    }
    nodes.value = nodes.value.filter((item) => item.id !== nodeId)
    edges.value = edges.value.filter((edge) => edge.from_node_id !== nodeId && edge.to_node_id !== nodeId)
    await refreshGraphData()
    successMessage.value = '节点已删除'
    errorMessage.value = ''
    cloudSyncManager.notifyDirty(projectId.value)
  } catch (error) {
    errorMessage.value = `节点删除失败，请重试${getErrorSuffix(error)}`
  } finally {
    isSaving.value = false
  }
}

async function deleteSelectedEdge(edge = selectedEdge.value) {
  if (!edge) {
    return
  }
  const edgeId = edge.id
  if (!window.confirm('确认删除该关系吗？')) {
    return
  }
  try {
    isSaving.value = true
    await deleteGraphEdge(edgeId)
    if (selectedEdgeId.value === edgeId) {
      clearSelection()
    }
    edges.value = edges.value.filter((item) => item.id !== edgeId)
    await refreshGraphData()
    successMessage.value = '关系已删除'
    errorMessage.value = ''
    cloudSyncManager.notifyDirty(projectId.value)
  } catch (error) {
    errorMessage.value = `关系删除失败，请重试${getErrorSuffix(error)}`
  } finally {
    isSaving.value = false
  }
}

async function refreshGraphData() {
  const [graphNodes, graphEdges] = await Promise.all([
    listGraphNodes(projectId.value),
    listGraphEdges(projectId.value),
  ])
  nodes.value = graphNodes
  edges.value = graphEdges
  reconcileSelection()
}

function getErrorSuffix(error: unknown) {
  if (error instanceof Error && error.message) {
    return `：${error.message}`
  }
  return ''
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
  const existingNode = findExistingBoundNode(boundType, boundId)
  if (existingNode) {
    selectNode(existingNode)
    canvasRef.value?.centerOnNode(existingNode.id)
    successMessage.value = '已打开现有关系图节点'
    errorMessage.value = ''
    return
  }
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

function findExistingBoundNode(boundType: Exclude<GraphNodeBoundType, 'custom'>, boundId: string) {
  return nodes.value.find((node) =>
    node.bound_type === boundType
    && node.bound_id === boundId
    && node.visibility !== 'hidden',
  ) ?? null
}

async function createMaterialFromSelectedNode() {
  const node = selectedNode.value
  if (!node || !isReverseMaterialType(node.node_type)) {
    return
  }
  if (node.bound_type || node.bound_id) {
    return
  }
  const title = nodeDraft.title.trim()
  if (!title) {
    errorMessage.value = '节点标题不能为空。'
    return
  }

  const existing = findExistingMaterial(node.node_type, title)
  if (existing && window.confirm('已存在同名资料，是否改为绑定已有资料？')) {
    await bindNodeToMaterial(node, node.node_type, existing.id, title, nodeDraft.summary, '已绑定已有资料')
    return
  }

  if (!window.confirm('当前节点尚未绑定资料，是否创建对应资料并绑定？')) {
    return
  }

  try {
    isSaving.value = true
    const created = await createMaterial(node.node_type, title, nodeDraft.summary)
    await bindNodeToMaterial(node, node.node_type, created.id, title, nodeDraft.summary, '已创建并绑定资料')
    await loadBindingData()
    successMessage.value = '已创建并绑定资料'
    errorMessage.value = ''
    cloudSyncManager.notifyDirty(projectId.value)
  } catch (error) {
    errorMessage.value = `资料创建失败，请重试${getErrorSuffix(error)}`
  } finally {
    isSaving.value = false
  }
}

function isReverseMaterialType(value: GraphNodeType): value is ReverseMaterialType {
  return value === 'character' || value === 'setting' || value === 'clue'
}

function findExistingMaterial(type: ReverseMaterialType, title: string) {
  const normalized = title.trim().toLowerCase()
  if (type === 'character') {
    const item = characters.value.find((character) => character.name.trim().toLowerCase() === normalized)
    return item ? { id: item.id } : null
  }
  if (type === 'setting') {
    const item = settings.value.find((setting) => setting.title.trim().toLowerCase() === normalized)
    return item ? { id: item.id } : null
  }
  const item = clues.value.find((clue) => clue.title.trim().toLowerCase() === normalized)
  return item ? { id: item.id } : null
}

async function createMaterial(type: ReverseMaterialType, title: string, summary: string) {
  if (type === 'character') {
    return createCharacter(projectId.value, {
      name: title,
      role: 'unknown',
      importance: 'normal',
      status: 'active',
      summary,
    })
  }
  if (type === 'setting') {
    return createSetting(projectId.value, {
      title,
      item_type: 'custom',
      canon_status: 'draft',
      summary,
      detail: '',
    })
  }
  return createClue(projectId.value, {
    title,
    description: summary,
    status: 'planned',
    visibility: 'hidden',
    importance: 'normal',
  })
}

async function bindNodeToMaterial(
  node: GraphNode,
  type: ReverseMaterialType,
  boundId: string,
  title: string,
  summary: string,
  message: string,
) {
  const saved = await updateGraphNode(node.id, {
    bound_type: type,
    bound_id: boundId,
    node_type: type,
    title,
    summary,
  })
  upsertNode(saved)
  selectNode(saved)
  successMessage.value = message
  errorMessage.value = ''
  cloudSyncManager.notifyDirty(projectId.value)
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
  void handleBoundSelectionChanged()
}

function handleBoundSelectionChanged() {
  const syncData = getBoundSyncData()
  if (!syncData) {
    if (nodeDraft.bound_type && nodeDraft.bound_id) {
      errorMessage.value = '绑定资料不存在或已被删除'
    }
    return
  }
  if (!nodeDraft.title.trim()) {
    nodeDraft.title = syncData.title
  }
  if (!nodeDraft.summary.trim()) {
    nodeDraft.summary = syncData.summary
  }
  if (nodeDraft.node_type !== syncData.nodeType && window.confirm('是否将节点类型同步为绑定资料类型？')) {
    nodeDraft.node_type = syncData.nodeType
  }
}

function syncSelectedNodeFromBound() {
  const syncData = getBoundSyncData()
  if (!syncData) {
    errorMessage.value = '绑定资料不存在或已被删除'
    return
  }
  const hasContent = Boolean(nodeDraft.title.trim() || nodeDraft.summary.trim())
  if (hasContent && !window.confirm('是否使用绑定资料覆盖当前节点标题和简介？')) {
    return
  }
  nodeDraft.title = syncData.title
  nodeDraft.summary = syncData.summary
  nodeDraft.node_type = syncData.nodeType
  void saveSelectedNode()
}

function getBoundSyncData(): BoundSyncData | null {
  if (!nodeDraft.bound_type || nodeDraft.bound_type === 'custom' || !nodeDraft.bound_id) {
    return null
  }
  if (nodeDraft.bound_type === 'character') {
    const item = characters.value.find((character) => character.id === nodeDraft.bound_id)
    return item ? { nodeType: 'character', title: item.name, summary: firstText(item.summary, item.biography) } : null
  }
  if (nodeDraft.bound_type === 'setting') {
    const item = settings.value.find((setting) => setting.id === nodeDraft.bound_id)
    return item ? { nodeType: 'setting', title: item.title, summary: firstText(item.summary, item.detail) } : null
  }
  if (nodeDraft.bound_type === 'clue') {
    const item = clues.value.find((clue) => clue.id === nodeDraft.bound_id)
    return item ? { nodeType: 'clue', title: item.title, summary: firstText(item.description, item.payoff_plan) } : null
  }
  const item = timelineEvents.value.find((event) => event.id === nodeDraft.bound_id)
  return item ? { nodeType: 'timeline_event', title: item.title, summary: item.description } : null
}

function firstText(...values: Array<string | null | undefined>) {
  return values.find((value) => value?.trim())?.trim() ?? ''
}

function handleSizePresetChanged() {
  const preset = presetNodeSize(nodeDraft.size)
  const currentPreset = selectedNode.value ? presetNodeSize(selectedNode.value.size) : preset
  const hasCustomSize = nodeDraft.width !== currentPreset.width || nodeDraft.height !== currentPreset.height
  if (!hasCustomSize || window.confirm('是否使用大小预设覆盖当前宽度和高度？')) {
    nodeDraft.width = preset.width
    nodeDraft.height = preset.height
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

function safeNodeWidth(value: number) {
  return clamp(Math.round(Number.isFinite(value) ? value : 160), 80, 420)
}

function safeNodeHeight(value: number) {
  return clamp(Math.round(Number.isFinite(value) ? value : 72), 40, 260)
}

function presetNodeSize(size: number) {
  if (size === 1) {
    return { width: 120, height: 56 }
  }
  if (size === 3) {
    return { width: 220, height: 96 }
  }
  return { width: 160, height: 72 }
}

function getNodeWidth(node: GraphNode) {
  return safeNodeWidth(node.width ?? presetNodeSize(node.size).width)
}

function getNodeHeight(node: GraphNode) {
  return safeNodeHeight(node.height ?? presetNodeSize(node.size).height)
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
      :writing-page-url="`/projects/${projectId}`"
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
            @click="selectNodeFromList(node)"
          >
            <strong>{{ node.title }}</strong>
            <small>
              <span class="type-badge">{{ graphNodeTypeLabels[node.node_type] }}</span>
              <span v-if="node.bound_type">已绑定 {{ graphNodeBoundTypeLabels[node.bound_type] }}</span>
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
        :mode-label="modeLabels[mode]"
        :show-grid="showGrid"
        :snap-to-grid="snapToGrid"
        :clean-mode="cleanMode"
        :zoom-percent="zoomPercent"
        @select-node="selectNode"
        @select-edge="selectEdge"
        @clear-selection="clearSelection"
        @create-node="createNodeAt"
        @create-edge="createEdgeBetween"
        @save-node-position="saveNodePosition"
        @save-node-size="saveNodeSize"
        @delete-node="deleteSelectedNode"
        @delete-edge="deleteSelectedEdge"
        @duplicate-node="duplicateNode"
        @open-bound="openBoundMaterial"
        @set-mode="mode = $event"
        @zoom-changed="zoomPercent = $event"
        @viewport-changed="scheduleGraphViewStateSave"
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
        @sync-from-bound="syncSelectedNodeFromBound"
        @create-material-from-node="createMaterialFromSelectedNode"
        @bound-type-changed="handleBoundTypeChanged"
        @bound-selection-changed="handleBoundSelectionChanged"
        @size-preset-changed="handleSizePresetChanged"
        @create-from-binding="createFromBinding"
      />
    </section>
  </main>
</template>

<style scoped>
.graph-page {
  display: grid;
  gap: var(--zs-space-3);
  min-height: 100vh;
  box-sizing: border-box;
  overflow-x: hidden;
  padding: var(--zs-space-5);
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: var(--zs-space-4);
}

.back-link {
  display: inline-flex;
  margin-bottom: var(--zs-space-2);
  color: var(--zs-color-primary);
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
  letter-spacing: 0;
}

.page-header p {
  margin-top: 6px;
  color: var(--zs-color-text-muted);
  line-height: 1.6;
}

.page-header span {
  display: inline-block;
  margin-top: 4px;
  color: var(--zs-color-text-muted);
  font-size: 0.86rem;
  font-weight: 700;
}

.status {
  border-radius: var(--zs-radius-md);
  padding: 9px 12px;
  font-size: 0.86rem;
}

.status.error {
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
}

.status.success {
  background: var(--zs-color-success-soft);
  color: var(--zs-color-success);
}

.workspace {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 340px;
  gap: var(--zs-space-3);
  min-height: calc(100vh - 184px);
}

.left-panel {
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

.left-panel header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-2);
}

.left-panel h2 {
  font-size: 1rem;
}

.left-panel header span {
  border-radius: 999px;
  padding: 3px 8px;
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-primary);
  font-size: 0.76rem;
  font-weight: 800;
}

.left-panel label {
  display: grid;
  gap: 6px;
}

.left-panel label span {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
}

input,
select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 8px 10px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.84rem;
}

.node-list {
  display: grid;
  gap: 8px;
}

.node-list button {
  display: grid;
  gap: 6px;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  padding: 9px 10px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  text-align: left;
  cursor: pointer;
}

.node-list button:hover,
.node-list button.active {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
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

.node-list small {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  align-items: center;
  color: var(--zs-color-text-muted);
  font-size: 0.74rem;
}

.type-badge {
  border-radius: 999px;
  padding: 1px 6px;
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-text);
  font-weight: 800;
}

.empty-list {
  color: var(--zs-color-text-muted);
  font-size: 0.76rem;
}

@media (max-width: 1240px) {
  .workspace {
    grid-template-columns: 240px minmax(560px, 1fr);
    overflow-x: auto;
  }

  .workspace > :last-child {
    grid-column: 1 / -1;
  }
}

@media (max-width: 860px) {
  .graph-page {
    padding: var(--zs-space-3);
  }

  .workspace {
    grid-template-columns: 1fr;
    overflow-x: visible;
  }
}
</style>
