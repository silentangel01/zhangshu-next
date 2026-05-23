<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

import type { GraphEdge, GraphNode as GraphNodeEntity } from '@/entities/graph/types'

import GraphContextMenu, { type GraphContextMenuItem } from './GraphContextMenu.vue'
import GraphEdgeOverlay from './GraphEdgeOverlay.vue'
import GraphNodeCard from './GraphNode.vue'
import type { GraphToolMode } from './GraphToolbar.vue'

interface Point {
  x: number
  y: number
}

export interface GraphViewportState {
  panX: number
  panY: number
  zoom: number
}

interface EdgeRenderItem {
  edge: GraphEdge
  fromNode: GraphNodeEntity
  toNode: GraphNodeEntity
  path: string
  labelX: number
  labelY: number
}

type GraphContextMenuTarget =
  | { type: 'canvas'; graphX: number; graphY: number }
  | { type: 'node'; nodeId: string }
  | { type: 'edge'; edgeId: string }

const props = defineProps<{
  nodes: GraphNodeEntity[]
  edges: GraphEdge[]
  selectedNodeId: string | null
  selectedEdgeId: string | null
  mode: GraphToolMode
  modeLabel: string
  showGrid: boolean
  snapToGrid: boolean
  cleanMode: boolean
  zoomPercent: number
}>()

const emit = defineEmits<{
  selectNode: [node: GraphNodeEntity]
  selectEdge: [edge: GraphEdge]
  clearSelection: []
  createNode: [point: Point]
  createEdge: [fromNodeId: string, toNodeId: string]
  saveNodePosition: [node: GraphNodeEntity, x: number, y: number, previous: Point]
  saveNodeSize: [node: GraphNodeEntity, width: number, height: number, previous: { width: number; height: number }]
  deleteNode: [node: GraphNodeEntity]
  deleteEdge: [edge: GraphEdge]
  duplicateNode: [node: GraphNodeEntity]
  openBound: [node: GraphNodeEntity]
  setMode: [mode: GraphToolMode]
  zoomChanged: [zoomPercent: number]
  viewportChanged: [viewport: GraphViewportState]
}>()

defineExpose({
  zoomIn,
  zoomOut,
  fitView,
  resetView,
  graphToScreen,
  screenToGraph,
  getViewportCenter,
  centerOnNode,
  getViewportState,
  applyViewportState,
})

const canvasRef = ref<HTMLElement | null>(null)
const size = reactive({ width: 1000, height: 680 })
const viewport = reactive({ panX: 0, panY: 0, zoom: 1 })
const contextMenu = reactive<{
  visible: boolean
  x: number
  y: number
  target: GraphContextMenuTarget | null
  items: GraphContextMenuItem[]
}>({
  visible: false,
  x: 0,
  y: 0,
  target: null,
  items: [],
})
const drag = reactive({
  nodeId: null as string | null,
  pointerId: null as number | null,
  startClientX: 0,
  startClientY: 0,
  startGraphX: 0,
  startGraphY: 0,
  currentX: 0,
  currentY: 0,
  previousX: 0,
  previousY: 0,
  active: false,
})
const pan = reactive({
  active: false,
  pointerId: null as number | null,
  startX: 0,
  startY: 0,
  originPanX: 0,
  originPanY: 0,
})
const resize = reactive({
  nodeId: null as string | null,
  pointerId: null as number | null,
  startClientX: 0,
  startClientY: 0,
  startWidth: 0,
  startHeight: 0,
  currentWidth: 0,
  currentHeight: 0,
  previousWidth: 0,
  previousHeight: 0,
  active: false,
})

const edgeSourceId = ref<string | null>(null)
const pointerGraph = ref<Point | null>(null)
const spacePressed = ref(false)
const pointerInsideCanvas = ref(false)
let resizeObserver: ResizeObserver | null = null

const GRID_SIZE = 20
const MIN_ZOOM = 0.25
const MAX_ZOOM = 2.5
const NODE_WIDTH = 190
const NODE_HEIGHT = 92
const MIN_NODE_WIDTH = 80
const MIN_NODE_HEIGHT = 40
const MAX_NODE_WIDTH = 420
const MAX_NODE_HEIGHT = 260

const visibleNodes = computed(() =>
  props.nodes.filter((node) => node.visibility !== 'hidden'),
)

const nodeMap = computed(() => new Map(props.nodes.map((node) => [node.id, node] as const)))
const canTemporaryPan = computed(() => spacePressed.value && pointerInsideCanvas.value)

const visibleEdges = computed<EdgeRenderItem[]>(() => {
  return props.edges
    .filter((edge) => {
      if (edge.visibility === 'hidden') {
        return false
      }
      if (props.cleanMode && edge.visibility === 'subtle') {
        return false
      }
      const fromNode = nodeMap.value.get(edge.from_node_id)
      const toNode = nodeMap.value.get(edge.to_node_id)
      return Boolean(fromNode && toNode && fromNode.visibility !== 'hidden' && toNode.visibility !== 'hidden')
    })
    .map((edge) => {
      const fromNode = nodeMap.value.get(edge.from_node_id)
      const toNode = nodeMap.value.get(edge.to_node_id)
      if (!fromNode || !toNode) {
        return null
      }
      const from = graphToScreen(getNodeX(fromNode), getNodeY(fromNode))
      const to = graphToScreen(getNodeX(toNode), getNodeY(toNode))
      const pathInfo = buildPath(from, to, edge.line_style === 'arc')
      return {
        edge,
        fromNode,
        toNode,
        path: pathInfo.path,
        labelX: pathInfo.labelX,
        labelY: pathInfo.labelY,
      }
    })
    .filter((item): item is EdgeRenderItem => item !== null)
})

const previewPath = computed(() => {
  if (!edgeSourceId.value || !pointerGraph.value) {
    return ''
  }
  const source = nodeMap.value.get(edgeSourceId.value)
  if (!source) {
    return ''
  }
  const from = graphToScreen(getNodeX(source), getNodeY(source))
  const to = graphToScreen(pointerGraph.value.x, pointerGraph.value.y)
  return buildPath(from, to, false).path
})

const gridStyle = computed(() => {
  if (!props.showGrid) {
    return {}
  }
  const grid = GRID_SIZE * viewport.zoom
  return {
    backgroundImage: 'linear-gradient(90deg, var(--zs-canvas-grid) 1px, transparent 1px), linear-gradient(var(--zs-canvas-grid) 1px, transparent 1px)',
    backgroundSize: `${grid}px ${grid}px`,
    backgroundPosition: `${viewport.panX}px ${viewport.panY}px`,
  }
})

onMounted(() => {
  resizeObserver = new ResizeObserver((entries) => {
    const rect = entries[0]?.contentRect
    if (!rect) {
      return
    }
    size.width = Math.max(480, Math.floor(rect.width))
    size.height = Math.max(420, Math.floor(rect.height))
  })
  if (canvasRef.value) {
    resizeObserver.observe(canvasRef.value)
  }
  window.addEventListener('pointermove', handleWindowPointerMove)
  window.addEventListener('pointerup', handleWindowPointerUp)
  window.addEventListener('keydown', handleKeyDown)
  window.addEventListener('keyup', handleKeyUp)
  window.addEventListener('blur', handleWindowBlur)
  window.addEventListener('click', closeContextMenu)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  window.removeEventListener('pointermove', handleWindowPointerMove)
  window.removeEventListener('pointerup', handleWindowPointerUp)
  window.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('keyup', handleKeyUp)
  window.removeEventListener('blur', handleWindowBlur)
  window.removeEventListener('click', closeContextMenu)
})

function graphToScreen(x: number, y: number): Point {
  return {
    x: x * viewport.zoom + viewport.panX,
    y: y * viewport.zoom + viewport.panY,
  }
}

function screenToGraph(clientX: number, clientY: number): Point {
  const rect = canvasRef.value?.getBoundingClientRect()
  const localX = clientX - (rect?.left ?? 0)
  const localY = clientY - (rect?.top ?? 0)
  return {
    x: (localX - viewport.panX) / viewport.zoom,
    y: (localY - viewport.panY) / viewport.zoom,
  }
}

function getViewportCenter(): Point {
  return {
    x: (size.width / 2 - viewport.panX) / viewport.zoom,
    y: (size.height / 2 - viewport.panY) / viewport.zoom,
  }
}

function handleWheel(event: WheelEvent) {
  event.preventDefault()
  const nextZoom = clamp(viewport.zoom * (event.deltaY > 0 ? 0.9 : 1.1), MIN_ZOOM, MAX_ZOOM)
  zoomAround(event.clientX, event.clientY, nextZoom)
}

function zoomIn() {
  zoomAroundCenter(clamp(viewport.zoom * 1.15, MIN_ZOOM, MAX_ZOOM))
}

function zoomOut() {
  zoomAroundCenter(clamp(viewport.zoom / 1.15, MIN_ZOOM, MAX_ZOOM))
}

function zoomAroundCenter(nextZoom: number) {
  const rect = canvasRef.value?.getBoundingClientRect()
  zoomAround((rect?.left ?? 0) + size.width / 2, (rect?.top ?? 0) + size.height / 2, nextZoom)
}

function zoomAround(clientX: number, clientY: number, nextZoom: number) {
  const before = screenToGraph(clientX, clientY)
  const rect = canvasRef.value?.getBoundingClientRect()
  const localX = clientX - (rect?.left ?? 0)
  const localY = clientY - (rect?.top ?? 0)
  viewport.zoom = nextZoom
  viewport.panX = localX - before.x * viewport.zoom
  viewport.panY = localY - before.y * viewport.zoom
  emit('zoomChanged', Math.round(viewport.zoom * 100))
  emitViewportChanged()
}

function resetView() {
  viewport.zoom = 1
  viewport.panX = 0
  viewport.panY = 0
  emit('zoomChanged', 100)
  emitViewportChanged()
}

function centerOnNode(nodeId: string) {
  const node = nodeMap.value.get(nodeId)
  if (!node) {
    return
  }
  viewport.panX = size.width / 2 - node.x * viewport.zoom
  viewport.panY = size.height / 2 - node.y * viewport.zoom
  emitViewportChanged()
}

function fitView() {
  if (visibleNodes.value.length === 0) {
    resetView()
    return
  }
  const xs = visibleNodes.value.map((node) => getNodeX(node))
  const ys = visibleNodes.value.map((node) => getNodeY(node))
  const minX = Math.min(...xs) - NODE_WIDTH
  const maxX = Math.max(...xs) + NODE_WIDTH
  const minY = Math.min(...ys) - NODE_HEIGHT
  const maxY = Math.max(...ys) + NODE_HEIGHT
  const nextZoom = clamp(Math.min(size.width / Math.max(1, maxX - minX), size.height / Math.max(1, maxY - minY), 1.6), MIN_ZOOM, MAX_ZOOM)
  viewport.zoom = nextZoom
  viewport.panX = (size.width - (minX + maxX) * nextZoom) / 2
  viewport.panY = (size.height - (minY + maxY) * nextZoom) / 2
  emit('zoomChanged', Math.round(viewport.zoom * 100))
  emitViewportChanged()
}

function getViewportState(): GraphViewportState {
  return {
    panX: viewport.panX,
    panY: viewport.panY,
    zoom: viewport.zoom,
  }
}

function applyViewportState(state: GraphViewportState) {
  viewport.panX = state.panX
  viewport.panY = state.panY
  viewport.zoom = clamp(state.zoom, MIN_ZOOM, MAX_ZOOM)
  emit('zoomChanged', Math.round(viewport.zoom * 100))
}

function emitViewportChanged() {
  emit('viewportChanged', getViewportState())
}

function handleCanvasPointerDown(event: PointerEvent) {
  canvasRef.value?.focus()
  closeContextMenu()
  pointerGraph.value = screenToGraph(event.clientX, event.clientY)

  if (event.button === 1) {
    startPan(event)
    return
  }

  if (event.button === 0 && (props.mode === 'pan' || spacePressed.value)) {
    startPan(event)
    return
  }

  if (event.button !== 0) {
    return
  }

  if (props.mode === 'node') {
    emit('createNode', snapPoint(screenToGraph(event.clientX, event.clientY)))
    return
  }

  emit('clearSelection')
}

function handleCanvasDoubleClick(event: MouseEvent) {
  if (props.mode !== 'select' || spacePressed.value || event.button !== 0) {
    return
  }
  if (!isBlankCanvasDoubleClick(event)) {
    return
  }
  emit('createNode', snapPoint(screenToGraph(event.clientX, event.clientY)))
}

function isBlankCanvasDoubleClick(event: MouseEvent) {
  const target = event.target
  if (!(target instanceof Element)) {
    return false
  }
  if (target.closest('[data-graph-node="true"]')) {
    return false
  }
  if (target.closest('[data-graph-edge="true"]')) {
    return false
  }
  if (target.closest('[data-graph-toolbar="true"]')) {
    return false
  }
  if (target.closest('[data-graph-inspector="true"]')) {
    return false
  }
  if (target.closest('[data-graph-context-menu="true"]')) {
    return false
  }
  return target === canvasRef.value
    || target.closest('[data-graph-canvas-background="true"]') === canvasRef.value
}

function startPan(event: PointerEvent) {
  event.preventDefault()
  pan.active = true
  pan.pointerId = event.pointerId
  pan.startX = event.clientX
  pan.startY = event.clientY
  pan.originPanX = viewport.panX
  pan.originPanY = viewport.panY
  clearDragState()
  canvasRef.value?.setPointerCapture(event.pointerId)
}

function handleNodePointerDown(event: PointerEvent, node: GraphNodeEntity) {
  if (event.button === 1 || props.mode === 'pan' || spacePressed.value) {
    startPan(event)
    return
  }
  if (event.button !== 0) {
    return
  }
  closeContextMenu()
  drag.nodeId = node.id
  drag.pointerId = event.pointerId
  drag.startClientX = event.clientX
  drag.startClientY = event.clientY
  drag.startGraphX = getNodeX(node)
  drag.startGraphY = getNodeY(node)
  drag.currentX = getNodeX(node)
  drag.currentY = getNodeY(node)
  drag.previousX = node.x
  drag.previousY = node.y
  drag.active = false
}

function handleNodeClick(event: MouseEvent, node: GraphNodeEntity) {
  event.stopPropagation()
  if (pan.active || spacePressed.value || props.mode === 'pan') {
    return
  }
  if (props.mode === 'edge') {
    if (!edgeSourceId.value) {
      edgeSourceId.value = node.id
      emit('selectNode', node)
      return
    }
    if (edgeSourceId.value === node.id) {
      edgeSourceId.value = null
      return
    }
    emit('createEdge', edgeSourceId.value, node.id)
    edgeSourceId.value = null
    return
  }
  emit('selectNode', node)
}

function handleWindowPointerMove(event: PointerEvent) {
  pointerGraph.value = screenToGraph(event.clientX, event.clientY)
  if (resize.nodeId && resize.pointerId === event.pointerId) {
    resize.active = true
    resize.currentWidth = clamp(
      resize.startWidth + (event.clientX - resize.startClientX) / viewport.zoom,
      MIN_NODE_WIDTH,
      MAX_NODE_WIDTH,
    )
    resize.currentHeight = clamp(
      resize.startHeight + (event.clientY - resize.startClientY) / viewport.zoom,
      MIN_NODE_HEIGHT,
      MAX_NODE_HEIGHT,
    )
    return
  }
  if (pan.active && pan.pointerId === event.pointerId) {
    viewport.panX = pan.originPanX + event.clientX - pan.startX
    viewport.panY = pan.originPanY + event.clientY - pan.startY
    return
  }
  if (!drag.nodeId || drag.pointerId !== event.pointerId) {
    return
  }
  const distance = Math.hypot(event.clientX - drag.startClientX, event.clientY - drag.startClientY)
  if (distance < 4 && !drag.active) {
    return
  }
  drag.active = true
  const deltaX = (event.clientX - drag.startClientX) / viewport.zoom
  const deltaY = (event.clientY - drag.startClientY) / viewport.zoom
  const point = snapPoint({
    x: clamp(drag.startGraphX + deltaX, -20000, 20000),
    y: clamp(drag.startGraphY + deltaY, -20000, 20000),
  })
  drag.currentX = point.x
  drag.currentY = point.y
}

function handleWindowPointerUp(event: PointerEvent) {
  if (resize.nodeId && resize.pointerId === event.pointerId) {
    const node = nodeMap.value.get(resize.nodeId)
    const wasResizing = resize.active
    const width = resize.currentWidth
    const height = resize.currentHeight
    const previous = { width: resize.previousWidth, height: resize.previousHeight }
    clearResizeState()
    if (node && wasResizing && Number.isFinite(width) && Number.isFinite(height)) {
      emit('saveNodeSize', node, width, height, previous)
    }
    return
  }
  if (pan.active && pan.pointerId === event.pointerId) {
    pan.active = false
    pan.pointerId = null
    emitViewportChanged()
    return
  }
  if (!drag.nodeId || drag.pointerId !== event.pointerId) {
    return
  }
  const node = nodeMap.value.get(drag.nodeId)
  const wasDragging = drag.active
  const x = drag.currentX
  const y = drag.currentY
  const previous = { x: drag.previousX, y: drag.previousY }
  clearDragState()
  if (node && wasDragging && Number.isFinite(x) && Number.isFinite(y)) {
    emit('saveNodePosition', node, x, y, previous)
  }
}

function handleContextCanvas(event: MouseEvent) {
  event.preventDefault()
  const point = snapPoint(screenToGraph(event.clientX, event.clientY))
  openContextMenu(event, {
    type: 'canvas',
    graphX: point.x,
    graphY: point.y,
  })
}

function handleNodeContextMenu(event: MouseEvent, node: GraphNodeEntity) {
  emit('selectNode', node)
  openContextMenu(event, { type: 'node', nodeId: node.id })
}

function handleEdgeContextMenu(event: MouseEvent, edge: GraphEdge) {
  emit('selectEdge', edge)
  openContextMenu(event, { type: 'edge', edgeId: edge.id })
}

function openContextMenu(event: MouseEvent, target: GraphContextMenuTarget) {
  contextMenu.visible = true
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.target = target
  contextMenu.items = buildContextMenuItems(target)
}

function closeContextMenu() {
  contextMenu.visible = false
  contextMenu.target = null
  contextMenu.items = []
}

function buildContextMenuItems(target: GraphContextMenuTarget): GraphContextMenuItem[] {
  if (target.type === 'canvas') {
    return [
      { key: 'create-node-here', label: '在此处新建节点' },
      { key: 'fit-view', label: '适应画布' },
      { key: 'reset-view', label: '重置视图' },
    ]
  }

  if (target.type === 'edge') {
    return [
      { key: 'edit-edge', label: '编辑关系' },
      { key: 'delete-edge', label: '删除关系', danger: true },
    ]
  }

  const node = nodeMap.value.get(target.nodeId)
  return [
    { key: 'edit-node', label: '编辑节点' },
    { key: 'connect-from-node', label: '从此节点连线' },
    { key: 'duplicate-node', label: '复制节点' },
    { key: 'delete-node', label: '删除节点', danger: true },
    {
      key: 'open-bound-material',
      label: '打开绑定资料',
      disabled: !node?.bound_type || !node.bound_id,
    },
  ]
}

function handleKeyDown(event: KeyboardEvent) {
  if (isTextEditingTarget(event.target)) {
    return
  }
  if (event.code === 'Space') {
    if (pointerInsideCanvas.value || document.activeElement === canvasRef.value) {
      event.preventDefault()
    }
    spacePressed.value = true
  }
  if (event.key === 'Escape') {
    edgeSourceId.value = null
    closeContextMenu()
  }
  if (event.key === 'Delete') {
    if (props.selectedNodeId) {
      const node = nodeMap.value.get(props.selectedNodeId)
      if (node) {
        emit('deleteNode', node)
      }
    } else if (props.selectedEdgeId) {
      const edge = props.edges.find((item) => item.id === props.selectedEdgeId)
      if (edge) {
        emit('deleteEdge', edge)
      }
    }
  }
}

function handleKeyUp(event: KeyboardEvent) {
  if (event.code === 'Space') {
    spacePressed.value = false
  }
}

function handleWindowBlur() {
  spacePressed.value = false
  pointerInsideCanvas.value = false
}

function handleCanvasPointerEnter() {
  pointerInsideCanvas.value = true
}

function handleCanvasPointerLeave() {
  pointerInsideCanvas.value = false
}

function isTextEditingTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) {
    return false
  }
  const tagName = target.tagName.toLowerCase()
  return tagName === 'input'
    || tagName === 'textarea'
    || tagName === 'select'
    || target.isContentEditable
}

function handleContextMenuAction(actionKey: string) {
  const target = contextMenu.target
  closeContextMenu()
  if (!target) {
    return
  }

  if (target.type === 'canvas') {
    handleCanvasContextAction(actionKey, target)
  } else if (target.type === 'node') {
    handleNodeContextAction(actionKey, target.nodeId)
  } else {
    handleEdgeContextAction(actionKey, target.edgeId)
  }
}

function handleCanvasContextAction(actionKey: string, target: Extract<GraphContextMenuTarget, { type: 'canvas' }>) {
  switch (actionKey) {
    case 'create-node-here':
      emit('createNode', { x: target.graphX, y: target.graphY })
      break
    case 'fit-view':
      fitView()
      break
    case 'reset-view':
      resetView()
      break
  }
}

function handleNodeContextAction(actionKey: string, nodeId: string) {
  const node = nodeMap.value.get(nodeId)
  if (!node) {
    return
  }

  switch (actionKey) {
    case 'edit-node':
      emit('selectNode', node)
      break
    case 'connect-from-node':
      edgeSourceId.value = node.id
      emit('selectNode', node)
      emit('setMode', 'edge')
      break
    case 'duplicate-node':
      emit('duplicateNode', node)
      break
    case 'delete-node':
      emit('deleteNode', node)
      break
    case 'open-bound-material':
      emit('openBound', node)
      break
  }
}

function handleEdgeContextAction(actionKey: string, edgeId: string) {
  const edge = props.edges.find((item) => item.id === edgeId)
  if (!edge) {
    return
  }

  switch (actionKey) {
    case 'edit-edge':
      emit('selectEdge', edge)
      break
    case 'delete-edge':
      emit('deleteEdge', edge)
      break
  }
}

function clearDragState() {
  drag.nodeId = null
  drag.pointerId = null
  drag.active = false
}

function clearResizeState() {
  resize.nodeId = null
  resize.pointerId = null
  resize.active = false
}

function handleResizePointerDown(event: PointerEvent, node: GraphNodeEntity) {
  event.preventDefault()
  event.stopPropagation()
  closeContextMenu()
  resize.nodeId = node.id
  resize.pointerId = event.pointerId
  resize.startClientX = event.clientX
  resize.startClientY = event.clientY
  resize.startWidth = getNodeWidth(node)
  resize.startHeight = getNodeHeight(node)
  resize.currentWidth = getNodeWidth(node)
  resize.currentHeight = getNodeHeight(node)
  resize.previousWidth = getNodeWidth(node)
  resize.previousHeight = getNodeHeight(node)
  resize.active = false
  clearDragState()
  canvasRef.value?.setPointerCapture(event.pointerId)
}

function getNodeX(node: GraphNodeEntity) {
  return drag.nodeId === node.id && drag.active ? drag.currentX : node.x
}

function getNodeY(node: GraphNodeEntity) {
  return drag.nodeId === node.id && drag.active ? drag.currentY : node.y
}

function getNodeStyle(node: GraphNodeEntity) {
  const point = graphToScreen(getNodeX(node), getNodeY(node))
  return {
    left: `${point.x}px`,
    top: `${point.y}px`,
    width: `${getNodeWidth(node)}px`,
    height: `${getNodeHeight(node)}px`,
    transform: `translate(-50%, -50%) scale(${viewport.zoom})`,
  }
}

function getNodeWidth(node: GraphNodeEntity) {
  if (resize.nodeId === node.id && resize.active) {
    return resize.currentWidth
  }
  return clamp(Number.isFinite(node.width) ? node.width : presetNodeSize(node.size).width, MIN_NODE_WIDTH, MAX_NODE_WIDTH)
}

function getNodeHeight(node: GraphNodeEntity) {
  if (resize.nodeId === node.id && resize.active) {
    return resize.currentHeight
  }
  return clamp(Number.isFinite(node.height) ? node.height : presetNodeSize(node.size).height, MIN_NODE_HEIGHT, MAX_NODE_HEIGHT)
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

function snapPoint(point: Point): Point {
  if (!props.snapToGrid) {
    return point
  }
  return {
    x: Math.round(point.x / GRID_SIZE) * GRID_SIZE,
    y: Math.round(point.y / GRID_SIZE) * GRID_SIZE,
  }
}

function buildPath(from: Point, to: Point, arc: boolean) {
  if (!arc) {
    return {
      path: `M ${from.x} ${from.y} L ${to.x} ${to.y}`,
      labelX: (from.x + to.x) / 2,
      labelY: (from.y + to.y) / 2 - 8,
    }
  }
  const midX = (from.x + to.x) / 2
  const midY = (from.y + to.y) / 2
  const dx = to.x - from.x
  const dy = to.y - from.y
  const length = Math.max(1, Math.hypot(dx, dy))
  const curve = Math.min(90, length * 0.18)
  const controlX = midX - (dy / length) * curve
  const controlY = midY + (dx / length) * curve
  return {
    path: `M ${from.x} ${from.y} Q ${controlX} ${controlY} ${to.x} ${to.y}`,
    labelX: controlX,
    labelY: controlY - 8,
  }
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}
</script>

<template>
  <section
    ref="canvasRef"
    tabindex="0"
    class="graph-canvas"
    data-graph-canvas-background="true"
    :class="[`mode-${mode}`, { panning: pan.active, 'space-pan-ready': canTemporaryPan }]"
    :style="gridStyle"
    @wheel="handleWheel"
    @pointerdown="handleCanvasPointerDown"
    @pointerenter="handleCanvasPointerEnter"
    @pointerleave="handleCanvasPointerLeave"
    @dblclick="handleCanvasDoubleClick"
    @auxclick.prevent
    @contextmenu="handleContextCanvas"
  >
    <div class="canvas-status">
      <span>当前模式：{{ modeLabel }}</span>
      <span>{{ zoomPercent }}%</span>
      <span v-if="selectedNodeId || selectedEdgeId">已选择 1 项</span>
    </div>

    <div class="canvas-hints">
      <span>滚轮缩放</span>
      <span>按住 Space 拖动画布</span>
      <span>中键拖动画布</span>
      <span>右键打开菜单</span>
      <span v-if="mode === 'pan'">平移模式：拖动画布移动视图</span>
      <span v-else>连线模式下依次点击两个节点创建关系</span>
    </div>

    <GraphEdgeOverlay
      :edges="visibleEdges"
      :selected-edge-id="selectedEdgeId"
      :clean-mode="cleanMode"
      :width="size.width"
      :height="size.height"
      :preview-path="previewPath"
      @select-edge="emit('selectEdge', $event)"
      @context-menu="handleEdgeContextMenu"
    />

    <div class="node-layer">
      <div
        v-for="node in visibleNodes"
        :key="node.id"
        class="node-position"
        data-graph-node="true"
        :style="getNodeStyle(node)"
        @dblclick.stop="handleNodeClick($event, node)"
      >
        <GraphNodeCard
          :node="node"
          :selected="selectedNodeId === node.id || edgeSourceId === node.id"
          :dragging="drag.nodeId === node.id && drag.active"
          :clean-mode="cleanMode"
          @pointer-down="handleNodePointerDown"
          @click-node="handleNodeClick"
          @context-menu="handleNodeContextMenu"
        />
        <button
          v-if="selectedNodeId === node.id"
          type="button"
          class="resize-handle"
          aria-label="调整节点大小"
          @pointerdown.stop="handleResizePointerDown($event, node)"
          @click.stop
          @dblclick.stop
          @contextmenu.prevent.stop
        />
      </div>
    </div>

    <div v-if="visibleNodes.length === 0" class="empty-state">
      <h2>暂无关系图节点</h2>
      <p>你可以：</p>
      <ul>
        <li>点击“新建节点”</li>
        <li>在画布中双击创建节点</li>
        <li>从人物、设定、伏笔或时间轴事件创建节点</li>
      </ul>
    </div>

    <GraphContextMenu
      :visible="contextMenu.visible"
      :x="contextMenu.x"
      :y="contextMenu.y"
      :items="contextMenu.items"
      @select="handleContextMenuAction"
    />
  </section>
</template>

<style scoped>
.graph-canvas {
  position: relative;
  min-height: 600px;
  height: 100%;
  overflow: hidden;
  border: 1px solid var(--zs-canvas-node-border);
  border-radius: var(--zs-radius-md);
  background-color: var(--zs-canvas-bg);
  box-shadow: inset 0 0 0 1px rgb(255 255 255 / 80%), 0 10px 26px rgb(15 23 42 / 6%);
  cursor: default;
  outline: none;
  user-select: none;
}

.graph-canvas.mode-node {
  cursor: crosshair;
}

.graph-canvas.mode-pan,
.graph-canvas.space-pan-ready {
  cursor: grab;
}

.graph-canvas.panning {
  cursor: grabbing;
}

.node-layer {
  position: absolute;
  inset: 0;
}

.node-position {
  position: absolute;
  z-index: 2;
  transform-origin: center;
}

.resize-handle {
  position: absolute;
  right: -7px;
  bottom: -7px;
  z-index: 5;
  width: 14px;
  height: 14px;
  box-sizing: border-box;
  border: 2px solid var(--zs-color-surface);
  border-radius: var(--zs-radius-sm);
  padding: 0;
  background: var(--zs-color-primary);
  box-shadow: 0 2px 8px rgb(15 23 42 / 22%);
  cursor: nwse-resize;
  touch-action: none;
}

.canvas-status,
.canvas-hints {
  position: absolute;
  z-index: 4;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  pointer-events: none;
}

.canvas-status {
  top: 10px;
  right: 10px;
}

.canvas-hints {
  right: 10px;
  bottom: 10px;
  max-width: min(620px, calc(100% - 20px));
  justify-content: flex-end;
}

.canvas-status span,
.canvas-hints span {
  border: 1px solid color-mix(in srgb, var(--zs-color-border) 80%, transparent);
  border-radius: 999px;
  padding: 4px 8px;
  background: color-mix(in srgb, var(--zs-color-surface) 86%, transparent);
  color: var(--zs-color-text-muted);
  font-size: 0.72rem;
  font-weight: 800;
  backdrop-filter: blur(8px);
}

.empty-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  gap: 9px;
  color: var(--zs-color-text-muted);
  text-align: center;
  pointer-events: none;
}

.empty-state h2,
.empty-state p {
  margin: 0;
}

.empty-state h2 {
  color: var(--zs-color-text);
  font-size: 1.08rem;
  font-weight: 900;
}

.empty-state p,
.empty-state li {
  font-size: 0.86rem;
}

.empty-state ul {
  display: grid;
  gap: 5px;
  margin: 0;
  padding: 0;
  list-style: none;
}
</style>
