<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

import type { GraphEdge, GraphNode as GraphNodeEntity } from '@/entities/graph/types'

import GraphContextMenu, { type GraphContextMenuKind } from './GraphContextMenu.vue'
import GraphEdgeOverlay from './GraphEdgeOverlay.vue'
import GraphNodeCard from './GraphNode.vue'
import type { GraphToolMode } from './GraphToolbar.vue'

interface Point {
  x: number
  y: number
}

interface EdgeRenderItem {
  edge: GraphEdge
  fromNode: GraphNodeEntity
  toNode: GraphNodeEntity
  path: string
  labelX: number
  labelY: number
}

const props = defineProps<{
  nodes: GraphNodeEntity[]
  edges: GraphEdge[]
  selectedNodeId: string | null
  selectedEdgeId: string | null
  mode: GraphToolMode
  showGrid: boolean
  snapToGrid: boolean
  cleanMode: boolean
}>()

const emit = defineEmits<{
  selectNode: [node: GraphNodeEntity]
  selectEdge: [edge: GraphEdge]
  clearSelection: []
  createNode: [point: Point]
  createEdge: [fromNodeId: string, toNodeId: string]
  saveNodePosition: [node: GraphNodeEntity, x: number, y: number, previous: Point]
  deleteNode: [node: GraphNodeEntity]
  deleteEdge: [edge: GraphEdge]
  duplicateNode: [node: GraphNodeEntity]
  openBound: [node: GraphNodeEntity]
  zoomChanged: [zoomPercent: number]
}>()

defineExpose({
  zoomIn,
  zoomOut,
  fitView,
  resetView,
  graphToScreen,
  screenToGraph,
  getViewportCenter,
})

const canvasRef = ref<HTMLElement | null>(null)
const size = reactive({ width: 1000, height: 680 })
const viewport = reactive({ panX: 0, panY: 0, zoom: 1 })
const contextMenu = reactive<{
  visible: boolean
  kind: GraphContextMenuKind
  x: number
  y: number
  graphPoint: Point
  node: GraphNodeEntity | null
  edge: GraphEdge | null
}>({
  visible: false,
  kind: 'canvas',
  x: 0,
  y: 0,
  graphPoint: { x: 0, y: 0 },
  node: null,
  edge: null,
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

const edgeSourceId = ref<string | null>(null)
const pointerGraph = ref<Point | null>(null)
const spacePressed = ref(false)
let resizeObserver: ResizeObserver | null = null

const GRID_SIZE = 20
const MIN_ZOOM = 0.25
const MAX_ZOOM = 2.5
const NODE_WIDTH = 190
const NODE_HEIGHT = 92

const visibleNodes = computed(() =>
  props.nodes.filter((node) => node.visibility !== 'hidden'),
)

const nodeMap = computed(() => new Map(props.nodes.map((node) => [node.id, node] as const)))

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
    backgroundImage: 'linear-gradient(90deg, rgb(148 163 184 / 16%) 1px, transparent 1px), linear-gradient(rgb(148 163 184 / 16%) 1px, transparent 1px)',
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
  window.addEventListener('click', closeContextMenu)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  window.removeEventListener('pointermove', handleWindowPointerMove)
  window.removeEventListener('pointerup', handleWindowPointerUp)
  window.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('keyup', handleKeyUp)
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
}

function resetView() {
  viewport.zoom = 1
  viewport.panX = 0
  viewport.panY = 0
  emit('zoomChanged', 100)
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
}

function handleCanvasPointerDown(event: PointerEvent) {
  closeContextMenu()
  pointerGraph.value = screenToGraph(event.clientX, event.clientY)
  if (event.button === 1 || props.mode === 'pan' || spacePressed.value) {
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

function startPan(event: PointerEvent) {
  pan.active = true
  pan.pointerId = event.pointerId
  pan.startX = event.clientX
  pan.startY = event.clientY
  pan.originPanX = viewport.panX
  pan.originPanY = viewport.panY
  canvasRef.value?.setPointerCapture(event.pointerId)
}

function handleNodePointerDown(event: PointerEvent, node: GraphNodeEntity) {
  if (props.mode === 'pan') {
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
  if (pan.active && pan.pointerId === event.pointerId) {
    pan.active = false
    pan.pointerId = null
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
  openContextMenu('canvas', event, point, null, null)
}

function handleNodeContextMenu(event: MouseEvent, node: GraphNodeEntity) {
  emit('selectNode', node)
  openContextMenu('node', event, screenToGraph(event.clientX, event.clientY), node, null)
}

function handleEdgeContextMenu(event: MouseEvent, edge: GraphEdge) {
  emit('selectEdge', edge)
  openContextMenu('edge', event, screenToGraph(event.clientX, event.clientY), null, edge)
}

function openContextMenu(kind: GraphContextMenuKind, event: MouseEvent, graphPoint: Point, node: GraphNodeEntity | null, edge: GraphEdge | null) {
  contextMenu.visible = true
  contextMenu.kind = kind
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.graphPoint = graphPoint
  contextMenu.node = node
  contextMenu.edge = edge
}

function closeContextMenu() {
  contextMenu.visible = false
}

function handleKeyDown(event: KeyboardEvent) {
  if (event.code === 'Space') {
    spacePressed.value = true
  }
  if (event.key === 'Escape') {
    edgeSourceId.value = null
    closeContextMenu()
  }
}

function handleKeyUp(event: KeyboardEvent) {
  if (event.code === 'Space') {
    spacePressed.value = false
  }
}

function createNodeFromMenu() {
  emit('createNode', contextMenu.graphPoint)
  closeContextMenu()
}

function startEdgeFromMenu() {
  if (contextMenu.node) {
    edgeSourceId.value = contextMenu.node.id
    emit('selectNode', contextMenu.node)
  }
  closeContextMenu()
}

function clearDragState() {
  drag.nodeId = null
  drag.pointerId = null
  drag.active = false
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
    transform: `translate(-50%, -50%) scale(${viewport.zoom})`,
  }
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
    class="graph-canvas"
    :class="[`mode-${mode}`, { panning: pan.active }]"
    :style="gridStyle"
    @wheel="handleWheel"
    @pointerdown="handleCanvasPointerDown"
    @contextmenu="handleContextCanvas"
  >
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
      <div v-for="node in visibleNodes" :key="node.id" class="node-position" :style="getNodeStyle(node)">
        <GraphNodeCard
          :node="node"
          :selected="selectedNodeId === node.id || edgeSourceId === node.id"
          :dragging="drag.nodeId === node.id && drag.active"
          :clean-mode="cleanMode"
          @pointer-down="handleNodePointerDown"
          @click-node="handleNodeClick"
          @context-menu="handleNodeContextMenu"
        />
      </div>
    </div>

    <div v-if="visibleNodes.length === 0" class="empty-state">
      <p>暂无关系图节点。</p>
      <span>可以点击“新建节点”，或从人物、设定、伏笔、时间轴事件创建节点。</span>
    </div>

    <GraphContextMenu
      :visible="contextMenu.visible"
      :kind="contextMenu.kind"
      :x="contextMenu.x"
      :y="contextMenu.y"
      :node="contextMenu.node"
      :edge="contextMenu.edge"
      @create-node="createNodeFromMenu"
      @fit-view="() => { fitView(); closeContextMenu() }"
      @reset-view="() => { resetView(); closeContextMenu() }"
      @edit-node="closeContextMenu"
      @start-edge="startEdgeFromMenu"
      @duplicate-node="() => { if (contextMenu.node) emit('duplicateNode', contextMenu.node); closeContextMenu() }"
      @delete-node="() => { if (contextMenu.node) emit('deleteNode', contextMenu.node); closeContextMenu() }"
      @open-bound="() => { if (contextMenu.node) emit('openBound', contextMenu.node); closeContextMenu() }"
      @edit-edge="closeContextMenu"
      @delete-edge="() => { if (contextMenu.edge) emit('deleteEdge', contextMenu.edge); closeContextMenu() }"
    />
  </section>
</template>

<style scoped>
.graph-canvas {
  position: relative;
  min-height: 680px;
  height: 100%;
  overflow: hidden;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  background-color: #fbfdff;
  cursor: default;
  user-select: none;
}

.graph-canvas.mode-node {
  cursor: crosshair;
}

.graph-canvas.mode-pan,
.graph-canvas.panning {
  cursor: grab;
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

.empty-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  gap: 8px;
  color: #64748b;
  text-align: center;
  pointer-events: none;
}

.empty-state p {
  margin: 0;
  color: #0f172a;
  font-size: 1rem;
  font-weight: 800;
}

.empty-state span {
  font-size: 0.86rem;
}
</style>
