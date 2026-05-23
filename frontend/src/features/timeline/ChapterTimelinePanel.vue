<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { listChapterTimelineEvents, listProjectTimelineEvents, listTimelineEdges, listTimelineTracks } from '@/entities/timeline/api'
import type { TimelineEdge, TimelineEdgeTemporalRelation, TimelineEvent, TimelineTrack } from '@/entities/timeline/types'
import {
  timelineEdgeTemporalRelationLabels,
  timelineEdgeTypeLabels,
  timelineEventTypeLabels,
  timelineTrackTypeLabels,
} from '@/entities/timeline/types'

const props = defineProps<{
  projectId: string
  chapterId: string | null
}>()

type ChapterEventSummary = {
  event: TimelineEvent
  trackTitle: string
  trackTypeLabel: string
  timeLabel: string
  description: string
  previousEvent: TimelineEvent | null
  nextEvent: TimelineEvent | null
}

type RelatedConnection = {
  id: string
  edgeTypeLabel: string
  directionLabel: string
  temporalRelationLabel: string
  visibilityLabel: string
  note: string
  orderRank: number
}

const isLoading = ref(false)
const errorMessage = ref('')
const directEvents = ref<TimelineEvent[]>([])
const tracks = ref<TimelineTrack[]>([])
const allEvents = ref<TimelineEvent[]>([])
const edges = ref<TimelineEdge[]>([])

let loadToken = 0

watch(
  () => [props.projectId, props.chapterId],
  () => {
    void refreshPanel()
  },
  { immediate: true },
)

const orderedTracks = computed(() =>
  [...tracks.value].sort((left, right) => {
    if (left.is_main !== right.is_main) {
      return left.is_main ? -1 : 1
    }

    return left.order_index - right.order_index || left.created_at.localeCompare(right.created_at, 'zh-Hans-CN')
  }),
)

const trackMap = computed(() =>
  orderedTracks.value.reduce<Record<string, TimelineTrack>>((accumulator, track) => {
    accumulator[track.id] = track
    return accumulator
  }, {}),
)

const eventMap = computed(() =>
  allEvents.value.reduce<Record<string, TimelineEvent>>((accumulator, event) => {
    accumulator[event.id] = event
    return accumulator
  }, {}),
)

const trackOrderMap = computed(() => new Map(orderedTracks.value.map((track, index) => [track.id, index])))

const trackEventsMap = computed(() => {
  const groups = new Map<string, TimelineEvent[]>()

  for (const track of orderedTracks.value) {
    groups.set(track.id, [])
  }

  groups.set('__unassigned__', [])

  for (const event of allEvents.value) {
    const groupKey = getTrackGroupKey(event.track_id)
    if (!groups.has(groupKey)) {
      groups.set(groupKey, [])
    }
    groups.get(groupKey)!.push(event)
  }

  for (const list of groups.values()) {
    list.sort(sortEvents)
  }

  return groups
})

const sortedDirectEvents = computed(() =>
  directEvents.value.slice().sort((left, right) => {
    const leftRank = getTrackSortRank(left.track_id)
    const rightRank = getTrackSortRank(right.track_id)
    return leftRank - rightRank || sortEvents(left, right)
  }),
)

const directEventOrderMap = computed(() => new Map(sortedDirectEvents.value.map((event, index) => [event.id, index])))

const directEventSummaries = computed<ChapterEventSummary[]>(() =>
  sortedDirectEvents.value.map((event) => {
    const groupKey = getTrackGroupKey(event.track_id)
    const sameTrackEvents = trackEventsMap.value.get(groupKey) ?? []
    const currentIndex = sameTrackEvents.findIndex((item) => item.id === event.id)
    const previousEvent = currentIndex > 0 ? sameTrackEvents[currentIndex - 1] ?? null : null
    const nextEvent = currentIndex >= 0 && currentIndex < sameTrackEvents.length - 1 ? sameTrackEvents[currentIndex + 1] ?? null : null

    return {
      event,
      trackTitle: getTrackTitle(event.track_id),
      trackTypeLabel: getTrackTypeLabel(event.track_id),
      timeLabel: formatEventTime(event),
      description: getDescriptionPreview(event),
      previousEvent,
      nextEvent,
    }
  }),
)

const relatedConnections = computed<RelatedConnection[]>(() => {
  const directIds = new Set(directEvents.value.map((event) => event.id))

  return edges.value
    .filter((edge) => edge.visibility !== 'hidden')
    .flatMap((edge) => {
      const fromEvent = eventMap.value[edge.from_event_id] ?? null
      const toEvent = eventMap.value[edge.to_event_id] ?? null
      if (!fromEvent || !toEvent) {
        return []
      }

      if (!directIds.has(edge.from_event_id) && !directIds.has(edge.to_event_id)) {
        return []
      }

      const relatedEntries: RelatedConnection[] = []

      if (directIds.has(edge.from_event_id)) {
        relatedEntries.push(buildRelatedConnection(edge, fromEvent, toEvent))
      }

      if (directIds.has(edge.to_event_id)) {
        relatedEntries.push(buildRelatedConnection(edge, toEvent, fromEvent))
      }

      return relatedEntries
    })
    .filter((item): item is RelatedConnection => Boolean(item))
    .sort((left, right) => left.orderRank - right.orderRank || left.id.localeCompare(right.id))
})

function buildRelatedConnection(edge: TimelineEdge, currentEvent: TimelineEvent, otherEvent: TimelineEvent): RelatedConnection {
  const orderRank = directEventOrderMap.value.get(currentEvent.id) ?? Number.MAX_SAFE_INTEGER
  const temporalRelation = getTemporalRelationForCurrentEvent(edge, currentEvent.id)

  return {
    id: `${edge.id}:${currentEvent.id}`,
    edgeTypeLabel: timelineEdgeTypeLabels[edge.edge_type],
    directionLabel: `${currentEvent.title} → ${otherEvent.title}`,
    temporalRelationLabel: timelineEdgeTemporalRelationLabels[temporalRelation],
    visibilityLabel: edge.visibility === 'normal' ? '正常' : edge.visibility === 'subtle' ? '弱化' : '隐藏',
    note: edge.note,
    orderRank,
  }
}

function getTemporalRelationForCurrentEvent(edge: TimelineEdge, currentEventId: string): TimelineEdgeTemporalRelation {
  if (edge.from_event_id === currentEventId) {
    return edge.temporal_relation
  }

  return invertTemporalRelation(edge.temporal_relation)
}

function invertTemporalRelation(relation: TimelineEdgeTemporalRelation): TimelineEdgeTemporalRelation {
  switch (relation) {
    case 'previous':
      return 'future'
    case 'future':
      return 'previous'
    case 'delayed':
      return 'previous'
    case 'parallel':
      return 'parallel'
    case 'unordered':
    default:
      return 'unordered'
  }
}

const hasChapterEvents = computed(() => directEventSummaries.value.length > 0)

async function refreshPanel() {
  const currentToken = ++loadToken

  if (!props.projectId || !props.chapterId) {
    clearState()
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    // 未来可以在这里叠加人物/设定/伏笔/关键词/AI 候选匹配；当前仅保留显式绑定结果。
    const [chapterEvents, projectTracks, projectEvents, projectEdges] = await Promise.all([
      listChapterTimelineEvents(props.chapterId),
      listTimelineTracks(props.projectId),
      listProjectTimelineEvents(props.projectId),
      listTimelineEdges(props.projectId),
    ])

    if (currentToken !== loadToken) {
      return
    }

    directEvents.value = chapterEvents
    tracks.value = projectTracks
    allEvents.value = projectEvents
    edges.value = projectEdges
  } catch (error) {
    if (currentToken === loadToken) {
      void error
      errorMessage.value = '时间轴信息加载失败，请稍后重试。'
    }
  } finally {
    if (currentToken === loadToken) {
      isLoading.value = false
    }
  }
}

function clearState() {
  isLoading.value = false
  errorMessage.value = ''
  directEvents.value = []
  tracks.value = []
  allEvents.value = []
  edges.value = []
}

function getTrackGroupKey(trackId: string | null) {
  if (!trackId || !trackMap.value[trackId]) {
    return '__unassigned__'
  }
  return trackId
}

function getTrackSortRank(trackId: string | null) {
  if (!trackId || !trackMap.value[trackId]) {
    return orderedTracks.value.length + 1
  }

  return trackOrderMap.value.get(trackId) ?? orderedTracks.value.length + 1
}

function getTrackTitle(trackId: string | null) {
  if (!trackId || !trackMap.value[trackId]) {
    return '未分配时间轴'
  }
  return trackMap.value[trackId].title
}

function getTrackTypeLabel(trackId: string | null) {
  if (!trackId || !trackMap.value[trackId]) {
    return '未分配'
  }
  return timelineTrackTypeLabels[trackMap.value[trackId].track_type]
}

function formatEventTime(event: TimelineEvent) {
  const parts = [event.story_date, event.story_time].filter(Boolean)
  if (parts.length === 0) {
    return '未填写时间'
  }
  return parts.join(' · ')
}

function getDescriptionPreview(event: TimelineEvent) {
  const text = event.description || event.note || '暂无描述。'
  if (text.length <= 72) {
    return text
  }
  return `${text.slice(0, 72)}…`
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
  return typeof event.position_ratio === 'number' ? event.position_ratio : 50
}
</script>

<template>
  <section class="chapter-timeline-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">本章时间轴</p>
        <h2>时间轴摘要</h2>
      </div>
      <RouterLink v-if="chapterId" class="timeline-link" :to="`/projects/${projectId}/timeline`">
        完整时间轴
      </RouterLink>
    </header>

    <p class="helper-note">仅显示与当前章节直接相关的时间轴信息。暂未启用智能匹配，当前结果来自显式绑定。</p>

    <p v-if="!chapterId" class="state-message">请选择章节后查看本章时间轴。</p>

    <template v-else>
      <p v-if="isLoading" class="state-message">正在加载本章时间轴摘要……</p>
      <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>

      <template v-else>
        <section class="section-block">
          <div class="section-head">
            <h3>本章事件</h3>
            <span class="count-pill">{{ directEventSummaries.length }}</span>
          </div>

          <p v-if="!hasChapterEvents" class="state-message compact">
            本章暂无时间轴事件。可在完整时间轴中为本章创建或绑定事件。
          </p>

          <div v-else class="event-list">
            <article v-for="item in directEventSummaries" :key="item.event.id" class="event-card">
              <div class="event-card-head">
                <div>
                  <p class="track-label">{{ item.trackTitle }}</p>
                  <h4>{{ item.event.title }}</h4>
                </div>
                <span class="time-pill">{{ item.timeLabel }}</span>
              </div>

              <div class="meta-grid">
                <div>
                  <span class="field-label">所属轴线</span>
                  <strong>{{ item.trackTitle }}</strong>
                </div>
                <div>
                  <span class="field-label">故事时间</span>
                  <strong>{{ item.timeLabel }}</strong>
                </div>
              </div>

              <p class="event-meta">
                {{ timelineEventTypeLabels[item.event.event_type] }} · {{ item.trackTypeLabel }}
              </p>
              <p class="event-description">{{ item.description }}</p>
            </article>
          </div>
        </section>

        <section class="section-block">
          <div class="section-head">
            <h3>前后节点</h3>
            <span class="count-pill">{{ directEventSummaries.length }}</span>
          </div>

          <p v-if="!hasChapterEvents" class="state-message compact">暂无可展示的前后节点。</p>

          <div v-else class="sequence-list">
            <article v-for="item in directEventSummaries" :key="item.event.id" class="sequence-card">
              <p class="sequence-title">{{ item.event.title }}</p>
              <p class="sequence-line">
                <span>前一节点</span>
                {{ item.previousEvent?.title || '无' }}
              </p>
              <p class="sequence-line">
                <span>后一节点</span>
                {{ item.nextEvent?.title || '无' }}
              </p>
            </article>
          </div>
        </section>

        <section class="section-block">
          <div class="section-head">
            <h3>相关连接</h3>
            <span class="count-pill">{{ relatedConnections.length }}</span>
          </div>

          <p v-if="relatedConnections.length === 0" class="state-message compact">暂无相关连接。</p>

          <div v-else class="connection-list">
            <article v-for="connection in relatedConnections" :key="connection.id" class="connection-card">
              <div class="connection-head">
                <span class="edge-label">{{ connection.edgeTypeLabel }}</span>
                <span class="temporal-pill">{{ connection.temporalRelationLabel }}</span>
                <span class="visibility-pill">{{ connection.visibilityLabel }}</span>
              </div>
              <p class="connection-title">{{ connection.directionLabel }}</p>
              <p v-if="connection.note" class="connection-note">{{ connection.note }}</p>
            </article>
          </div>
        </section>
      </template>
    </template>
  </section>
</template>

<style scoped>
.chapter-timeline-panel {
  display: grid;
  gap: 12px;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.eyebrow,
.helper-note,
.state-message,
.error-message,
.section-head h3,
.track-label,
.event-meta,
.event-description,
.sequence-title,
.sequence-line,
.connection-title,
.connection-note {
  margin: 0;
}

.eyebrow {
  color: var(--zs-color-text-muted);
  font-size: 0.75rem;
  font-weight: 800;
}

h2 {
  margin: 0;
  color: var(--zs-color-text);
  font-size: 1rem;
}

.timeline-link {
  color: var(--zs-color-primary);
  font-size: 0.8rem;
  font-weight: 800;
  text-decoration: none;
  white-space: nowrap;
}

.helper-note {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  line-height: 1.6;
}

.state-message,
.error-message {
  border: 1px dashed var(--zs-color-border);
  border-radius: 8px;
  padding: 14px;
  color: var(--zs-color-text-muted);
  line-height: 1.6;
  text-align: center;
}

.state-message.compact {
  padding: 12px;
}

.error-message {
  border-color: var(--zs-color-danger);
  color: var(--zs-color-danger);
}

.section-block {
  display: grid;
  gap: 10px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.section-head h3 {
  color: var(--zs-color-text);
  font-size: 0.95rem;
}

.count-pill {
  min-width: 28px;
  border-radius: 999px;
  padding: 3px 8px;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
  font-size: 0.75rem;
  font-weight: 800;
  text-align: center;
}

.event-list,
.sequence-list,
.connection-list {
  display: grid;
  gap: 10px;
}

.event-card,
.sequence-card,
.connection-card {
  display: grid;
  gap: 10px;
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  padding: 12px;
  background: var(--zs-color-surface);
}

.event-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.track-label {
  color: var(--zs-color-text-muted);
  font-size: 0.76rem;
  font-weight: 800;
}

.event-card h4 {
  margin: 2px 0 0;
  color: var(--zs-color-text);
  font-size: 0.95rem;
}

.time-pill {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 4px 8px;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
  font-size: 0.74rem;
  font-weight: 800;
  text-align: center;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.meta-grid div {
  display: grid;
  gap: 4px;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: 8px;
  padding: 10px;
  background: var(--zs-color-bg);
}

.field-label {
  color: var(--zs-color-text-muted);
  font-size: 0.76rem;
  font-weight: 800;
}

.meta-grid strong {
  color: var(--zs-color-text);
  font-size: 0.88rem;
}

.event-meta {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
}

.event-description {
  color: var(--zs-color-text);
  font-size: 0.83rem;
  line-height: 1.7;
  white-space: pre-wrap;
}

.sequence-title {
  color: var(--zs-color-text);
  font-size: 0.9rem;
  font-weight: 800;
}

.sequence-line {
  color: var(--zs-color-text-muted);
  font-size: 0.8rem;
  line-height: 1.6;
}

.sequence-line span {
  margin-right: 8px;
  color: var(--zs-color-text-muted);
  font-weight: 800;
}

.connection-head {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.edge-label,
.temporal-pill,
.visibility-pill {
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 0.74rem;
  font-weight: 800;
}

.edge-label {
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-info);
}

.temporal-pill {
  background: var(--zs-color-warning-soft);
  color: var(--zs-color-warning);
}

.visibility-pill {
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-text-muted);
}

.connection-title {
  color: var(--zs-color-text);
  font-size: 0.88rem;
  font-weight: 800;
}

.connection-note {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  line-height: 1.6;
  white-space: pre-wrap;
}

@media (max-width: 900px) {
  .meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>
