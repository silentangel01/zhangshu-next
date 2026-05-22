<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { listChapters } from '@/entities/chapter/api'
import type { Chapter } from '@/entities/chapter/types'
import { getProject } from '@/entities/project/api'
import type { Project } from '@/entities/project/types'
import MaterialLinkPanel from '@/features/material-links/MaterialLinkPanel.vue'
import { listProjectSettings } from '@/entities/setting/api'
import type { SettingItem } from '@/entities/setting/types'
import {
  createTimelineEdge,
  createTimelineEvent,
  createTimelineTrack,
  deleteTimelineEdge,
  deleteTimelineEvent,
  deleteTimelineTrack,
  listProjectTimelineEvents,
  listTimelineEdges,
  listTimelineTracks,
  updateTimelineEdge,
  updateTimelineEvent,
  updateTimelineTrack,
} from '@/entities/timeline/api'
import type {
  TimelineEdge,
  TimelineEdgeCreatePayload,
  TimelineEdgeLineStyle,
  TimelineEdgeTemporalRelation,
  TimelineEdgeType,
  TimelineEdgeUpdatePayload,
  TimelineEdgeVisibility,
  TimelineEvent,
  TimelineEventCreatePayload,
  TimelineEventImportance,
  TimelineEventStatus,
  TimelineEventType,
  TimelineTrack,
  TimelineTrackCreatePayload,
  TimelineTrackType,
  TimelineTrackUpdatePayload,
} from '@/entities/timeline/types'
import {
  timelineEdgeLineStyleLabels,
  timelineEdgeTemporalRelationLabels,
  timelineEdgeTypeLabels,
  timelineEdgeVisibilityLabels,
  timelineEventImportanceLabels,
  timelineEventStatusLabels,
  timelineEventTypeLabels,
  timelineTrackTypeLabels,
} from '@/entities/timeline/types'
import ContextMenu, { type ContextMenuItem } from '@/shared/ui/ContextMenu.vue'

const route = useRoute()

type PanelKind = 'none' | 'track' | 'event' | 'edge'
type PanelMode = 'view' | 'create' | 'edit'

type TrackRow = {
  id: string
  title: string
  description: string
  track: TimelineTrack | null
  events: TimelineEvent[]
  isVirtual: boolean
}

type RenderedEdge = {
  id: string
  edge: TimelineEdge
  path: string
  labelX: number
  labelY: number
  dashed: boolean
  hasArrow: boolean
  curved: boolean
}

const project = ref<Project | null>(null)
const chapters = ref<Chapter[]>([])
const settings = ref<SettingItem[]>([])
const tracks = ref<TimelineTrack[]>([])
const events = ref<TimelineEvent[]>([])
const edges = ref<TimelineEdge[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const cleanMode = ref(false)

const panelKind = ref<PanelKind>('none')
const panelMode = ref<PanelMode>('view')
const selectedTrackId = ref<string | null>(null)
const selectedEventId = ref<string | null>(null)
const selectedEdgeId = ref<string | null>(null)

const trackForm = reactive({
  title: '',
  description: '',
  track_type: 'custom' as TimelineTrackType,
  bound_type: '',
  bound_id: '',
  order_index: 0,
  color: '',
  is_main: false,
})

const eventForm = reactive({
  title: '',
  description: '',
  track_id: '',
  event_type: 'plot' as TimelineEventType,
  story_date: '',
  story_time: '',
  chapter_id: '',
  location_setting_id: '',
  order_index: 0,
  position_index: 0,
  importance: 'normal' as TimelineEventImportance,
  status: 'planned' as TimelineEventStatus,
  note: '',
})

const edgeForm = reactive({
  from_event_id: '',
  to_event_id: '',
  edge_type: 'related' as TimelineEdgeType,
  temporal_relation: 'unordered' as TimelineEdgeTemporalRelation,
  line_style: 'straight' as TimelineEdgeLineStyle,
  label: '',
  note: '',
  visibility: 'normal' as TimelineEdgeVisibility,
})

const trackMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  trackId: '',
})

const eventTypes: TimelineEventType[] = ['plot', 'background', 'character', 'world', 'clue', 'conflict', 'custom']
const eventImportances: TimelineEventImportance[] = ['low', 'normal', 'high', 'critical']
const eventStatuses: TimelineEventStatus[] = ['planned', 'happened', 'revised', 'deprecated']
const trackTypes: TimelineTrackType[] = ['main', 'character', 'organization', 'setting', 'clue', 'volume', 'custom']
const edgeTypes: TimelineEdgeType[] = ['cause', 'parallel', 'clue_payoff', 'conflict', 'echo', 'related', 'custom']
const temporalRelations: TimelineEdgeTemporalRelation[] = ['previous', 'parallel', 'delayed', 'future', 'unordered']
const lineStyles: TimelineEdgeLineStyle[] = ['straight', 'arc', 'dashed', 'arrow']
const visibilities: TimelineEdgeVisibility[] = ['normal', 'subtle', 'hidden']
const hiddenTrackIds = ref<string[]>([])
const progressMessage = ref('')
const DRAG_START_THRESHOLD_PX = 4
const dragState = reactive({
  active: false,
  eventId: '',
  trackId: '',
  pointerId: -1,
  startX: 0,
  startY: 0,
  startRatio: 0,
  currentRatio: 0,
  dragging: false,
  suppressClick: false,
})

const projectId = computed<string>(() => {
  const value = route.params.projectId
  return (Array.isArray(value) ? value[0] : value) ?? ''
})

const trackMap = computed(() =>
  tracks.value.reduce<Record<string, TimelineTrack>>((acc, track) => {
    acc[track.id] = track
    return acc
  }, {}),
)

const chapterMap = computed(() =>
  chapters.value.reduce<Record<string, Chapter>>((acc, chapter) => {
    acc[chapter.id] = chapter
    return acc
  }, {}),
)

const settingMap = computed(() =>
  settings.value.reduce<Record<string, SettingItem>>((acc, setting) => {
    acc[setting.id] = setting
    return acc
  }, {}),
)

const eventMap = computed(() =>
  events.value.reduce<Record<string, TimelineEvent>>((acc, event) => {
    acc[event.id] = event
    return acc
  }, {}),
)

const mainTrack = computed(() => tracks.value.find((track) => track.is_main) ?? tracks.value[0] ?? null)

const orderedTracks = computed(() =>
  [...tracks.value].sort((left, right) => {
    if (left.is_main !== right.is_main) {
      return left.is_main ? -1 : 1
    }
    return (
      left.order_index - right.order_index ||
      left.created_at.localeCompare(right.created_at, 'zh-Hans-CN')
    )
  }),
)

const visibleTracks = computed(() => orderedTracks.value.filter((track) => !isTrackHidden(track.id)))

const groupedEvents = computed(() => {
  const groups = new Map<string, TimelineEvent[]>()
  for (const track of orderedTracks.value) {
    groups.set(track.id, [])
  }

  for (const event of events.value) {
    if (!event.track_id) {
      continue
    }
    if (!groups.has(event.track_id)) {
      groups.set(event.track_id, [])
    }
    groups.get(event.track_id)!.push(event)
  }

  for (const list of groups.values()) {
    list.sort(sortEvents)
  }

  return groups
})

const unassignedEvents = computed(() =>
  events.value
    .filter((event) => !event.track_id || !trackMap.value[event.track_id])
    .slice()
    .sort(sortEvents),
)

const rows = computed<TrackRow[]>(() => {
  const actualRows: TrackRow[] = visibleTracks.value.map((track) => ({
    id: track.id,
    title: track.title,
    description: track.description,
    track,
    events: groupedEvents.value.get(track.id) ?? [],
    isVirtual: false,
  }))

  if (unassignedEvents.value.length > 0) {
    actualRows.push({
      id: '__unassigned__',
      title: '未分配时间轴',
      description: '用于暂时没有 track_id 的事件',
      track: null,
      events: unassignedEvents.value,
      isVirtual: true,
    })
  }

  return actualRows
})

const visibleEdges = computed(() =>
  edges.value.filter((edge) => {
    const fromEvent = eventMap.value[edge.from_event_id]
    const toEvent = eventMap.value[edge.to_event_id]
    if (!fromEvent || !toEvent) {
      return false
    }
    if (edge.visibility === 'hidden') {
      return false
    }
    if (cleanMode.value && edge.visibility === 'subtle') {
      return false
    }
    if (isTrackHidden(fromEvent.track_id) || isTrackHidden(toEvent.track_id)) {
      return false
    }
    return true
  }),
)

const invalidEdgeCount = computed(() =>
  edges.value.filter((edge) => !eventMap.value[edge.from_event_id] || !eventMap.value[edge.to_event_id]).length,
)

const selectedTrack = computed(() => {
  if (!selectedTrackId.value) {
    return null
  }
  return trackMap.value[selectedTrackId.value] ?? null
})

const selectedEvent = computed(() => {
  if (!selectedEventId.value) {
    return null
  }
  return eventMap.value[selectedEventId.value] ?? null
})

const selectedEdge = computed(() => {
  if (!selectedEdgeId.value) {
    return null
  }
  return edges.value.find((edge) => edge.id === selectedEdgeId.value) ?? null
})

const trackOptions = computed(() =>
  orderedTracks.value.map((track) => ({
    id: track.id,
    label: track.title,
  })),
)

const eventOptions = computed(() =>
  events.value
    .slice()
    .sort(sortEvents)
    .map((event) => {
      const track = event.track_id ? trackMap.value[event.track_id] : null
      const suffix = track ? `（${track.title}）` : ''
      return {
        id: event.id,
        label: `${event.title}${suffix}`,
      }
    }),
)

const chapterOptions = computed(() =>
  chapters.value
    .slice()
    .sort((left, right) => left.order_index - right.order_index || left.title.localeCompare(right.title, 'zh-Hans-CN'))
    .map((chapter) => ({
      id: chapter.id,
      label: chapter.title,
    })),
)

const settingOptions = computed(() =>
  settings.value
    .slice()
    .sort((left, right) => {
      const leftPriority = left.item_type === 'location' ? 0 : 1
      const rightPriority = right.item_type === 'location' ? 0 : 1
      return leftPriority - rightPriority || left.title.localeCompare(right.title, 'zh-Hans-CN')
    })
    .map((setting) => ({
      id: setting.id,
      label: `${setting.title}（${setting.item_type}）`,
    })),
)

const defaultEventTrackId = computed(() => {
  if (selectedTrackId.value && trackMap.value[selectedTrackId.value]) {
    return selectedTrackId.value
  }
  return mainTrack.value?.id || ''
})

const hasDetailSelection = computed(() => panelKind.value !== 'none')

const edgePoints = ref<RenderedEdge[]>([])
const canvasWidth = ref(0)
const canvasHeight = ref(0)
const canvasViewportRef = ref<HTMLElement | null>(null)
const canvasBodyRef = ref<HTMLElement | null>(null)
const trackLaneRefs = ref<Record<string, HTMLElement | null>>({})
const eventNodeRefs = ref<Record<string, HTMLElement | null>>({})
let edgeMeasureFrameId: number | null = null
let timelineResizeObserver: ResizeObserver | null = null

onMounted(() => {
  void loadWorkspace()
  window.addEventListener('resize', scheduleMeasureEdges)
  void nextTick(() => {
    setupTimelineResizeObserver()
    requestMeasureEdges()
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', scheduleMeasureEdges)
  timelineResizeObserver?.disconnect()
  timelineResizeObserver = null
  if (edgeMeasureFrameId !== null) {
    window.cancelAnimationFrame(edgeMeasureFrameId)
    edgeMeasureFrameId = null
  }
})

watch(projectId, () => {
  resetSelection()
  void loadWorkspace()
})

watch(
  () => [orderedTracks.value.length, events.value.length, edges.value.length, cleanMode.value],
  () => {
    void scheduleMeasureEdges()
  },
  { deep: true },
)

watch(
  () => [panelKind.value, panelMode.value, selectedTrackId.value, selectedEventId.value, selectedEdgeId.value, hasDetailSelection.value],
  () => {
    requestMeasureEdges()
  },
)

watch(
  () => rows.value.map((row) => `${row.id}:${row.events.length}`).join('|'),
  () => {
    requestMeasureEdges()
  },
)

async function loadWorkspace() {
  if (!projectId.value) {
    errorMessage.value = '项目 ID 缺失。'
    return
  }

  isLoading.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const [projectDetail, projectChapters, projectSettings, projectTracks, projectEvents, projectEdges] =
      await Promise.all([
        getProject(projectId.value),
        listChapters(projectId.value),
        listProjectSettings(projectId.value),
        listTimelineTracks(projectId.value),
        listProjectTimelineEvents(projectId.value),
        listTimelineEdges(projectId.value),
      ])

    project.value = projectDetail
    chapters.value = projectChapters
    settings.value = projectSettings
    tracks.value = projectTracks
    events.value = projectEvents
    edges.value = projectEdges

    syncSelectionAfterLoad()
    await scheduleMeasureEdges()
  } catch (error) {
    errorMessage.value = formatErrorMessage(error, '加载时间轴失败。')
  } finally {
    isLoading.value = false
  }
}

async function refreshWorkspace() {
  await loadWorkspace()
}

function syncSelectionAfterLoad() {
  if (panelKind.value === 'track') {
    if (panelMode.value === 'edit' && selectedTrackId.value) {
      const track = trackMap.value[selectedTrackId.value]
      if (track) {
        applyTrackToForm(track)
      } else {
        resetSelection()
      }
    }
    return
  }

  if (panelKind.value === 'event') {
    if (panelMode.value === 'edit' && selectedEventId.value) {
      const event = eventMap.value[selectedEventId.value]
      if (event) {
        applyEventToForm(event)
      } else {
        resetSelection()
      }
    }
    return
  }

  if (panelKind.value === 'edge') {
    if (panelMode.value === 'edit' && selectedEdgeId.value) {
      const edge = edges.value.find((item) => item.id === selectedEdgeId.value)
      if (edge) {
        applyEdgeToForm(edge)
      } else {
        resetSelection()
      }
    }
    return
  }
}

function resetSelection() {
  panelKind.value = 'none'
  panelMode.value = 'view'
  selectedTrackId.value = null
  selectedEventId.value = null
  selectedEdgeId.value = null
}

function openCreateTrack() {
  panelKind.value = 'track'
  panelMode.value = 'create'
  selectedTrackId.value = null
  selectedEventId.value = null
  selectedEdgeId.value = null
  resetTrackForm()
}

function openCreateEvent() {
  panelKind.value = 'event'
  panelMode.value = 'create'
  selectedTrackId.value = defaultEventTrackId.value || null
  selectedEventId.value = null
  selectedEdgeId.value = null
  resetEventForm()
  eventForm.track_id = defaultEventTrackId.value
  eventForm.order_index = nextOrderIndexForTrack(defaultEventTrackId.value)
  eventForm.position_index = eventForm.order_index
}

function openCreateEdge() {
  panelKind.value = 'edge'
  panelMode.value = 'create'
  selectedEventId.value = null
  selectedEdgeId.value = null
  resetEdgeForm()
  if (selectedEvent.value) {
    edgeForm.from_event_id = selectedEvent.value.id
  }
}

function selectTrack(track: TimelineTrack) {
  panelKind.value = 'track'
  panelMode.value = 'edit'
  selectedTrackId.value = track.id
  selectedEventId.value = null
  selectedEdgeId.value = null
  applyTrackToForm(track)
}

function selectEvent(event: TimelineEvent) {
  panelKind.value = 'event'
  panelMode.value = 'edit'
  selectedTrackId.value = event.track_id ?? null
  selectedEventId.value = event.id
  selectedEdgeId.value = null
  applyEventToForm(event)
}

function selectEdge(edge: TimelineEdge) {
  panelKind.value = 'edge'
  panelMode.value = 'edit'
  selectedTrackId.value = eventMap.value[edge.from_event_id]?.track_id ?? selectedTrackId.value
  selectedEventId.value = null
  selectedEdgeId.value = edge.id
  applyEdgeToForm(edge)
}

function openTrackMenu(track: TimelineTrack, event: MouseEvent) {
  event.preventDefault()
  event.stopPropagation()
  trackMenu.visible = true
  trackMenu.x = event.clientX
  trackMenu.y = event.clientY
  trackMenu.trackId = track.id
}

function closeTrackMenu() {
  trackMenu.visible = false
}

function handleTrackMenuSelect(item: ContextMenuItem) {
  const track = trackMap.value[trackMenu.trackId]
  if (!track) {
    return
  }

  if (item.id === 'edit') {
    selectTrack(track)
  }

  if (item.id === 'delete') {
    void handleDeleteTrack(track)
  }
}

function applyTrackToForm(track: TimelineTrack) {
  trackForm.title = track.title
  trackForm.description = track.description
  trackForm.track_type = track.track_type
  trackForm.bound_type = track.bound_type ?? ''
  trackForm.bound_id = track.bound_id ?? ''
  trackForm.order_index = track.order_index
  trackForm.color = track.color ?? ''
  trackForm.is_main = track.is_main
}

function resetTrackForm() {
  trackForm.title = ''
  trackForm.description = ''
  trackForm.track_type = 'custom'
  trackForm.bound_type = ''
  trackForm.bound_id = ''
  trackForm.order_index = orderedTracks.value.length
  trackForm.color = ''
  trackForm.is_main = false
}

function applyEventToForm(event: TimelineEvent) {
  eventForm.title = event.title
  eventForm.description = event.description
  eventForm.track_id = event.track_id ?? defaultEventTrackId.value
  eventForm.event_type = event.event_type
  eventForm.story_date = event.story_date ?? ''
  eventForm.story_time = event.story_time ?? ''
  eventForm.chapter_id = event.chapter_id ?? ''
  eventForm.location_setting_id = event.location_setting_id ?? ''
  eventForm.order_index = event.order_index
  eventForm.position_index = event.position_index
  eventForm.importance = event.importance
  eventForm.status = event.status
  eventForm.note = event.note
}

function resetEventForm() {
  eventForm.title = ''
  eventForm.description = ''
  eventForm.track_id = defaultEventTrackId.value
  eventForm.event_type = 'plot'
  eventForm.story_date = ''
  eventForm.story_time = ''
  eventForm.chapter_id = ''
  eventForm.location_setting_id = ''
  eventForm.order_index = nextOrderIndexForTrack(defaultEventTrackId.value)
  eventForm.position_index = eventForm.order_index
  eventForm.importance = 'normal'
  eventForm.status = 'planned'
  eventForm.note = ''
}

function applyEdgeToForm(edge: TimelineEdge) {
  edgeForm.from_event_id = edge.from_event_id
  edgeForm.to_event_id = edge.to_event_id
  edgeForm.edge_type = edge.edge_type
  edgeForm.temporal_relation = edge.temporal_relation as TimelineEdgeTemporalRelation
  edgeForm.line_style = edge.line_style
  edgeForm.label = edge.label
  edgeForm.note = edge.note
  edgeForm.visibility = edge.visibility
}

function resetEdgeForm() {
  edgeForm.from_event_id = selectedEvent.value?.id ?? ''
  edgeForm.to_event_id = ''
  edgeForm.edge_type = 'related'
  edgeForm.temporal_relation = 'unordered'
  edgeForm.line_style = 'straight'
  edgeForm.label = ''
  edgeForm.note = ''
  edgeForm.visibility = 'normal'
}

function nextOrderIndexForTrack(trackId: string) {
  return getTrackEvents(trackId).length
}

function getTrackEvents(trackId: string) {
  return groupedEvents.value.get(trackId) ?? []
}

function getTrackEventCount(trackId: string) {
  return getTrackEvents(trackId).length
}

function getTrackLabel(track: TimelineTrack) {
  return timelineTrackTypeLabels[track.track_type]
}

function getEventSubtitle(event: TimelineEvent) {
  const timeParts = [event.story_date, event.story_time].filter(Boolean)
  if (timeParts.length > 0) {
    return timeParts.join(' · ')
  }

  const chapterTitle = event.chapter?.title ?? (event.chapter_id ? chapterMap.value[event.chapter_id]?.title : '')
  if (chapterTitle) {
    return chapterTitle
  }

  const settingTitle = event.location_setting?.title ?? (event.location_setting_id ? settingMap.value[event.location_setting_id]?.title : '')
  if (settingTitle) {
    return settingTitle
  }

  return '未填写时间'
}

function getEventTrackTitle(event: TimelineEvent) {
  if (event.track_id && trackMap.value[event.track_id]) {
    return trackMap.value[event.track_id]?.title ?? '未分配时间轴'
  }
  return '未分配时间轴'
}

function getTrackSummary(track: TimelineTrack) {
  if (!track.description) {
    return timelineTrackTypeLabels[track.track_type]
  }
  return track.description
}

function getEventDetailChapter(event: TimelineEvent) {
  if (event.chapter?.title) {
    return event.chapter.title
  }
  if (!event.chapter_id) {
    return '未绑定'
  }
  return chapterMap.value[event.chapter_id]?.title ?? '未知章节'
}

function getEventDetailSetting(event: TimelineEvent) {
  if (event.location_setting?.title) {
    return event.location_setting.title
  }
  if (!event.location_setting_id) {
    return '未绑定'
  }
  return settingMap.value[event.location_setting_id]?.title ?? '未知设定'
}

function getTrackNameById(trackId: string | null) {
  if (!trackId) {
    return '自动使用主时间轴'
  }
  return trackMap.value[trackId]?.title ?? '未知时间轴'
}

function getEventNameById(eventId: string) {
  return eventMap.value[eventId]?.title ?? '未知节点'
}

function getEdgeLabel(edge: TimelineEdge) {
  return edge.label || timelineEdgeTypeLabels[edge.edge_type]
}

function buildEdgeDescription(edge: TimelineEdge) {
  const fromTitle = getEventNameById(edge.from_event_id)
  const toTitle = getEventNameById(edge.to_event_id)
  return `${fromTitle} → ${toTitle}`
}

function shouldShowEdgeTemporalRelation(edge: TimelineEdge) {
  return !cleanMode.value || selectedEdgeId.value === edge.id
}

function buildEdgeSummary(edge: TimelineEdge) {
  const label = getEdgeLabel(edge)
  const temporalRelation = shouldShowEdgeTemporalRelation(edge)
    ? timelineEdgeTemporalRelationLabels[edge.temporal_relation]
    : ''
  const style = timelineEdgeLineStyleLabels[edge.line_style]
  const visibility = timelineEdgeVisibilityLabels[edge.visibility]
  return temporalRelation ? `${label} · ${temporalRelation} · ${style} · ${visibility}` : `${label} · ${style} · ${visibility}`
}

function selectTrackMenuButton(track: TimelineTrack, event: MouseEvent) {
  openTrackMenu(track, event)
}

async function handleSaveTrack() {
  if (!projectId.value) {
    return
  }

  await runSave(async () => {
    const payload: TimelineTrackCreatePayload = {
      title: trackForm.title,
      description: trackForm.description,
      track_type: trackForm.track_type,
      bound_type: trackForm.bound_type || null,
      bound_id: trackForm.bound_id || null,
      order_index: Number(trackForm.order_index) || 0,
      color: trackForm.color || null,
      is_main: trackForm.is_main,
    }

    const saved =
      panelMode.value === 'create' || !selectedTrackId.value
        ? await createTimelineTrack(projectId.value, payload)
        : await updateTimelineTrack(selectedTrackId.value, payload as TimelineTrackUpdatePayload)

    selectedTrackId.value = saved.id
    panelKind.value = 'track'
    panelMode.value = 'edit'
    await loadWorkspace()
    selectedTrackId.value = saved.id
    successMessage.value = '时间轴已保存。'
  }, '保存时间轴失败。')
}

async function handleDeleteTrack(track: TimelineTrack) {
  const confirmed = window.confirm(`确认删除该时间轴“${track.title}”吗？`)
  if (!confirmed) {
    return
  }

  await runSave(async () => {
    await deleteTimelineTrack(track.id)
    if (selectedTrackId.value === track.id) {
      resetSelection()
    }
    await loadWorkspace()
    successMessage.value = '时间轴已删除。'
  }, '删除时间轴失败。')
}

async function handleSaveEvent() {
  if (!projectId.value) {
    return
  }

  await runSave(async () => {
    const payload: TimelineEventCreatePayload = {
      title: eventForm.title,
      description: eventForm.description,
      track_id: eventForm.track_id || null,
      event_type: eventForm.event_type,
      story_date: eventForm.story_date || null,
      story_time: eventForm.story_time || null,
      chapter_id: eventForm.chapter_id || null,
      location_setting_id: eventForm.location_setting_id || null,
      order_index: Number(eventForm.order_index) || 0,
      position_index: Number(eventForm.position_index) || 0,
      importance: eventForm.importance,
      status: eventForm.status,
      note: eventForm.note,
    }

    const saved =
      panelMode.value === 'create' || !selectedEventId.value
        ? await createTimelineEvent(projectId.value, payload)
        : await updateTimelineEvent(selectedEventId.value, payload)

    selectedEventId.value = saved.id
    selectedTrackId.value = saved.track_id
    panelKind.value = 'event'
    panelMode.value = 'edit'
    await loadWorkspace()
    selectedEventId.value = saved.id
    selectedTrackId.value = saved.track_id
    successMessage.value = '时间轴节点已保存。'
  }, '保存时间轴节点失败。')
}

async function handleDeleteEvent() {
  if (!selectedEvent.value) {
    return
  }

  const confirmed = window.confirm(`确认删除时间轴节点“${selectedEvent.value.title}”吗？`)
  if (!confirmed) {
    return
  }

  const deletedTrackId = selectedEvent.value.track_id
  await runSave(async () => {
    await deleteTimelineEvent(selectedEvent.value!.id)
    selectedEventId.value = null
    selectedEdgeId.value = null
    panelKind.value = 'none'
    panelMode.value = 'view'
    if (deletedTrackId && selectedTrackId.value !== deletedTrackId) {
      selectedTrackId.value = deletedTrackId
    }
    await loadWorkspace()
    successMessage.value = '时间轴节点已删除。'
  }, '删除时间轴节点失败。')
}

async function handleSaveEdge() {
  if (!projectId.value) {
    return
  }

  await runSave(async () => {
    const payload: TimelineEdgeCreatePayload = {
      from_event_id: edgeForm.from_event_id,
      to_event_id: edgeForm.to_event_id,
      edge_type: edgeForm.edge_type,
      temporal_relation: edgeForm.temporal_relation,
      line_style: edgeForm.line_style,
      label: edgeForm.label,
      note: edgeForm.note,
      visibility: edgeForm.visibility,
    }

    const saved =
      panelMode.value === 'create' || !selectedEdgeId.value
        ? await createTimelineEdge(projectId.value, payload)
        : await updateTimelineEdge(selectedEdgeId.value, payload as TimelineEdgeUpdatePayload)

    selectedEdgeId.value = saved.id
    panelKind.value = 'edge'
    panelMode.value = 'edit'
    await loadWorkspace()
    selectedEdgeId.value = saved.id
    successMessage.value = '时间轴连接已保存。'
  }, '保存时间轴连接失败。')
}

async function handleDeleteEdge() {
  if (!selectedEdge.value) {
    return
  }

  const confirmed = window.confirm(`确认删除时间轴连接“${buildEdgeDescription(selectedEdge.value)}”吗？`)
  if (!confirmed) {
    return
  }

  await runSave(async () => {
    await deleteTimelineEdge(selectedEdge.value!.id)
    selectedEdgeId.value = null
    panelKind.value = 'none'
    panelMode.value = 'view'
    await loadWorkspace()
    successMessage.value = '时间轴连接已删除。'
  }, '删除时间轴连接失败。')
}

async function runSave(action: () => Promise<void>, fallback: string) {
  isSaving.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    await action()
  } catch (error) {
    errorMessage.value = formatErrorMessage(error, fallback)
  } finally {
    isSaving.value = false
  }
}

function formatErrorMessage(error: unknown, fallback: string) {
  const message = error instanceof Error ? error.message : ''
  if (!message) {
    return fallback
  }

  const normalized = message.trim()
  const mapped: Record<string, string> = {
    'Project not found': '项目不存在。',
    'Track not found': '时间轴不存在。',
    'Track does not belong to project': '时间轴不属于当前项目。',
    'Cannot remove the only main timeline track': '不能移除唯一的主时间轴。',
    'Cannot delete the only main timeline track': '不能删除唯一的主时间轴。',
    'Timeline track still has events': '时间轴下还有节点，暂时不能删除。',
    'Timeline event not found': '时间轴节点不存在。',
    'Timeline event does not belong to project': '时间轴节点不属于当前项目。',
    'Position ratio must be between 0 and 100': '节点位置必须在 0 到 100 之间。',
    'Edge cannot connect the same event': '连接的起点和终点不能相同。',
    'Timeline edge not found': '时间轴连接不存在。',
  }

  return mapped[normalized] ?? normalized
}

function sortEvents(left: TimelineEvent, right: TimelineEvent) {
  return (
    getEventPositionRatio(left) - getEventPositionRatio(right) ||
    left.position_index - right.position_index ||
    left.order_index - right.order_index ||
    left.created_at.localeCompare(right.created_at, 'zh-Hans-CN')
  )
}

function getEventPositionRatio(event: TimelineEvent) {
  return typeof event.position_ratio === 'number' && Number.isFinite(event.position_ratio)
    ? event.position_ratio
    : 50
}

function truncateText(value: string, limit: number) {
  if (value.length <= limit) {
    return value
  }
  return `${value.slice(0, limit)}…`
}

function registerEventNode(eventId: string, element: Element | null) {
  if (element instanceof HTMLElement) {
    eventNodeRefs.value[eventId] = element
    requestMeasureEdges()
    return
  }
  delete eventNodeRefs.value[eventId]
  requestMeasureEdges()
}

function registerTrackLane(trackId: string, element: Element | null) {
  if (element instanceof HTMLElement) {
    trackLaneRefs.value[trackId] = element
    requestMeasureEdges()
    return
  }
  delete trackLaneRefs.value[trackId]
  requestMeasureEdges()
}

function setupTimelineResizeObserver() {
  timelineResizeObserver?.disconnect()
  timelineResizeObserver = null

  if (typeof ResizeObserver === 'undefined') {
    return
  }

  timelineResizeObserver = new ResizeObserver(() => {
    requestMeasureEdges()
  })

  if (canvasViewportRef.value) {
    timelineResizeObserver.observe(canvasViewportRef.value)
  }
  if (canvasBodyRef.value) {
    timelineResizeObserver.observe(canvasBodyRef.value)
  }
}

async function scheduleMeasureEdges() {
  await nextTick()
  measureEdgeOverlay()
}

function requestMeasureEdges() {
  if (edgeMeasureFrameId !== null) {
    return
  }

  edgeMeasureFrameId = window.requestAnimationFrame(() => {
    edgeMeasureFrameId = null
    void scheduleMeasureEdges()
  })
}

function measureEdgeOverlay() {
  const viewport = canvasViewportRef.value
  const body = canvasBodyRef.value
  if (!viewport || !body) {
    edgePoints.value = []
    canvasWidth.value = 0
    canvasHeight.value = 0
    return
  }

  const bodyRect = body.getBoundingClientRect()
  const scrollLeft = viewport.scrollLeft
  const scrollTop = viewport.scrollTop
  const nextPoints: RenderedEdge[] = []
  const nodeBoxes = Object.entries(eventNodeRefs.value)
    .flatMap(([eventId, node]) => {
      if (!node) {
        return []
      }
      const rect = node.getBoundingClientRect()
      return [{
        eventId,
        left: rect.left - bodyRect.left + scrollLeft,
        right: rect.right - bodyRect.left + scrollLeft,
        top: rect.top - bodyRect.top + scrollTop,
        bottom: rect.bottom - bodyRect.top + scrollTop,
      }]
    })
  const similarEdgeCounts = new Map<string, number>()

  for (const edge of visibleEdges.value) {
    const fromNode = eventNodeRefs.value[edge.from_event_id]
    const toNode = eventNodeRefs.value[edge.to_event_id]
    if (!fromNode || !toNode) {
      continue
    }

    const fromRect = fromNode.getBoundingClientRect()
    const toRect = toNode.getBoundingClientRect()
    const start = {
      x: fromRect.left - bodyRect.left + scrollLeft + fromRect.width / 2,
      y: fromRect.top - bodyRect.top + scrollTop + fromRect.height / 2,
    }
    const end = {
      x: toRect.left - bodyRect.left + scrollLeft + toRect.width / 2,
      y: toRect.top - bodyRect.top + scrollTop + toRect.height / 2,
    }

    const areaKey = buildEdgeAreaKey(start.x, start.y, end.x, end.y)
    const similarIndex = similarEdgeCounts.get(areaKey) ?? 0
    similarEdgeCounts.set(areaKey, similarIndex + 1)

    const obstacleBoxes = nodeBoxes.filter(
      (box) => box.eventId !== edge.from_event_id && box.eventId !== edge.to_event_id,
    )
    const route = buildEdgeRoute(start.x, start.y, end.x, end.y, edge.line_style, similarIndex, obstacleBoxes)
    nextPoints.push({
      id: edge.id,
      edge,
      path: route.path,
      labelX: route.labelX,
      labelY: route.labelY,
      dashed: edge.line_style === 'dashed',
      hasArrow: edge.line_style === 'arrow',
      curved: route.curved,
    })
  }

  edgePoints.value = nextPoints
  canvasWidth.value = Math.max(body.scrollWidth, body.clientWidth)
  canvasHeight.value = Math.max(body.scrollHeight, body.clientHeight)
}

type NodeBox = {
  eventId: string
  left: number
  right: number
  top: number
  bottom: number
}

function buildEdgeAreaKey(x1: number, y1: number, x2: number, y2: number) {
  const left = Math.round(Math.min(x1, x2) / 80)
  const right = Math.round(Math.max(x1, x2) / 80)
  const top = Math.round(Math.min(y1, y2) / 60)
  const bottom = Math.round(Math.max(y1, y2) / 60)
  return `${left}:${right}:${top}:${bottom}`
}

function buildEdgeRoute(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  style: TimelineEdgeLineStyle,
  similarIndex: number,
  obstacleBoxes: NodeBox[],
) {
  const crossesTrack = Math.abs(y2 - y1) > 36
  const overlapsNode = obstacleBoxes.some((box) => lineIntersectsBox(x1, y1, x2, y2, box, 10))
  const shouldCurve = style === 'arc' || crossesTrack || overlapsNode
  const distance = Math.hypot(x2 - x1, y2 - y1)
  const siblingOffset = ((similarIndex % 5) - 2) * 12

  if (shouldCurve) {
    const distance = Math.abs(x2 - x1)
    const liftDirection = y2 >= y1 ? -1 : 1
    const lift = Math.max(34, Math.min(140, distance / 4 + Math.abs(y2 - y1) / 3))
    const controlX = (x1 + x2) / 2
    const controlY = (y1 + y2) / 2 + liftDirection * lift + siblingOffset
    return {
      path: `M ${x1} ${y1} Q ${controlX} ${controlY} ${x2} ${y2}`,
      labelX: controlX,
      labelY: controlY - 8,
      curved: true,
    }
  }

  const normalX = distance > 0 ? -(y2 - y1) / distance : 0
  const normalY = distance > 0 ? (x2 - x1) / distance : 0
  const offsetX = normalX * siblingOffset
  const offsetY = normalY * siblingOffset
  return {
    path: `M ${x1 + offsetX} ${y1 + offsetY} L ${x2 + offsetX} ${y2 + offsetY}`,
    labelX: (x1 + x2) / 2 + offsetX,
    labelY: (y1 + y2) / 2 + offsetY - 8,
    curved: false,
  }
}

function lineIntersectsBox(x1: number, y1: number, x2: number, y2: number, box: NodeBox, padding: number) {
  const left = box.left - padding
  const right = box.right + padding
  const top = box.top - padding
  const bottom = box.bottom + padding

  if ((x1 >= left && x1 <= right && y1 >= top && y1 <= bottom) || (x2 >= left && x2 <= right && y2 >= top && y2 <= bottom)) {
    return true
  }

  return (
    segmentsIntersect(x1, y1, x2, y2, left, top, right, top) ||
    segmentsIntersect(x1, y1, x2, y2, right, top, right, bottom) ||
    segmentsIntersect(x1, y1, x2, y2, right, bottom, left, bottom) ||
    segmentsIntersect(x1, y1, x2, y2, left, bottom, left, top)
  )
}

function segmentsIntersect(
  ax: number,
  ay: number,
  bx: number,
  by: number,
  cx: number,
  cy: number,
  dx: number,
  dy: number,
) {
  const ccw = (px: number, py: number, qx: number, qy: number, rx: number, ry: number) =>
    (ry - py) * (qx - px) > (qy - py) * (rx - px)

  return ccw(ax, ay, cx, cy, dx, dy) !== ccw(bx, by, cx, cy, dx, dy) &&
    ccw(ax, ay, bx, by, cx, cy) !== ccw(ax, ay, bx, by, dx, dy)
}

function getNodeClass(event: TimelineEvent) {
  return {
    active: selectedEventId.value === event.id,
    clean: cleanMode.value,
    dragging: dragState.dragging && dragState.eventId === event.id,
  }
}

function getNodeStyle(row: TrackRow, event: TimelineEvent) {
  const ratio = getDisplayPositionRatio(row, event)
  return {
    left: `${ratio}%`,
  }
}

function getDisplayPositionRatio(row: TrackRow, event: TimelineEvent) {
  if (dragState.dragging && dragState.eventId === event.id) {
    return clampNumber(dragState.currentRatio, 0, 100)
  }

  return getStaticNodePositionRatio(row, event)
}

function getStaticNodePositionRatio(row: TrackRow, event: TimelineEvent) {
  if (typeof event.position_ratio === 'number' && Number.isFinite(event.position_ratio)) {
    return clampNumber(event.position_ratio, 0, 100)
  }

  const sameRowEvents = row.events
  const index = sameRowEvents.findIndex((item) => item.id === event.id)
  if (index < 0 || sameRowEvents.length <= 1) {
    return 50
  }

  return clampNumber(((index + 1) / (sameRowEvents.length + 1)) * 100, 0, 100)
}

function clampNumber(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function getNodeWidth(eventId: string) {
  return eventNodeRefs.value[eventId]?.offsetWidth ?? 156
}

function getLaneWidth(trackId: string) {
  return trackLaneRefs.value[trackId]?.getBoundingClientRect().width ?? 0
}

function clampNodePositionRatio(trackId: string, eventId: string, candidateRatio: number) {
  const laneWidth = getLaneWidth(trackId)
  if (laneWidth <= 0) {
    return clampNumber(candidateRatio, 0, 100)
  }

  const draggedWidth = getNodeWidth(eventId)
  const minCenter = (draggedWidth / 2 / laneWidth) * 100
  const maxCenter = 100 - minCenter

  const siblings = getTrackEvents(trackId)
    .filter((item) => item.id !== eventId)
    .map((item) => ({
      event: item,
      ratio: getEventPositionRatio(item),
      width: getNodeWidth(item.id),
    }))
    .sort((left, right) => left.ratio - right.ratio)

  let lowerBound = minCenter
  let upperBound = maxCenter

  for (const sibling of siblings) {
    const gapRatio = ((draggedWidth / 2 + sibling.width / 2 + 12) / laneWidth) * 100
    if (sibling.ratio <= candidateRatio) {
      lowerBound = Math.max(lowerBound, sibling.ratio + gapRatio)
      continue
    }

    upperBound = Math.min(upperBound, sibling.ratio - gapRatio)
    break
  }

  if (lowerBound > upperBound) {
    return clampNumber(candidateRatio, minCenter, maxCenter)
  }

  return clampNumber(candidateRatio, lowerBound, upperBound)
}

function handleNodePointerDown(track: TimelineTrack, event: TimelineEvent, pointerEvent: PointerEvent) {
  if (pointerEvent.button !== 0) {
    return
  }

  const currentTarget = pointerEvent.currentTarget
  if (!(currentTarget instanceof HTMLElement)) {
    return
  }

  dragState.active = true
  dragState.eventId = event.id
  dragState.trackId = track.id
  dragState.pointerId = pointerEvent.pointerId
  dragState.startX = pointerEvent.clientX
  dragState.startY = pointerEvent.clientY
  dragState.startRatio = getStaticNodePositionRatio(
    { id: track.id, title: track.title, description: track.description, track, events: getTrackEvents(track.id), isVirtual: false },
    event,
  )
  dragState.currentRatio = dragState.startRatio
  dragState.dragging = false
  dragState.suppressClick = false

  try {
    currentTarget.setPointerCapture(pointerEvent.pointerId)
  } catch {
    // 某些浏览器/测试环境可能不支持 capture，忽略即可。
  }
}

function handleNodePointerMove(track: TimelineTrack, event: TimelineEvent, pointerEvent: PointerEvent) {
  if (!dragState.active || dragState.pointerId !== pointerEvent.pointerId || dragState.eventId !== event.id) {
    return
  }

  const lane = trackLaneRefs.value[track.id]
  if (!lane) {
    return
  }

  const movedDistance = Math.max(
    Math.abs(pointerEvent.clientX - dragState.startX),
    Math.abs(pointerEvent.clientY - dragState.startY),
  )
  if (!dragState.dragging && movedDistance < DRAG_START_THRESHOLD_PX) {
    return
  }

  dragState.dragging = true
  pointerEvent.preventDefault()

  const laneRect = lane.getBoundingClientRect()
  if (laneRect.width <= 0) {
    return
  }

  const candidateRatio = dragState.startRatio + ((pointerEvent.clientX - dragState.startX) / laneRect.width) * 100
  dragState.currentRatio = clampNodePositionRatio(track.id, event.id, candidateRatio)
  requestMeasureEdges()
}

async function handleNodePointerUp(_track: TimelineTrack, event: TimelineEvent, pointerEvent: PointerEvent) {
  if (!dragState.active || dragState.pointerId !== pointerEvent.pointerId || dragState.eventId !== event.id) {
    return
  }

  const currentTarget = pointerEvent.currentTarget
  if (currentTarget instanceof HTMLElement) {
    try {
      if (currentTarget.hasPointerCapture(pointerEvent.pointerId)) {
        currentTarget.releasePointerCapture(pointerEvent.pointerId)
      }
    } catch {
      // ignore release issues
    }
  }

  if (!dragState.dragging) {
    clearDragState()
    return
  }

  dragState.suppressClick = true
  progressMessage.value = '正在调整节点位置……'

  try {
    await runSave(async () => {
      const saved = await updateTimelineEvent(event.id, {
        position_ratio: clampNumber(Number(dragState.currentRatio.toFixed(2)), 0, 100),
      })
      events.value = events.value.map((item) => (item.id === saved.id ? saved : item))
      successMessage.value = '节点位置已更新'
    }, '节点位置更新失败，请重试')
    await scheduleMeasureEdges()
  } finally {
    progressMessage.value = ''
    clearDragState()
    window.setTimeout(() => {
      dragState.suppressClick = false
    }, 0)
  }
}

function handleNodePointerCancel(_track: TimelineTrack, event: TimelineEvent, pointerEvent: PointerEvent) {
  if (!dragState.active || dragState.pointerId !== pointerEvent.pointerId || dragState.eventId !== event.id) {
    return
  }

  const currentTarget = pointerEvent.currentTarget
  if (currentTarget instanceof HTMLElement) {
    try {
      if (currentTarget.hasPointerCapture(pointerEvent.pointerId)) {
        currentTarget.releasePointerCapture(pointerEvent.pointerId)
      }
    } catch {
      // ignore release issues
    }
  }

  clearDragState()
}

function handleNodeClick(event: TimelineEvent) {
  if (dragState.dragging || dragState.suppressClick) {
    return
  }

  selectEvent(event)
}

function isTrackHidden(trackId: string | null | undefined) {
  if (!trackId) {
    return false
  }
  return hiddenTrackIds.value.includes(trackId)
}

function toggleTrackVisibility(track: TimelineTrack) {
  const next = new Set(hiddenTrackIds.value)
  if (next.has(track.id)) {
    next.delete(track.id)
  } else {
    next.add(track.id)
  }

  hiddenTrackIds.value = Array.from(next)
  void scheduleMeasureEdges()
}

function clearDragState() {
  dragState.active = false
  dragState.eventId = ''
  dragState.trackId = ''
  dragState.pointerId = -1
  dragState.startX = 0
  dragState.startY = 0
  dragState.startRatio = 0
  dragState.currentRatio = 0
  dragState.dragging = false
}
</script>

<template>
  <main class="timeline-page">
    <header class="page-header">
      <div>
        <RouterLink class="back-link" :to="`/projects/${projectId}`">返回写作页</RouterLink>
        <p class="eyebrow">项目时间轴管理</p>
        <h1>时间轴</h1>
        <p class="page-note">用多条时间轴管理主线、角色线、伏笔线和其他剧情事件。</p>
        <p class="project-title">{{ project?.title || '正在加载项目…' }}</p>
      </div>
    </header>

    <section class="toolbar">
      <button class="primary-button" type="button" :disabled="isSaving || isLoading" @click="openCreateTrack">
        新建时间轴
      </button>
      <button class="secondary-button" type="button" :disabled="isSaving || isLoading" @click="openCreateEvent">
        新建节点
      </button>
      <button class="secondary-button" type="button" :disabled="isSaving || isLoading" @click="openCreateEdge">
        新建连接
      </button>
      <button class="toggle-button" type="button" :class="{ active: cleanMode }" @click="cleanMode = !cleanMode">
        纯净模式
      </button>
      <button class="secondary-button" type="button" :disabled="isLoading" @click="refreshWorkspace">
        刷新
      </button>
    </section>

    <p v-if="progressMessage" class="status-banner warning">{{ progressMessage }}</p>
    <p v-if="errorMessage" class="status-banner error">{{ errorMessage }}</p>
    <p v-else-if="successMessage" class="status-banner success">{{ successMessage }}</p>
    <p v-if="invalidEdgeCount > 0" class="status-banner warning">
      已跳过 {{ invalidEdgeCount }} 条无效连接。
    </p>

    <section class="workspace" :class="{ 'detail-visible': hasDetailSelection }">
      <aside class="left-panel">
        <div class="panel-head">
          <div>
            <p class="panel-eyebrow">时间轴列表</p>
            <h2>轨道</h2>
          </div>
          <span class="count-pill">{{ orderedTracks.length }}</span>
        </div>

        <p v-if="orderedTracks.length === 0" class="empty-tip">暂无时间轴，请先新建时间轴。</p>

        <div v-else class="track-list">
          <div
            v-for="track in orderedTracks"
            :key="track.id"
            class="track-list-item"
            :class="{ active: selectedTrackId === track.id, hidden: isTrackHidden(track.id) }"
            @click="selectTrack(track)"
            @contextmenu.prevent="openTrackMenu(track, $event)"
            role="button"
            tabindex="0"
            @keydown.enter.prevent="selectTrack(track)"
            @keydown.space.prevent="selectTrack(track)"
          >
            <span class="track-color" :style="{ background: track.color || '#2563eb' }"></span>
            <span class="track-content">
              <span class="track-title">
                {{ track.title }}
                <small v-if="track.is_main" class="main-tag">主</small>
                <small v-if="isTrackHidden(track.id)" class="hidden-tag">已隐藏</small>
              </span>
              <span class="track-subtitle">{{ getTrackLabel(track) }} · {{ getTrackEventCount(track.id) }} 个节点</span>
            </span>
            <button
              class="track-visibility-button"
              type="button"
              :aria-label="isTrackHidden(track.id) ? '显示时间轴' : '隐藏时间轴'"
              :title="isTrackHidden(track.id) ? '显示时间轴' : '隐藏时间轴'"
              @click.stop="toggleTrackVisibility(track)"
            >
              {{ isTrackHidden(track.id) ? '👁' : '👁' }}
            </button>
            <button
              class="mini-menu-button"
              type="button"
              aria-label="更多操作"
              @click.stop="selectTrackMenuButton(track, $event)"
            >
              ⋯
              </button>
          </div>

          <div v-if="unassignedEvents.length" class="unassigned-note">
            <p>未分配时间轴</p>
            <span>{{ unassignedEvents.length }} 个节点</span>
          </div>
        </div>
      </aside>

      <section class="timeline-canvas-panel">
        <div v-if="isLoading" class="loading-mask">正在加载时间轴…</div>

        <div ref="canvasViewportRef" class="timeline-canvas-viewport" @click.self="resetSelection">
          <div ref="canvasBodyRef" class="timeline-canvas-body" @click.self="resetSelection">
            <svg
              v-if="edgePoints.length > 0"
              class="timeline-edge-overlay"
              :width="canvasWidth"
              :height="canvasHeight"
              :viewBox="`0 0 ${canvasWidth} ${canvasHeight}`"
            >
              <defs>
                <marker
                  id="timeline-arrow"
                  markerWidth="10"
                  markerHeight="10"
                  refX="8"
                  refY="3"
                  orient="auto"
                  markerUnits="strokeWidth"
                >
                  <path d="M0,0 L0,6 L8,3 z" fill="#64748b" />
                </marker>
              </defs>
              <g
                v-for="edge in edgePoints"
                :key="edge.id"
                class="timeline-edge"
                :class="{ selected: selectedEdgeId === edge.id, curved: edge.curved }"
                @click.stop="selectEdge(edge.edge)"
              >
                <path class="edge-hitbox" :d="edge.path" />
                <path
                  class="edge-line"
                  :d="edge.path"
                  :class="{ dashed: edge.dashed }"
                  :marker-end="edge.hasArrow ? 'url(#timeline-arrow)' : undefined"
                />
                <text
                  v-if="edge.edge.label || selectedEdgeId === edge.id"
                  class="edge-floating-label"
                  :x="edge.labelX"
                  :y="edge.labelY"
                  text-anchor="middle"
                >
                  {{ edge.edge.label || getEdgeLabel(edge.edge) }}
                </text>
              </g>
            </svg>

            <article
              v-for="row in rows"
              :key="row.id"
              class="track-row"
              :class="{ virtual: row.isVirtual, active: selectedTrackId === row.id, dragging: dragState.dragging && dragState.trackId === row.id }"
              @click.self="resetSelection"
            >
              <button
                class="track-row-label"
                type="button"
                :class="{ virtual: row.isVirtual }"
                @click="row.track ? selectTrack(row.track) : resetSelection()"
              >
                <span class="row-title">{{ row.title }}</span>
                <span class="row-meta">
                  <template v-if="row.track">
                    {{ timelineTrackTypeLabels[row.track.track_type] }} · {{ row.events.length }} 个节点
                  </template>
                  <template v-else>
                    {{ row.description }}
                  </template>
                </span>
              </button>

              <div
                :ref="(element) => registerTrackLane(row.id, element as Element | null)"
                class="track-row-lane"
                :class="{ dragging: dragState.dragging && dragState.trackId === row.id }"
                @click.self="resetSelection"
              >
                <span class="lane-axis"></span>

                <button
                  v-for="trackEvent in row.events"
                  :key="trackEvent.id"
                  :ref="(element) => registerEventNode(trackEvent.id, element as Element | null)"
                  class="timeline-node"
                  :class="getNodeClass(trackEvent)"
                  :style="getNodeStyle(row, trackEvent)"
                  type="button"
                  @click="handleNodeClick(trackEvent)"
                  @pointerdown="row.track ? handleNodePointerDown(row.track, trackEvent, $event) : undefined"
                  @pointermove="row.track ? handleNodePointerMove(row.track, trackEvent, $event) : undefined"
                  @pointerup="row.track ? handleNodePointerUp(row.track, trackEvent, $event) : undefined"
                  @pointercancel="row.track ? handleNodePointerCancel(row.track, trackEvent, $event) : undefined"
                >
                  <span v-if="row.track" class="drag-handle" aria-hidden="true">
                    ⋮⋮
                  </span>
                  <span class="node-title">{{ trackEvent.title }}</span>
                  <span class="node-meta">{{ getEventSubtitle(trackEvent) }}</span>
                  <span v-if="!cleanMode && trackEvent.chapter_id" class="node-chip">
                    {{ getEventDetailChapter(trackEvent) }}
                  </span>
                  <span v-if="!cleanMode && trackEvent.description" class="node-description">
                    {{ truncateText(trackEvent.description, 54) }}
                  </span>
                </button>
              </div>
            </article>
          </div>
        </div>
      </section>

      <aside v-if="hasDetailSelection" class="detail-panel">
        <template v-if="panelKind === 'track'">
          <header class="detail-header">
            <div>
              <p class="panel-eyebrow">{{ panelMode === 'create' ? '新建时间轴' : '时间轴详情' }}</p>
              <h2>{{ panelMode === 'create' ? '创建时间轴' : selectedTrack?.title || '时间轴' }}</h2>
            </div>
          </header>

          <div class="form-grid">
            <label class="field">
              <span>标题</span>
              <input v-model="trackForm.title" type="text" placeholder="例如：主角成长线" />
            </label>

            <label class="field field-wide">
              <span>描述</span>
              <textarea v-model="trackForm.description" rows="3" placeholder="说明这条时间轴追踪什么内容" />
            </label>

            <label class="field">
              <span>类型</span>
              <select v-model="trackForm.track_type">
                <option v-for="trackType in trackTypes" :key="trackType" :value="trackType">
                  {{ timelineTrackTypeLabels[trackType] }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>排序序号</span>
              <input v-model.number="trackForm.order_index" type="number" min="0" />
            </label>

            <label class="field">
              <span>颜色</span>
              <input v-model="trackForm.color" type="text" placeholder="#6B8AFD" />
            </label>

            <label class="field">
              <span>是否主时间轴</span>
              <select v-model="trackForm.is_main">
                <option :value="true">是</option>
                <option :value="false">否</option>
              </select>
            </label>

            <label class="field">
              <span>绑定对象类型</span>
              <input v-model="trackForm.bound_type" type="text" placeholder="例如：character" />
            </label>

            <label class="field">
              <span>绑定对象 ID</span>
              <input v-model="trackForm.bound_id" type="text" placeholder="可选" />
            </label>
          </div>

          <div class="form-actions">
            <button class="primary-button" type="button" :disabled="isSaving" @click="handleSaveTrack">
              保存时间轴
            </button>
            <button
              v-if="panelMode === 'edit' && selectedTrack"
              class="danger-button"
              type="button"
              :disabled="isSaving"
              @click="handleDeleteTrack(selectedTrack)"
            >
              删除时间轴
            </button>
          </div>
          <MaterialLinkPanel
            v-if="panelMode === 'edit' && selectedEvent"
            :project-id="projectId"
            source-type="timeline_event"
            :source-id="selectedEvent.id"
            :source-title="selectedEvent.title"
          />
        </template>

        <template v-else-if="panelKind === 'event'">
          <header class="detail-header">
            <div>
              <p class="panel-eyebrow">{{ panelMode === 'create' ? '新建节点' : '节点详情' }}</p>
              <h2>{{ panelMode === 'create' ? '创建时间轴节点' : selectedEvent?.title || '时间轴节点' }}</h2>
            </div>
          </header>

          <div class="form-grid">
            <label class="field field-wide">
              <span>标题</span>
              <input v-model="eventForm.title" type="text" placeholder="例如：主角进入青萍城" />
            </label>

            <label class="field field-wide">
              <span>描述</span>
              <textarea v-model="eventForm.description" rows="3" placeholder="节点发生了什么" />
            </label>

            <label class="field">
              <span>所属时间轴</span>
              <select v-model="eventForm.track_id">
                <option value="">自动使用主时间轴</option>
                <option v-for="track in trackOptions" :key="track.id" :value="track.id">
                  {{ track.label }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>事件类型</span>
              <select v-model="eventForm.event_type">
                <option v-for="eventType in eventTypes" :key="eventType" :value="eventType">
                  {{ timelineEventTypeLabels[eventType] }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>故事日期</span>
              <input v-model="eventForm.story_date" type="text" placeholder="第一卷第一日" />
            </label>

            <label class="field">
              <span>故事时间</span>
              <input v-model="eventForm.story_time" type="text" placeholder="傍晚" />
            </label>

            <label class="field">
              <span>关联章节</span>
              <select v-model="eventForm.chapter_id">
                <option value="">未绑定</option>
                <option v-for="chapter in chapterOptions" :key="chapter.id" :value="chapter.id">
                  {{ chapter.label }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>发生地点 / 关联地点设定</span>
              <select v-model="eventForm.location_setting_id">
                <option value="">未绑定</option>
                <option v-for="setting in settingOptions" :key="setting.id" :value="setting.id">
                  {{ setting.label }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>排序序号</span>
              <input v-model.number="eventForm.order_index" type="number" min="0" />
            </label>

            <label class="field">
              <span>位置序号</span>
              <input v-model.number="eventForm.position_index" type="number" min="0" />
            </label>

            <label class="field">
              <span>重要程度</span>
              <select v-model="eventForm.importance">
                <option v-for="importance in eventImportances" :key="importance" :value="importance">
                  {{ timelineEventImportanceLabels[importance] }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>状态</span>
              <select v-model="eventForm.status">
                <option v-for="status in eventStatuses" :key="status" :value="status">
                  {{ timelineEventStatusLabels[status] }}
                </option>
              </select>
            </label>

            <label class="field field-wide">
              <span>备注</span>
              <textarea v-model="eventForm.note" rows="3" placeholder="补充说明" />
            </label>
          </div>

          <div class="form-actions">
            <button class="primary-button" type="button" :disabled="isSaving" @click="handleSaveEvent">
              保存节点
            </button>
            <button
              v-if="panelMode === 'edit' && selectedEvent"
              class="danger-button"
              type="button"
              :disabled="isSaving"
              @click="handleDeleteEvent"
            >
              删除节点
            </button>
          </div>
        </template>

        <template v-else-if="panelKind === 'edge'">
          <header class="detail-header">
            <div>
              <p class="panel-eyebrow">{{ panelMode === 'create' ? '新建连接' : '连接详情' }}</p>
              <h2>{{ panelMode === 'create' ? '创建时间轴连接' : selectedEdge ? getEdgeLabel(selectedEdge) : '时间轴连接' }}</h2>
            </div>
          </header>

          <div class="form-grid">
            <label class="field field-wide">
              <span>起点事件</span>
              <select v-model="edgeForm.from_event_id">
                <option value="" disabled>请选择起点事件</option>
                <option v-for="event in eventOptions" :key="event.id" :value="event.id">
                  {{ event.label }}
                </option>
              </select>
            </label>

            <label class="field field-wide">
              <span>终点事件</span>
              <select v-model="edgeForm.to_event_id">
                <option value="" disabled>请选择终点事件</option>
                <option v-for="event in eventOptions" :key="event.id" :value="event.id">
                  {{ event.label }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>关系类型</span>
              <select v-model="edgeForm.edge_type">
                <option v-for="edgeType in edgeTypes" :key="edgeType" :value="edgeType">
                  {{ timelineEdgeTypeLabels[edgeType] }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>时序关系</span>
              <select v-model="edgeForm.temporal_relation">
                <option v-for="temporalRelation in temporalRelations" :key="temporalRelation" :value="temporalRelation">
                  {{ timelineEdgeTemporalRelationLabels[temporalRelation] }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>线条样式</span>
              <select v-model="edgeForm.line_style">
                <option v-for="lineStyle in lineStyles" :key="lineStyle" :value="lineStyle">
                  {{ timelineEdgeLineStyleLabels[lineStyle] }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>标签</span>
              <input v-model="edgeForm.label" type="text" placeholder="例如：导致" />
            </label>

            <label class="field">
              <span>可见性</span>
              <select v-model="edgeForm.visibility">
                <option v-for="visibility in visibilities" :key="visibility" :value="visibility">
                  {{ timelineEdgeVisibilityLabels[visibility] }}
                </option>
              </select>
            </label>

            <label class="field field-wide">
              <span>批注</span>
              <textarea v-model="edgeForm.note" rows="3" placeholder="说明这条连接的用途" />
            </label>
          </div>

          <div class="form-actions">
            <button class="primary-button" type="button" :disabled="isSaving" @click="handleSaveEdge">
              保存连接
            </button>
            <button
              v-if="panelMode === 'edit' && selectedEdge"
              class="danger-button"
              type="button"
              :disabled="isSaving"
              @click="handleDeleteEdge"
            >
              删除连接
            </button>
          </div>
        </template>

        <template v-else>
          <section class="empty-detail">
            <h2>时间轴操作说明</h2>
            <p>左侧选择时间轴，中间查看轨道式时间线，右侧编辑时间轴、节点或连接。</p>
            <ul>
              <li>点击时间轴节点可以编辑节点详情。</li>
              <li>点击时间轴条目可以编辑时间轴本身。</li>
              <li>连接列表支持创建、修改和删除。</li>
              <li>若有无效连接，会在上方显示提示并自动跳过。</li>
            </ul>
          </section>
        </template>

        <section class="edge-list-panel">
          <div class="panel-head compact">
            <div>
              <p class="panel-eyebrow">连接列表</p>
              <h2>时间轴连接</h2>
            </div>
            <span class="count-pill">{{ visibleEdges.length }}</span>
          </div>

          <p v-if="visibleEdges.length === 0" class="empty-tip">暂无可显示的时间轴连接。</p>

          <div v-else class="edge-list">
            <button
              v-for="edge in visibleEdges"
              :key="edge.id"
              type="button"
              class="edge-list-item"
              :class="{ active: selectedEdgeId === edge.id }"
              @click="selectEdge(edge)"
            >
              <span class="edge-list-title">{{ getEdgeLabel(edge) }}</span>
              <span class="edge-list-meta">{{ buildEdgeDescription(edge) }}</span>
              <span class="edge-list-note" v-if="!cleanMode && edge.note">{{ edge.note }}</span>
            </button>
          </div>
        </section>
      </aside>
    </section>

    <ContextMenu
      :visible="trackMenu.visible"
      :x="trackMenu.x"
      :y="trackMenu.y"
      :items="[
        { id: 'edit', label: '编辑时间轴' },
        { id: 'delete', label: '删除时间轴', danger: true },
      ]"
      @close="closeTrackMenu"
      @select="handleTrackMenuSelect"
    />
  </main>
</template>

<style scoped>
.timeline-page {
  display: grid;
  gap: 16px;
  padding: 20px;
}

.page-header,
.toolbar,
.status-banner,
.workspace {
  max-width: 100%;
}

.page-header {
  display: grid;
  gap: 8px;
}

.back-link {
  color: #2563eb;
  font-size: 0.85rem;
  font-weight: 700;
  text-decoration: none;
}

.eyebrow,
.project-title,
.page-note,
.panel-eyebrow,
.status-banner,
.empty-tip,
.row-meta,
.node-meta,
.node-chip,
.node-description,
.edge-list-meta,
.edge-list-note,
.empty-detail p,
.empty-detail li {
  margin: 0;
}

.eyebrow,
.panel-eyebrow {
  color: #64748b;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0;
}

h1 {
  margin: 0;
  color: #111827;
  font-size: 1.6rem;
}

.page-note {
  color: #475569;
  line-height: 1.6;
}

.project-title {
  color: #0f172a;
  font-size: 0.92rem;
  font-weight: 700;
}

.toolbar {
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

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.status-banner {
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
  color: #027a48;
}

.status-banner.warning {
  background: #fffbeb;
  color: #92400e;
}

.workspace {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 14px;
  min-height: 0;
}

.workspace.detail-visible {
  grid-template-columns: 280px minmax(0, 1fr) 360px;
}

.left-panel,
.timeline-canvas-panel,
.detail-panel {
  min-height: 0;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  background: #ffffff;
}

.left-panel,
.detail-panel {
  display: grid;
  gap: 12px;
  padding: 14px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.panel-head.compact {
  margin-bottom: 2px;
}

h2 {
  margin: 0;
  color: #111827;
  font-size: 1.03rem;
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

.empty-tip {
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 12px;
  color: #64748b;
  line-height: 1.6;
}

.track-list {
  display: grid;
  gap: 8px;
}

.track-list-item {
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr) auto auto;
  gap: 10px;
  align-items: center;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  background: #ffffff;
  color: #0f172a;
  text-align: left;
}

.track-list-item:hover,
.track-list-item.active {
  border-color: #93c5fd;
  background: #eff6ff;
}

.track-list-item.hidden {
  opacity: 0.66;
}

.track-color {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.track-content {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.track-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  font-weight: 800;
}

.main-tag {
  border-radius: 999px;
  padding: 1px 6px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 0.72rem;
}

.hidden-tag {
  border-radius: 999px;
  padding: 1px 6px;
  background: #f1f5f9;
  color: #475569;
  font-size: 0.72rem;
}

.track-subtitle {
  color: #64748b;
  font-size: 0.78rem;
  line-height: 1.4;
}

.track-visibility-button {
  border: 0;
  border-radius: 6px;
  padding: 4px 6px;
  background: transparent;
  color: #475569;
  font-size: 0.92rem;
  cursor: pointer;
}

.mini-menu-button {
  border: 0;
  border-radius: 6px;
  padding: 2px 7px;
  background: transparent;
  color: #64748b;
  font-size: 1rem;
  opacity: 0;
}

.track-list-item:hover .mini-menu-button,
.track-list-item:focus-within .mini-menu-button {
  opacity: 1;
}

.unassigned-note {
  border-radius: 8px;
  padding: 10px 12px;
  background: #f8fafc;
  color: #475569;
}

.unassigned-note p {
  margin: 0 0 4px;
  font-size: 0.88rem;
  font-weight: 800;
}

.unassigned-note span {
  font-size: 0.78rem;
}

.timeline-canvas-panel {
  position: relative;
  overflow: hidden;
}

.loading-mask {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: grid;
  place-items: center;
  background: rgb(255 255 255 / 75%);
  color: #475569;
  font-size: 0.92rem;
  font-weight: 700;
}

.timeline-canvas-viewport {
  overflow: auto;
  width: 100%;
  height: 100%;
}

.timeline-canvas-body {
  position: relative;
  min-height: 100%;
  min-width: 100%;
  padding: 18px 20px 20px;
}

.timeline-edge-overlay {
  position: absolute;
  inset: 0 auto auto 0;
  z-index: 0;
  pointer-events: auto;
}

.timeline-edge {
  cursor: pointer;
}

.timeline-edge .edge-line {
  fill: none;
  stroke: #94a3b8;
  stroke-width: 2;
  opacity: 0.72;
  pointer-events: none;
}

.timeline-edge .edge-hitbox {
  fill: none;
  stroke: transparent;
  stroke-width: 16;
  pointer-events: stroke;
}

.timeline-edge .edge-line.dashed {
  stroke-dasharray: 8 6;
}

.timeline-edge.selected .edge-line {
  stroke: #2563eb;
  stroke-width: 3;
  opacity: 0.98;
}

.edge-floating-label {
  fill: #1e293b;
  stroke: #ffffff;
  stroke-width: 4;
  paint-order: stroke;
  font-size: 0.75rem;
  font-weight: 800;
  opacity: 0;
  pointer-events: none;
}

.timeline-edge:hover .edge-floating-label,
.timeline-edge.selected .edge-floating-label {
  opacity: 1;
}

.track-row {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  gap: 16px;
  align-items: center;
  padding: 14px 0;
}

.track-row:not(:last-child) {
  border-bottom: 1px solid #eef2f7;
}

.track-row.virtual {
  background: linear-gradient(90deg, rgb(239 246 255 / 72%), transparent);
}

.track-row.active .track-row-label {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.track-row-label {
  display: grid;
  gap: 5px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 12px 11px;
  background: #ffffff;
  color: #0f172a;
  text-align: left;
}

.track-row-label.virtual {
  background: #f8fafc;
}

.row-title {
  font-size: 0.95rem;
  font-weight: 800;
}

.row-meta {
  color: #64748b;
  font-size: 0.78rem;
  line-height: 1.5;
}

.track-row-lane {
  position: relative;
  min-height: 128px;
  padding: 18px 10px 18px 8px;
  overflow: visible;
}

.lane-axis {
  position: absolute;
  inset-inline: 0;
  top: 50%;
  height: 2px;
  transform: translateY(-50%);
  background: linear-gradient(90deg, transparent, #cbd5e1 8%, #94a3b8 50%, #cbd5e1 92%, transparent);
}

.track-row-lane.dragging .lane-axis {
  background: linear-gradient(90deg, transparent, #93c5fd 8%, #3b82f6 50%, #93c5fd 92%, transparent);
}

.timeline-node {
  position: absolute;
  top: 50%;
  z-index: 1;
  display: grid;
  align-content: start;
  gap: 4px;
  width: 156px;
  min-height: 70px;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 20px 12px 11px;
  background: #ffffff;
  box-shadow: 0 8px 18px rgb(15 23 42 / 5%);
  text-align: left;
  transform: translate(-50%, -50%);
  touch-action: none;
  cursor: grab;
}

.timeline-node:hover,
.timeline-node.active {
  border-color: #60a5fa;
  background: #f8fbff;
}

.timeline-node.dragging {
  opacity: 0.82;
  border-style: dashed;
  box-shadow: 0 16px 32px rgb(37 99 235 / 14%);
  cursor: grabbing;
}

.timeline-node.clean {
  width: 148px;
  min-height: 66px;
}

.node-title {
  color: #0f172a;
  font-size: 0.88rem;
  font-weight: 800;
  line-height: 1.45;
}

.node-meta {
  color: #2563eb;
  font-size: 0.76rem;
  line-height: 1.35;
}

.node-chip {
  display: inline-flex;
  justify-self: start;
  border-radius: 999px;
  padding: 2px 8px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 0.72rem;
  font-weight: 800;
}

.node-description {
  color: #475569;
  font-size: 0.76rem;
  line-height: 1.45;
}

.drag-handle {
  position: absolute;
  top: 6px;
  right: 8px;
  color: #94a3b8;
  font-size: 0.9rem;
  line-height: 1;
  pointer-events: none;
  user-select: none;
}

.track-row.dragging .track-row-label {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.track-row-lane.dragging {
  background: linear-gradient(90deg, rgb(239 246 255 / 25%), transparent);
}

.detail-panel {
  overflow: auto;
  align-content: start;
}

.detail-header {
  display: grid;
  gap: 6px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.field {
  display: grid;
  gap: 6px;
}

.field-wide {
  grid-column: 1 / -1;
}

.field span {
  color: #475569;
  font-size: 0.8rem;
  font-weight: 700;
}

input,
select,
textarea {
  width: 100%;
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

.empty-detail ul {
  margin: 0;
  padding-left: 18px;
  line-height: 1.7;
}

.edge-list-panel {
  display: grid;
  gap: 10px;
  padding-top: 10px;
  border-top: 1px solid #eef2f7;
}

.edge-list {
  display: grid;
  gap: 8px;
}

.edge-list-item {
  display: grid;
  gap: 4px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  background: #ffffff;
  color: #0f172a;
  text-align: left;
}

.edge-list-item:hover,
.edge-list-item.active {
  border-color: #93c5fd;
  background: #eff6ff;
}

.edge-list-title {
  font-size: 0.88rem;
  font-weight: 800;
}

.edge-list-meta,
.edge-list-note {
  color: #64748b;
  font-size: 0.77rem;
  line-height: 1.45;
}

@media (max-width: 1280px) {
  .workspace,
  .workspace.detail-visible {
    grid-template-columns: 260px minmax(0, 1fr);
  }

  .detail-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 900px) {
  .workspace,
  .workspace.detail-visible {
    grid-template-columns: 1fr;
  }

  .timeline-canvas-panel {
    min-height: 520px;
  }
}
</style>
