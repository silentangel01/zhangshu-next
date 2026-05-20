<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

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
  GraphEdgeDirection,
  GraphEdgeLineStyle,
  GraphEdgeRelationType,
  GraphEdgeUpdatePayload,
  GraphNode,
  GraphNodeBoundType,
  GraphNodeCreatePayload,
  GraphNodeType,
  GraphNodeUpdatePayload,
  GraphVisibility,
} from '@/entities/graph/types'
import {
  graphEdgeDirectionLabels,
  graphEdgeLineStyleLabels,
  graphEdgeRelationLabels,
  graphNodeTypeLabels,
  graphNodeVisibilityLabels,
  graphVisibilityLabels,
} from '@/entities/graph/types'
import { listProjectSettings } from '@/entities/setting/api'
import type { SettingItem } from '@/entities/setting/types'
import { listProjectTimelineEvents } from '@/entities/timeline/api'
import type { TimelineEvent } from '@/entities/timeline/types'
import { getProject } from '@/entities/project/api'
import type { Project } from '@/entities/project/types'

type CanvasPoint = { x: number; y: number }
type PanelKind = 'none' | 'node' | 'edge'
type PanelMode = 'view' | 'create'

interface NodeDraft {
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

interface EdgeDraft {
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

interface CanvasEdgeRenderItem {
  edge: GraphEdge
  from: CanvasPoint
  to: CanvasPoint
  path: string
  labelPoint: CanvasPoint
  isArc: boolean
}

const route = useRoute()

const project = ref<Project | null>(null)
const graphNodes = ref<GraphNode[]>([])
const graphEdges = ref<GraphEdge[]>([])
const characters = ref<Character[]>([])
const settings = ref<SettingItem[]>([])
const clues = ref<Clue[]>([])
const timelineEvents = ref<TimelineEvent[]>([])

const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const cleanMode = ref(false)

const selectedNodeId = ref<string | null>(null)
const selectedEdgeId = ref<string | null>(null)
const panelKind = ref<PanelKind>('none')
const panelMode = ref<PanelMode>('view')

const canvasShellRef = ref<HTMLElement | null>(null)
const canvasSize = reactive({ width: 1180, height: 760 })
let resizeObserver: ResizeObserver | null = null

const filters = reactive({
  keyword: '',
  nodeType: '' as GraphNodeType | '',
  visibility: '' as GraphVisibility | '',
})

const nodeForm = reactive<NodeDraft>({
  title: '',
  node_type: 'custom',
  bound_type: null,
  bound_id: '',
  summary: '',
  x: 360,
  y: 220,
  color: '',
  size: 1,
  visibility: 'normal',
})

const edgeForm = reactive<EdgeDraft>({
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

const dragState = reactive({
  nodeId: null as string | null,
  pointerId: null as number | null,
  startX: 0,
  startY: 0,
  originX: 0,
  originY: 0,
  currentX: 0,
  currentY: 0,
  nodeSize: 1,
  dragging: false,
})

const nodeTypeOptions: GraphNodeType[] = [
  'character',
  'setting',
  'clue',
  'timeline_event',
  'organization',
  'location',
  'custom',
]
const visibilityOptions: GraphVisibility[] = ['normal', 'subtle', 'hidden']
const relationTypeOptions: GraphEdgeRelationType[] = [
  'relationship',
  'conflict',
  'ally',
  'family',
  'belongs_to',
  'controls',
  'clue_related',
  'timeline_related',
  'setting_related',
  'cause',
  'custom',
]
const directionOptions: GraphEdgeDirection[] = ['undirected', 'directed']
const lineStyleOptions: GraphEdgeLineStyle[] = ['solid', 'dashed', 'dotted', 'arc']
const boundTypeOptions: Array<GraphNodeBoundType | ''> = ['', 'character', 'setting', 'clue', 'timeline_event', 'custom']
const sizeOptions = [1, 2, 3]
const DRAG_START_THRESHOLD_PX = 5

const projectId = computed<string>(() => {
  const value = route.params.projectId
  return (Array.isArray(value) ? value[0] : value) ?? ''
})

const nodeMap = computed(() => new Map(graphNodes.value.map((node) => [node.id, node] as const)))
const edgeMap = computed(() => new Map(graphEdges.value.map((edge) => [edge.id, edge] as const)))

const filteredNodes = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  return graphNodes.value
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
      return (
        node.title.toLowerCase().includes(keyword)
        || node.summary.toLowerCase().includes(keyword)
        || (node.bound_id ?? '').toLowerCase().includes(keyword)
      )
    })
    .sort((left, right) => {
      if (left.visibility !== right.visibility) {
        return left.visibility === 'hidden' ? 1 : -1
      }
      return left.title.localeCompare(right.title, 'zh-Hans-CN')
    })
})

const canvasNodes = computed(() =>
  graphNodes.value.filter((node) => node.visibility !== 'hidden'),
)

const renderNodeMap = computed(() => {
  const map = new Map<string, CanvasPoint>()
  for (const node of canvasNodes.value) {
    map.set(node.id, getDisplayNodePoint(node))
  }
  return map
})

const canvasEdges = computed<CanvasEdgeRenderItem[]>(() =>
  graphEdges.value
    .filter((edge) => {
      if (edge.visibility === 'hidden') {
        return false
      }
      if (cleanMode.value && edge.visibility === 'subtle') {
        return false
      }
      const fromNode = nodeMap.value.get(edge.from_node_id)
      const toNode = nodeMap.value.get(edge.to_node_id)
      if (!fromNode || !toNode) {
        return false
      }
      if (fromNode.visibility === 'hidden' || toNode.visibility === 'hidden') {
        return false
      }
      return true
    })
    .map((edge) => {
      const fromNode = renderNodeMap.value.get(edge.from_node_id)
      const toNode = renderNodeMap.value.get(edge.to_node_id)
      if (!fromNode || !toNode) {
        return null
      }

      const pathInfo = buildEdgePath(fromNode, toNode, edge.line_style)
      return {
        edge,
        from: fromNode,
        to: toNode,
        path: pathInfo.path,
        labelPoint: pathInfo.labelPoint,
        isArc: pathInfo.isArc,
      }
    })
    .filter((item): item is CanvasEdgeRenderItem => item !== null),
)

const selectedNode = computed(() => {
  if (!selectedNodeId.value) {
    return null
  }
  return nodeMap.value.get(selectedNodeId.value) ?? null
})

const selectedEdge = computed(() => {
  if (!selectedEdgeId.value) {
    return null
  }
  return edgeMap.value.get(selectedEdgeId.value) ?? null
})

const selectedNodeTypeLabel = computed(() => {
  if (!selectedNode.value) {
    return ''
  }
  return graphNodeTypeLabels[selectedNode.value.node_type]
})

const selectedNodeBindingLabel = computed(() => {
  if (!selectedNode.value) {
    return '未绑定'
  }
  return selectedNode.value.bound_type ? graphNodeTypeLabels[selectedNode.value.bound_type as GraphNodeType] ?? selectedNode.value.bound_type : '未绑定'
})

const isNodeCreating = computed(() => panelKind.value === 'node' && panelMode.value === 'create')
const isEdgeCreating = computed(() => panelKind.value === 'edge' && panelMode.value === 'create')
const hasDetailPanel = computed(() => panelKind.value !== 'none' || panelMode.value === 'create')

const nodeBindingTargets = computed(() => {
  return {
    character: characters.value.map((item) => ({ id: item.id, label: item.name })),
    setting: settings.value.map((item) => ({ id: item.id, label: item.title })),
    clue: clues.value.map((item) => ({ id: item.id, label: item.title })),
    timeline_event: timelineEvents.value.map((item) => ({ id: item.id, label: item.title })),
  }
})

const currentNodeBindingOptions = computed(() => {
  switch (nodeForm.bound_type) {
    case 'character':
      return nodeBindingTargets.value.character
    case 'setting':
      return nodeBindingTargets.value.setting
    case 'clue':
      return nodeBindingTargets.value.clue
    case 'timeline_event':
      return nodeBindingTargets.value.timeline_event
    default:
      return []
  }
})

const graphCanvasStyle = computed(() => ({
  width: `${Math.max(canvasSize.width, 960)}px`,
  height: `${Math.max(canvasSize.height, 680)}px`,
}))

const nodeListCount = computed(() => filteredNodes.value.length)
const edgeListCount = computed(() => canvasEdges.value.length)

onMounted(() => {
  observeCanvasSize()
  void loadWorkspace()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
})

watch(projectId, () => {
  resetSelectionState()
  void loadWorkspace()
})

function observeCanvasSize() {
  if (!canvasShellRef.value || typeof ResizeObserver === 'undefined') {
    return
  }

  resizeObserver?.disconnect()
  resizeObserver = new ResizeObserver((entries) => {
    const entry = entries[0]
    if (!entry) {
      return
    }
    canvasSize.width = Math.max(960, Math.floor(entry.contentRect.width))
    canvasSize.height = Math.max(680, Math.floor(entry.contentRect.height))
  })
  resizeObserver.observe(canvasShellRef.value)
}

async function loadWorkspace() {
  if (!projectId.value) {
    errorMessage.value = '项目 ID 缺失。'
    return
  }

  isLoading.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const [projectDetail, nodes, edges] = await Promise.all([
      getProject(projectId.value),
      listGraphNodes(projectId.value),
      listGraphEdges(projectId.value),
    ])

    project.value = projectDetail
    graphNodes.value = nodes
    graphEdges.value = edges
    reconcileSelection()
    await loadBindingData()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载关系图失败。')
  } finally {
    isLoading.value = false
  }
}

async function loadBindingData() {
  if (!projectId.value) {
    return
  }

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
  if (selectedNodeId.value && !graphNodes.value.some((node) => node.id === selectedNodeId.value)) {
    selectedNodeId.value = null
    if (panelKind.value === 'node' && panelMode.value === 'view') {
      panelKind.value = 'none'
    }
  }

  if (selectedEdgeId.value && !graphEdges.value.some((edge) => edge.id === selectedEdgeId.value)) {
    selectedEdgeId.value = null
    if (panelKind.value === 'edge' && panelMode.value === 'view') {
      panelKind.value = 'none'
    }
  }
}

function resetSelectionState() {
  selectedNodeId.value = null
  selectedEdgeId.value = null
  panelKind.value = 'none'
  panelMode.value = 'view'
  clearNodeForm()
  clearEdgeForm()
  resetDragState()
}

function resetDragState() {
  dragState.nodeId = null
  dragState.pointerId = null
  dragState.startX = 0
  dragState.startY = 0
  dragState.originX = 0
  dragState.originY = 0
  dragState.currentX = 0
  dragState.currentY = 0
  dragState.nodeSize = 1
  dragState.dragging = false
}

function clearSelection() {
  if (panelMode.value === 'create') {
    return
  }
  selectedNodeId.value = null
  selectedEdgeId.value = null
  panelKind.value = 'none'
  panelMode.value = 'view'
}

function handleCanvasPointerDown() {
  clearSelection()
}

function defaultNodePosition(): CanvasPoint {
  const baseX = Math.max(220, Math.round(canvasSize.width / 2))
  const baseY = Math.max(160, Math.round(canvasSize.height / 2))
  const offset = graphNodes.value.length * 28
  const x = clamp(baseX + offset, 120, Math.max(120, canvasSize.width - 120))
  const y = clamp(baseY + offset * 0.6, 80, Math.max(80, canvasSize.height - 80))
  return { x, y }
}

function resetNodeForm(position: CanvasPoint = defaultNodePosition()) {
  nodeForm.title = ''
  nodeForm.node_type = 'custom'
  nodeForm.bound_type = null
  nodeForm.bound_id = ''
  nodeForm.summary = ''
  nodeForm.x = position.x
  nodeForm.y = position.y
  nodeForm.color = ''
  nodeForm.size = 1
  nodeForm.visibility = 'normal'
}

function resetEdgeForm() {
  edgeForm.from_node_id = selectedNodeId.value ?? graphNodes.value[0]?.id ?? ''
  edgeForm.to_node_id = graphNodes.value.find((node) => node.id !== edgeForm.from_node_id)?.id ?? ''
  edgeForm.relation_type = 'relationship'
  edgeForm.direction = 'undirected'
  edgeForm.strength = 1
  edgeForm.label = ''
  edgeForm.note = ''
  edgeForm.line_style = 'solid'
  edgeForm.visibility = 'normal'
}

function clearNodeForm() {
  resetNodeForm()
}

function clearEdgeForm() {
  resetEdgeForm()
}

function openCreateNode() {
  panelKind.value = 'node'
  panelMode.value = 'create'
  selectedNodeId.value = null
  selectedEdgeId.value = null
  resetNodeForm()
  syncNodeBindingDefaults()
  successMessage.value = ''
  errorMessage.value = ''
}

function openCreateEdge() {
  panelKind.value = 'edge'
  panelMode.value = 'create'
  const sourceNodeId = selectedNodeId.value
  selectedEdgeId.value = null
  resetEdgeForm()
  if (sourceNodeId) {
    edgeForm.from_node_id = sourceNodeId
  }
  successMessage.value = ''
  errorMessage.value = ''
}

function selectNode(node: GraphNode) {
  selectedNodeId.value = node.id
  selectedEdgeId.value = null
  panelKind.value = 'node'
  panelMode.value = 'view'
  applyNodeToForm(node)
  successMessage.value = ''
  errorMessage.value = ''
}

function selectEdge(edge: GraphEdge) {
  selectedEdgeId.value = edge.id
  selectedNodeId.value = null
  panelKind.value = 'edge'
  panelMode.value = 'view'
  applyEdgeToForm(edge)
  successMessage.value = ''
  errorMessage.value = ''
}

function applyNodeToForm(node: GraphNode) {
  nodeForm.title = node.title
  nodeForm.node_type = node.node_type
  nodeForm.bound_type = node.bound_type
  nodeForm.bound_id = node.bound_id ?? ''
  nodeForm.summary = node.summary
  nodeForm.x = Math.round(node.x)
  nodeForm.y = Math.round(node.y)
  nodeForm.color = node.color ?? ''
  nodeForm.size = node.size
  nodeForm.visibility = node.visibility
  syncNodeBindingDefaults()
}

function applyEdgeToForm(edge: GraphEdge) {
  edgeForm.from_node_id = edge.from_node_id
  edgeForm.to_node_id = edge.to_node_id
  edgeForm.relation_type = edge.relation_type
  edgeForm.direction = edge.direction
  edgeForm.strength = edge.strength
  edgeForm.label = edge.label
  edgeForm.note = edge.note
  edgeForm.line_style = edge.line_style
  edgeForm.visibility = edge.visibility
}

function syncNodeBindingDefaults() {
  if (nodeForm.node_type === 'character' || nodeForm.node_type === 'setting' || nodeForm.node_type === 'clue' || nodeForm.node_type === 'timeline_event') {
    nodeForm.bound_type = nodeForm.node_type
  }

  if (nodeForm.bound_type === 'custom') {
    if (nodeForm.bound_id && nodeForm.bound_id.length > 0 && currentNodeBindingOptions.value.length > 0) {
      const valid = currentNodeBindingOptions.value.some((item) => item.id === nodeForm.bound_id)
      if (!valid) {
        nodeForm.bound_id = ''
      }
    }
    return
  }

  if (nodeForm.bound_type === null) {
    nodeForm.bound_id = ''
    return
  }

  const valid = currentNodeBindingOptions.value.some((item) => item.id === nodeForm.bound_id)
  if (!valid) {
    nodeForm.bound_id = ''
  }
}

function handleNodeTypeChanged() {
  syncNodeBindingDefaults()
}

function handleBoundTypeChanged() {
  if (nodeForm.bound_type !== 'custom') {
    syncNodeBindingDefaults()
  }
}

async function handleSaveNode() {
  if (!projectId.value) {
    return
  }

  const payload = buildNodePayload()
  if (!payload) {
    return
  }

  await saveWithFeedback(async () => {
    const savedNode = panelMode.value === 'create' || !selectedNodeId.value
      ? await createGraphNode(projectId.value, payload)
      : await updateGraphNode(selectedNodeId.value, payload)

    upsertGraphNode(savedNode)
    selectedNodeId.value = savedNode.id
    selectedEdgeId.value = null
    panelKind.value = 'node'
    panelMode.value = 'view'
    applyNodeToForm(savedNode)
    successMessage.value = '节点已保存'
  }, '节点保存失败，请重试')
}

async function handleDeleteNode() {
  if (!selectedNode.value) {
    return
  }

  const confirmed = window.confirm('确认删除该节点吗？相关关系也可能被隐藏或删除。')
  if (!confirmed) {
    return
  }

  await saveWithFeedback(async () => {
    const deleted = await deleteGraphNode(selectedNode.value!.id)
    removeGraphNode(deleted.id)
    graphEdges.value = graphEdges.value.filter(
      (edge) => edge.from_node_id !== deleted.id && edge.to_node_id !== deleted.id,
    )
    resetSelectionState()
    successMessage.value = '节点已删除'
  }, '节点删除失败，请重试')
}

function buildNodePayload(): GraphNodeCreatePayload | null {
  const title = nodeForm.title.trim()
  if (!title) {
    errorMessage.value = '节点标题不能为空。'
    return null
  }

  const x = sanitizeNumber(nodeForm.x, defaultNodePosition().x)
  const y = sanitizeNumber(nodeForm.y, defaultNodePosition().y)

  return {
    title,
    node_type: nodeForm.node_type,
    bound_type: nodeForm.bound_type,
    bound_id: nodeForm.bound_id.trim() || null,
    summary: nodeForm.summary,
    x,
    y,
    color: nodeForm.color.trim() || null,
    size: clamp(Math.round(sanitizeNumber(nodeForm.size, 1)), 1, 3),
    visibility: nodeForm.visibility,
  }
}

async function handleSaveEdge() {
  if (!projectId.value) {
    return
  }

  if (!edgeForm.from_node_id || !edgeForm.to_node_id) {
    errorMessage.value = '请先选择起点节点和终点节点。'
    return
  }

  if (edgeForm.from_node_id === edgeForm.to_node_id) {
    errorMessage.value = '起点节点和终点节点不能相同。'
    return
  }

  const payload: GraphEdgeCreatePayload = {
    from_node_id: edgeForm.from_node_id,
    to_node_id: edgeForm.to_node_id,
    relation_type: edgeForm.relation_type,
    direction: edgeForm.direction,
    strength: clamp(Math.round(sanitizeNumber(edgeForm.strength, 1)), 1, 5),
    label: edgeForm.label,
    note: edgeForm.note,
    line_style: edgeForm.line_style,
    visibility: edgeForm.visibility,
  }

  await saveWithFeedback(async () => {
    const savedEdge = panelMode.value === 'create' || !selectedEdgeId.value
      ? await createGraphEdge(projectId.value, payload)
      : await updateGraphEdge(selectedEdgeId.value, payload)

    upsertGraphEdge(savedEdge)
    selectedEdgeId.value = savedEdge.id
    selectedNodeId.value = null
    panelKind.value = 'edge'
    panelMode.value = 'view'
    applyEdgeToForm(savedEdge)
    successMessage.value = '关系已保存'
  }, '关系保存失败，请重试')
}

async function handleDeleteEdge() {
  if (!selectedEdge.value) {
    return
  }

  const confirmed = window.confirm('确认删除该关系吗？')
  if (!confirmed) {
    return
  }

  await saveWithFeedback(async () => {
    const deleted = await deleteGraphEdge(selectedEdge.value!.id)
    removeGraphEdge(deleted.id)
    resetSelectionState()
    successMessage.value = '关系已删除'
  }, '关系删除失败，请重试')
}

function upsertGraphNode(node: GraphNode) {
  const index = graphNodes.value.findIndex((item) => item.id === node.id)
  if (index === -1) {
    graphNodes.value = [...graphNodes.value, node]
    return
  }
  graphNodes.value = graphNodes.value.map((item) => (item.id === node.id ? node : item))
}

function removeGraphNode(nodeId: string) {
  graphNodes.value = graphNodes.value.filter((item) => item.id !== nodeId)
}

function upsertGraphEdge(edge: GraphEdge) {
  const index = graphEdges.value.findIndex((item) => item.id === edge.id)
  if (index === -1) {
    graphEdges.value = [...graphEdges.value, edge]
    return
  }
  graphEdges.value = graphEdges.value.map((item) => (item.id === edge.id ? edge : item))
}

function removeGraphEdge(edgeId: string) {
  graphEdges.value = graphEdges.value.filter((item) => item.id !== edgeId)
}

function getDisplayNodePoint(node: GraphNode): CanvasPoint {
  if (dragState.nodeId === node.id && dragState.dragging) {
    return { x: dragState.currentX, y: dragState.currentY }
  }
  return {
    x: sanitizeNumber(node.x, defaultNodePosition().x),
    y: sanitizeNumber(node.y, defaultNodePosition().y),
  }
}

function handleNodePointerDown(event: PointerEvent, node: GraphNode) {
  if (event.button !== 0) {
    return
  }

  event.preventDefault()
  event.stopPropagation()

  dragState.nodeId = node.id
  dragState.pointerId = event.pointerId
  dragState.startX = event.clientX
  dragState.startY = event.clientY
  dragState.originX = sanitizeNumber(node.x, defaultNodePosition().x)
  dragState.originY = sanitizeNumber(node.y, defaultNodePosition().y)
  dragState.currentX = dragState.originX
  dragState.currentY = dragState.originY
  dragState.nodeSize = clamp(Math.round(node.size || 1), 1, 3)
  dragState.dragging = false

  const target = event.currentTarget as HTMLElement | null
  target?.setPointerCapture?.(event.pointerId)
}

function handleNodePointerMove(event: PointerEvent, node: GraphNode) {
  if (dragState.nodeId !== node.id || dragState.pointerId !== event.pointerId) {
    return
  }

  const deltaX = event.clientX - dragState.startX
  const deltaY = event.clientY - dragState.startY

  if (!dragState.dragging) {
    if (Math.hypot(deltaX, deltaY) <= DRAG_START_THRESHOLD_PX) {
      return
    }
    dragState.dragging = true
    selectedNodeId.value = node.id
    selectedEdgeId.value = null
    panelKind.value = 'node'
    panelMode.value = 'view'
  }

  const width = getNodeBoxSize(dragState.nodeSize).width
  const height = getNodeBoxSize(dragState.nodeSize).height
  const nextX = clamp(
    dragState.originX + deltaX,
    width / 2,
    Math.max(width / 2, canvasSize.width - width / 2),
  )
  const nextY = clamp(
    dragState.originY + deltaY,
    height / 2,
    Math.max(height / 2, canvasSize.height - height / 2),
  )

  dragState.currentX = nextX
  dragState.currentY = nextY
}

async function handleNodePointerUp(event: PointerEvent, node: GraphNode) {
  if (dragState.nodeId !== node.id || dragState.pointerId !== event.pointerId) {
    return
  }

  event.stopPropagation()

  const wasDragging = dragState.dragging
  const originX = dragState.originX
  const originY = dragState.originY
  const finalX = dragState.currentX
  const finalY = dragState.currentY
  resetDragState()

  if (!wasDragging) {
    selectNode(node)
    return
  }

  const localNode = graphNodes.value.find((item) => item.id === node.id)
  if (localNode) {
    localNode.x = finalX
    localNode.y = finalY
  }

  await saveWithFeedback(async () => {
    const saved = await updateGraphNode(node.id, {
      x: finalX,
      y: finalY,
    })
    upsertGraphNode(saved)
    selectedNodeId.value = saved.id
    selectedEdgeId.value = null
    panelKind.value = 'node'
    panelMode.value = 'view'
    applyNodeToForm(saved)
    successMessage.value = '节点位置已保存'
  }, '节点位置保存失败，请重试', () => {
    const current = graphNodes.value.find((item) => item.id === node.id)
    if (current) {
      current.x = originX
      current.y = originY
    }
    if (selectedNodeId.value === node.id) {
      applyNodeToForm({
        ...node,
        x: originX,
        y: originY,
      })
    }
  })
}

function handleNodePointerCancel(event: PointerEvent, node: GraphNode) {
  if (dragState.nodeId !== node.id || dragState.pointerId !== event.pointerId) {
    return
  }
  resetDragState()
}

function handleBlankCanvasPointerDown() {
  clearSelection()
}

function getNodeBoxSize(size: number) {
  switch (clamp(Math.round(size || 1), 1, 3)) {
    case 1:
      return { width: 170, height: 74 }
    case 2:
      return { width: 200, height: 90 }
    case 3:
      return { width: 230, height: 108 }
    default:
      return { width: 170, height: 74 }
  }
}

function getNodeAccentColor(node: GraphNode): string {
  if (node.color) {
    return node.color
  }

  switch (node.node_type) {
    case 'character':
      return '#6366f1'
    case 'setting':
      return '#0ea5e9'
    case 'clue':
      return '#f59e0b'
    case 'timeline_event':
      return '#10b981'
    case 'organization':
      return '#8b5cf6'
    case 'location':
      return '#ef4444'
    default:
      return '#64748b'
  }
}

function getNodeMetaLabel(node: GraphNode): string {
  return graphNodeTypeLabels[node.node_type]
}

function getNodeSubtitle(node: GraphNode): string {
  const parts: string[] = []
  if (node.bound_type) {
    parts.push(`绑定：${node.bound_type}`)
  }
  if (node.bound_id) {
    parts.push(node.bound_id)
  }
  return parts.join(' · ')
}

function getNodeListSummary(node: GraphNode): string {
  if (cleanMode.value) {
    return ''
  }
  return node.summary.trim()
}

function getEdgeLabel(edge: GraphEdge): string {
  const parts: string[] = [graphEdgeRelationLabels[edge.relation_type]]
  if (edge.label.trim()) {
    parts.push(edge.label.trim())
  }
  return parts.join(' · ')
}

function getEdgeMeta(edge: GraphEdge): string {
  return `${graphEdgeDirectionLabels[edge.direction]} · ${graphEdgeLineStyleLabels[edge.line_style]} · 强度 ${edge.strength}`
}

function getVisibleEdgeLabel(edge: GraphEdge): string {
  if (cleanMode.value && selectedEdgeId.value !== edge.id) {
    return ''
  }
  return edge.label.trim()
}

function getEdgeLineStyle(edge: GraphEdge) {
  return {
    opacity: edge.visibility === 'subtle' ? 0.52 : 0.85,
    strokeWidth: 1.6 + (edge.strength - 1) * 0.6,
  }
}

function buildEdgePath(from: CanvasPoint, to: CanvasPoint, lineStyle: GraphEdgeLineStyle) {
  const midX = (from.x + to.x) / 2
  const midY = (from.y + to.y) / 2
  const dx = to.x - from.x
  const dy = to.y - from.y

  if (lineStyle === 'arc') {
    const curvature = Math.min(120, Math.max(40, Math.abs(dx) * 0.22))
    const controlX = midX
    const controlY = midY - curvature - Math.sign(dy || dx || 1) * 12
    return {
      path: `M ${from.x} ${from.y} Q ${controlX} ${controlY} ${to.x} ${to.y}`,
      labelPoint: { x: midX, y: controlY - 6 },
      isArc: true,
    }
  }

  return {
    path: `M ${from.x} ${from.y} L ${to.x} ${to.y}`,
    labelPoint: { x: midX, y: midY - 10 },
    isArc: false,
  }
}

function clamp(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) {
    return min
  }
  return Math.min(max, Math.max(min, value))
}

function sanitizeNumber(value: number, fallback: number) {
  return Number.isFinite(value) ? value : fallback
}

async function saveWithFeedback(
  action: () => Promise<void>,
  fallbackMessage: string,
  revert?: () => void,
) {
  isSaving.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    await action()
  } catch (error) {
    if (revert) {
      revert()
    }
    errorMessage.value = getErrorMessage(error, fallbackMessage)
  } finally {
    isSaving.value = false
  }
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}
</script>

<template>
  <main class="graph-page">
    <header class="page-header">
      <div>
        <RouterLink class="back-link" :to="`/projects/${projectId}`">返回写作页</RouterLink>
        <p class="eyebrow">关系图</p>
        <h1>关系图</h1>
        <p class="page-note">用节点和连线管理人物、设定、伏笔、时间轴事件之间的关系。</p>
        <p class="project-title">{{ project?.title || '正在加载项目…' }}</p>
      </div>
      <div class="header-actions">
        <button class="secondary-button" type="button" @click="openCreateNode">新建节点</button>
        <button class="secondary-button" type="button" @click="openCreateEdge">新建关系</button>
        <button class="toggle-button" type="button" :class="{ active: cleanMode }" @click="cleanMode = !cleanMode">
          纯净模式
        </button>
        <button class="secondary-button" type="button" :disabled="isLoading || isSaving" @click="loadWorkspace">
          刷新
        </button>
      </div>
    </header>

    <section v-if="errorMessage" class="status-banner error" role="alert">{{ errorMessage }}</section>
    <section v-if="successMessage" class="status-banner success" role="status">{{ successMessage }}</section>
    <section v-if="isLoading" class="state-message">正在加载关系图…</section>

    <section v-else class="workspace" :class="{ 'detail-visible': hasDetailPanel }">
      <aside class="left-panel">
        <div class="panel-head">
          <div>
            <p class="panel-eyebrow">节点与关系</p>
            <h2>图谱列表</h2>
          </div>
          <span class="count-pill">{{ graphNodes.length }}</span>
        </div>

        <label class="field">
          <span>关键词</span>
          <input v-model.trim="filters.keyword" type="search" placeholder="搜索标题、简介、绑定 ID" />
        </label>

        <div class="filters-grid">
          <label class="field">
            <span>节点类型</span>
            <select v-model="filters.nodeType">
              <option value="">全部类型</option>
              <option v-for="type in nodeTypeOptions" :key="type" :value="type">
                {{ graphNodeTypeLabels[type] }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>可见性</span>
            <select v-model="filters.visibility">
              <option value="">全部可见性</option>
              <option v-for="visibility in visibilityOptions" :key="visibility" :value="visibility">
                {{ graphVisibilityLabels[visibility] }}
              </option>
            </select>
          </label>
        </div>

        <div class="binding-helper">
          <p class="binding-helper-title">绑定辅助</p>
          <p>创建节点时可以直接绑定人物、设定、伏笔或时间轴事件。</p>
          <ul>
            <li>人物：{{ characters.length }}</li>
            <li>设定：{{ settings.length }}</li>
            <li>伏笔：{{ clues.length }}</li>
            <li>时间轴事件：{{ timelineEvents.length }}</li>
          </ul>
        </div>

        <section class="list-section">
          <div class="section-head">
            <div>
              <p class="panel-eyebrow">图节点</p>
              <h2>节点列表</h2>
            </div>
            <span class="count-pill">{{ nodeListCount }}</span>
          </div>

          <p v-if="graphNodes.length === 0" class="empty-tip">
            暂无关系图节点。可先新建节点，或从人物、设定、伏笔、时间轴事件创建节点。
          </p>
          <p v-else-if="nodeListCount === 0" class="empty-tip">暂无符合筛选条件的节点。</p>

          <div v-else class="node-list">
            <button
              v-for="node in filteredNodes"
              :key="node.id"
              type="button"
              class="node-list-item"
              :class="{ active: selectedNodeId === node.id, hidden: node.visibility === 'hidden' }"
              @click="selectNode(node)"
            >
              <span class="node-list-color" :style="{ background: getNodeAccentColor(node) }" />
              <span class="node-list-body">
                <span class="node-list-title">
                  {{ node.title }}
                  <span v-if="node.visibility === 'hidden'" class="hidden-tag">隐藏</span>
                  <span v-else-if="node.visibility === 'subtle'" class="hidden-tag subtle">弱化</span>
                </span>
                <span class="node-list-meta">{{ getNodeMetaLabel(node) }}</span>
                <span v-if="node.bound_type || node.bound_id" class="node-list-subtitle">
                  {{ getNodeSubtitle(node) || '未绑定' }}
                </span>
                <span v-if="!cleanMode && node.summary" class="node-list-summary">
                  {{ node.summary }}
                </span>
              </span>
            </button>
          </div>
        </section>

        <section class="list-section">
          <div class="section-head">
            <div>
              <p class="panel-eyebrow">图关系</p>
              <h2>关系列表</h2>
            </div>
            <span class="count-pill">{{ edgeListCount }}</span>
          </div>

          <p v-if="edgeListCount === 0" class="empty-tip">暂无可显示的关系。</p>

          <div v-else class="edge-list">
            <button
              v-for="edge in canvasEdges"
              :key="edge.edge.id"
              type="button"
              class="edge-list-item"
              :class="{ active: selectedEdgeId === edge.edge.id }"
              @click="selectEdge(edge.edge)"
            >
              <span class="edge-list-title">{{ getEdgeLabel(edge.edge) }}</span>
              <span class="edge-list-meta">{{ getEdgeMeta(edge.edge) }}</span>
              <span v-if="!cleanMode && edge.edge.note" class="edge-list-note">{{ edge.edge.note }}</span>
            </button>
          </div>
        </section>
      </aside>

      <section ref="canvasShellRef" class="graph-canvas-panel">
        <div v-if="canvasNodes.length === 0" class="canvas-empty">
          <p>暂无关系图节点。</p>
          <span>可先新建节点，或从人物、设定、伏笔、时间轴事件创建节点。</span>
        </div>

        <div class="graph-canvas-viewport">
          <div class="graph-canvas-body" :style="graphCanvasStyle" @pointerdown.self="handleBlankCanvasPointerDown">
            <svg
              class="graph-edge-overlay"
              :viewBox="`0 0 ${Math.max(canvasSize.width, 960)} ${Math.max(canvasSize.height, 680)}`"
              aria-hidden="true"
              @pointerdown.self="handleBlankCanvasPointerDown"
            >
              <defs>
                <marker
                  id="graph-arrow"
                  markerWidth="10"
                  markerHeight="10"
                  refX="8"
                  refY="3"
                  orient="auto"
                  markerUnits="strokeWidth"
                >
                  <path d="M0,0 L0,6 L8,3 z" fill="currentColor" />
                </marker>
              </defs>

              <g
                v-for="edge in canvasEdges"
                :key="edge.edge.id"
                class="edge-group"
                :class="{ selected: selectedEdgeId === edge.edge.id, subtle: edge.edge.visibility === 'subtle' }"
                @click.stop="selectEdge(edge.edge)"
              >
                <path
                  class="edge-hit"
                  :d="edge.path"
                  :marker-end="edge.edge.direction === 'directed' ? 'url(#graph-arrow)' : undefined"
                />
                <path
                  class="edge-line"
                  :class="[edge.edge.line_style, { selected: selectedEdgeId === edge.edge.id }]"
                  :d="edge.path"
                  :marker-end="edge.edge.direction === 'directed' ? 'url(#graph-arrow)' : undefined"
                  :style="getEdgeLineStyle(edge.edge)"
                />
                <text
                  v-if="(!cleanMode || selectedEdgeId === edge.edge.id) && edge.edge.label"
                  class="edge-label"
                  :x="edge.labelPoint.x"
                  :y="edge.labelPoint.y"
                >
                  {{ edge.edge.label }}
                </text>
              </g>
            </svg>

            <button
              v-for="node in canvasNodes"
              :key="node.id"
              type="button"
              class="graph-node"
              :class="[
                `size-${clamp(Math.round(node.size || 1), 1, 3)}`,
                node.visibility,
                {
                  active: selectedNodeId === node.id,
                  dragging: dragState.nodeId === node.id && dragState.dragging,
                },
              ]"
              :style="{
                left: `${getDisplayNodePoint(node).x}px`,
                top: `${getDisplayNodePoint(node).y}px`,
                '--node-accent': getNodeAccentColor(node),
              }"
              @pointerdown="handleNodePointerDown($event, node)"
              @pointermove="handleNodePointerMove($event, node)"
              @pointerup="handleNodePointerUp($event, node)"
              @pointercancel="handleNodePointerCancel($event, node)"
            >
              <span class="drag-handle">⋮⋮</span>
              <span class="node-title">{{ node.title }}</span>
              <span class="node-type">{{ graphNodeTypeLabels[node.node_type] }}</span>
              <span v-if="!cleanMode && node.summary" class="node-summary">{{ node.summary }}</span>
            </button>
          </div>
        </div>
      </section>

      <aside v-if="hasDetailPanel" class="detail-panel">
        <template v-if="panelKind === 'node'">
          <header class="detail-header">
            <div>
              <p class="panel-eyebrow">{{ panelMode === 'create' ? '新建节点' : '节点详情' }}</p>
              <h2>{{ panelMode === 'create' ? '创建关系图节点' : selectedNode?.title || '节点详情' }}</h2>
            </div>
            <span v-if="selectedNode && panelMode === 'view'" class="count-pill">{{ selectedNode.version }}</span>
          </header>

          <div class="form-grid">
            <label class="field field-wide">
              <span>标题</span>
              <input v-model.trim="nodeForm.title" type="text" placeholder="请输入节点标题" />
            </label>

            <label class="field">
              <span>类型</span>
              <select v-model="nodeForm.node_type" @change="handleNodeTypeChanged">
                <option v-for="type in nodeTypeOptions" :key="type" :value="type">
                  {{ graphNodeTypeLabels[type] }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>绑定对象类型</span>
              <select v-model="nodeForm.bound_type" @change="handleBoundTypeChanged">
                <option :value="null">未绑定</option>
                <option v-for="type in boundTypeOptions.slice(1)" :key="type" :value="type">
                  {{ graphNodeTypeLabels[type as GraphNodeType] }}
                </option>
              </select>
            </label>

            <label v-if="nodeForm.bound_type && nodeForm.bound_type !== 'custom'" class="field field-wide">
              <span>绑定对象 ID</span>
              <select v-model="nodeForm.bound_id">
                <option value="">请选择绑定对象</option>
                <option v-for="item in currentNodeBindingOptions" :key="item.id" :value="item.id">
                  {{ item.label }}
                </option>
              </select>
            </label>

            <label v-else class="field field-wide">
              <span>绑定对象 ID</span>
              <input v-model.trim="nodeForm.bound_id" type="text" placeholder="请输入对象 ID" />
            </label>

            <label class="field field-wide">
              <span>简介</span>
              <textarea v-model="nodeForm.summary" rows="4" placeholder="节点简要说明" />
            </label>

            <label class="field">
              <span>颜色</span>
              <input v-model.trim="nodeForm.color" type="text" placeholder="#6B8AFD" />
            </label>

            <label class="field">
              <span>大小</span>
              <select v-model.number="nodeForm.size">
                <option v-for="size in sizeOptions" :key="size" :value="size">{{ size }}</option>
              </select>
            </label>

            <label class="field">
              <span>可见性</span>
              <select v-model="nodeForm.visibility">
                <option v-for="visibility in visibilityOptions" :key="visibility" :value="visibility">
                  {{ graphNodeVisibilityLabels[visibility] }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>x</span>
              <input v-model.number="nodeForm.x" type="number" min="0" step="1" />
            </label>

            <label class="field">
              <span>y</span>
              <input v-model.number="nodeForm.y" type="number" min="0" step="1" />
            </label>
          </div>

          <div class="form-actions">
            <button class="secondary-button" type="button" @click="resetNodeForm()">重置</button>
            <button class="secondary-button" type="button" @click="clearSelection">取消</button>
            <button class="primary-button" type="button" :disabled="isSaving || !nodeForm.title.trim()" @click="handleSaveNode">
              {{ panelMode === 'create' ? '创建节点' : '保存节点' }}
            </button>
            <button
              v-if="panelMode === 'view' && selectedNode"
              class="danger-button"
              type="button"
              :disabled="isSaving"
              @click="handleDeleteNode"
            >
              删除节点
            </button>
          </div>
        </template>

        <template v-else-if="panelKind === 'edge'">
          <header class="detail-header">
            <div>
              <p class="panel-eyebrow">{{ panelMode === 'create' ? '新建关系' : '关系详情' }}</p>
              <h2>{{ panelMode === 'create' ? '创建节点关系' : selectedEdge ? getEdgeLabel(selectedEdge) : '关系详情' }}</h2>
            </div>
            <span v-if="selectedEdge && panelMode === 'view'" class="count-pill">{{ selectedEdge.version }}</span>
          </header>

          <div class="form-grid">
            <label class="field field-wide">
              <span>起点节点</span>
              <select v-model="edgeForm.from_node_id">
                <option value="">请选择起点节点</option>
                <option v-for="node in canvasNodes" :key="node.id" :value="node.id">
                  {{ node.title }} · {{ graphNodeTypeLabels[node.node_type] }}
                </option>
              </select>
            </label>

            <label class="field field-wide">
              <span>终点节点</span>
              <select v-model="edgeForm.to_node_id">
                <option value="">请选择终点节点</option>
                <option v-for="node in canvasNodes" :key="node.id" :value="node.id">
                  {{ node.title }} · {{ graphNodeTypeLabels[node.node_type] }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>关系类型</span>
              <select v-model="edgeForm.relation_type">
                <option v-for="relationType in relationTypeOptions" :key="relationType" :value="relationType">
                  {{ graphEdgeRelationLabels[relationType] }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>方向</span>
              <select v-model="edgeForm.direction">
                <option v-for="direction in directionOptions" :key="direction" :value="direction">
                  {{ graphEdgeDirectionLabels[direction] }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>强度</span>
              <input v-model.number="edgeForm.strength" type="number" min="1" max="5" step="1" />
            </label>

            <label class="field">
              <span>标签</span>
              <input v-model.trim="edgeForm.label" type="text" placeholder="例如：所在地" />
            </label>

            <label class="field">
              <span>线条样式</span>
              <select v-model="edgeForm.line_style">
                <option v-for="lineStyle in lineStyleOptions" :key="lineStyle" :value="lineStyle">
                  {{ graphEdgeLineStyleLabels[lineStyle] }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>可见性</span>
              <select v-model="edgeForm.visibility">
                <option v-for="visibility in visibilityOptions" :key="visibility" :value="visibility">
                  {{ graphVisibilityLabels[visibility] }}
                </option>
              </select>
            </label>

            <label class="field field-wide">
              <span>批注</span>
              <textarea v-model="edgeForm.note" rows="4" placeholder="说明这条关系的含义" />
            </label>
          </div>

          <div class="form-actions">
            <button class="secondary-button" type="button" @click="resetEdgeForm()">重置</button>
            <button class="secondary-button" type="button" @click="clearSelection">取消</button>
            <button
              class="primary-button"
              type="button"
              :disabled="isSaving || !edgeForm.from_node_id || !edgeForm.to_node_id || edgeForm.from_node_id === edgeForm.to_node_id"
              @click="handleSaveEdge"
            >
              {{ panelMode === 'create' ? '创建关系' : '保存关系' }}
            </button>
            <button
              v-if="panelMode === 'view' && selectedEdge"
              class="danger-button"
              type="button"
              :disabled="isSaving"
              @click="handleDeleteEdge"
            >
              删除关系
            </button>
          </div>
        </template>

        <section v-else class="empty-detail">
          <h2>请选择节点或关系查看详情。</h2>
          <p>左侧可以筛选节点和关系，中间画布可以拖动节点，右侧会显示编辑表单。</p>
        </section>
      </aside>
    </section>
  </main>
</template>

<style scoped>
.graph-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 20px;
  background: #f6f8fb;
  color: #111827;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin: 0 auto 16px;
  max-width: 1640px;
}

.back-link {
  display: inline-flex;
  margin-bottom: 10px;
  color: #2563eb;
  font-weight: 800;
  text-decoration: none;
}

.eyebrow,
.panel-eyebrow,
.page-note,
.project-title,
.binding-helper p,
.binding-helper li,
.empty-tip,
.canvas-empty p,
.canvas-empty span,
.edge-list-meta,
.edge-list-note,
.node-list-meta,
.node-list-subtitle,
.node-list-summary {
  margin: 0;
}

.eyebrow,
.panel-eyebrow {
  color: #64748b;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1,
h2 {
  margin: 0;
  line-height: 1.15;
}

h1 {
  font-size: 1.8rem;
}

h2 {
  font-size: 1.02rem;
}

.page-note {
  color: #475569;
  line-height: 1.6;
}

.project-title {
  color: #0f172a;
  font-size: 0.9rem;
  font-weight: 700;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.primary-button,
.secondary-button,
.toggle-button,
.danger-button {
  min-height: 36px;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 0 14px;
  font: inherit;
  font-size: 0.88rem;
  font-weight: 800;
  cursor: pointer;
}

.primary-button {
  background: #2563eb;
  color: #ffffff;
}

.secondary-button {
  border-color: #d8dee9;
  background: #ffffff;
  color: #111827;
}

.toggle-button {
  border-color: #d8dee9;
  background: #f8fafc;
  color: #334155;
}

.toggle-button.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

.danger-button {
  border-color: #fecaca;
  background: #fff1f2;
  color: #b42318;
}

.status-banner {
  max-width: 1640px;
  margin: 0 auto 12px;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 0.88rem;
  line-height: 1.6;
}

.status-banner.error {
  background: #fef2f2;
  color: #b42318;
}

.status-banner.success {
  background: #ecfdf5;
  color: #047857;
}

.state-message {
  max-width: 1640px;
  margin: 0 auto;
  display: grid;
  place-items: center;
  min-height: 360px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #64748b;
}

.workspace {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
  max-width: 1640px;
  min-height: calc(100vh - 162px);
  margin: 0 auto;
}

.workspace.detail-visible {
  grid-template-columns: 320px minmax(0, 1fr) 360px;
}

.left-panel,
.graph-canvas-panel,
.detail-panel {
  min-width: 0;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgb(20 24 31 / 6%);
}

.left-panel,
.detail-panel {
  display: grid;
  gap: 12px;
  padding: 14px;
}

.panel-head,
.section-head,
.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.count-pill {
  min-width: 30px;
  border-radius: 999px;
  padding: 5px 10px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 0.8rem;
  font-weight: 800;
  text-align: center;
}

.field {
  display: grid;
  gap: 6px;
}

.field span {
  color: #475569;
  font-size: 0.8rem;
  font-weight: 800;
}

input,
select,
textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 9px 10px;
  background: #ffffff;
  color: #111827;
  font: inherit;
  font-size: 0.88rem;
}

textarea {
  resize: vertical;
  line-height: 1.7;
}

.filters-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.binding-helper {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  background: #f8fafc;
  color: #475569;
}

.binding-helper-title {
  margin-bottom: 4px;
  color: #0f172a;
  font-size: 0.82rem;
  font-weight: 800;
}

.binding-helper ul {
  margin: 8px 0 0;
  padding-left: 18px;
  line-height: 1.6;
}

.list-section {
  display: grid;
  gap: 10px;
}

.empty-tip {
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 12px;
  color: #64748b;
  line-height: 1.6;
}

.node-list,
.edge-list {
  display: grid;
  gap: 8px;
}

.node-list-item,
.edge-list-item {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  background: #ffffff;
  color: #0f172a;
  text-align: left;
}

.node-list-item:hover,
.edge-list-item:hover,
.node-list-item.active,
.edge-list-item.active {
  border-color: #93c5fd;
  background: #eff6ff;
}

.node-list-item.hidden {
  opacity: 0.66;
}

.node-list-color {
  width: 10px;
  height: 10px;
  margin-top: 6px;
  border-radius: 999px;
}

.node-list-body {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.node-list-title {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  color: #111827;
  font-size: 0.9rem;
  font-weight: 800;
}

.node-list-meta,
.node-list-subtitle,
.edge-list-meta,
.edge-list-note {
  color: #64748b;
  font-size: 0.77rem;
  line-height: 1.45;
}

.node-list-summary {
  color: #334155;
  font-size: 0.77rem;
  line-height: 1.5;
}

.hidden-tag {
  border-radius: 999px;
  padding: 1px 6px;
  background: #f1f5f9;
  color: #475569;
  font-size: 0.7rem;
}

.hidden-tag.subtle {
  background: #eef2ff;
  color: #4338ca;
}

.graph-canvas-panel {
  position: relative;
  overflow: hidden;
  min-height: 0;
}

.graph-canvas-viewport {
  overflow: auto;
  width: 100%;
  height: 100%;
}

.graph-canvas-body {
  position: relative;
  min-height: 100%;
  min-width: 100%;
  background-color: #ffffff;
  background-image:
    linear-gradient(90deg, rgb(148 163 184 / 9%) 1px, transparent 1px),
    linear-gradient(rgb(148 163 184 / 9%) 1px, transparent 1px);
  background-size: 34px 34px;
  background-position: 0 0;
}

.canvas-empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 6px;
  color: #64748b;
  text-align: center;
}

.canvas-empty p {
  color: #0f172a;
  font-size: 0.98rem;
  font-weight: 800;
}

.canvas-empty span {
  font-size: 0.84rem;
  line-height: 1.6;
}

.graph-edge-overlay {
  position: absolute;
  inset: 0;
  z-index: 1;
  overflow: visible;
}

.edge-group {
  color: #64748b;
}

.edge-group.selected {
  color: #2563eb;
}

.edge-hit,
.edge-line {
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.edge-hit {
  stroke: transparent;
  stroke-width: 12;
  pointer-events: stroke;
  cursor: pointer;
}

.edge-line {
  opacity: 0.82;
}

.edge-line.dashed {
  stroke-dasharray: 8 6;
}

.edge-line.dotted {
  stroke-dasharray: 2 7;
}

.edge-line.selected {
  opacity: 1;
  stroke-width: 3 !important;
}

.edge-label {
  fill: #0f172a;
  font-size: 12px;
  font-weight: 800;
  paint-order: stroke;
  stroke: #ffffff;
  stroke-width: 4px;
  stroke-linejoin: round;
  pointer-events: none;
}

.graph-node {
  position: absolute;
  z-index: 2;
  display: grid;
  gap: 4px;
  border: 1px solid #cbd5e1;
  border-left: 4px solid var(--node-accent);
  border-radius: 10px;
  padding: 16px 12px 12px;
  background: #ffffff;
  box-shadow: 0 8px 18px rgb(15 23 42 / 5%);
  text-align: left;
  transform: translate(-50%, -50%);
  touch-action: none;
  cursor: grab;
}

.graph-node:hover,
.graph-node.active {
  border-color: #60a5fa;
  background: #f8fbff;
}

.graph-node.dragging {
  opacity: 0.84;
  border-style: dashed;
  box-shadow: 0 18px 32px rgb(37 99 235 / 16%);
  cursor: grabbing;
}

.graph-node.normal {
  opacity: 1;
}

.graph-node.subtle {
  opacity: 0.72;
}

.graph-node.hidden {
  opacity: 0.65;
}

.graph-node.size-1 {
  width: 170px;
  min-height: 74px;
}

.graph-node.size-2 {
  width: 200px;
  min-height: 90px;
}

.graph-node.size-3 {
  width: 230px;
  min-height: 108px;
}

.drag-handle {
  position: absolute;
  top: 6px;
  right: 8px;
  color: #94a3b8;
  font-size: 0.88rem;
  line-height: 1;
  user-select: none;
  pointer-events: none;
}

.node-title {
  color: #0f172a;
  font-size: 0.88rem;
  font-weight: 800;
  line-height: 1.45;
}

.node-type {
  color: #2563eb;
  font-size: 0.76rem;
  line-height: 1.35;
}

.node-summary {
  color: #475569;
  font-size: 0.76rem;
  line-height: 1.45;
}

.detail-panel {
  overflow: auto;
  align-content: start;
}

.detail-header {
  align-items: flex-start;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.field-wide {
  grid-column: 1 / -1;
}

.form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding-top: 4px;
}

.empty-detail {
  display: grid;
  gap: 12px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 14px;
  background: #f8fafc;
  color: #475569;
}

.empty-detail h2 {
  font-size: 0.98rem;
}

.empty-detail p {
  margin: 0;
  line-height: 1.6;
}

@media (max-width: 1280px) {
  .workspace,
  .workspace.detail-visible {
    grid-template-columns: 300px minmax(0, 1fr);
  }

  .detail-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 900px) {
  .graph-page {
    padding: 16px;
  }

  .page-header,
  .header-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .workspace,
  .workspace.detail-visible {
    grid-template-columns: 1fr;
  }

  .form-grid,
  .filters-grid {
    grid-template-columns: 1fr;
  }

  .graph-canvas-panel {
    min-height: 520px;
  }
}
</style>
