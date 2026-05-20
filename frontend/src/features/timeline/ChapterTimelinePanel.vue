<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import { listChapters } from '@/entities/chapter/api'
import type { Chapter } from '@/entities/chapter/types'
import { listProjectSettings } from '@/entities/setting/api'
import type { SettingItem } from '@/entities/setting/types'
import { settingItemTypeLabels } from '@/entities/setting/types'
import { listChapterTimelineEvents } from '@/entities/timeline/api'
import type { TimelineEvent } from '@/entities/timeline/types'
import {
  timelineEventImportanceLabels,
  timelineEventStatusLabels,
  timelineEventTypeLabels,
} from '@/entities/timeline/types'

const props = defineProps<{
  projectId: string
  chapterId: string | null
}>()

const events = ref<TimelineEvent[]>([])
const chapters = ref<Chapter[]>([])
const settings = ref<SettingItem[]>([])
const isLoading = ref(false)
const errorMessage = ref('')
const selectedEventId = ref<string | null>(null)

onMounted(() => {
  void refreshPanel()
})

watch(
  () => props.chapterId,
  () => {
    selectedEventId.value = null
    void refreshPanel()
  },
)

async function refreshPanel() {
  if (!props.chapterId) {
    events.value = []
    await loadReferences()
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    const [chapterEvents] = await Promise.all([
      listChapterTimelineEvents(props.chapterId),
      loadReferences(),
    ])
    events.value = chapterEvents
    if (selectedEventId.value) {
      selectedEventId.value =
        chapterEvents.find((event) => event.id === selectedEventId.value)?.id ?? null
    }
  } catch (error) {
    void error
    errorMessage.value = '加载本章时间轴事件失败。'
  } finally {
    isLoading.value = false
  }
}

async function loadReferences() {
  if (!props.projectId) {
    return
  }

  const [projectChapters, projectSettings] = await Promise.all([
    listChapters(props.projectId),
    listProjectSettings(props.projectId),
  ])
  chapters.value = projectChapters
  settings.value = projectSettings
}

function getChapterTitle(chapterId: string | null, event?: TimelineEvent) {
  if (event?.chapter?.title) {
    return event.chapter.title
  }
  if (!chapterId) {
    return '未绑定'
  }
  return chapters.value.find((chapter) => chapter.id === chapterId)?.title ?? '未知章节'
}

function getSettingTitle(settingId: string | null, event?: TimelineEvent) {
  if (event?.location_setting?.title) {
    return event.location_setting.title
  }
  if (!settingId) {
    return '未绑定'
  }
  return settings.value.find((setting) => setting.id === settingId)?.title ?? '未知设定'
}

function selectEvent(event: TimelineEvent) {
  selectedEventId.value = event.id
}

function backToList() {
  selectedEventId.value = null
}

const selectedEvent = ref<TimelineEvent | null>(null)

watch(
  [events, selectedEventId],
  () => {
    selectedEvent.value = events.value.find((event) => event.id === selectedEventId.value) ?? null
  },
  { immediate: true, deep: true },
)
</script>

<template>
  <section class="chapter-timeline-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">本章时间轴</p>
        <h2>时间序列</h2>
      </div>
    </header>

    <p v-if="!chapterId" class="state-message">请选择章节后查看本章时间轴事件。</p>

    <template v-else>
      <p v-if="isLoading" class="state-message">正在加载本章时间轴事件……</p>
      <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>

      <template v-else-if="selectedEvent">
        <article class="event-detail">
          <header class="event-header">
            <div>
              <p class="event-eyebrow">时间信息</p>
              <h3>{{ selectedEvent.title }}</h3>
            </div>
            <button class="text-button" type="button" @click="backToList">返回列表</button>
          </header>

          <div class="timeline-meta">
            <span>{{ timelineEventTypeLabels[selectedEvent.event_type] }}</span>
            <span>·</span>
            <span>{{ timelineEventImportanceLabels[selectedEvent.importance] }}</span>
            <span>·</span>
            <span>{{ timelineEventStatusLabels[selectedEvent.status] }}</span>
          </div>

          <div class="summary-grid">
            <div>
              <span class="field-label">故事日期</span>
              <strong>{{ selectedEvent.story_date || '未填写' }}</strong>
            </div>
            <div>
              <span class="field-label">故事时间</span>
              <strong>{{ selectedEvent.story_time || '未填写' }}</strong>
            </div>
            <div>
              <span class="field-label">关联章节</span>
              <strong>{{ getChapterTitle(selectedEvent.chapter_id, selectedEvent) }}</strong>
            </div>
            <div>
              <span class="field-label">关联地点设定</span>
              <strong>{{ getSettingTitle(selectedEvent.location_setting_id, selectedEvent) }}</strong>
            </div>
          </div>

          <section class="section-block">
            <p class="section-label">事件描述</p>
            <p v-if="selectedEvent.description" class="text-block">{{ selectedEvent.description }}</p>
            <p v-else class="muted-block">暂无描述。</p>
          </section>

          <section class="section-block">
            <p class="section-label">备注</p>
            <p v-if="selectedEvent.note" class="text-block">{{ selectedEvent.note }}</p>
            <p v-else class="muted-block">暂无备注。</p>
          </section>
        </article>
      </template>

      <template v-else>
        <p v-if="events.length === 0" class="state-message">本章暂无时间轴事件</p>

        <ul v-else class="event-list">
          <li v-for="event in events" :key="event.id">
            <button
              class="event-card"
              type="button"
              :class="{ active: selectedEventId === event.id }"
              @click="selectEvent(event)"
            >
              <div class="event-header">
                <div>
                  <span class="event-title">{{ event.title }}</span>
                  <p class="event-meta">
                    {{ timelineEventTypeLabels[event.event_type] }} ·
                    {{ timelineEventImportanceLabels[event.importance] }} ·
                    {{ timelineEventStatusLabels[event.status] }}
                  </p>
                </div>
                <span class="date-pill">{{ event.story_date || '未填写日期' }}</span>
              </div>

              <p class="event-time">{{ event.story_time || '未填写时间' }}</p>
              <p v-if="event.description" class="summary">{{ event.description }}</p>
            </button>
          </li>
        </ul>
      </template>
    </template>
  </section>
</template>

<style scoped>
.chapter-timeline-panel {
  display: grid;
  gap: 12px;
}

.panel-header,
.event-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
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
  font-size: 1rem;
}

.text-button {
  min-height: 34px;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 0 10px;
  background: #ffffff;
  color: #2563eb;
  font: inherit;
  font-size: 0.8rem;
  font-weight: 800;
  cursor: pointer;
}

.event-detail,
.event-card {
  display: grid;
  gap: 12px;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 14px;
  background: #ffffff;
}

.event-eyebrow,
.field-label,
.section-label,
.event-meta,
.event-time {
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 800;
}

.timeline-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  color: #1e293b;
  font-size: 0.82rem;
  font-weight: 800;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 10px;
}

.summary-grid div {
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 10px;
  background: #fbfcfe;
}

.field-label {
  display: block;
  margin-bottom: 4px;
}

.summary-grid strong {
  color: #111827;
  font-size: 0.9rem;
}

.section-block {
  display: grid;
  gap: 8px;
}

.text-block,
.muted-block,
.summary {
  color: #334155;
  line-height: 1.7;
  white-space: pre-wrap;
}

.muted-block {
  color: #94a3b8;
}

.event-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.event-card {
  width: 100%;
  text-align: left;
  background: linear-gradient(180deg, #ffffff 0%, #fbfcfe 100%);
  box-shadow: inset 3px 0 0 #2563eb;
}

.event-card.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.event-title {
  color: #111827;
  font-weight: 800;
}

.date-pill {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 4px 8px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 0.76rem;
  font-weight: 800;
}

.event-time {
  color: #0f172a;
}

.state-message,
.error-message {
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 14px;
  color: #64748b;
  text-align: center;
}

.error-message {
  border-color: #fecaca;
  color: #b42318;
}
</style>
