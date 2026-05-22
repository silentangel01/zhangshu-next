<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { listChapterCharacters } from '@/entities/chapter-character/api'
import type { ChapterCharacterLink } from '@/entities/chapter-character/types'
import { listChapterClues } from '@/entities/chapter-clue/api'
import type { ChapterClueLink } from '@/entities/chapter-clue/types'
import { listChapterSettings } from '@/entities/chapter-setting/api'
import type { ChapterSettingLink } from '@/entities/chapter-setting/types'
import { listProjectCharacters } from '@/entities/character/api'
import type { Character } from '@/entities/character/types'
import { listProjectClues } from '@/entities/clue/api'
import type { Clue } from '@/entities/clue/types'
import { listGraphEdges, listGraphNodes } from '@/entities/graph/api'
import type { GraphEdge, GraphNode } from '@/entities/graph/types'
import { listProjectOutlines, listChapterOutlines } from '@/entities/outline/api'
import type { OutlineItem } from '@/entities/outline/types'
import { listProjectSettings } from '@/entities/setting/api'
import type { SettingItem } from '@/entities/setting/types'
import { listChapterTimelineEvents, listProjectTimelineEvents, listTimelineEdges, listTimelineTracks } from '@/entities/timeline/api'
import type { TimelineEdge, TimelineEvent, TimelineTrack } from '@/entities/timeline/types'
import {
  listOutlineCharacters,
  listOutlineClues,
  listOutlineSettings,
  listOutlineTimelineEvents,
  listTimelineEventCharacters,
  listTimelineEventClues,
  listTimelineEventSettings,
} from '@/entities/material-links/api'
import type {
  OutlineCharacterLink,
  OutlineClueLink,
  OutlineSettingLink,
  OutlineTimelineEventLink,
  TimelineEventCharacterLink,
  TimelineEventClueLink,
  TimelineEventSettingLink,
} from '@/entities/material-links/types'

import ChapterContextSection from './ChapterContextSection.vue'

type ContextKind = 'outline' | 'characters' | 'settings' | 'clues' | 'timeline' | 'graph'
type RelatedItem = { id: string; label: string; meta?: string }
type Reminder = { id: string; text: string }

const props = defineProps<{
  projectId: string
  chapterId: string | null
  kind: ContextKind
}>()

const isLoading = ref(false)
const errorMessage = ref('')
const chapterOutlines = ref<OutlineItem[]>([])
const projectOutlines = ref<OutlineItem[]>([])
const chapterCharacters = ref<ChapterCharacterLink[]>([])
const chapterSettings = ref<ChapterSettingLink[]>([])
const chapterClues = ref<ChapterClueLink[]>([])
const chapterEvents = ref<TimelineEvent[]>([])
const projectCharacters = ref<Character[]>([])
const projectSettings = ref<SettingItem[]>([])
const projectClues = ref<Clue[]>([])
const projectEvents = ref<TimelineEvent[]>([])
const timelineTracks = ref<TimelineTrack[]>([])
const timelineEdges = ref<TimelineEdge[]>([])
const graphNodes = ref<GraphNode[]>([])
const graphEdges = ref<GraphEdge[]>([])
const outlineCharacterLinks = ref<OutlineCharacterLink[]>([])
const outlineSettingLinks = ref<OutlineSettingLink[]>([])
const outlineClueLinks = ref<OutlineClueLink[]>([])
const outlineEventLinks = ref<OutlineTimelineEventLink[]>([])
const eventCharacterLinks = ref<TimelineEventCharacterLink[]>([])
const eventSettingLinks = ref<TimelineEventSettingLink[]>([])
const eventClueLinks = ref<TimelineEventClueLink[]>([])

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

const characterMap = computed(() => mapById(projectCharacters.value))
const settingMap = computed(() => mapById(projectSettings.value))
const clueMap = computed(() => mapById(projectClues.value))
const eventMap = computed(() => mapById(projectEvents.value))
const trackMap = computed(() => mapById(timelineTracks.value))
const nodeMap = computed(() => mapById(graphNodes.value))

const directItems = computed(() => {
  switch (props.kind) {
    case 'outline':
      return chapterOutlines.value.map((outline) => ({
        id: outline.id,
        title: outline.title,
        meta: `${outlineTypeLabel(outline.item_type)}｜${outlineStatusLabel(outline.status)}｜${outlineImportanceLabel(outline.importance)}`,
        body: preview(outline.content),
      }))
    case 'characters':
      return chapterCharacters.value.map((link) => ({
        id: link.id,
        title: link.character.name,
        meta: `${characterRoleLabel(link.character.role)}｜${chapterCharacterRelationLabel(link.relation_type)}`,
        body: preview(link.character.summary || link.note),
      }))
    case 'settings':
      return chapterSettings.value.map((link) => ({
        id: link.id,
        title: link.setting_item.title,
        meta: `${settingTypeLabel(link.setting_item.item_type)}｜${settingStatusLabel(link.setting_item.canon_status)}`,
        body: preview(link.setting_item.summary || link.note),
      }))
    case 'clues':
      return chapterClues.value.map((link) => ({
        id: link.id,
        title: link.clue.title,
        meta: `${chapterClueRelationLabel(link.relation_type)}｜${clueStatusLabel(link.clue.status)}｜${clueVisibilityLabel(link.clue.visibility)}`,
        body: preview(link.clue.description || link.note),
      }))
    case 'timeline':
      return chapterEvents.value.map((event) => ({
        id: event.id,
        title: event.title,
        meta: `${trackTitle(event.track_id)}｜${timeLabel(event)}`,
        body: preview(event.description || event.note),
      }))
    case 'graph':
      return matchedGraphNodes.value.map((node) => ({
        id: node.id,
        title: node.title,
        meta: `${graphNodeTypeLabel(node.node_type)}｜${boundTypeLabel(node.bound_type)}`,
        body: preview(node.summary),
      }))
    default:
      return []
  }
})

const relatedGroups = computed<Array<{ title: string; items: RelatedItem[] }>>(() => {
  switch (props.kind) {
    case 'outline':
      return [
        { title: '涉及人物', items: uniqueItems(outlineCharacterLinks.value, (link) => nameOf(characterMap.value[link.character_id])) },
        { title: '涉及设定', items: uniqueItems(outlineSettingLinks.value, (link) => titleOf(settingMap.value[link.setting_id])) },
        { title: '涉及伏笔', items: uniqueItems(outlineClueLinks.value, (link) => titleOf(clueMap.value[link.clue_id])) },
        { title: '对应时间轴事件', items: uniqueItems(outlineEventLinks.value, (link) => titleOf(eventMap.value[link.timeline_event_id])) },
      ]
    case 'characters':
      return [
        { title: '相关伏笔', items: relatedCluesForCharacters.value },
        { title: '相关设定', items: relatedSettingsForCharacters.value },
        { title: '相关时间轴事件', items: relatedEventsForCharacters.value },
        { title: '关系图节点', items: graphNodesFor('character') },
      ]
    case 'settings':
      return [
        { title: '相关人物', items: relatedCharactersForSettings.value },
        { title: '相关伏笔', items: relatedCluesForSettings.value },
        { title: '相关时间轴事件', items: relatedEventsForSettings.value },
        { title: '关系图节点', items: graphNodesFor('setting') },
      ]
    case 'clues':
      return [
        { title: '相关人物', items: relatedCharactersForClues.value },
        { title: '相关设定', items: relatedSettingsForClues.value },
        { title: '相关时间轴事件', items: relatedEventsForClues.value },
        { title: '关系图节点', items: graphNodesFor('clue') },
      ]
    case 'timeline':
      return [
        { title: '前后 / 并行事件', items: timelineConnectionItems.value },
        { title: '相关人物', items: uniqueItems(eventCharacterLinks.value, (link) => nameOf(characterMap.value[link.character_id])) },
        { title: '相关设定', items: uniqueItems(eventSettingLinks.value, (link) => titleOf(settingMap.value[link.setting_id])) },
        { title: '相关伏笔', items: uniqueItems(eventClueLinks.value, (link) => titleOf(clueMap.value[link.clue_id])) },
      ]
    case 'graph':
      return [
        { title: '直接关系', items: graphEdgeItems.value },
        { title: '关联节点', items: associatedGraphNodeItems.value },
      ]
    default:
      return []
  }
})

const reminders = computed<Reminder[]>(() => {
  const items: Reminder[] = []
  if (props.kind === 'outline') {
    chapterOutlines.value.filter((outline) => outline.status !== 'done').forEach((outline) => {
      items.push({ id: `outline-open-${outline.id}`, text: `有细纲未完成：${outline.title}` })
    })
    chapterOutlines.value.filter((outline) => outline.status === 'abandoned').forEach((outline) => {
      items.push({ id: `outline-abandoned-${outline.id}`, text: `有废弃细纲仍显示在本章：${outline.title}` })
    })
    projectOutlines.value.filter((outline) => outline.importance === 'critical' && !outline.chapter_id).forEach((outline) => {
      items.push({ id: `outline-unbound-${outline.id}`, text: `有关键细纲未绑定章节：${outline.title}` })
    })
  }
  if (props.kind === 'characters' && !chapterCharacters.value.some((link) => link.relation_type === 'pov')) {
    items.push({ id: 'no-pov', text: '本章未设置 POV 人物' })
  }
  if (props.kind === 'settings') {
    chapterSettings.value.filter((link) => link.setting_item.canon_status !== 'confirmed').forEach((link) => {
      items.push({ id: `setting-draft-${link.id}`, text: `设定未定稿：${link.setting_item.title}` })
    })
    chapterSettings.value.filter((link) => !link.setting_item.summary).forEach((link) => {
      items.push({ id: `setting-summary-${link.id}`, text: `设定缺少摘要：${link.setting_item.title}` })
    })
  }
  if (props.kind === 'clues') {
    chapterClues.value.filter((link) => link.clue.status !== 'resolved' && link.clue.status !== 'abandoned').forEach((link) => {
      items.push({ id: `clue-open-${link.id}`, text: `已埋设但未回收：${link.clue.title}` })
    })
    chapterClues.value.filter((link) => link.relation_type === 'payoff').forEach((link) => {
      const setup = link.clue.setup_chapter_id ? '已记录埋设章节' : '未记录埋设章节'
      items.push({ id: `clue-payoff-${link.id}`, text: `本章回收：${link.clue.title}｜${setup}` })
    })
  }
  if (props.kind === 'timeline') {
    chapterEvents.value.filter((event) => event.importance === 'critical' || event.importance === 'high').forEach((event) => {
      const hasEdge = timelineEdges.value.some((edge) => edge.from_event_id === event.id || edge.to_event_id === event.id)
      if (!hasEdge) {
        items.push({ id: `event-edge-${event.id}`, text: `重要事件缺少时序关系：${event.title}` })
      }
    })
  }
  if (props.kind === 'graph') {
    matchedGraphNodes.value.filter((node) => node.bound_type && node.bound_id && !chapterTargetKeys.value.has(`${node.bound_type}:${node.bound_id}`)).forEach((node) => {
      items.push({ id: `graph-invalid-${node.id}`, text: `绑定资料已失效：${node.title}` })
    })
  }
  return items.slice(0, 6)
})

const chapterTargetKeys = computed(() => {
  const keys = new Set<string>()
  chapterCharacters.value.forEach((link) => keys.add(`character:${link.character_id}`))
  chapterSettings.value.forEach((link) => keys.add(`setting:${link.setting_item_id}`))
  chapterClues.value.forEach((link) => keys.add(`clue:${link.clue_id}`))
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

const relatedCluesForCharacters = computed(() => {
  const characterIds = new Set(chapterCharacters.value.map((link) => link.character_id))
  return uniqueItems([...outlineClueLinks.value, ...eventClueLinks.value], (link) => titleOf(clueMap.value[link.clue_id]))
    .filter(Boolean)
    .concat(graphNodesFor('clue').filter((item) => characterIds.size > 0).slice(0, 0))
})
const relatedSettingsForCharacters = computed(() => uniqueItems([...outlineSettingLinks.value, ...eventSettingLinks.value], (link) => titleOf(settingMap.value[link.setting_id])))
const relatedEventsForCharacters = computed(() => uniqueItems(outlineEventLinks.value, (link) => titleOf(eventMap.value[link.timeline_event_id])))
const relatedCharactersForSettings = computed(() => uniqueItems([...outlineCharacterLinks.value, ...eventCharacterLinks.value], (link) => nameOf(characterMap.value[link.character_id])))
const relatedCluesForSettings = computed(() => uniqueItems([...outlineClueLinks.value, ...eventClueLinks.value], (link) => titleOf(clueMap.value[link.clue_id])))
const relatedEventsForSettings = computed(() => uniqueItems(outlineEventLinks.value, (link) => titleOf(eventMap.value[link.timeline_event_id])))
const relatedCharactersForClues = computed(() => uniqueItems([...outlineCharacterLinks.value, ...eventCharacterLinks.value], (link) => nameOf(characterMap.value[link.character_id])))
const relatedSettingsForClues = computed(() => uniqueItems([...outlineSettingLinks.value, ...eventSettingLinks.value], (link) => titleOf(settingMap.value[link.setting_id])))
const relatedEventsForClues = computed(() => uniqueItems(outlineEventLinks.value, (link) => titleOf(eventMap.value[link.timeline_event_id])))

const timelineConnectionItems = computed(() => {
  const ids = new Set(chapterEvents.value.map((event) => event.id))
  return timelineEdges.value
    .filter((edge) => edge.visibility !== 'hidden' && (ids.has(edge.from_event_id) || ids.has(edge.to_event_id)))
    .map((edge) => {
      const from = eventMap.value[edge.from_event_id]
      const to = eventMap.value[edge.to_event_id]
      return {
        id: edge.id,
        label: `${titleOf(from)} → ${titleOf(to)}`,
        meta: temporalRelationLabel(edge.temporal_relation),
      }
    })
})

const graphEdgeItems = computed(() => {
  const matchedIds = new Set(matchedGraphNodes.value.map((node) => node.id))
  return graphEdges.value
    .filter((edge) => edge.visibility !== 'hidden' && (matchedIds.has(edge.from_node_id) || matchedIds.has(edge.to_node_id)))
    .map((edge) => ({
      id: edge.id,
      label: `${titleOf(nodeMap.value[edge.from_node_id])} → ${titleOf(nodeMap.value[edge.to_node_id])}`,
      meta: `${graphEdgeRelationLabel(edge.relation_type)}｜强度 ${edge.strength}`,
    }))
})

const associatedGraphNodeItems = computed(() => {
  const matchedIds = new Set(matchedGraphNodes.value.map((node) => node.id))
  const items = new Map<string, RelatedItem>()
  graphEdges.value.forEach((edge) => {
    if (edge.visibility === 'hidden') {
      return
    }
    const endpoints = [edge.from_node_id, edge.to_node_id]
    if (!endpoints.some((id) => matchedIds.has(id))) {
      return
    }
    endpoints.filter((id) => !matchedIds.has(id)).forEach((id) => {
      const node = nodeMap.value[id]
      if (node && node.visibility !== 'hidden') {
        items.set(id, { id, label: node.title, meta: graphNodeTypeLabel(node.node_type) })
      }
    })
  })
  return [...items.values()]
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
      outlines,
      allOutlines,
      characters,
      settings,
      clues,
      events,
      allCharacters,
      allSettings,
      allClues,
      allEvents,
      tracks,
      edges,
      nodes,
      graphRelations,
    ] = await Promise.all([
      listChapterOutlines(props.chapterId),
      listProjectOutlines(props.projectId),
      listChapterCharacters(props.chapterId),
      listChapterSettings(props.chapterId),
      listChapterClues(props.chapterId),
      listChapterTimelineEvents(props.chapterId),
      listProjectCharacters(props.projectId),
      listProjectSettings(props.projectId),
      listProjectClues(props.projectId),
      listProjectTimelineEvents(props.projectId),
      listTimelineTracks(props.projectId),
      listTimelineEdges(props.projectId),
      listGraphNodes(props.projectId),
      listGraphEdges(props.projectId),
    ])
    if (token !== loadToken) {
      return
    }
    chapterOutlines.value = outlines
    projectOutlines.value = allOutlines
    chapterCharacters.value = characters
    chapterSettings.value = settings
    chapterClues.value = clues
    chapterEvents.value = events
    projectCharacters.value = allCharacters
    projectSettings.value = allSettings
    projectClues.value = allClues
    projectEvents.value = allEvents
    timelineTracks.value = tracks
    timelineEdges.value = edges
    graphNodes.value = nodes
    graphEdges.value = graphRelations
    await loadMaterialLinks(outlines, events, token)
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

async function loadMaterialLinks(outlines: OutlineItem[], events: TimelineEvent[], token: number) {
  const [
    outlineCharacters,
    outlineSettings,
    outlineClues,
    outlineEvents,
    eventCharacters,
    eventSettings,
    eventClues,
  ] = await Promise.all([
    Promise.all(outlines.map((outline) => listOutlineCharacters(outline.id))).then((groups) => groups.flat()),
    Promise.all(outlines.map((outline) => listOutlineSettings(outline.id))).then((groups) => groups.flat()),
    Promise.all(outlines.map((outline) => listOutlineClues(outline.id))).then((groups) => groups.flat()),
    Promise.all(outlines.map((outline) => listOutlineTimelineEvents(outline.id))).then((groups) => groups.flat()),
    Promise.all(events.map((event) => listTimelineEventCharacters(event.id))).then((groups) => groups.flat()),
    Promise.all(events.map((event) => listTimelineEventSettings(event.id))).then((groups) => groups.flat()),
    Promise.all(events.map((event) => listTimelineEventClues(event.id))).then((groups) => groups.flat()),
  ])
  if (token !== loadToken) {
    return
  }
  outlineCharacterLinks.value = outlineCharacters
  outlineSettingLinks.value = outlineSettings
  outlineClueLinks.value = outlineClues
  outlineEventLinks.value = outlineEvents
  eventCharacterLinks.value = eventCharacters
  eventSettingLinks.value = eventSettings
  eventClueLinks.value = eventClues
}

function clearState() {
  isLoading.value = false
  errorMessage.value = ''
  chapterOutlines.value = []
  chapterCharacters.value = []
  chapterSettings.value = []
  chapterClues.value = []
  chapterEvents.value = []
}

function graphNodesFor(boundType: 'character' | 'setting' | 'clue' | 'timeline_event') {
  const ids = new Set<string>()
  if (boundType === 'character') chapterCharacters.value.forEach((link) => ids.add(link.character_id))
  if (boundType === 'setting') chapterSettings.value.forEach((link) => ids.add(link.setting_item_id))
  if (boundType === 'clue') chapterClues.value.forEach((link) => ids.add(link.clue_id))
  if (boundType === 'timeline_event') chapterEvents.value.forEach((event) => ids.add(event.id))
  return graphNodes.value
    .filter((node) => node.visibility !== 'hidden' && node.bound_type === boundType && node.bound_id && ids.has(node.bound_id))
    .map((node) => ({ id: node.id, label: node.title, meta: graphNodeTypeLabel(node.node_type) }))
}

function mapById<T extends { id: string }>(items: T[]) {
  return items.reduce<Record<string, T>>((acc, item) => {
    acc[item.id] = item
    return acc
  }, {})
}

function uniqueItems<T extends { id: string }>(items: T[], getLabel: (item: T) => string) {
  const result = new Map<string, RelatedItem>()
  items.forEach((item) => {
    const label = getLabel(item)
    if (label && !label.startsWith('未知')) {
      result.set(label, { id: item.id, label })
    }
  })
  return [...result.values()]
}

function titleOf(item: { title: string } | undefined) {
  return item?.title ?? '未知资料'
}

function nameOf(item: { name: string } | undefined) {
  return item?.name ?? '未知人物'
}

function preview(text: string | null | undefined) {
  const source = (text ?? '').trim()
  if (!source) {
    return '暂无摘要'
  }
  return source.length > 72 ? `${source.slice(0, 72)}...` : source
}

function timeLabel(event: TimelineEvent) {
  return [event.story_date, event.story_time].filter(Boolean).join('｜') || '未填写时间'
}

function trackTitle(trackId: string | null) {
  if (!trackId) return '未分配轨道'
  return trackMap.value[trackId]?.title ?? '未分配轨道'
}

function outlineTypeLabel(value: string) {
  return ({ book_outline: '全书大纲', volume_outline: '分卷大纲', chapter_outline: '章节细纲', scene: '场景', plot_point: '剧情节点', note: '备注' } as Record<string, string>)[value] ?? value
}
function outlineStatusLabel(value: string) {
  return ({ planned: '计划中', writing: '写作中', done: '已完成', abandoned: '已废弃' } as Record<string, string>)[value] ?? value
}
function outlineImportanceLabel(value: string) {
  return ({ normal: '普通', important: '重要', critical: '关键' } as Record<string, string>)[value] ?? value
}
function characterRoleLabel(value: string) {
  return ({ protagonist: '主角', deuteragonist: '副主角', antagonist: '反派', supporting: '配角', minor: '小角色', unknown: '未知' } as Record<string, string>)[value] ?? value
}
function chapterCharacterRelationLabel(value: string) {
  return ({ appears: '出场', mentioned: '提及', pov: 'POV', conflict: '冲突', supports: '协助' } as Record<string, string>)[value] ?? value
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
        <p class="eyebrow">章节上下文</p>
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
      <ChapterContextSection title="本章直接相关" :count="directItems.length">
        <p v-if="directItems.length === 0" class="state-message compact">
          本章暂无相关资料。可在完整资料库中创建或绑定。当前结果来自显式绑定，暂未启用智能匹配。
        </p>
        <div v-else class="card-list">
          <article v-for="item in directItems" :key="item.id" class="context-card">
            <h4>{{ item.title }}</h4>
            <p class="meta">{{ item.meta }}</p>
            <p class="body">{{ item.body }}</p>
          </article>
        </div>
      </ChapterContextSection>

      <ChapterContextSection title="关联资料">
        <div class="related-grid">
          <article v-for="group in relatedGroups" :key="group.title" class="related-group">
            <h4>{{ group.title }}</h4>
            <p v-if="group.items.length === 0" class="empty-line">暂无关联</p>
            <ul v-else>
              <li v-for="item in group.items.slice(0, 6)" :key="item.id">
                <span>{{ item.label }}</span>
                <small v-if="item.meta">{{ item.meta }}</small>
              </li>
            </ul>
          </article>
        </div>
      </ChapterContextSection>

      <ChapterContextSection title="状态提醒" :count="reminders.length">
        <p v-if="reminders.length === 0" class="state-message compact">暂无需要提醒的状态。</p>
        <ul v-else class="reminder-list">
          <li v-for="item in reminders" :key="item.id">{{ item.text }}</li>
        </ul>
      </ChapterContextSection>

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

.card-list,
.related-grid {
  display: grid;
  gap: 10px;
}

.context-card,
.related-group {
  display: grid;
  gap: 6px;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 11px;
  background: #ffffff;
}

.context-card h4,
.related-group h4 {
  color: #111827;
  font-size: 0.9rem;
}

.meta,
.empty-line,
.related-group small {
  color: #64748b;
  font-size: 0.78rem;
}

.body {
  color: #334155;
  font-size: 0.82rem;
  line-height: 1.65;
}

.related-group ul,
.reminder-list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding-left: 18px;
  color: #334155;
  font-size: 0.82rem;
  line-height: 1.55;
}

.related-group li {
  display: grid;
  gap: 2px;
}

.reminder-list li {
  padding-left: 2px;
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
