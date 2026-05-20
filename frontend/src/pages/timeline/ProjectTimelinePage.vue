<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { listChapters } from '@/entities/chapter/api'
import type { Chapter } from '@/entities/chapter/types'
import { listProjectSettings } from '@/entities/setting/api'
import type { SettingItem } from '@/entities/setting/types'
import { settingItemTypeLabels } from '@/entities/setting/types'
import {
  createTimelineEvent,
  deleteTimelineEvent,
  getTimelineEvent,
  listProjectTimelineEvents,
  updateTimelineEvent,
} from '@/entities/timeline/api'
import type {
  TimelineEvent,
  TimelineEventImportance,
  TimelineEventStatus,
  TimelineEventType,
} from '@/entities/timeline/types'
import {
  timelineEventImportanceLabels,
  timelineEventStatusLabels,
  timelineEventTypeLabels,
} from '@/entities/timeline/types'
import { getProject } from '@/entities/project/api'
import type { Project } from '@/entities/project/types'

const route = useRoute()

const project = ref<Project | null>(null)
const chapters = ref<Chapter[]>([])
const settings = ref<SettingItem[]>([])
const events = ref<TimelineEvent[]>([])
const selectedEvent = ref<TimelineEvent | null>(null)
const isCreating = ref(true)
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const filters = reactive({
  keyword: '',
  event_type: '',
  status: '',
  importance: '',
})

const form = reactive({
  title: '',
  description: '',
  event_type: 'plot' as TimelineEventType,
  story_date: '',
  story_time: '',
  order_index: 0,
  importance: 'normal' as TimelineEventImportance,
  status: 'planned' as TimelineEventStatus,
  chapter_id: '',
  location_setting_id: '',
  note: '',
})

const eventTypes: TimelineEventType[] = [
  'plot',
  'background',
  'character',
  'world',
  'clue',
  'conflict',
  'custom',
]
const importances: TimelineEventImportance[] = ['low', 'normal', 'high', 'critical']
const statuses: TimelineEventStatus[] = ['planned', 'happened', 'revised', 'deprecated']

const projectId = computed<string>(() => {
  const value = route.params.projectId
  return (Array.isArray(value) ? value[0] : value) ?? ''
})

const chapterTitleMap = computed(() => {
  return chapters.value.reduce<Record<string, string>>((acc, chapter) => {
    acc[chapter.id] = chapter.title
    return acc
  }, {})
})

const sortedSettings = computed(() =>
  [...settings.value].sort((left, right) => {
    const leftPriority = left.item_type === 'location' ? 0 : 1
    const rightPriority = right.item_type === 'location' ? 0 : 1
    return (
      leftPriority - rightPriority ||
      left.title.localeCompare(right.title, 'zh-Hans-CN')
    )
  }),
)

const settingTitleMap = computed(() => {
  return settings.value.reduce<Record<string, string>>((acc, setting) => {
    acc[setting.id] = setting.title
    return acc
  }, {})
})

onMounted(() => {
  void loadWorkspace()
})

watch(projectId, () => {
  selectedEvent.value = null
  resetForm()
  void loadWorkspace()
})

async function loadWorkspace() {
  if (!projectId.value) {
    errorMessage.value = '项目 ID 缺失。'
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    const [projectDetail, projectChapters, projectSettings, projectEvents] = await Promise.all([
      getProject(projectId.value),
      listChapters(projectId.value),
      listProjectSettings(projectId.value),
      listProjectTimelineEvents(projectId.value, buildFilters()),
    ])
    project.value = projectDetail
    chapters.value = projectChapters
    settings.value = projectSettings
    events.value = projectEvents
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载时间轴失败。')
  } finally {
    isLoading.value = false
  }
}

async function refreshEvents() {
  if (!projectId.value) {
    return
  }
  events.value = await listProjectTimelineEvents(projectId.value, buildFilters())
  if (selectedEvent.value) {
    selectedEvent.value = events.value.find((event) => event.id === selectedEvent.value?.id) ?? null
  }
}

function buildFilters() {
  return {
    keyword: filters.keyword.trim() || undefined,
    event_type: (filters.event_type || undefined) as TimelineEventType | undefined,
    status: (filters.status || undefined) as TimelineEventStatus | undefined,
    importance: (filters.importance || undefined) as TimelineEventImportance | undefined,
  }
}

async function handleApplyFilters() {
  await saveSafe(async () => {
    await refreshEvents()
  }, '筛选时间轴事件失败。')
}

async function handleSelectEvent(event: TimelineEvent) {
  errorMessage.value = ''
  successMessage.value = ''

  try {
    selectedEvent.value = await getTimelineEvent(event.id)
    isCreating.value = false
    applyEventToForm(selectedEvent.value)
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载时间轴事件详情失败。')
  }
}

function handleNewEvent() {
  selectedEvent.value = null
  isCreating.value = true
  successMessage.value = ''
  errorMessage.value = ''
  resetForm()
}

async function handleSaveEvent() {
  if (!projectId.value) {
    return
  }

  await saveSafe(async () => {
    const payload = {
      title: form.title,
      description: form.description,
      event_type: form.event_type,
      story_date: form.story_date || null,
      story_time: form.story_time || null,
      order_index: Number(form.order_index) || 0,
      importance: form.importance,
      status: form.status,
      chapter_id: form.chapter_id || null,
      location_setting_id: form.location_setting_id || null,
      note: form.note,
    }

    const saved = isCreating.value
      ? await createTimelineEvent(projectId.value, payload)
      : await updateTimelineEvent(selectedEvent.value!.id, payload)

    selectedEvent.value = saved
    isCreating.value = false
    applyEventToForm(saved)
    await refreshEvents()
    successMessage.value = '时间轴事件已保存。'
  }, '保存时间轴事件失败。')
}

async function handleDeleteEvent() {
  if (!selectedEvent.value) {
    return
  }

  const confirmed = window.confirm(`确认删除时间轴事件“${selectedEvent.value.title}”吗？`)
  if (!confirmed) {
    return
  }

  await saveSafe(async () => {
    await deleteTimelineEvent(selectedEvent.value!.id)
    selectedEvent.value = null
    isCreating.value = true
    resetForm()
    await refreshEvents()
    successMessage.value = '时间轴事件已删除。'
  }, '删除时间轴事件失败。')
}

async function saveSafe(action: () => Promise<void>, fallback: string) {
  isSaving.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    await action()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, fallback)
  } finally {
    isSaving.value = false
  }
}

function applyEventToForm(event: TimelineEvent) {
  form.title = event.title
  form.description = event.description
  form.event_type = event.event_type
  form.story_date = event.story_date ?? ''
  form.story_time = event.story_time ?? ''
  form.order_index = event.order_index
  form.importance = event.importance
  form.status = event.status
  form.chapter_id = event.chapter_id ?? ''
  form.location_setting_id = event.location_setting_id ?? ''
  form.note = event.note
}

function resetForm() {
  form.title = ''
  form.description = ''
  form.event_type = 'plot'
  form.story_date = ''
  form.story_time = ''
  form.order_index = 0
  form.importance = 'normal'
  form.status = 'planned'
  form.chapter_id = ''
  form.location_setting_id = ''
  form.note = ''
}

function getChapterTitle(chapterId: string | null, event?: TimelineEvent) {
  if (event?.chapter?.title) {
    return event.chapter.title
  }
  if (!chapterId) {
    return '未绑定'
  }
  return chapterTitleMap.value[chapterId] ?? '未知章节'
}

function getSettingTitle(settingId: string | null, event?: TimelineEvent) {
  if (event?.location_setting?.title) {
    return event.location_setting.title
  }
  if (!settingId) {
    return '未绑定'
  }
  return settingTitleMap.value[settingId] ?? '未知设定'
}

function getSettingLabel(setting: SettingItem) {
  return `${setting.title}（${settingItemTypeLabels[setting.item_type]}）`
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}
</script>

<template>
  <main class="timeline-page">
    <header class="page-header">
      <div>
        <RouterLink class="back-link" :to="`/projects/${projectId}`">返回写作页</RouterLink>
        <p class="eyebrow">故事时间管理</p>
        <h1>时间轴</h1>
        <p class="project-title">{{ project?.title || '正在加载项目…' }}</p>
        <p class="page-note">时间轴用于管理故事事件的先后顺序、发生时间、关联章节和关键剧情节点。</p>
      </div>
      <button class="primary-button" type="button" :disabled="isSaving" @click="handleNewEvent">
        新建事件
      </button>
    </header>

    <section v-if="errorMessage" class="error-banner" role="alert">{{ errorMessage }}</section>
    <section v-if="successMessage" class="success-banner" role="status">{{ successMessage }}</section>
    <section v-if="isLoading" class="state-message">正在加载时间轴…</section>

    <section v-else class="timeline-layout">
      <aside class="list-panel">
        <div class="filters">
          <input v-model="filters.keyword" type="search" placeholder="搜索标题、描述、故事日期、备注" />
          <select v-model="filters.event_type">
            <option value="">全部事件类型</option>
            <option v-for="eventType in eventTypes" :key="eventType" :value="eventType">
              {{ timelineEventTypeLabels[eventType] }}
            </option>
          </select>
          <select v-model="filters.status">
            <option value="">全部状态</option>
            <option v-for="status in statuses" :key="status" :value="status">
              {{ timelineEventStatusLabels[status] }}
            </option>
          </select>
          <select v-model="filters.importance">
            <option value="">全部重要程度</option>
            <option v-for="importance in importances" :key="importance" :value="importance">
              {{ timelineEventImportanceLabels[importance] }}
            </option>
          </select>
          <button class="secondary-button" type="button" :disabled="isSaving" @click="handleApplyFilters">
            筛选
          </button>
        </div>

        <p v-if="events.length === 0" class="empty-state">暂无时间轴事件，请先新建事件。</p>

        <ul v-else class="event-list">
          <li v-for="event in events" :key="event.id">
            <button
              class="event-card"
              type="button"
              :class="{ active: selectedEvent?.id === event.id }"
              @click="handleSelectEvent(event)"
            >
              <span class="name">{{ event.title }}</span>
              <span class="meta">
                {{ timelineEventTypeLabels[event.event_type] }} ·
                {{ timelineEventImportanceLabels[event.importance] }} ·
                {{ timelineEventStatusLabels[event.status] }}
              </span>
              <span class="meta">
                {{ event.story_date || '未填写日期' }}
                <span v-if="event.story_time"> · {{ event.story_time }}</span>
              </span>
              <span class="chapter-line">章节：{{ getChapterTitle(event.chapter_id, event) }}</span>
              <span class="chapter-line">地点：{{ getSettingTitle(event.location_setting_id, event) }}</span>
              <span class="summary">{{ event.description || '暂无描述' }}</span>
            </button>
          </li>
        </ul>
      </aside>

      <form class="editor-panel" @submit.prevent="handleSaveEvent">
        <header class="editor-header">
          <div>
            <p class="eyebrow">{{ isCreating ? '新建事件' : '事件详情' }}</p>
            <h2>{{ form.title || '未命名事件' }}</h2>
          </div>
          <span v-if="selectedEvent" class="version">v{{ selectedEvent.version }}</span>
        </header>

        <div class="form-grid">
          <label>
            <span>标题</span>
            <input v-model.trim="form.title" type="text" required />
          </label>
          <label>
            <span>事件类型</span>
            <select v-model="form.event_type">
              <option v-for="eventType in eventTypes" :key="eventType" :value="eventType">
                {{ timelineEventTypeLabels[eventType] }}
              </option>
            </select>
          </label>
          <label>
            <span>故事日期</span>
            <input v-model.trim="form.story_date" type="text" placeholder="第一卷第一日" />
          </label>
          <label>
            <span>故事时间</span>
            <input v-model.trim="form.story_time" type="text" placeholder="傍晚" />
          </label>
          <label>
            <span>排序序号</span>
            <input v-model.number="form.order_index" type="number" min="0" />
          </label>
          <label>
            <span>重要程度</span>
            <select v-model="form.importance">
              <option v-for="importance in importances" :key="importance" :value="importance">
                {{ timelineEventImportanceLabels[importance] }}
              </option>
            </select>
          </label>
          <label>
            <span>状态</span>
            <select v-model="form.status">
              <option v-for="status in statuses" :key="status" :value="status">
                {{ timelineEventStatusLabels[status] }}
              </option>
            </select>
          </label>
          <label>
            <span>关联章节</span>
            <select v-model="form.chapter_id">
              <option value="">未绑定</option>
              <option v-for="chapter in chapters" :key="chapter.id" :value="chapter.id">
                {{ chapter.title }}
              </option>
            </select>
          </label>
          <label>
            <span>关联地点设定</span>
            <select v-model="form.location_setting_id">
              <option value="">未绑定</option>
              <option v-for="setting in sortedSettings" :key="setting.id" :value="setting.id">
                {{ getSettingLabel(setting) }}
              </option>
            </select>
          </label>
        </div>

        <label>
          <span>描述</span>
          <textarea v-model="form.description" rows="4" />
        </label>

        <label>
          <span>备注</span>
          <textarea v-model="form.note" rows="5" />
        </label>

        <footer class="editor-actions">
          <button
            class="danger-button"
            type="button"
            :disabled="isSaving || isCreating || !selectedEvent"
            @click="handleDeleteEvent"
          >
            删除事件
          </button>
          <button class="primary-button" type="submit" :disabled="isSaving || !form.title.trim()">
            {{ isSaving ? '正在保存…' : '保存事件' }}
          </button>
        </footer>
      </form>
    </section>
  </main>
</template>

<style scoped>
.timeline-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 32px;
  background: #f6f8fb;
  color: #111827;
}

.page-header,
.error-banner,
.success-banner,
.state-message,
.timeline-layout {
  max-width: 1280px;
  margin-right: auto;
  margin-left: auto;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 22px;
}

.back-link {
  display: inline-flex;
  margin-bottom: 14px;
  color: #2563eb;
  font-weight: 800;
  text-decoration: none;
}

.eyebrow,
.project-title,
.page-note {
  margin: 0;
  color: #64748b;
  font-weight: 800;
}

.eyebrow {
  margin-bottom: 6px;
  font-size: 0.78rem;
}

.page-note {
  max-width: 780px;
  margin-top: 10px;
  line-height: 1.7;
  font-weight: 700;
}

h1,
h2 {
  margin: 0;
  line-height: 1.15;
}

h1 {
  margin-bottom: 8px;
  font-size: 2rem;
}

h2 {
  font-size: 1.35rem;
}

.error-banner,
.success-banner {
  box-sizing: border-box;
  margin-bottom: 16px;
  border-radius: 8px;
  padding: 12px 14px;
  font-weight: 800;
}

.error-banner {
  border: 1px solid #f4b4ad;
  background: #fff1f0;
  color: #9f1c12;
}

.success-banner {
  border: 1px solid #bbf7d0;
  background: #f0fdf4;
  color: #047857;
}

.state-message,
.empty-state {
  display: grid;
  place-items: center;
  min-height: 220px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #64748b;
  text-align: center;
}

.timeline-layout {
  display: grid;
  grid-template-columns: minmax(320px, 400px) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.list-panel,
.editor-panel {
  min-width: 0;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 20px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgb(20 24 31 / 6%);
}

.filters {
  display: grid;
  gap: 10px;
  margin-bottom: 14px;
}

input,
select,
textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 10px 12px;
  color: #111827;
  font: inherit;
}

textarea {
  resize: vertical;
  line-height: 1.7;
}

.event-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.event-card {
  display: grid;
  gap: 6px;
  width: 100%;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
  color: #111827;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.event-card.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.name {
  font-size: 1rem;
  font-weight: 800;
}

.meta,
.chapter-line,
.summary {
  color: #64748b;
  font-size: 0.86rem;
  line-height: 1.5;
}

.summary {
  color: #374151;
}

.editor-panel {
  display: grid;
  gap: 16px;
}

.editor-header,
.editor-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

label {
  display: grid;
  gap: 7px;
  color: #4b5563;
  font-weight: 800;
}

.version {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 4px 9px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 0.78rem;
  font-weight: 800;
}

button {
  min-height: 38px;
  border-radius: 6px;
  border: 1px solid transparent;
  padding: 0 14px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.primary-button {
  background: #2563eb;
  color: #ffffff;
}

.secondary-button {
  border-color: #cfd7e3;
  background: #ffffff;
  color: #374151;
}

.danger-button {
  border-color: #fecaca;
  background: #fff7f7;
  color: #b42318;
}

@media (max-width: 860px) {
  .timeline-page {
    padding: 24px 16px;
  }

  .page-header,
  .timeline-layout {
    align-items: stretch;
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }
}
</style>
