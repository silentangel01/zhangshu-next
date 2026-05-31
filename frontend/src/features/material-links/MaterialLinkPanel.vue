<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { listProjectCharacters } from '@/entities/character/api'
import type { Character } from '@/entities/character/types'
import { listProjectClues } from '@/entities/clue/api'
import type { Clue } from '@/entities/clue/types'
import { listGraphNodes } from '@/entities/graph/api'
import type { GraphNode } from '@/entities/graph/types'
import {
  addLink,
  listLinks,
  removeLink,
} from '@/entities/material-links/api'
import type {
  MaterialLinkRelation,
  MaterialLinkTargetType,
} from '@/entities/material-links/types'
import { listProjectOutlines } from '@/entities/outline/api'
import type { OutlineItem } from '@/entities/outline/types'
import { listProjectSettings } from '@/entities/setting/api'
import type { SettingItem } from '@/entities/setting/types'
import { listProjectTimelineEvents } from '@/entities/timeline/api'
import type { TimelineEvent } from '@/entities/timeline/types'
import { ensureMaterialGraphNode, graphFocusRoute } from '@/features/graph/useMaterialGraphNode'
import { cloudSyncManager } from '@/features/cloud/cloudSyncManager'

type SourceType = Extract<
  MaterialLinkTargetType,
  'outline' | 'character' | 'setting' | 'clue' | 'timeline_event'
>

type DisplayTargetType = Exclude<MaterialLinkTargetType, 'chapter'>

type LinkItem = {
  id: string
  targetId: string
  label: string
  relationType: string
  note: string
  targetType: DisplayTargetType
  to: string
  removable: boolean
}

type LinkGroup = {
  key: DisplayTargetType
  title: string
  addLabel: string
  items: LinkItem[]
}

type AddFormState = {
  targetId: string
  relationType: string
  note: string
}

const DEFAULT_RELATION_TYPE: Record<DisplayTargetType, string> = {
  outline: 'related',
  character: 'related',
  setting: 'related',
  clue: 'related',
  timeline_event: 'related',
  graph_node: 'bound',
}

const TARGET_TITLES: Record<DisplayTargetType, string> = {
  outline: '大纲',
  character: '人物',
  setting: '设定',
  clue: '伏笔',
  timeline_event: '时间轴事件',
  graph_node: '关系图节点',
}

const DEFAULT_TARGET_TYPES: Record<SourceType, DisplayTargetType[]> = {
  outline: ['character', 'setting', 'clue', 'timeline_event'],
  timeline_event: ['character', 'setting', 'clue', 'graph_node'],
  clue: ['outline', 'character', 'setting', 'timeline_event', 'graph_node'],
  character: ['outline', 'clue', 'timeline_event', 'graph_node'],
  setting: ['outline', 'clue', 'timeline_event', 'graph_node'],
}

const props = withDefaults(
  defineProps<{
    projectId: string
    sourceType: SourceType
    sourceId: string | null
    sourceTitle: string
    allowedTargetTypes?: DisplayTargetType[]
    compact?: boolean
  }>(),
  {
    allowedTargetTypes: undefined,
    compact: false,
  },
)

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

const linkState = ref<Partial<Record<DisplayTargetType, MaterialLinkRelation[]>>>({})

const addForm = ref<Record<DisplayTargetType, AddFormState>>({
  outline: createFormState('outline'),
  character: createFormState('character'),
  setting: createFormState('setting'),
  clue: createFormState('clue'),
  timeline_event: createFormState('timeline_event'),
  graph_node: createFormState('graph_node'),
})

const supportedTargetTypes = computed<DisplayTargetType[]>(() => {
  const types = props.allowedTargetTypes?.length
    ? props.allowedTargetTypes
    : DEFAULT_TARGET_TYPES[props.sourceType]
  return types.filter((type) => type !== 'graph_node' || props.sourceType !== 'outline')
})

const characterMap = computed(() => mapById(characters.value))
const settingMap = computed(() => mapById(settings.value))
const clueMap = computed(() => mapById(clues.value))
const outlineMap = computed(() => mapById(outlines.value))
const eventMap = computed(() => mapById(events.value))

const groups = computed<LinkGroup[]>(() =>
  supportedTargetTypes.value.map((targetType) => ({
    key: targetType,
    title: TARGET_TITLES[targetType],
    addLabel: `添加${TARGET_TITLES[targetType]}`,
    items: targetType === 'graph_node'
      ? graphNodeItems()
      : (linkState.value[targetType] ?? []).map((link) => toLinkItem(targetType, link)),
  })),
)

watch(
  () => [props.projectId, props.sourceType, props.sourceId],
  () => {
    void refresh()
  },
  { immediate: true },
)

async function refresh() {
  if (!props.projectId || !props.sourceId) {
    return
  }
  isLoading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const [
      projectCharacters,
      projectSettings,
      projectClues,
      projectOutlines,
      projectEvents,
      projectGraphNodes,
    ] = await Promise.all([
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
  if (!props.sourceId) {
    return
  }

  linkState.value = {}

  if (props.sourceType === 'outline' || props.sourceType === 'timeline_event') {
    const entries = await Promise.all(
      supportedTargetTypes.value
        .filter((targetType) => targetType !== 'graph_node')
        .map(async (targetType) => {
          const links = await listLinks(props.sourceType, props.sourceId!, targetType)
          return [targetType, links] as const
        }),
    )

    linkState.value = Object.fromEntries(entries)
    return
  }

  if (props.sourceType === 'clue') {
    const [charactersLinks, settingLinks, outlineLinks, eventLinks] = await Promise.all([
      listLinks('clue', props.sourceId, 'character'),
      listLinks('clue', props.sourceId, 'setting'),
      collectReverseLinks('outline', outlines.value, 'clue'),
      collectReverseLinks('timeline_event', events.value, 'clue'),
    ])

    linkState.value = {
      character: charactersLinks,
      setting: settingLinks,
      outline: outlineLinks,
      timeline_event: eventLinks,
    }
    return
  }

  await refreshReverseLinks()
}

async function refreshReverseLinks() {
  if (!props.sourceId) {
    return
  }

  const nextState: Partial<Record<DisplayTargetType, MaterialLinkRelation[]>> = {}

  if (props.sourceType === 'character') {
    const [outlineLinks, eventLinks, clueLinks] = await Promise.all([
      collectReverseLinks('outline', outlines.value, 'character'),
      collectReverseLinks('timeline_event', events.value, 'character'),
      collectReverseLinks('clue', clues.value, 'character'),
    ])
    nextState.outline = outlineLinks
    nextState.timeline_event = eventLinks
    nextState.clue = clueLinks
  }

  if (props.sourceType === 'setting') {
    const [outlineLinks, eventLinks, clueLinks] = await Promise.all([
      collectReverseLinks('outline', outlines.value, 'setting'),
      collectReverseLinks('timeline_event', events.value, 'setting'),
      collectReverseLinks('clue', clues.value, 'setting'),
    ])
    nextState.outline = outlineLinks
    nextState.timeline_event = eventLinks
    nextState.clue = clueLinks
  }

  linkState.value = nextState
}

async function collectReverseLinks(
  sourceType: Extract<MaterialLinkTargetType, 'outline' | 'timeline_event' | 'clue'>,
  items: Array<{ id: string }>,
  targetType: Extract<DisplayTargetType, 'character' | 'setting' | 'clue'>,
) {
  const linkGroups = await Promise.all(items.map((item) => listLinks(sourceType, item.id, targetType)))
  return linkGroups
    .flat()
    .filter((link) => link.target_id === props.sourceId)
}

async function handleAdd(targetType: DisplayTargetType) {
  if (!props.sourceId || targetType === 'graph_node') {
    return
  }

  const form = addForm.value[targetType]
  if (!form.targetId) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    await persistAddLink(targetType, form)
    resetForm(targetType)
    await refreshLinks()
    successMessage.value = '关联已添加。'
    cloudSyncManager.notifyDirty(props.projectId)
  } catch (error) {
    void error
    errorMessage.value = '添加关联失败，请检查资料是否属于同一项目。'
  } finally {
    isSaving.value = false
  }
}

async function persistAddLink(targetType: DisplayTargetType, form: AddFormState) {
  if (!props.sourceId) {
    return
  }

  if (props.sourceType === 'outline' || props.sourceType === 'timeline_event' || props.sourceType === 'clue') {
    if (
      props.sourceType === 'clue' &&
      (targetType === 'outline' || targetType === 'timeline_event')
    ) {
      await addLink(targetType, form.targetId, 'clue', {
        target_id: props.sourceId,
        relation_type: form.relationType || DEFAULT_RELATION_TYPE[targetType],
        note: form.note,
      })
    } else {
      await addLink(props.sourceType, props.sourceId, targetType, {
        target_id: form.targetId,
        relation_type: form.relationType || DEFAULT_RELATION_TYPE[targetType],
        note: form.note,
      })
    }
    return
  }

  if (props.sourceType === 'character') {
    if (targetType === 'outline' || targetType === 'timeline_event' || targetType === 'clue') {
      await addLink(targetType, form.targetId, 'character', {
        target_id: props.sourceId,
        relation_type: form.relationType || 'related',
        note: form.note,
      })
    }
    return
  }

  if (props.sourceType === 'setting') {
    if (targetType === 'outline' || targetType === 'timeline_event' || targetType === 'clue') {
      await addLink(targetType, form.targetId, 'setting', {
        target_id: props.sourceId,
        relation_type: form.relationType || 'related',
        note: form.note,
      })
    }
  }
}

async function handleRemove(targetType: DisplayTargetType, item: LinkItem) {
  if (!props.sourceId || !window.confirm('确认移除这条关联吗？')) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    await persistRemoveLink(targetType, item)
    await refreshLinks()
    successMessage.value = '关联已移除。'
    cloudSyncManager.notifyDirty(props.projectId)
  } catch (error) {
    void error
    errorMessage.value = '移除关联失败。'
  } finally {
    isSaving.value = false
  }
}

async function persistRemoveLink(targetType: DisplayTargetType, item: LinkItem) {
  if (!props.sourceId || targetType === 'graph_node') {
    return
  }

  if (props.sourceType === 'outline' || props.sourceType === 'timeline_event' || props.sourceType === 'clue') {
    if (
      props.sourceType === 'clue' &&
      (targetType === 'outline' || targetType === 'timeline_event')
    ) {
      await removeLink(targetType, item.targetId, 'clue', props.sourceId, { linkId: item.id })
    } else {
      await removeLink(props.sourceType, props.sourceId, targetType, item.targetId, { linkId: item.id })
    }
    return
  }

  if (props.sourceType === 'character') {
    if (targetType === 'outline' || targetType === 'timeline_event' || targetType === 'clue') {
      await removeLink(targetType, item.targetId, 'character', props.sourceId, { linkId: item.id })
    }
    return
  }

  if (props.sourceType === 'setting') {
    if (targetType === 'outline' || targetType === 'timeline_event' || targetType === 'clue') {
      await removeLink(targetType, item.targetId, 'setting', props.sourceId, { linkId: item.id })
    }
  }
}

async function openOrCreateGraphNode() {
  if (!props.sourceId) {
    return
  }
  if (
    props.sourceType !== 'character' &&
    props.sourceType !== 'setting' &&
    props.sourceType !== 'clue' &&
    props.sourceType !== 'timeline_event'
  ) {
    return
  }

  const node = await ensureMaterialGraphNode({
    projectId: props.projectId,
    boundType: props.sourceType,
    boundId: props.sourceId,
    nodeType: props.sourceType,
    title: props.sourceTitle,
    summary: '',
  })

  cloudSyncManager.notifyDirty(props.projectId)
  window.location.href = graphFocusRoute(props.projectId, node.id)
}

function graphNodeItems(): LinkItem[] {
  if (!props.sourceId || props.sourceType === 'outline') {
    return []
  }

  return graphNodes.value
    .filter(
      (node) =>
        node.bound_type === props.sourceType &&
        node.bound_id === props.sourceId &&
        node.visibility !== 'hidden',
    )
    .map((node) => ({
      id: node.id,
      targetId: node.id,
      label: node.title || '未命名节点',
      relationType: 'bound',
      note: '',
      targetType: 'graph_node',
      to: graphFocusRoute(props.projectId, node.id),
      removable: false,
    }))
}

function toLinkItem(targetType: DisplayTargetType, link: MaterialLinkRelation): LinkItem {
  return {
    id: link.id ?? `${targetType}:${link.target_id}`,
    targetId: link.target_id,
    label: resolveTargetLabel(targetType, link.target_id),
    relationType: link.relation_type,
    note: link.note ?? '',
    targetType,
    to: materialRoute(targetType),
    removable: true,
  }
}

function targetOptions(targetType: DisplayTargetType) {
  if (targetType === 'character') {
    return characters.value.map((item) => ({ id: item.id, label: item.name }))
  }
  if (targetType === 'setting') {
    return settings.value.map((item) => ({ id: item.id, label: item.title }))
  }
  if (targetType === 'clue') {
    return clues.value.map((item) => ({ id: item.id, label: item.title }))
  }
  if (targetType === 'outline') {
    return outlines.value.map((item) => ({ id: item.id, label: item.title }))
  }
  if (targetType === 'timeline_event') {
    return events.value.map((item) => ({ id: item.id, label: item.title }))
  }
  return []
}

function resolveTargetLabel(targetType: DisplayTargetType, targetId: string) {
  if (targetType === 'character') {
    return characterMap.value[targetId]?.name ?? '未知人物'
  }
  if (targetType === 'setting') {
    return settingMap.value[targetId]?.title ?? '未知设定'
  }
  if (targetType === 'clue') {
    return clueMap.value[targetId]?.title ?? '未知伏笔'
  }
  if (targetType === 'outline') {
    return outlineMap.value[targetId]?.title ?? '未知大纲'
  }
  if (targetType === 'timeline_event') {
    return eventMap.value[targetId]?.title ?? '未知时间轴事件'
  }
  return '未知关系图节点'
}

function materialRoute(targetType: DisplayTargetType) {
  const routeMap: Record<DisplayTargetType, string> = {
    character: 'characters',
    setting: 'settings',
    clue: 'clues',
    outline: 'outlines',
    timeline_event: 'timeline',
    graph_node: 'graph',
  }
  return `/projects/${props.projectId}/${routeMap[targetType]}`
}

function createFormState(targetType: DisplayTargetType): AddFormState {
  return {
    targetId: '',
    relationType: DEFAULT_RELATION_TYPE[targetType],
    note: '',
  }
}

function resetForm(targetType: DisplayTargetType) {
  addForm.value[targetType] = createFormState(targetType)
}

function mapById<T extends { id: string }>(items: T[]) {
  return items.reduce<Record<string, T>>((acc, item) => {
    acc[item.id] = item
    return acc
  }, {})
}
</script>

<template>
  <section v-if="sourceId" class="material-link-panel" :class="{ compact }">
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
            <div class="item-content">
              <strong>{{ link.label }}</strong>
              <small>
                {{ link.relationType }}
                <template v-if="link.note">｜{{ link.note }}</template>
              </small>
            </div>
            <div class="item-actions">
              <RouterLink :to="link.to">打开资料</RouterLink>
              <button
                v-if="link.removable"
                type="button"
                :disabled="isSaving"
                @click="handleRemove(groupItem.key, link)"
              >
                移除
              </button>
            </div>
          </li>
        </ul>

        <form
          v-if="groupItem.key !== 'graph_node'"
          class="add-form"
          @submit.prevent="handleAdd(groupItem.key)"
        >
          <select v-model="addForm[groupItem.key].targetId" required>
            <option value="">请选择资料</option>
            <option
              v-for="option in targetOptions(groupItem.key)"
              :key="option.id"
              :value="option.id"
            >
              {{ option.label }}
            </option>
          </select>
          <input
            v-model.trim="addForm[groupItem.key].relationType"
            type="text"
            placeholder="关系类型"
          />
          <input v-model.trim="addForm[groupItem.key].note" type="text" placeholder="备注" />
          <button
            type="submit"
            :disabled="isSaving || !addForm[groupItem.key].targetId"
          >
            {{ groupItem.addLabel }}
          </button>
        </form>
      </article>
    </div>
  </section>
</template>

<style scoped>
.material-link-panel {
  display: grid;
  gap: var(--zs-space-3);
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-3);
  background: var(--zs-color-surface);
}

.material-link-panel.compact {
  gap: var(--zs-space-2);
  padding: var(--zs-space-3);
}

.panel-header,
.link-group header,
.link-group li,
.item-actions {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--zs-space-2);
}

.eyebrow,
h2,
h3,
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

h3 {
  color: var(--zs-color-text);
  font-size: 0.92rem;
}

button,
select,
input {
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 7px 9px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.82rem;
}

button {
  color: var(--zs-color-primary);
  font-weight: 800;
  cursor: pointer;
}

.group-list {
  display: grid;
  gap: var(--zs-space-3);
}

.link-group {
  display: grid;
  gap: var(--zs-space-2);
  border-top: 1px solid var(--zs-color-border-soft);
  padding-top: var(--zs-space-2);
}

.link-group header span {
  border-radius: var(--zs-radius-pill);
  padding: 2px 8px;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
  font-size: 0.75rem;
  font-weight: 800;
}

ul {
  display: grid;
  gap: var(--zs-space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

li {
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  padding: 9px;
  background: var(--zs-color-surface-soft);
}

.item-content {
  display: grid;
  gap: 3px;
}

li strong {
  color: var(--zs-color-text);
  font-size: 0.86rem;
}

li small,
.empty-message {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
}

a {
  color: var(--zs-color-primary);
  font-size: 0.8rem;
  font-weight: 800;
  text-decoration: none;
  white-space: nowrap;
}

.item-actions {
  flex: 0 0 auto;
}

.add-form {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) minmax(0, 1fr) auto;
  gap: var(--zs-space-2);
}

.state-message,
.error-message,
.success-message {
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: 10px;
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
  text-align: center;
}

.error-message {
  border-color: var(--zs-color-danger);
  color: var(--zs-color-danger);
}

.success-message {
  border-color: var(--zs-color-success);
  color: var(--zs-color-success);
}

@media (max-width: 960px) {
  .add-form {
    grid-template-columns: 1fr;
  }
}
</style>
