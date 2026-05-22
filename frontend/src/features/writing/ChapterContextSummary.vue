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
import { listChapterTimelineEvents, listProjectTimelineEvents, listTimelineEdges, listTimelineTracks } from '@/entities/timeline/api'
import type { TimelineEdge, TimelineEvent, TimelineTrack } from '@/entities/timeline/types'

import ChapterContextSection from './ChapterContextSection.vue'

type ContextKind = 'outline' | 'characters' | 'settings' | 'clues' | 'timeline' | 'graph'
type CardItem = { id: string; title: string; meta: string; body: string }
type HintItem = { id: string; text: string }

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
const projectEvents = ref<TimelineEvent[]>([])
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

const trackMap = computed(() => mapById(tracks.value))
const eventMap = computed(() => mapById(projectEvents.value))
const nodeMap = computed(() => mapById(graphNodes.value))

const chapterTargetKeys = computed(() => {
  const keys = new Set<string>()
  characters.value.forEach((link) => keys.add(`character:${link.character_id}`))
  settings.value.forEach((link) => keys.add(`setting:${link.setting_item_id}`))
  clues.value.forEach((link) => keys.add(`clue:${link.clue_id}`))
  chapterEvents.value.forEach((event) => keys.add(`timeline_event:${event.id}`))
  return keys
})

const matchedGraphNodes = computed(() =>
  graphNodes.value.filter((node) =>
    node.visibility !== 'hidden'
    && node.bound_type
    && node.bound_id
    && chapterTargetKeys.value.has(`${node.bound_type}:${node.bound_id}`),
  ),
)

const matchedNodeIds = computed(() => new Set(matchedGraphNodes.value.map((node) => node.id)))

const directItems = computed<CardItem[]>(() => {
  if (props.kind === 'outline') {
    return outlines.value.map((outline) => ({
      id: outline.id,
      title: outline.title,
      meta: `${outlineTypeLabel(outline.item_type)}｜${outlineStatusLabel(outline.status)}｜${outlineImportanceLabel(outline.importance)}`,
      body: preview(outline.content),
    }))
  }
  if (props.kind === 'characters') {
    return characters.value.map((link) => ({
      id: link.id,
      title: link.character.name,
      meta: `${chapterCharacterRelationLabel(link.relation_type)}｜${characterRoleLabel(link.character.role)}｜${importanceLabel(link.character.importance)}｜${characterStatusLabel(link.character.status)}`,
      body: preview(link.character.summary || link.note),
    }))
  }
  if (props.kind === 'settings') {
    return settings.value.map((link) => ({
      id: link.id,
      title: link.setting_item.title,
      meta: `${settingTypeLabel(link.setting_item.item_type)}｜${settingStatusLabel(link.setting_item.canon_status)}｜${importanceLabel(link.setting_item.importance)}`,
      body: preview(link.setting_item.summary || link.note),
    }))
  }
  if (props.kind === 'clues') {
    return clues.value.map((link) => ({
      id: link.id,
      title: link.clue.title,
      meta: `${chapterClueRelationLabel(link.relation_type)}｜${clueStatusLabel(link.clue.status)}｜${clueVisibilityLabel(link.clue.visibility)}｜${importanceLabel(link.clue.importance)}`,
      body: preview(link.clue.description || link.clue.payoff_plan || link.note),
    }))
  }
  if (props.kind === 'timeline') {
    return chapterEvents.value.map((event) => ({
      id: event.id,
      title: event.title,
      meta: `${trackTitle(event.track_id)}｜${timeLabel(event)}｜${importanceLabel(event.importance)}`,
      body: preview(event.description || event.note),
    }))
  }
  return matchedGraphNodes.value.slice(0, 8).map((node) => ({
    id: node.id,
    title: node.title,
    meta: `${graphNodeTypeLabel(node.node_type)}｜${boundTypeLabel(node.bound_type)}`,
    body: preview(node.summary),
  }))
})

const secondaryItems = computed<HintItem[]>(() => {
  if (props.kind === 'outline') {
    return outlines.value.map((outline) => ({
      id: outline.id,
      text: `${outline.title}：${outlineStatusLabel(outline.status)}`,
    }))
  }
  if (props.kind === 'timeline') {
    return timelineConnectionItems.value
  }
  if (props.kind === 'graph') {
    return graphEdgeItems.value.slice(0, 8)
  }
  return []
})

const compactHint = computed(() => {
  if (props.kind === 'outline') {
    return `已关联资料：人物 ${characters.value.length}、设定 ${settings.value.length}、伏笔 ${clues.value.length}`
  }
  if (props.kind === 'characters') return '关联资料可在人物库中维护。'
  if (props.kind === 'settings') return '关联资料可在设定集中维护。'
  if (props.kind === 'clues') return '关联资料可在伏笔库中维护。'
  if (props.kind === 'timeline') return '人物、设定和伏笔关联可在完整时间轴中维护。'
  return `本章相关节点 ${matchedGraphNodes.value.length} 个，直接关系 ${graphEdgeItems.value.length} 条。`
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
      allEvents,
      timelineTracks,
      edges,
      nodes,
      graphRelations,
    ] = await Promise.all([
      listChapterOutlines(props.chapterId),
      listChapterCharacters(props.chapterId),
      listChapterSettings(props.chapterId),
      listChapterClues(props.chapterId),
      listChapterTimelineEvents(props.chapterId),
      listProjectTimelineEvents(props.projectId),
      listTimelineTracks(props.projectId),
      listTimelineEdges(props.projectId),
      listGraphNodes(props.projectId),
      listGraphEdges(props.projectId),
    ])

    if (token !== loadToken) return

    outlines.value = chapterOutlines
    characters.value = chapterCharacters
    settings.value = chapterSettings
    clues.value = chapterClues
    chapterEvents.value = events
    projectEvents.value = allEvents
    tracks.value = timelineTracks
    timelineEdges.value = edges
    graphNodes.value = nodes
    graphEdges.value = graphRelations
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
  graphNodes.value = []
  graphEdges.value = []
}

const timelineConnectionItems = computed<HintItem[]>(() => {
  const ids = new Set(chapterEvents.value.map((event) => event.id))
  return timelineEdges.value
    .filter((edge) => edge.visibility !== 'hidden' && (ids.has(edge.from_event_id) || ids.has(edge.to_event_id)))
    .slice(0, 8)
    .map((edge) => ({
      id: edge.id,
      text: `${titleOf(eventMap.value[edge.from_event_id])} → ${titleOf(eventMap.value[edge.to_event_id])}｜${temporalRelationLabel(edge.temporal_relation)}`,
    }))
})

const graphEdgeItems = computed<HintItem[]>(() =>
  graphEdges.value
    .filter((edge) => edge.visibility !== 'hidden' && (matchedNodeIds.value.has(edge.from_node_id) || matchedNodeIds.value.has(edge.to_node_id)))
    .map((edge) => ({
      id: edge.id,
      text: `${titleOf(nodeMap.value[edge.from_node_id])} → ${titleOf(nodeMap.value[edge.to_node_id])}｜${graphEdgeRelationLabel(edge.relation_type)}`,
    })),
)

function mapById<T extends { id: string }>(items: T[]) {
  return items.reduce<Record<string, T>>((acc, item) => {
    acc[item.id] = item
    return acc
  }, {})
}

function titleOf(item: { title: string } | undefined) {
  return item?.title ?? '未知'
}

function preview(text: string | null | undefined) {
  const source = (text ?? '').trim()
  if (!source) return '暂无摘要'
  return source.length > 72 ? `${source.slice(0, 72)}...` : source
}

function timeLabel(event: TimelineEvent) {
  return [event.story_date, event.story_time].filter(Boolean).join('｜') || '未填写时间'
}

function trackTitle(trackId: string | null) {
  return trackId ? trackMap.value[trackId]?.title ?? '未分配轨道' : '未分配轨道'
}

function outlineTypeLabel(value: string) {
  return ({ book_outline: '全书大纲', volume_outline: '分卷大纲', chapter_outline: '章节细纲', scene: '场景', plot_point: '关键剧情点', note: '备注' } as Record<string, string>)[value] ?? value
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
  return ({ protagonist: '主角', deuteragonist: '副主角', antagonist: '反派', supporting: '配角', minor: '小角色', unknown: '未知' } as Record<string, string>)[value] ?? value
}

function characterStatusLabel(value: string) {
  return ({ active: '活跃', inactive: '暂不活跃', dead: '死亡', missing: '失踪', unknown: '未知' } as Record<string, string>)[value] ?? value
}

function settingTypeLabel(value: string) {
  return ({ world: '世界', location: '地点', organization: '组织', power_system: '力量体系', history: '历史', technology: '技术', rule: '规则', race: '种族', object: '物品', custom: '自定义' } as Record<string, string>)[value] ?? value
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

function clueVisibilityLabel(value: string) {
  return ({ hidden: '隐藏', hinted: '暗示', revealed: '已揭示' } as Record<string, string>)[value] ?? value
}

function importanceLabel(value: string) {
  return ({ low: '低', normal: '普通', high: '重要', critical: '核心' } as Record<string, string>)[value] ?? value
}

function temporalRelationLabel(value: string) {
  return ({ previous: '过去 / 前置', parallel: '并行', delayed: '滞后', future: '后续', unordered: '无明确时序' } as Record<string, string>)[value] ?? value
}

function graphNodeTypeLabel(value: string) {
  return ({ character: '人物', setting: '设定', clue: '伏笔', timeline_event: '时间轴事件', organization: '组织', location: '地点', custom: '自定义' } as Record<string, string>)[value] ?? value
}

function boundTypeLabel(value: string | null) {
  return value ? graphNodeTypeLabel(value) : '未绑定'
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
        :title="kind === 'outline' ? '本章细纲' : kind === 'timeline' ? '本章时间轴事件' : kind === 'graph' ? '本章相关节点' : `本章${titleMap[kind]}`"
        :count="directItems.length"
      >
        <p v-if="directItems.length === 0" class="state-message compact">本章暂无相关资料。</p>
        <div v-else class="card-list">
          <article v-for="item in directItems" :key="item.id" class="context-card">
            <h4>{{ item.title }}</h4>
            <p class="meta">{{ item.meta }}</p>
            <p class="body">{{ item.body }}</p>
          </article>
        </div>
      </ChapterContextSection>

      <ChapterContextSection
        v-if="kind === 'outline' || kind === 'timeline' || kind === 'graph'"
        :title="kind === 'outline' ? '大纲条目状态' : kind === 'timeline' ? '前后 / 并行事件' : '直接关系'"
        :count="secondaryItems.length"
      >
        <p v-if="secondaryItems.length === 0" class="state-message compact">暂无可显示内容。</p>
        <ul v-else class="compact-list">
          <li v-for="item in secondaryItems" :key="item.id">{{ item.text }}</li>
        </ul>
      </ChapterContextSection>

      <p class="compact-hint">{{ compactHint }}</p>

      <ChapterContextSection title="完整资料库">
        <RouterLink class="full-link" :to="actionMap[kind].to">{{ actionMap[kind].label }}</RouterLink>
      </ChapterContextSection>
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
  color: #64748b;
  font-size: 0.75rem;
  font-weight: 800;
}

h2 {
  color: #111827;
  font-size: 1rem;
}

.context-link,
.full-link {
  color: #2563eb;
  font-size: 0.8rem;
  font-weight: 800;
  text-decoration: none;
  white-space: nowrap;
}

.subtle-note,
.compact-hint {
  color: #64748b;
  font-size: 0.78rem;
  line-height: 1.6;
}

.compact-hint {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 9px 10px;
  background: #f8fafc;
}

.card-list {
  display: grid;
  gap: 10px;
}

.context-card {
  display: grid;
  gap: 6px;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 11px;
  background: #ffffff;
}

.context-card h4 {
  color: #111827;
  font-size: 0.9rem;
}

.meta {
  color: #64748b;
  font-size: 0.78rem;
}

.body {
  color: #334155;
  font-size: 0.82rem;
  line-height: 1.65;
}

.compact-list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding-left: 18px;
  color: #334155;
  font-size: 0.82rem;
  line-height: 1.55;
}

.state-message,
.error-message {
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 14px;
  color: #64748b;
  line-height: 1.6;
  text-align: center;
}

.state-message.compact {
  padding: 11px;
}

.error-message {
  border-color: #fecaca;
  color: #b42318;
}

.full-link {
  justify-self: start;
}
</style>
