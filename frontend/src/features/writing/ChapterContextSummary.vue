<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { listChapterCharacters } from '@/entities/chapter-character/api'
import type { ChapterCharacterLink } from '@/entities/chapter-character/types'
import { listChapterClues } from '@/entities/chapter-clue/api'
import type { ChapterClueLink } from '@/entities/chapter-clue/types'
import { listChapterSettings } from '@/entities/chapter-setting/api'
import type { ChapterSettingLink } from '@/entities/chapter-setting/types'
import { listGraphEdges, listGraphNodes } from '@/entities/graph/api'
import type { GraphEdge, GraphNode } from '@/entities/graph/types'
import { listChapterOutlines } from '@/entities/outline/api'
import type { OutlineItem } from '@/entities/outline/types'
import {
  listChapterTimelineEvents,
  listTimelineEdges,
  listTimelineTracks,
} from '@/entities/timeline/api'
import type { TimelineEdge, TimelineEvent, TimelineTrack } from '@/entities/timeline/types'

import ChapterContextSection from './ChapterContextSection.vue'

type ContextKind =
  | 'overview'
  | 'outline'
  | 'characters'
  | 'settings'
  | 'clues'
  | 'timeline'
  | 'graph'
type MaterialContextKind = Exclude<ContextKind, 'overview'>
type SummaryItem = { id: string; title: string; meta: string; body: string }
type BriefItem = { id: string; text: string }
type OverviewGroup = {
  kind: MaterialContextKind
  label: string
  count: number
  detail: string
}

const props = defineProps<{
  projectId: string
  chapterId: string | null
  kind: ContextKind
}>()

const emit = defineEmits<{
  selectContext: [kind: MaterialContextKind]
}>()

const isLoading = ref(false)
const errorMessage = ref('')
const outlines = ref<OutlineItem[]>([])
const characters = ref<ChapterCharacterLink[]>([])
const settings = ref<ChapterSettingLink[]>([])
const clues = ref<ChapterClueLink[]>([])
const chapterEvents = ref<TimelineEvent[]>([])
const tracks = ref<TimelineTrack[]>([])
const timelineEdges = ref<TimelineEdge[]>([])
const graphNodes = ref<GraphNode[]>([])
const graphEdges = ref<GraphEdge[]>([])

let loadToken = 0

const titleMap: Record<ContextKind, string> = {
  overview: '资料联动',
  outline: '大纲',
  characters: '人物',
  settings: '设定',
  clues: '伏笔',
  timeline: '时间轴',
  graph: '关系图',
}

const actionMap = computed<Record<MaterialContextKind, { label: string; to: string }>>(() => ({
  outline: { label: '完整大纲', to: `/projects/${props.projectId}/outlines` },
  characters: { label: '人物库', to: `/projects/${props.projectId}/characters` },
  settings: { label: '设定集', to: `/projects/${props.projectId}/settings` },
  clues: { label: '伏笔库', to: `/projects/${props.projectId}/clues` },
  timeline: { label: '完整时间轴', to: `/projects/${props.projectId}/timeline` },
  graph: { label: '完整关系图', to: `/projects/${props.projectId}/graph` },
}))

const emptyStateMap: Record<MaterialContextKind, string> = {
  outline: '本章暂无细纲',
  characters: '本章暂无人物',
  settings: '本章暂无设定',
  clues: '本章暂无伏笔',
  timeline: '本章暂无时间轴事件',
  graph: '本章暂无关系图摘要',
}

const contextAction = computed(() =>
  props.kind === 'overview' ? null : actionMap.value[props.kind],
)

const activeEmptyState = computed(() =>
  props.kind === 'overview' ? '' : emptyStateMap[props.kind],
)

const trackMap = computed(() => mapById(tracks.value))

const chapterTargetKeys = computed(() => {
  const keys = new Set<string>()
  characters.value.forEach((link) => keys.add(`character:${link.character_id}`))
  settings.value.forEach((link) => keys.add(`setting:${link.setting_item_id}`))
  clues.value.forEach((link) => keys.add(`clue:${link.clue_id}`))
  chapterEvents.value.forEach((event) => keys.add(`timeline_event:${event.id}`))
  return keys
})

const matchedGraphNodes = computed(() =>
  graphNodes.value.filter((node) => {
    if (node.visibility === 'hidden' || !node.bound_type || !node.bound_id) {
      return false
    }
    return chapterTargetKeys.value.has(`${node.bound_type}:${node.bound_id}`)
  }),
)

const matchedNodeIds = computed(() => new Set(matchedGraphNodes.value.map((node) => node.id)))

const overviewGroups = computed<OverviewGroup[]>(() => [
  {
    kind: 'outline',
    label: '细纲',
    count: outlines.value.length,
    detail: compactNames(outlines.value.map((item) => item.title)),
  },
  {
    kind: 'characters',
    label: '人物',
    count: characters.value.length,
    detail: compactNames(characters.value.map((item) => item.character.name)),
  },
  {
    kind: 'settings',
    label: '设定',
    count: settings.value.length,
    detail: compactNames(settings.value.map((item) => item.setting_item.title)),
  },
  {
    kind: 'clues',
    label: '伏笔',
    count: clues.value.length,
    detail: compactNames(clues.value.map((item) => item.clue.title)),
  },
  {
    kind: 'timeline',
    label: '时间',
    count: chapterEvents.value.length,
    detail: compactNames(chapterEvents.value.map((item) => item.title)),
  },
  {
    kind: 'graph',
    label: '关系',
    count: matchedGraphNodes.value.length,
    detail: compactNames(matchedGraphNodes.value.map((item) => item.title || '未命名节点')),
  },
])

const linkedOverviewGroupCount = computed(
  () => overviewGroups.value.filter((group) => group.count > 0).length,
)

const missingOverviewGroups = computed(() =>
  overviewGroups.value.filter((group) => group.count === 0),
)

const directItems = computed<SummaryItem[]>(() => {
  if (props.kind === 'overview') {
    return []
  }

  if (props.kind === 'outline') {
    return outlines.value.map((outline) => ({
      id: outline.id,
      title: outline.title,
      meta: `${outlineStatusLabel(outline.status)}｜${outlineImportanceLabel(outline.importance)}`,
      body: preview(outline.content),
    }))
  }

  if (props.kind === 'characters') {
    return characters.value.map((link) => ({
      id: link.id,
      title: link.character.name,
      meta: `${chapterCharacterRelationLabel(link.relation_type)}｜${characterRoleLabel(link.character.role)}`,
      body: preview(link.note || link.character.summary),
    }))
  }

  if (props.kind === 'settings') {
    return settings.value.map((link) => ({
      id: link.id,
      title: link.setting_item.title,
      meta: `${settingTypeLabel(link.setting_item.item_type)}｜${settingStatusLabel(link.setting_item.canon_status)}`,
      body: preview(link.note || link.setting_item.summary),
    }))
  }

  if (props.kind === 'clues') {
    return clues.value.map((link) => ({
      id: link.id,
      title: link.clue.title,
      meta: `${chapterClueRelationLabel(link.relation_type)}｜${clueStatusLabel(link.clue.status)}`,
      body: preview(link.clue.payoff_plan || link.clue.description || link.note),
    }))
  }

  if (props.kind === 'timeline') {
    return chapterEvents.value.map((event) => ({
      id: event.id,
      title: event.title,
      meta: `${trackTitle(event.track_id)}｜${timeLabel(event)}`,
      body: preview(event.note || event.description),
    }))
  }

  return matchedGraphNodes.value.slice(0, 6).map((node) => ({
    id: node.id,
    title: node.title || '未命名节点',
    meta: graphNodeTypeLabel(node.node_type),
    body: preview(node.summary),
  }))
})

const secondaryItems = computed<BriefItem[]>(() => {
  if (props.kind === 'timeline') {
    const eventIds = new Set(chapterEvents.value.map((event) => event.id))
    return timelineEdges.value
      .filter(
        (edge) =>
          edge.visibility !== 'hidden' &&
          (eventIds.has(edge.from_event_id) || eventIds.has(edge.to_event_id)),
      )
      .slice(0, 6)
      .map((edge) => ({
        id: edge.id,
        text: `${eventTitle(edge.from_event_id)} → ${eventTitle(edge.to_event_id)}｜${temporalRelationLabel(edge.temporal_relation)}`,
      }))
  }

  if (props.kind === 'graph') {
    return graphEdges.value
      .filter(
        (edge) =>
          edge.visibility !== 'hidden' &&
          (matchedNodeIds.value.has(edge.from_node_id) ||
            matchedNodeIds.value.has(edge.to_node_id)),
      )
      .slice(0, 6)
      .map((edge) => ({
        id: edge.id,
        text: `${nodeTitle(edge.from_node_id)} → ${nodeTitle(edge.to_node_id)}｜${graphEdgeRelationLabel(edge.relation_type)}`,
      }))
  }

  return []
})

const graphSummaryText = computed(() => {
  if (props.kind !== 'graph') {
    return ''
  }
  return `本章相关节点 ${matchedGraphNodes.value.length} 个，直接关系 ${secondaryItems.value.length} 条`
})

watch(
  () => [props.projectId, props.chapterId, props.kind],
  () => {
    void refresh()
  },
  { immediate: true },
)

async function refresh() {
  const token = ++loadToken
  if (!props.projectId || !props.chapterId) {
    clearState()
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    const [
      chapterOutlines,
      chapterCharacters,
      chapterSettings,
      chapterClues,
      events,
      timelineTracks,
      edges,
      nodes,
      relations,
    ] = await Promise.all([
      listChapterOutlines(props.chapterId),
      listChapterCharacters(props.chapterId),
      listChapterSettings(props.chapterId),
      listChapterClues(props.chapterId),
      listChapterTimelineEvents(props.chapterId),
      listTimelineTracks(props.projectId),
      listTimelineEdges(props.projectId),
      listGraphNodes(props.projectId),
      listGraphEdges(props.projectId),
    ])

    if (token !== loadToken) {
      return
    }

    outlines.value = chapterOutlines
    characters.value = chapterCharacters
    settings.value = chapterSettings
    clues.value = chapterClues
    chapterEvents.value = events
    tracks.value = timelineTracks
    timelineEdges.value = edges
    graphNodes.value = nodes
    graphEdges.value = relations
  } catch (error) {
    void error
    if (token === loadToken) {
      errorMessage.value = '章节资料加载失败，请稍后重试。'
    }
  } finally {
    if (token === loadToken) {
      isLoading.value = false
    }
  }
}

function clearState() {
  isLoading.value = false
  errorMessage.value = ''
  outlines.value = []
  characters.value = []
  settings.value = []
  clues.value = []
  chapterEvents.value = []
  tracks.value = []
  timelineEdges.value = []
  graphNodes.value = []
  graphEdges.value = []
}

function mapById<T extends { id: string }>(items: T[]) {
  return items.reduce<Record<string, T>>((acc, item) => {
    acc[item.id] = item
    return acc
  }, {})
}

function preview(text: string | null | undefined) {
  const source = (text ?? '').trim()
  if (!source) return '暂无摘要'
  return source.length > 60 ? `${source.slice(0, 60)}...` : source
}

function compactNames(names: string[]) {
  if (names.length === 0) {
    return '尚未关联'
  }

  const visibleNames = names.slice(0, 2).join('、')
  return names.length > 2 ? `${visibleNames} 等 ${names.length} 项` : visibleNames
}

function timeLabel(event: TimelineEvent) {
  return [event.story_date, event.story_time].filter(Boolean).join(' ') || '未填写时间'
}

function trackTitle(trackId: string | null) {
  return trackId ? (trackMap.value[trackId]?.title ?? '未分配轨道') : '未分配轨道'
}

function eventTitle(eventId: string) {
  return chapterEvents.value.find((event) => event.id === eventId)?.title ?? '未知事件'
}

function nodeTitle(nodeId: string) {
  return graphNodes.value.find((node) => node.id === nodeId)?.title ?? '未知节点'
}

function outlineStatusLabel(value: string) {
  return (
    (
      { planned: '计划中', writing: '写作中', done: '已完成', abandoned: '已废弃' } as Record<
        string,
        string
      >
    )[value] ?? value
  )
}

function outlineImportanceLabel(value: string) {
  return (
    ({ normal: '普通', important: '重要', critical: '关键' } as Record<string, string>)[value] ??
    value
  )
}

function chapterCharacterRelationLabel(value: string) {
  return (
    (
      {
        appears: '出场',
        mentioned: '提及',
        pov: '视角',
        conflict: '冲突',
        supports: '支援',
      } as Record<string, string>
    )[value] ?? value
  )
}

function characterRoleLabel(value: string) {
  return (
    (
      {
        protagonist: '主角',
        deuteragonist: '副主角',
        antagonist: '反派',
        supporting: '配角',
        minor: '次要角色',
        unknown: '未知',
      } as Record<string, string>
    )[value] ?? value
  )
}

function settingTypeLabel(value: string) {
  return (
    (
      {
        world: '世界',
        location: '地点',
        organization: '组织',
        power_system: '体系',
        history: '历史',
        technology: '技术',
        rule: '规则',
        race: '种族',
        object: '物品',
        custom: '自定义',
      } as Record<string, string>
    )[value] ?? value
  )
}

function settingStatusLabel(value: string) {
  return (
    (
      { draft: '草稿', confirmed: '已定稿', deprecated: '已废弃', conflicted: '有冲突' } as Record<
        string,
        string
      >
    )[value] ?? value
  )
}

function chapterClueRelationLabel(value: string) {
  return (
    (
      {
        setup: '埋设',
        mention: '提及',
        develop: '推进',
        payoff: '回收',
        related: '相关',
      } as Record<string, string>
    )[value] ?? value
  )
}

function clueStatusLabel(value: string) {
  return (
    (
      {
        planned: '计划中',
        planted: '已埋设',
        developing: '推进中',
        resolved: '已回收',
        abandoned: '已废弃',
      } as Record<string, string>
    )[value] ?? value
  )
}

function temporalRelationLabel(value: string) {
  return (
    (
      {
        previous: '前置',
        parallel: '并行',
        delayed: '滞后',
        future: '后续',
        unordered: '无明确时序',
      } as Record<string, string>
    )[value] ?? value
  )
}

function graphNodeTypeLabel(value: string) {
  return (
    (
      {
        character: '人物',
        setting: '设定',
        clue: '伏笔',
        timeline_event: '时间轴事件',
        organization: '组织',
        location: '地点',
        custom: '自定义',
      } as Record<string, string>
    )[value] ?? value
  )
}

function graphEdgeRelationLabel(value: string) {
  return (
    (
      {
        relationship: '关系',
        conflict: '冲突',
        ally: '同盟',
        family: '亲属',
        belongs_to: '归属',
        controls: '控制',
        clue_related: '伏笔相关',
        timeline_related: '时间轴相关',
        setting_related: '设定相关',
        cause: '因果',
        custom: '自定义',
      } as Record<string, string>
    )[value] ?? value
  )
}
</script>

<template>
  <section class="chapter-context-summary">
    <header class="context-header">
      <div>
        <h2>{{ titleMap[kind] }}</h2>
      </div>
      <RouterLink v-if="chapterId && contextAction" class="context-link" :to="contextAction.to">
        {{ contextAction.label }}
      </RouterLink>
    </header>

    <p v-if="!chapterId" class="state-message">请选择章节后查看写作资料。</p>
    <p v-else-if="isLoading" class="state-message">正在加载章节资料...</p>
    <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>

    <template v-else>
      <section v-if="kind === 'overview'" class="overview-panel">
        <p class="overview-status">
          已关联 {{ linkedOverviewGroupCount }} /
          {{ overviewGroups.length }} 类资料。点击分类可查看当前章节的关联内容。
        </p>

        <div class="overview-grid">
          <button
            v-for="group in overviewGroups"
            :key="group.kind"
            type="button"
            class="overview-card"
            :class="{ unlinked: group.count === 0 }"
            @click="emit('selectContext', group.kind)"
          >
            <span class="overview-card-head">
              <span>{{ group.label }}</span>
              <strong>{{ group.count }}</strong>
            </span>
            <span class="overview-card-detail">{{ group.detail }}</span>
          </button>
        </div>

        <div v-if="missingOverviewGroups.length > 0" class="missing-link-note">
          <p>
            可考虑补充本章关联：{{ missingOverviewGroups.map((group) => group.label).join('、') }}
          </p>
          <div class="missing-link-actions">
            <button
              v-for="group in missingOverviewGroups"
              :key="group.kind"
              type="button"
              @click="emit('selectContext', group.kind)"
            >
              查看{{ group.label }}
            </button>
          </div>
        </div>

        <p class="maintenance-hint">关联内容来自章节的显式资料绑定；可在对应资料页维护。</p>
      </section>

      <template v-else>
        <ChapterContextSection
          :title="
            kind === 'outline'
              ? '本章细纲'
              : kind === 'timeline'
                ? '本章时间轴事件'
                : kind === 'graph'
                  ? '本章核心关系摘要'
                  : `本章${titleMap[kind]}`
          "
          :count="directItems.length"
        >
          <p v-if="directItems.length === 0" class="state-message compact">
            {{ activeEmptyState }}
          </p>
          <div v-else class="card-list">
            <article v-for="item in directItems" :key="item.id" class="context-card">
              <h4>{{ item.title }}</h4>
              <p class="meta">{{ item.meta }}</p>
              <p class="body">{{ item.body }}</p>
            </article>
          </div>
        </ChapterContextSection>

        <ChapterContextSection
          v-if="kind === 'timeline' && secondaryItems.length > 0"
          title="时序关系"
          :count="secondaryItems.length"
        >
          <ul class="compact-list">
            <li v-for="item in secondaryItems" :key="item.id">{{ item.text }}</li>
          </ul>
        </ChapterContextSection>

        <ChapterContextSection
          v-if="kind === 'graph'"
          title="直接关系"
          :count="secondaryItems.length"
        >
          <p class="compact-hint">{{ graphSummaryText || '本章暂无关系图摘要' }}</p>
          <ul v-if="secondaryItems.length > 0" class="compact-list">
            <li v-for="item in secondaryItems" :key="item.id">{{ item.text }}</li>
          </ul>
        </ChapterContextSection>

        <p class="maintenance-hint">可在完整资料库中维护。</p>
      </template>
    </template>
  </section>
</template>

<style scoped>
.chapter-context-summary {
  display: grid;
  gap: 12px;
}

.context-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

h2,
h4,
p {
  margin: 0;
}

h2 {
  color: var(--zs-color-text);
  font-size: 1rem;
}

.context-link {
  color: var(--zs-color-primary);
  font-size: 0.8rem;
  font-weight: 600;
  text-decoration: underline;
  text-decoration-color: var(--zs-color-border-strong);
  text-underline-offset: 3px;
  white-space: nowrap;
}

.maintenance-hint {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  line-height: 1.6;
}

.overview-panel {
  display: grid;
  gap: 12px;
}

.overview-status {
  border: 0;
  border-left: 2px solid var(--zs-color-primary);
  border-radius: 0;
  padding: 5px 0 5px 10px;
  background: transparent;
  color: var(--zs-color-text);
  font-size: 0.82rem;
  line-height: 1.6;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0;
  border-top: 1px solid var(--zs-color-border-soft);
}

.overview-card {
  display: grid;
  gap: 5px;
  border: 0;
  border-right: 1px solid var(--zs-color-border-soft);
  border-bottom: 1px solid var(--zs-color-border-soft);
  border-radius: 0;
  padding: 11px 10px;
  background: transparent;
  color: var(--zs-color-text);
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.overview-card:hover {
  background: var(--zs-color-surface-soft);
}

.overview-card.unlinked {
  color: var(--zs-color-text-muted);
}

.overview-card:nth-child(even) {
  border-right: 0;
}

.overview-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.82rem;
  font-weight: 700;
}

.overview-card-head strong {
  min-width: 0;
  padding: 0;
  background: transparent;
  color: var(--zs-color-primary);
  font-size: 0.74rem;
  text-align: center;
}

.overview-card-detail {
  overflow: hidden;
  color: var(--zs-color-text-muted);
  font-size: 0.76rem;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.missing-link-note {
  display: grid;
  gap: 8px;
  border-top: 1px solid var(--zs-color-border);
  border-bottom: 1px solid var(--zs-color-border);
  border-radius: 0;
  padding: 10px 0;
  color: var(--zs-color-text-muted);
  font-size: 0.8rem;
  line-height: 1.6;
}

.missing-link-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.missing-link-actions button {
  border: 0;
  border-radius: 0;
  padding: 2px 0;
  background: transparent;
  color: var(--zs-color-primary);
  cursor: pointer;
  font: inherit;
  font-size: 0.76rem;
  font-weight: 600;
  text-decoration: underline;
  text-decoration-color: var(--zs-color-border-strong);
  text-underline-offset: 3px;
}

.card-list {
  display: grid;
  gap: 10px;
}

.context-card {
  display: grid;
  gap: 5px;
  border: none;
  border-left: 3px solid var(--zs-color-border);
  border-radius: 0;
  padding: 8px 10px 8px 12px;
  background: transparent;
}

.context-card h4 {
  color: var(--zs-color-text);
  font-size: 0.88rem;
  font-weight: 600;
}

.meta {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
}

.body {
  color: var(--zs-color-text);
  font-size: 0.82rem;
  line-height: 1.65;
}

.compact-list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding-left: 18px;
  color: var(--zs-color-text);
  font-size: 0.82rem;
  line-height: 1.55;
}

.compact-hint,
.state-message,
.error-message {
  border: 0;
  border-top: 1px solid var(--zs-color-border-soft);
  border-bottom: 1px solid var(--zs-color-border-soft);
  border-radius: 0;
  padding: 12px;
  color: var(--zs-color-text-muted);
  line-height: 1.6;
  text-align: center;
}

.state-message.compact {
  padding: 11px;
}

.error-message {
  border-color: var(--zs-color-danger);
  color: var(--zs-color-danger);
}
</style>
