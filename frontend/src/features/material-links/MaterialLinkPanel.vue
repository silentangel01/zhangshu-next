<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { listProjectCharacters } from '@/entities/character/api'
import type { Character } from '@/entities/character/types'
import { listProjectClues } from '@/entities/clue/api'
import type { Clue } from '@/entities/clue/types'
import { addClueCharacter, deleteClueCharacter, listClueCharacters } from '@/entities/clue-character/api'
import type { ClueCharacterLink } from '@/entities/clue-character/types'
import { addClueSetting, deleteClueSetting, listClueSettings } from '@/entities/clue-setting/api'
import type { ClueSettingLink } from '@/entities/clue-setting/types'
import { listGraphNodes } from '@/entities/graph/api'
import type { GraphNode } from '@/entities/graph/types'
import {
  addOutlineCharacter,
  addOutlineClue,
  addOutlineSetting,
  addOutlineTimelineEvent,
  addTimelineEventCharacter,
  addTimelineEventClue,
  addTimelineEventSetting,
  listOutlineCharacters,
  listOutlineClues,
  listOutlineSettings,
  listOutlineTimelineEvents,
  listTimelineEventCharacters,
  listTimelineEventClues,
  listTimelineEventSettings,
  removeOutlineCharacter,
  removeOutlineClue,
  removeOutlineSetting,
  removeOutlineTimelineEvent,
  removeTimelineEventCharacter,
  removeTimelineEventClue,
  removeTimelineEventSetting,
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
import { listProjectOutlines } from '@/entities/outline/api'
import type { OutlineItem } from '@/entities/outline/types'
import { listProjectSettings } from '@/entities/setting/api'
import type { SettingItem } from '@/entities/setting/types'
import { listProjectTimelineEvents } from '@/entities/timeline/api'
import type { TimelineEvent } from '@/entities/timeline/types'
import { ensureMaterialGraphNode, graphFocusRoute } from '@/features/graph/useMaterialGraphNode'

type SourceType = 'outline' | 'character' | 'setting' | 'clue' | 'timeline_event'
type GroupKey = 'characters' | 'settings' | 'clues' | 'outlines' | 'timeline_events' | 'graph_nodes'
type LinkItem = {
  id: string
  targetId: string
  label: string
  relationType: string
  note: string
  to: string
  removable: boolean
}
type LinkGroup = {
  key: GroupKey
  title: string
  addLabel: string
  items: LinkItem[]
}

const props = defineProps<{
  projectId: string
  sourceType: SourceType
  sourceId: string | null
  sourceTitle: string
}>()

const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const characters = ref<Character[]>([])
const settings = ref<SettingItem[]>([])
const clues = ref<Clue[]>([])
const outlines = ref<OutlineItem[]>([])
const events = ref<TimelineEvent[]>([])
const graphNodes = ref<GraphNode[]>([])

const outlineCharacterLinks = ref<OutlineCharacterLink[]>([])
const outlineSettingLinks = ref<OutlineSettingLink[]>([])
const outlineClueLinks = ref<OutlineClueLink[]>([])
const outlineEventLinks = ref<OutlineTimelineEventLink[]>([])
const eventCharacterLinks = ref<TimelineEventCharacterLink[]>([])
const eventSettingLinks = ref<TimelineEventSettingLink[]>([])
const eventClueLinks = ref<TimelineEventClueLink[]>([])
const clueCharacterLinks = ref<ClueCharacterLink[]>([])
const clueSettingLinks = ref<ClueSettingLink[]>([])

const addForm = ref<Record<GroupKey, { targetId: string; relationType: string; note: string }>>({
  characters: { targetId: '', relationType: 'related', note: '' },
  settings: { targetId: '', relationType: 'related', note: '' },
  clues: { targetId: '', relationType: 'related', note: '' },
  outlines: { targetId: '', relationType: 'related', note: '' },
  timeline_events: { targetId: '', relationType: 'related', note: '' },
  graph_nodes: { targetId: '', relationType: 'related', note: '' },
})

const characterMap = computed(() => mapById(characters.value))
const settingMap = computed(() => mapById(settings.value))
const clueMap = computed(() => mapById(clues.value))
const outlineMap = computed(() => mapById(outlines.value))
const eventMap = computed(() => mapById(events.value))

const groups = computed<LinkGroup[]>(() => {
  if (!props.sourceId) return []
  if (props.sourceType === 'outline') {
    return [
      group('characters', '人物', outlineCharacterLinks.value.map((link) => item(link.id, link.character_id, nameOf(characterMap.value[link.character_id]), link.relation_type, link.note, materialUrl('character')))),
      group('settings', '设定', outlineSettingLinks.value.map((link) => item(link.id, link.setting_id, titleOf(settingMap.value[link.setting_id]), link.relation_type, link.note, materialUrl('setting')))),
      group('clues', '伏笔', outlineClueLinks.value.map((link) => item(link.id, link.clue_id, titleOf(clueMap.value[link.clue_id]), link.relation_type, link.note, materialUrl('clue')))),
      group('timeline_events', '时间轴事件', outlineEventLinks.value.map((link) => item(link.id, link.timeline_event_id, titleOf(eventMap.value[link.timeline_event_id]), link.relation_type, link.note, materialUrl('timeline_event')))),
    ]
  }
  if (props.sourceType === 'timeline_event') {
    return [
      group('characters', '人物', eventCharacterLinks.value.map((link) => item(link.id, link.character_id, nameOf(characterMap.value[link.character_id]), link.relation_type, link.note, materialUrl('character')))),
      group('settings', '设定', eventSettingLinks.value.map((link) => item(link.id, link.setting_id, titleOf(settingMap.value[link.setting_id]), link.relation_type, link.note, materialUrl('setting')))),
      group('clues', '伏笔', eventClueLinks.value.map((link) => item(link.id, link.clue_id, titleOf(clueMap.value[link.clue_id]), link.relation_type, link.note, materialUrl('clue')))),
      group('graph_nodes', '关系图节点', graphNodeItems('timeline_event')),
    ]
  }
  if (props.sourceType === 'character') {
    return [
      group('outlines', '大纲', outlineCharacterLinks.value.map((link) => item(link.id, link.outline_item_id, titleOf(outlineMap.value[link.outline_item_id]), link.relation_type, link.note, materialUrl('outline')))),
      group('clues', '伏笔', clueCharacterLinks.value.map((link) => item(link.id, link.clue_id, titleOf(clueMap.value[link.clue_id]), link.relation_type, link.note, materialUrl('clue')))),
      group('timeline_events', '时间轴事件', eventCharacterLinks.value.map((link) => item(link.id, link.timeline_event_id, titleOf(eventMap.value[link.timeline_event_id]), link.relation_type, link.note, materialUrl('timeline_event')))),
      group('graph_nodes', '关系图节点', graphNodeItems('character')),
    ]
  }
  if (props.sourceType === 'setting') {
    return [
      group('outlines', '大纲', outlineSettingLinks.value.map((link) => item(link.id, link.outline_item_id, titleOf(outlineMap.value[link.outline_item_id]), link.relation_type, link.note, materialUrl('outline')))),
      group('clues', '伏笔', clueSettingLinks.value.map((link) => item(link.id, link.clue_id, titleOf(clueMap.value[link.clue_id]), link.relation_type, link.note, materialUrl('clue')))),
      group('timeline_events', '时间轴事件', eventSettingLinks.value.map((link) => item(link.id, link.timeline_event_id, titleOf(eventMap.value[link.timeline_event_id]), link.relation_type, link.note, materialUrl('timeline_event')))),
      group('graph_nodes', '关系图节点', graphNodeItems('setting')),
    ]
  }
  return [
    group('outlines', '大纲', outlineClueLinks.value.map((link) => item(link.id, link.outline_item_id, titleOf(outlineMap.value[link.outline_item_id]), link.relation_type, link.note, materialUrl('outline')))),
    group('characters', '人物', clueCharacterLinks.value.map((link) => item(link.id, link.character_id, nameOf(characterMap.value[link.character_id]), link.relation_type, link.note, materialUrl('character')))),
    group('settings', '设定', clueSettingLinks.value.map((link) => item(link.id, link.setting_item_id, titleOf(settingMap.value[link.setting_item_id]), link.relation_type, link.note, materialUrl('setting')))),
    group('timeline_events', '时间轴事件', eventClueLinks.value.map((link) => item(link.id, link.timeline_event_id, titleOf(eventMap.value[link.timeline_event_id]), link.relation_type, link.note, materialUrl('timeline_event')))),
    group('graph_nodes', '关系图节点', graphNodeItems('clue')),
  ]
})

watch(
  () => [props.projectId, props.sourceType, props.sourceId],
  () => {
    void refresh()
  },
  { immediate: true },
)

async function refresh() {
  if (!props.projectId || !props.sourceId) return
  isLoading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const [projectCharacters, projectSettings, projectClues, projectOutlines, projectEvents, projectGraphNodes] = await Promise.all([
      listProjectCharacters(props.projectId),
      listProjectSettings(props.projectId),
      listProjectClues(props.projectId),
      listProjectOutlines(props.projectId),
      listProjectTimelineEvents(props.projectId),
      listGraphNodes(props.projectId),
    ])
    characters.value = projectCharacters
    settings.value = projectSettings
    clues.value = projectClues
    outlines.value = projectOutlines
    events.value = projectEvents
    graphNodes.value = projectGraphNodes
    await refreshLinks()
  } catch (error) {
    void error
    errorMessage.value = '关联资料加载失败，请稍后重试。'
  } finally {
    isLoading.value = false
  }
}

async function refreshLinks() {
  if (!props.sourceId) return
  clearLinks()
  if (props.sourceType === 'outline') {
    const [a, b, c, d] = await Promise.all([
      listOutlineCharacters(props.sourceId),
      listOutlineSettings(props.sourceId),
      listOutlineClues(props.sourceId),
      listOutlineTimelineEvents(props.sourceId),
    ])
    outlineCharacterLinks.value = a
    outlineSettingLinks.value = b
    outlineClueLinks.value = c
    outlineEventLinks.value = d
    return
  }
  if (props.sourceType === 'timeline_event') {
    const [a, b, c] = await Promise.all([
      listTimelineEventCharacters(props.sourceId),
      listTimelineEventSettings(props.sourceId),
      listTimelineEventClues(props.sourceId),
    ])
    eventCharacterLinks.value = a
    eventSettingLinks.value = b
    eventClueLinks.value = c
    return
  }
  await refreshReverseLinks()
}

async function refreshReverseLinks() {
  const [outlineLinks, eventLinks, clueCharacterGroups, clueSettingGroups] = await Promise.all([
    Promise.all(outlines.value.map(async (outline) => ({
      outlineId: outline.id,
      characters: await listOutlineCharacters(outline.id),
      settings: await listOutlineSettings(outline.id),
      clues: await listOutlineClues(outline.id),
    }))),
    Promise.all(events.value.map(async (event) => ({
      eventId: event.id,
      characters: await listTimelineEventCharacters(event.id),
      settings: await listTimelineEventSettings(event.id),
      clues: await listTimelineEventClues(event.id),
    }))),
    Promise.all(clues.value.map((clue) => listClueCharacters(clue.id))),
    Promise.all(clues.value.map((clue) => listClueSettings(clue.id))),
  ])
  if (props.sourceType === 'character') {
    outlineCharacterLinks.value = outlineLinks.flatMap((entry) => entry.characters).filter((link) => link.character_id === props.sourceId)
    eventCharacterLinks.value = eventLinks.flatMap((entry) => entry.characters).filter((link) => link.character_id === props.sourceId)
    clueCharacterLinks.value = clueCharacterGroups.flat().filter((link) => link.character_id === props.sourceId)
  }
  if (props.sourceType === 'setting') {
    outlineSettingLinks.value = outlineLinks.flatMap((entry) => entry.settings).filter((link) => link.setting_id === props.sourceId)
    eventSettingLinks.value = eventLinks.flatMap((entry) => entry.settings).filter((link) => link.setting_id === props.sourceId)
    clueSettingLinks.value = clueSettingGroups.flat().filter((link) => link.setting_item_id === props.sourceId)
  }
  if (props.sourceType === 'clue') {
    outlineClueLinks.value = outlineLinks.flatMap((entry) => entry.clues).filter((link) => link.clue_id === props.sourceId)
    eventClueLinks.value = eventLinks.flatMap((entry) => entry.clues).filter((link) => link.clue_id === props.sourceId)
    clueCharacterLinks.value = clueCharacterGroups.flat().filter((link) => link.clue_id === props.sourceId)
    clueSettingLinks.value = clueSettingGroups.flat().filter((link) => link.clue_id === props.sourceId)
  }
}

async function handleAdd(groupKey: GroupKey) {
  if (!props.sourceId) return
  const form = addForm.value[groupKey]
  if (!form.targetId) return
  isSaving.value = true
  errorMessage.value = ''
  try {
    await addLink(groupKey, form.targetId, form.relationType || 'related', form.note)
    form.targetId = ''
    form.note = ''
    form.relationType = 'related'
    await refreshLinks()
    successMessage.value = '关联已添加。'
  } catch (error) {
    void error
    errorMessage.value = '添加关联失败，请检查资料是否属于同一项目。'
  } finally {
    isSaving.value = false
  }
}

async function addLink(groupKey: GroupKey, targetId: string, relationType: string, note: string) {
  if (!props.sourceId) return
  if (props.sourceType === 'outline') {
    if (groupKey === 'characters') return addOutlineCharacter(props.sourceId, { character_id: targetId, relation_type: relationType as never, note })
    if (groupKey === 'settings') return addOutlineSetting(props.sourceId, { setting_id: targetId, relation_type: relationType as never, note })
    if (groupKey === 'clues') return addOutlineClue(props.sourceId, { clue_id: targetId, relation_type: relationType as never, note })
    if (groupKey === 'timeline_events') return addOutlineTimelineEvent(props.sourceId, { timeline_event_id: targetId, relation_type: relationType as never, note })
  }
  if (props.sourceType === 'timeline_event') {
    if (groupKey === 'characters') return addTimelineEventCharacter(props.sourceId, { character_id: targetId, relation_type: relationType as never, note })
    if (groupKey === 'settings') return addTimelineEventSetting(props.sourceId, { setting_id: targetId, relation_type: relationType as never, note })
    if (groupKey === 'clues') return addTimelineEventClue(props.sourceId, { clue_id: targetId, relation_type: relationType as never, note })
  }
  if (props.sourceType === 'character') {
    if (groupKey === 'outlines') return addOutlineCharacter(targetId, { character_id: props.sourceId, relation_type: relationType as never, note })
    if (groupKey === 'timeline_events') return addTimelineEventCharacter(targetId, { character_id: props.sourceId, relation_type: relationType as never, note })
    if (groupKey === 'clues') return addClueCharacter(targetId, { character_id: props.sourceId, relation_type: relationType as never, note })
  }
  if (props.sourceType === 'setting') {
    if (groupKey === 'outlines') return addOutlineSetting(targetId, { setting_id: props.sourceId, relation_type: relationType as never, note })
    if (groupKey === 'timeline_events') return addTimelineEventSetting(targetId, { setting_id: props.sourceId, relation_type: relationType as never, note })
    if (groupKey === 'clues') return addClueSetting(targetId, { setting_item_id: props.sourceId, relation_type: relationType as never, note })
  }
  if (props.sourceType === 'clue') {
    if (groupKey === 'outlines') return addOutlineClue(targetId, { clue_id: props.sourceId, relation_type: relationType as never, note })
    if (groupKey === 'timeline_events') return addTimelineEventClue(targetId, { clue_id: props.sourceId, relation_type: relationType as never, note })
    if (groupKey === 'characters') return addClueCharacter(props.sourceId, { character_id: targetId, relation_type: relationType as never, note })
    if (groupKey === 'settings') return addClueSetting(props.sourceId, { setting_item_id: targetId, relation_type: relationType as never, note })
  }
}

async function handleRemove(groupKey: GroupKey, item: LinkItem) {
  if (!props.sourceId || !window.confirm('确认移除这条关联吗？')) return
  isSaving.value = true
  errorMessage.value = ''
  try {
    await removeLink(groupKey, item)
    await refreshLinks()
    successMessage.value = '关联已移除。'
  } catch (error) {
    void error
    errorMessage.value = '移除关联失败。'
  } finally {
    isSaving.value = false
  }
}

async function removeLink(groupKey: GroupKey, item: LinkItem) {
  if (!props.sourceId) return
  if (props.sourceType === 'outline') {
    if (groupKey === 'characters') return removeOutlineCharacter(props.sourceId, item.targetId)
    if (groupKey === 'settings') return removeOutlineSetting(props.sourceId, item.targetId)
    if (groupKey === 'clues') return removeOutlineClue(props.sourceId, item.targetId)
    if (groupKey === 'timeline_events') return removeOutlineTimelineEvent(props.sourceId, item.targetId)
  }
  if (props.sourceType === 'timeline_event') {
    if (groupKey === 'characters') return removeTimelineEventCharacter(props.sourceId, item.targetId)
    if (groupKey === 'settings') return removeTimelineEventSetting(props.sourceId, item.targetId)
    if (groupKey === 'clues') return removeTimelineEventClue(props.sourceId, item.targetId)
  }
  if (props.sourceType === 'character') {
    if (groupKey === 'outlines') return removeOutlineCharacter(item.targetId, props.sourceId)
    if (groupKey === 'timeline_events') return removeTimelineEventCharacter(item.targetId, props.sourceId)
    if (groupKey === 'clues') return deleteClueCharacter(item.id)
  }
  if (props.sourceType === 'setting') {
    if (groupKey === 'outlines') return removeOutlineSetting(item.targetId, props.sourceId)
    if (groupKey === 'timeline_events') return removeTimelineEventSetting(item.targetId, props.sourceId)
    if (groupKey === 'clues') return deleteClueSetting(item.id)
  }
  if (props.sourceType === 'clue') {
    if (groupKey === 'outlines') return removeOutlineClue(item.targetId, props.sourceId)
    if (groupKey === 'timeline_events') return removeTimelineEventClue(item.targetId, props.sourceId)
    if (groupKey === 'characters') return deleteClueCharacter(item.id)
    if (groupKey === 'settings') return deleteClueSetting(item.id)
  }
}

async function openOrCreateGraphNode() {
  if (!props.sourceId || props.sourceType === 'outline') return
  if (!['character', 'setting', 'clue', 'timeline_event'].includes(props.sourceType)) return
  const nodeType = props.sourceType
  const node = await ensureMaterialGraphNode({
    projectId: props.projectId,
    boundType: nodeType,
    boundId: props.sourceId,
    nodeType,
    title: props.sourceTitle,
    summary: '',
  })
  window.location.href = graphFocusRoute(props.projectId, node.id)
}

function clearLinks() {
  outlineCharacterLinks.value = []
  outlineSettingLinks.value = []
  outlineClueLinks.value = []
  outlineEventLinks.value = []
  eventCharacterLinks.value = []
  eventSettingLinks.value = []
  eventClueLinks.value = []
  clueCharacterLinks.value = []
  clueSettingLinks.value = []
}

function targetOptions(groupKey: GroupKey) {
  if (groupKey === 'characters') return characters.value.map((item) => ({ id: item.id, label: item.name }))
  if (groupKey === 'settings') return settings.value.map((item) => ({ id: item.id, label: item.title }))
  if (groupKey === 'clues') return clues.value.map((item) => ({ id: item.id, label: item.title }))
  if (groupKey === 'outlines') return outlines.value.map((item) => ({ id: item.id, label: item.title }))
  if (groupKey === 'timeline_events') return events.value.map((item) => ({ id: item.id, label: item.title }))
  return []
}

function group(key: GroupKey, title: string, items: LinkItem[]): LinkGroup {
  return { key, title, addLabel: `添加${title}`, items }
}

function item(id: string, targetId: string, label: string, relationType: string, note: string, to: string): LinkItem {
  return { id, targetId, label, relationType, note, to, removable: true }
}

function graphNodeItems(boundType: 'character' | 'setting' | 'clue' | 'timeline_event') {
  if (!props.sourceId) return []
  return graphNodes.value
    .filter((node) => node.bound_type === boundType && node.bound_id === props.sourceId && node.visibility !== 'hidden')
    .map((node) => ({
      id: node.id,
      targetId: node.id,
      label: node.title,
      relationType: 'bound',
      note: '',
      to: graphFocusRoute(props.projectId, node.id),
      removable: false,
    }))
}

function materialUrl(type: 'character' | 'setting' | 'clue' | 'outline' | 'timeline_event') {
  const map = {
    character: 'characters',
    setting: 'settings',
    clue: 'clues',
    outline: 'outlines',
    timeline_event: 'timeline',
  }
  return `/projects/${props.projectId}/${map[type]}`
}

function mapById<T extends { id: string }>(items: T[]) {
  return items.reduce<Record<string, T>>((acc, item) => {
    acc[item.id] = item
    return acc
  }, {})
}

function titleOf(item: { title: string } | undefined) {
  return item?.title ?? '未知资料'
}

function nameOf(item: { name: string } | undefined) {
  return item?.name ?? '未知人物'
}
</script>

<template>
  <section v-if="sourceId" class="material-link-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">关联资料</p>
        <h2>关联资料</h2>
      </div>
      <button
        v-if="sourceType !== 'outline'"
        type="button"
        :disabled="isSaving"
        @click="openOrCreateGraphNode"
      >
        在关系图中查看
      </button>
    </header>

    <p v-if="isLoading" class="state-message">正在加载关联资料...</p>
    <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    <p v-if="successMessage" class="success-message">{{ successMessage }}</p>

    <div v-if="!isLoading" class="group-list">
      <article v-for="groupItem in groups" :key="groupItem.key" class="link-group">
        <header>
          <h3>{{ groupItem.title }}</h3>
          <span>{{ groupItem.items.length }}</span>
        </header>

        <p v-if="groupItem.items.length === 0" class="empty-message">暂无关联资料</p>
        <ul v-else>
          <li v-for="link in groupItem.items" :key="link.id">
            <div>
              <strong>{{ link.label }}</strong>
              <small>{{ link.relationType }}<template v-if="link.note">｜{{ link.note }}</template></small>
            </div>
            <RouterLink :to="link.to">打开资料</RouterLink>
            <button v-if="link.removable" type="button" :disabled="isSaving" @click="handleRemove(groupItem.key, link)">移除</button>
          </li>
        </ul>

        <form v-if="groupItem.key !== 'graph_nodes'" class="add-form" @submit.prevent="handleAdd(groupItem.key)">
          <select v-model="addForm[groupItem.key].targetId" required>
            <option value="">请选择资料</option>
            <option v-for="option in targetOptions(groupItem.key)" :key="option.id" :value="option.id">
              {{ option.label }}
            </option>
          </select>
          <input v-model.trim="addForm[groupItem.key].relationType" placeholder="关系类型" />
          <input v-model.trim="addForm[groupItem.key].note" placeholder="备注" />
          <button type="submit" :disabled="isSaving || !addForm[groupItem.key].targetId">添加关联</button>
        </form>
      </article>
    </div>
  </section>
</template>

<style scoped>
.material-link-panel {
  display: grid;
  gap: 12px;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 14px;
  background: #ffffff;
}

.panel-header,
.link-group header,
.link-group li {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.eyebrow,
h2,
h3,
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

h3 {
  color: #111827;
  font-size: 0.92rem;
}

button,
select,
input {
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  padding: 7px 9px;
  background: #ffffff;
  color: #111827;
  font: inherit;
  font-size: 0.82rem;
}

button {
  color: #2563eb;
  font-weight: 800;
  cursor: pointer;
}

.group-list {
  display: grid;
  gap: 12px;
}

.link-group {
  display: grid;
  gap: 8px;
  border-top: 1px solid #eef2f7;
  padding-top: 10px;
}

.link-group header span {
  border-radius: 999px;
  padding: 2px 8px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 0.75rem;
  font-weight: 800;
}

ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

li {
  border: 1px solid #eef2f7;
  border-radius: 8px;
  padding: 9px;
  background: #fbfcfe;
}

li div {
  display: grid;
  gap: 3px;
}

li strong {
  color: #111827;
  font-size: 0.86rem;
}

li small,
.empty-message {
  color: #64748b;
  font-size: 0.78rem;
}

a {
  color: #2563eb;
  font-size: 0.8rem;
  font-weight: 800;
  text-decoration: none;
  white-space: nowrap;
}

.add-form {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) minmax(0, 1fr) auto;
  gap: 8px;
}

.state-message,
.error-message,
.success-message {
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 10px;
  color: #64748b;
  font-size: 0.85rem;
  text-align: center;
}

.error-message {
  border-color: #fecaca;
  color: #b42318;
}

.success-message {
  border-color: #bbf7d0;
  color: #166534;
}
</style>
