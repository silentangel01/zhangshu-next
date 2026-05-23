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

type ContextKind = 'outline' | 'characters' | 'settings' | 'clues' | 'timeline' | 'graph'
type SummaryItem = { id: string; title: string; meta: string; body: string }
type BriefItem = { id: string; text: string }

const props = defineProps<{
  projectId: string
  chapterId: string | null
  kind: ContextKind
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
  outline: '大纲',
  characters: '人物',
  settings: '设定',
  clues: '伏笔',
  timeline: '时间轴',
  graph: '关系图',
}

const actionMap = computed<Record<ContextKind, { label: string; to: string }>>(() => ({
  outline: { label: '完整大纲', to: `/projects/${props.projectId}/outlines` },
  characters: { label: '人物库', to: `/projects/${props.projectId}/characters` },
  settings: { label: '设定集', to: `/projects/${props.projectId}/settings` },
  clues: { label: '伏笔库', to: `/projects/${props.projectId}/clues` },
  timeline: { label: '完整时间轴', to: `/projects/${props.projectId}/timeline` },
  graph: { label: '完整关系图', to: `/projects/${props.projectId}/graph` },
}))

const emptyStateMap: Record<ContextKind, string> = {
  outline: '本章暂无细纲',
  characters: '本章暂无人物',
  settings: '本章暂无设定',
  clues: '本章暂无伏笔',
  timeline: '本章暂无时间轴事件',
  graph: '本章暂无关系图摘要',
}

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

const directItems = computed<SummaryItem[]>(() => {
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
          (matchedNodeIds.value.has(edge.from_node_id) || matchedNodeIds.value.has(edge.to_node_id)),
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

function timeLabel(event: TimelineEvent) {
  return [event.story_date, event.story_time].filter(Boolean).join(' ') || '未填写时间'
}

function trackTitle(trackId: string | null) {
  return trackId ? trackMap.value[trackId]?.title ?? '未分配轨道' : '未分配轨道'
}

function eventTitle(eventId: string) {
  return chapterEvents.value.find((event) => event.id === eventId)?.title ?? '未知事件'
}

function nodeTitle(nodeId: string) {
  return graphNodes.value.find((node) => node.id === nodeId)?.title ?? '未知节点'
}

function outlineStatusLabel(value: string) {
  return ({ planned: '计划中', writing: '写作中', done: '已完成', abandoned: '已废弃' } as Record<string, string>)[value] ?? value
}

function outlineImportanceLabel(value: string) {
  return ({ normal: '普通', important: '重要', critical: '关键' } as Record<string, string>)[value] ?? value
}

function chapterCharacterRelationLabel(value: string) {
  return ({ appears: '出场', mentioned: '提及', pov: '视角', conflict: '冲突', supports: '支援' } as Record<string, string>)[value] ?? value
}

function characterRoleLabel(value: string) {
  return ({ protagonist: '主角', deuteragonist: '副主角', antagonist: '反派', supporting: '配角', minor: '次要角色', unknown: '未知' } as Record<string, string>)[value] ?? value
}

function settingTypeLabel(value: string) {
  return ({ world: '世界', location: '地点', organization: '组织', power_system: '体系', history: '历史', technology: '技术', rule: '规则', race: '种族', object: '物品', custom: '自定义' } as Record<string, string>)[value] ?? value
}

function settingStatusLabel(value: string) {
  return ({ draft: '草稿', confirmed: '已定稿', deprecated: '已废弃', conflicted: '有冲突' } as Record<string, string>)[value] ?? value
}

function chapterClueRelationLabel(value: string) {
  return ({ setup: '埋设', mention: '提及', develop: '推进', payoff: '回收', related: '相关' } as Record<string, string>)[value] ?? value
}

function clueStatusLabel(value: string) {
  return ({ planned: '计划中', planted: '已埋设', developing: '推进中', resolved: '已回收', abandoned: '已废弃' } as Record<string, string>)[value] ?? value
}

function temporalRelationLabel(value: string) {
  return ({ previous: '前置', parallel: '并行', delayed: '滞后', future: '后续', unordered: '无明确时序' } as Record<string, string>)[value] ?? value
}

function graphNodeTypeLabel(value: string) {
  return ({ character: '人物', setting: '设定', clue: '伏笔', timeline_event: '时间轴事件', organization: '组织', location: '地点', custom: '自定义' } as Record<string, string>)[value] ?? value
}

function graphEdgeRelationLabel(value: string) {
  return ({ relationship: '关系', conflict: '冲突', ally: '同盟', family: '亲属', belongs_to: '归属', controls: '控制', clue_related: '伏笔相关', timeline_related: '时间轴相关', setting_related: '设定相关', cause: '因果', custom: '自定义' } as Record<string, string>)[value] ?? value
}
</script>

<template>
  <section class="chapter-context-summary">
    <header class="context-header">
      <div>
        <p class="eyebrow">写作辅助</p>
        <h2>{{ titleMap[kind] }}</h2>
      </div>
      <RouterLink v-if="chapterId" class="context-link" :to="actionMap[kind].to">
        {{ actionMap[kind].label }}
      </RouterLink>
    </header>

    <p v-if="!chapterId" class="state-message">请选择章节后查看写作资料。</p>
    <p v-else-if="isLoading" class="state-message">正在加载章节资料...</p>
    <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>

    <template v-else>
      <p class="subtle-note">当前写作辅助基于手动绑定资料生成。</p>

      <ChapterContextSection
        :title="kind === 'outline' ? '本章细纲' : kind === 'timeline' ? '本章时间轴事件' : kind === 'graph' ? '本章核心关系摘要' : `本章${titleMap[kind]}`"
        :count="directItems.length"
      >
        <p v-if="directItems.length === 0" class="state-message compact">
          {{ emptyStateMap[kind] }}
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
  </section>
</template>

<style scoped>
.chapter-context-summary {
  display: grid;
  gap: 14px;
}

.context-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.eyebrow,
h2,
h4,
p {
  margin: 0;
}

.eyebrow {
  color: var(--zs-color-text-muted);
  font-size: 0.75rem;
  font-weight: 800;
}

h2 {
  color: var(--zs-color-text);
  font-size: 1rem;
}

.context-link {
  color: var(--zs-color-primary);
  font-size: 0.8rem;
  font-weight: 800;
  text-decoration: none;
  white-space: nowrap;
}

.subtle-note,
.maintenance-hint {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  line-height: 1.6;
}

.card-list {
  display: grid;
  gap: 10px;
}

.context-card {
  display: grid;
  gap: 6px;
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  padding: 11px;
  background: var(--zs-color-surface);
}

.context-card h4 {
  color: var(--zs-color-text);
  font-size: 0.9rem;
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
  border: 1px dashed var(--zs-color-border);
  border-radius: 8px;
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
