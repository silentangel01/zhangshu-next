<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, onUnmounted, ref, useTemplateRef, watch } from 'vue'

import type { CharacterProfileDimension } from '@/entities/character/types'
import {
  convertDimensionsToScale,
  createEmptyDimension,
  detectScaleMode,
  DIMENSION_SCALE_MODES,
  snapToStep,
  type DimensionScaleMode,
} from '@/features/characters/characterProfileDefaults'

const props = defineProps<{
  modelValue: CharacterProfileDimension[]
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [dimensions: CharacterProfileDimension[]]
}>()

const svgRef = useTemplateRef<SVGSVGElement>('svgEl')
const draggingIndex = ref<number | null>(null)

const SVG_SIZE = 280
const CENTER = SVG_SIZE / 2
const RADIUS = 110
const GRID_LEVELS = 4
const MIN_DIMENSIONS_FOR_CHART = 3

const canDrawChart = computed(() => props.modelValue.length >= MIN_DIMENSIONS_FOR_CHART)

const axisAngles = computed(() => {
  const count = props.modelValue.length
  if (count === 0) return []
  const step = (2 * Math.PI) / count
  return Array.from({ length: count }, (_, i) => -Math.PI / 2 + i * step)
})

// ---------------------------------------------------------------------------
// Scale mode
// ---------------------------------------------------------------------------

const isScaleMenuOpen = ref(false)
const scaleMenuRef = ref<HTMLElement | null>(null)

const activeScale = computed<DimensionScaleMode>(() => detectScaleMode(props.modelValue))

function currentStep(): number {
  return activeScale.value.step
}

function formatValue(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function handleSwitchScale(mode: DimensionScaleMode) {
  if (mode.max === activeScale.value.max) {
    isScaleMenuOpen.value = false
    return
  }
  const converted = convertDimensionsToScale(props.modelValue, mode)
  emit('update:modelValue', converted)
  isScaleMenuOpen.value = false
}

function toggleScaleMenu() {
  isScaleMenuOpen.value = !isScaleMenuOpen.value
}

function handleScaleMenuClickOutside(event: MouseEvent) {
  if (!isScaleMenuOpen.value) return
  const el = scaleMenuRef.value
  if (el && !el.contains(event.target as Node)) {
    isScaleMenuOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleScaleMenuClickOutside, true)
})

onUnmounted(() => {
  document.removeEventListener('click', handleScaleMenuClickOutside, true)
})

// ---------------------------------------------------------------------------
// Chart geometry
// ---------------------------------------------------------------------------

function getVertexPosition(index: number, value: number, max: number): { x: number; y: number } {
  const angle = axisAngles.value[index]
  if (angle === undefined) return { x: CENTER, y: CENTER }
  const ratio = max > 0 ? Math.max(0, Math.min(1, value / max)) : 0
  return {
    x: CENTER + Math.cos(angle) * RADIUS * ratio,
    y: CENTER + Math.sin(angle) * RADIUS * ratio,
  }
}

function getGridPoint(level: number, angleIndex: number): { x: number; y: number } {
  const angle = axisAngles.value[angleIndex]
  if (angle === undefined) return { x: CENTER, y: CENTER }
  const ratio = (level + 1) / GRID_LEVELS
  return {
    x: CENTER + Math.cos(angle) * RADIUS * ratio,
    y: CENTER + Math.sin(angle) * RADIUS * ratio,
  }
}

const dataPolygonPoints = computed(() => {
  if (!canDrawChart.value) return ''
  return props.modelValue
    .map((dim, i) => {
      const pos = getVertexPosition(i, dim.value, dim.max)
      return `${pos.x},${pos.y}`
    })
    .join(' ')
})

function getGridPolygonPoints(level: number): string {
  if (!canDrawChart.value) return ''
  return axisAngles.value
    .map((_, i) => {
      const pos = getGridPoint(level, i)
      return `${pos.x},${pos.y}`
    })
    .join(' ')
}

function getLabelPosition(index: number): { x: number; y: number; anchor: string } {
  const angle = axisAngles.value[index]
  if (angle === undefined) return { x: CENTER, y: CENTER - RADIUS - 16, anchor: 'middle' }
  const labelRadius = RADIUS + 20
  const x = CENTER + Math.cos(angle) * labelRadius
  const y = CENTER + Math.sin(angle) * labelRadius

  let anchor = 'middle'
  if (Math.cos(angle) > 0.1) anchor = 'start'
  else if (Math.cos(angle) < -0.1) anchor = 'end'

  return { x, y, anchor }
}

// ---------------------------------------------------------------------------
// Drag handling
// ---------------------------------------------------------------------------

function onVertexPointerDown(event: PointerEvent, index: number) {
  if (props.disabled) return
  event.preventDefault()
  const target = event.target as SVGElement
  target.setPointerCapture(event.pointerId)
  draggingIndex.value = index
}

function onSvgPointerMove(event: PointerEvent) {
  if (draggingIndex.value === null) return
  const svg = svgRef.value
  if (!svg) return

  const rect = svg.getBoundingClientRect()
  const scaleX = SVG_SIZE / rect.width
  const scaleY = SVG_SIZE / rect.height
  const svgX = (event.clientX - rect.left) * scaleX
  const svgY = (event.clientY - rect.top) * scaleY

  const dx = svgX - CENTER
  const dy = svgY - CENTER
  const distance = Math.sqrt(dx * dx + dy * dy)

  const dim = props.modelValue[draggingIndex.value]
  if (!dim) return

  const ratio = Math.max(0, Math.min(1, distance / RADIUS))
  const rawValue = ratio * dim.max
  const step = currentStep()
  const snapped = snapToStep(rawValue, step)
  const clamped = Math.max(0, Math.min(dim.max, snapped))

  updateDimension(draggingIndex.value, { value: clamped })
}

function onSvgPointerUp() {
  draggingIndex.value = null
}

onBeforeUnmount(() => {
  draggingIndex.value = null
})

watch(draggingIndex, (val) => {
  document.body.style.userSelect = val !== null ? 'none' : ''
})

// ---------------------------------------------------------------------------
// Dimension CRUD
// ---------------------------------------------------------------------------

function updateDimension(index: number, patch: Partial<CharacterProfileDimension>) {
  const step = currentStep()
  const dim = props.modelValue[index]
  if (!dim) return

  const patched = { ...patch }
  if (patched.value !== undefined) {
    patched.value = snapToStep(patched.value, step)
    patched.value = Math.max(0, Math.min(dim.max, patched.value))
  }

  const next = props.modelValue.map((d, i) => (i === index ? { ...d, ...patched } : d))
  emit('update:modelValue', next)
}

function addDimension() {
  if (props.modelValue.length >= 12) return
  const next = [
    ...props.modelValue,
    createEmptyDimension(props.modelValue.length, activeScale.value.max),
  ]
  emit('update:modelValue', next)
}

function removeDimension(index: number) {
  if (props.disabled) return
  const next = props.modelValue.filter((_, i) => i !== index).map((d, i) => ({ ...d, order: i }))
  emit('update:modelValue', next)
}

function handleSliderInput(index: number, event: Event) {
  const raw = Number((event.target as HTMLInputElement).value)
  updateDimension(index, { value: raw })
}

function handleNumberInput(index: number, event: Event) {
  const dim = props.modelValue[index]
  if (!dim) return
  const raw = Number((event.target as HTMLInputElement).value)
  const clamped = Math.max(0, Math.min(dim.max, raw))
  updateDimension(index, { value: clamped })
}
</script>

<template>
  <section class="dimension-radar" aria-label="多维度图">
    <header class="section-header">
      <h4 class="section-title">多维度图</h4>
      <div class="section-actions">
        <div ref="scaleMenuRef" class="scale-menu-wrapper">
          <button
            type="button"
            class="scale-button"
            :disabled="disabled"
            @click.stop="toggleScaleMenu"
          >
            {{ activeScale.label }} ▾
          </button>
          <div v-if="isScaleMenuOpen" class="scale-menu">
            <button
              v-for="mode in DIMENSION_SCALE_MODES"
              :key="mode.key"
              type="button"
              class="scale-menu-item"
              :class="{ active: mode.max === activeScale.max }"
              @click="handleSwitchScale(mode)"
            >
              {{ mode.label }}
              <span class="scale-hint">（步进 {{ mode.step }}）</span>
            </button>
          </div>
        </div>
        <button
          type="button"
          class="add-button"
          :disabled="disabled || modelValue.length >= 12"
          @click="addDimension"
        >
          + 新增维度
        </button>
      </div>
    </header>

    <p v-if="modelValue.length === 0" class="empty-hint">
      暂无维度数据，点击上方按钮新增。至少需要 3 个维度才能生成图形。
    </p>

    <div v-else class="radar-layout">
      <div class="chart-area">
        <svg
          ref="svgEl"
          :viewBox="`0 0 ${SVG_SIZE} ${SVG_SIZE}`"
          class="radar-svg"
          @pointermove="onSvgPointerMove"
          @pointerup="onSvgPointerUp"
          @pointercancel="onSvgPointerUp"
        >
          <!-- Grid polygons -->
          <template v-if="canDrawChart">
            <polygon
              v-for="level in GRID_LEVELS"
              :key="`grid-${level}`"
              :points="getGridPolygonPoints(level - 1)"
              class="grid-polygon"
            />
          </template>

          <!-- Axis lines -->
          <template v-if="canDrawChart">
            <line
              v-for="(angle, i) in axisAngles"
              :key="`axis-${i}`"
              :x1="CENTER"
              :y1="CENTER"
              :x2="CENTER + Math.cos(angle) * RADIUS"
              :y2="CENTER + Math.sin(angle) * RADIUS"
              class="axis-line"
            />
          </template>

          <!-- Data polygon -->
          <polygon
            v-if="canDrawChart && dataPolygonPoints"
            :points="dataPolygonPoints"
            class="data-polygon"
          />

          <!-- Data vertices (draggable) -->
          <template v-if="canDrawChart">
            <circle
              v-for="(dim, i) in modelValue"
              :key="`vertex-${dim.id}`"
              :cx="getVertexPosition(i, dim.value, dim.max).x"
              :cy="getVertexPosition(i, dim.value, dim.max).y"
              r="7"
              :class="['data-vertex', { dragging: draggingIndex === i }]"
              @pointerdown="onVertexPointerDown($event, i)"
            />
          </template>

          <!-- Dimension labels -->
          <template v-if="canDrawChart">
            <text
              v-for="(dim, i) in modelValue"
              :key="`label-${dim.id}`"
              :x="getLabelPosition(i).x"
              :y="getLabelPosition(i).y"
              :text-anchor="getLabelPosition(i).anchor"
              dominant-baseline="central"
              class="dim-label"
            >{{ dim.name }}</text>
          </template>

          <!-- Placeholder when not enough dimensions -->
          <text
            v-if="!canDrawChart"
            :x="CENTER"
            :y="CENTER"
            text-anchor="middle"
            dominant-baseline="central"
            class="placeholder-text"
          >至少需要 3 个维度</text>
        </svg>
      </div>

      <div class="dimension-list">
        <div
          v-for="(dim, index) in modelValue"
          :key="dim.id"
          class="dim-row"
        >
          <input
            type="text"
            class="dim-name-input"
            :value="dim.name"
            :disabled="disabled"
            maxlength="24"
            placeholder="维度名"
            @input="updateDimension(index, { name: ($event.target as HTMLInputElement).value })"
          >
          <input
            type="range"
            class="dim-slider"
            :value="dim.value"
            :min="0"
            :max="dim.max"
            :step="currentStep()"
            :disabled="disabled"
            @input="handleSliderInput(index, $event)"
          >
          <input
            type="number"
            class="dim-value-input"
            :value="dim.value"
            :min="0"
            :max="dim.max"
            :step="currentStep()"
            :disabled="disabled"
            @input="handleNumberInput(index, $event)"
          >
          <span class="dim-max-label">/{{ formatValue(dim.max) }}</span>
          <button
            type="button"
            class="dim-remove"
            :disabled="disabled"
            title="删除维度"
            @click="removeDimension(index)"
          >✕</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.dimension-radar {
  display: grid;
  gap: var(--zs-space-2);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-2);
}

.section-title {
  margin: 0;
  color: var(--zs-color-text-faint);
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: var(--zs-space-3);
}

.scale-menu-wrapper {
  position: relative;
}

.scale-button {
  min-height: 26px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 var(--zs-space-2);
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  font: inherit;
  font-size: 0.74rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.scale-button:hover:not(:disabled) {
  border-color: var(--zs-color-primary);
  color: var(--zs-color-primary);
}

.scale-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.scale-menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  z-index: 20;
  min-width: 160px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 4px;
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-md);
}

.scale-menu-item {
  display: flex;
  align-items: center;
  gap: var(--zs-space-1);
  width: 100%;
  min-height: 30px;
  border: none;
  border-radius: var(--zs-radius-sm);
  padding: 0 var(--zs-space-2);
  background: transparent;
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}

.scale-menu-item:hover {
  background: var(--zs-color-bg);
}

.scale-menu-item.active {
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-primary);
}

.scale-hint {
  color: var(--zs-color-text-muted);
  font-size: 0.74rem;
  font-weight: 400;
}

.add-button {
  min-height: 26px;
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 var(--zs-space-2);
  background: transparent;
  color: var(--zs-color-text-muted);
  font: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}

.add-button:hover:not(:disabled) {
  border-color: var(--zs-color-primary);
  color: var(--zs-color-primary);
}

.add-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-hint {
  margin: 0;
  padding: var(--zs-space-3);
  border: 1px dashed var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  text-align: center;
}

.radar-layout {
  display: flex;
  gap: var(--zs-space-3);
  align-items: flex-start;
  flex-wrap: wrap;
}

.chart-area {
  flex-shrink: 0;
  width: 280px;
}

.radar-svg {
  width: 100%;
  height: auto;
  touch-action: none;
}

.grid-polygon {
  fill: none;
  stroke: var(--zs-color-border-soft);
  stroke-width: 1;
}

.axis-line {
  stroke: var(--zs-color-border-soft);
  stroke-width: 1;
}

.data-polygon {
  fill: var(--zs-color-primary);
  fill-opacity: 0.15;
  stroke: var(--zs-color-primary);
  stroke-width: 2;
}

.data-vertex {
  fill: var(--zs-color-primary);
  stroke: var(--zs-color-surface);
  stroke-width: 2;
  cursor: grab;
  transition: r 0.1s;
}

.data-vertex:hover {
  r: 9;
}

.data-vertex.dragging {
  r: 10;
  cursor: grabbing;
  fill-opacity: 0.8;
}

.dim-label {
  fill: var(--zs-color-text-muted);
  font-size: 11px;
  font-weight: 600;
}

.placeholder-text {
  fill: var(--zs-color-text-muted);
  font-size: 12px;
}

.dimension-list {
  display: grid;
  gap: 6px;
  flex: 0 1 380px;
  max-width: 420px;
  width: min(100%, 380px);
  min-width: 180px;
}

.dim-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface);
}

.dim-name-input {
  width: 72px;
  min-width: 0;
  border: none;
  border-bottom: 1px solid transparent;
  padding: 2px 0;
  background: transparent;
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 600;
}

.dim-name-input:focus {
  border-bottom-color: var(--zs-color-primary);
  outline: none;
}

.dim-slider {
  flex: 0 0 128px;
  width: 128px;
  min-width: 96px;
  height: 4px;
  accent-color: var(--zs-color-primary);
  cursor: pointer;
}

.dim-value-input {
  width: 42px;
  min-width: 0;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  padding: 2px 4px;
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.78rem;
  text-align: center;
  -moz-appearance: textfield;
}

.dim-value-input::-webkit-outer-spin-button,
.dim-value-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.dim-value-input:focus {
  border-color: var(--zs-color-primary);
  outline: none;
}

.dim-max-label {
  color: var(--zs-color-text-muted);
  font-size: 0.72rem;
  white-space: nowrap;
}

.dim-remove {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  border: none;
  border-radius: var(--zs-radius-sm);
  padding: 0;
  background: transparent;
  color: var(--zs-color-text-muted);
  font-size: 0.72rem;
  cursor: pointer;
}

.dim-remove:hover:not(:disabled) {
  color: var(--zs-color-danger);
}

.dim-remove:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
</style>
