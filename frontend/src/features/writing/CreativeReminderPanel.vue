<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { listCreativeReminders } from '@/entities/creative-reminder/api'
import type { CreativeReminder } from '@/entities/creative-reminder/types'

const props = defineProps<{
  projectId: string
  chapterId: string | null
}>()

const reminders = ref<CreativeReminder[]>([])
const isLoading = ref(false)
const errorMessage = ref('')

const severityLabels = {
  info: '提示',
  warning: '注意',
  critical: '重要',
}

const sortedReminders = computed(() => {
  const rank = { critical: 0, warning: 1, info: 2 }
  return [...reminders.value].sort((left, right) => rank[left.severity] - rank[right.severity])
})

watch(
  () => [props.projectId, props.chapterId],
  () => {
    void refresh()
  },
  { immediate: true },
)

async function refresh() {
  if (!props.projectId) {
    reminders.value = []
    return
  }
  isLoading.value = true
  errorMessage.value = ''
  try {
    const result = await listCreativeReminders(props.projectId, {
      scope: props.chapterId ? 'chapter' : 'project',
      chapter_id: props.chapterId || undefined,
    })
    reminders.value = result.items
  } catch (error) {
    void error
    errorMessage.value = '创作提醒加载失败，请稍后重试。'
  } finally {
    isLoading.value = false
  }
}

function targetLink(item: CreativeReminder) {
  const base = `/projects/${props.projectId}`
  if (item.target_type === 'clue') return `${base}/clues`
  if (item.target_type === 'character') return `${base}/characters`
  if (item.target_type === 'outline') return `${base}/outlines`
  if (item.target_type === 'timeline_event') return `${base}/timeline`
  if (item.target_type === 'graph_node') return `${base}/graph?focusNodeId=${encodeURIComponent(item.target_id)}`
  if (item.target_type === 'setting') return `${base}/settings`
  return base
}
</script>

<template>
  <section class="creative-reminder-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">规则提醒</p>
        <h2>{{ chapterId ? '本章提醒' : '全书提醒' }}</h2>
      </div>
      <button type="button" :disabled="isLoading" @click="refresh">刷新</button>
    </header>

    <p class="helper-note">规则提醒，不会自动修改正文。当前仅使用结构化资料和显式绑定，暂未启用智能匹配。</p>

    <p v-if="isLoading" class="state-message">正在加载创作提醒...</p>
    <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    <p v-else-if="sortedReminders.length === 0" class="state-message">暂无提醒</p>

    <div v-else class="reminder-list">
      <article
        v-for="item in sortedReminders"
        :key="item.id"
        class="reminder-card"
        :class="item.severity"
      >
        <div class="card-head">
          <span class="severity">{{ severityLabels[item.severity] }}</span>
          <h3>{{ item.title }}</h3>
        </div>
        <p>{{ item.message }}</p>
        <RouterLink class="target-link" :to="targetLink(item)">{{ item.action_label || '查看目标' }}</RouterLink>
      </article>
    </div>
  </section>
</template>

<style scoped>
.creative-reminder-panel {
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

button {
  min-height: 30px;
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  padding: 0 10px;
  background: #ffffff;
  color: #2563eb;
  font: inherit;
  font-size: 0.8rem;
  font-weight: 800;
  cursor: pointer;
}

.helper-note {
  color: #64748b;
  font-size: 0.78rem;
  line-height: 1.6;
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

.error-message {
  border-color: #fecaca;
  color: #b42318;
}

.reminder-list {
  display: grid;
  gap: 10px;
}

.reminder-card {
  display: grid;
  gap: 8px;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
}

.reminder-card.warning {
  border-color: #facc15;
  background: #fffbeb;
}

.reminder-card.critical {
  border-color: #fca5a5;
  background: #fff1f2;
}

.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.severity {
  border-radius: 999px;
  padding: 2px 7px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 0.72rem;
  font-weight: 800;
}

.reminder-card h3 {
  color: #111827;
  font-size: 0.9rem;
}

.reminder-card p {
  color: #334155;
  font-size: 0.82rem;
  line-height: 1.65;
}

.target-link {
  justify-self: start;
  color: #2563eb;
  font-size: 0.8rem;
  font-weight: 800;
  text-decoration: none;
}
</style>
