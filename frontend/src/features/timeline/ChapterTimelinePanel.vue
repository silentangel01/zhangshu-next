<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

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
const isLoading = ref(false)
const errorMessage = ref('')

onMounted(() => {
  void refreshPanel()
})

watch(
  () => props.chapterId,
  () => {
    void refreshPanel()
  },
)

async function refreshPanel() {
  if (!props.chapterId) {
    events.value = []
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    events.value = await listChapterTimelineEvents(props.chapterId)
  } catch (error) {
    void error
    errorMessage.value = '加载本章时间轴失败。'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <section class="chapter-timeline-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">本章时间轴</p>
        <h2>时间轴事件</h2>
      </div>
      <RouterLink class="library-link" :to="`/projects/${projectId}/timeline`">打开时间轴</RouterLink>
    </header>

    <p v-if="!chapterId" class="state-message">请选择章节后查看本章时间轴事件。</p>

    <template v-else>
      <p v-if="isLoading" class="state-message">正在加载本章时间轴…</p>
      <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      <p v-else-if="events.length === 0" class="state-message">本章尚未绑定时间轴事件。</p>

      <ul v-else class="event-list">
        <li v-for="event in events" :key="event.id" class="event-card">
          <header>
            <div>
              <h3>{{ event.title }}</h3>
              <p class="meta">
                {{ timelineEventTypeLabels[event.event_type] }} ·
                {{ timelineEventImportanceLabels[event.importance] }} ·
                {{ timelineEventStatusLabels[event.status] }}
              </p>
              <p class="meta">
                {{ event.story_date || '未填写日期' }}
                <span v-if="event.story_time"> · {{ event.story_time }}</span>
              </p>
            </div>
          </header>

          <p v-if="event.description" class="summary">{{ event.description }}</p>
          <p v-if="event.note" class="note">备注：{{ event.note }}</p>
        </li>
      </ul>
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
  font-size: 0.96rem;
}

.library-link {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 0 10px;
  background: #ffffff;
  color: #2563eb;
  font-size: 0.86rem;
  font-weight: 800;
  text-decoration: none;
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

.event-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.event-card {
  display: grid;
  gap: 8px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
}

.meta {
  margin-top: 4px;
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 800;
}

.summary,
.note {
  color: #374151;
  line-height: 1.7;
  white-space: pre-wrap;
}
</style>
