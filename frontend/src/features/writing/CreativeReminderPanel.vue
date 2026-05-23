<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { listCreativeReminders } from '@/entities/creative-reminder/api'
import type {
  CreativeReminder,
  CreativeReminderSeverity,
  CreativeReminderType,
} from '@/entities/creative-reminder/types'

const props = defineProps<{
  projectId: string
  chapterId: string | null
}>()

const reminders = ref<CreativeReminder[]>([])
const isLoading = ref(false)
const errorMessage = ref('')
const severityFilter = ref<CreativeReminderSeverity | ''>('')
const typeFilter = ref<CreativeReminderType | ''>('')

const severityLabels: Record<CreativeReminderSeverity, string> = {
  info: '提示',
  warning: '注意',
  critical: '重要',
}

const typeLabels: Record<CreativeReminderType, string> = {
  important_clue_unresolved: '伏笔',
  important_character_absent: '人物',
  outline_not_done_for_written_chapter: '大纲',
  timeline_event_missing_chapter: '时间线',
  graph_node_broken_binding: '关系图',
  clue_payoff_without_setup: '伏笔',
  setting_used_but_draft: '设定',
}

const SEVERITY_OPTIONS: { value: CreativeReminderSeverity | ''; label: string }[] = [
  { value: '', label: '全部程度' },
  { value: 'critical', label: '重要' },
  { value: 'warning', label: '注意' },
  { value: 'info', label: '提示' },
]

const TYPE_OPTIONS: { value: CreativeReminderType | ''; label: string }[] = [
  { value: '', label: '全部类型' },
  { value: 'important_clue_unresolved', label: '伏笔' },
  { value: 'important_character_absent', label: '人物' },
  { value: 'outline_not_done_for_written_chapter', label: '大纲' },
  { value: 'timeline_event_missing_chapter', label: '时间线' },
  { value: 'graph_node_broken_binding', label: '关系图' },
  { value: 'clue_payoff_without_setup', label: '伏笔回收' },
  { value: 'setting_used_but_draft', label: '设定' },
]

const filteredReminders = computed(() => {
  const severityRank: Record<CreativeReminderSeverity, number> = { critical: 0, warning: 1, info: 2 }
  let items = reminders.value

  if (severityFilter.value) {
    items = items.filter((item) => item.severity === severityFilter.value)
  }
  if (typeFilter.value) {
    items = items.filter((item) => item.type === typeFilter.value)
  }

  return [...items].sort((left, right) => {
    const severityDiff = severityRank[left.severity] - severityRank[right.severity]
    if (severityDiff !== 0) return severityDiff
    const leftHasChapter = left.chapter_id !== null ? 0 : 1
    const rightHasChapter = right.chapter_id !== null ? 0 : 1
    return leftHasChapter - rightHasChapter
  })
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
        <p class="total-count">共 {{ filteredReminders.length }} 条提醒</p>
      </div>
      <button class="zs-button zs-button-ghost" type="button" :disabled="isLoading" @click="refresh">
        刷新
      </button>
    </header>

    <p class="helper-note">规则提醒，不会自动修改正文。当前仅使用结构化资料和显式绑定，暂未启用智能匹配。</p>

    <div class="filter-bar">
      <label class="zs-field filter-field">
        <span class="zs-field-label">程度</span>
        <select v-model="severityFilter">
          <option v-for="opt in SEVERITY_OPTIONS" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </label>
      <label class="zs-field filter-field">
        <span class="zs-field-label">类型</span>
        <select v-model="typeFilter">
          <option v-for="opt in TYPE_OPTIONS" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </label>
    </div>

    <p v-if="isLoading" class="state-message">正在加载创作提醒...</p>
    <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    <p v-else-if="filteredReminders.length === 0" class="state-message">
      当前规则未发现需要处理的提醒
    </p>

    <div v-else class="reminder-list">
      <article
        v-for="item in filteredReminders"
        :key="item.id"
        class="reminder-card"
        :class="item.severity"
      >
        <div class="card-head">
          <span class="severity" :class="item.severity">{{ severityLabels[item.severity] }}</span>
          <span class="scope-label">{{ item.scope_label }}</span>
          <h3>{{ item.title }}</h3>
        </div>

        <p class="message">{{ item.message }}</p>

        <div class="advice-block">
          <p class="advice-row">
            <span class="advice-key">为什么提醒</span>
            <span>{{ item.reason }}</span>
          </p>
          <p class="advice-row">
            <span class="advice-key">建议处理</span>
            <span>{{ item.suggestion }}</span>
          </p>
        </div>

        <p v-if="item.context_summary" class="context-summary">{{ item.context_summary }}</p>

        <RouterLink class="target-link" :to="targetLink(item)">
          {{ item.action_label || '查看目标' }}
        </RouterLink>
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
  color: var(--zs-color-text-muted);
  font-size: 0.75rem;
  font-weight: 800;
}

h2 {
  color: var(--zs-color-text);
  font-size: 1rem;
}

.total-count {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  margin-top: 2px;
}

.helper-note {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  line-height: 1.6;
}

.filter-bar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-field {
  flex: 1;
  min-width: 120px;
}

.filter-field select {
  min-height: 32px;
  padding: 0 8px;
  font-size: 0.84rem;
}

.state-message,
.error-message {
  border: 1px dashed var(--zs-color-border);
  border-radius: 8px;
  padding: 14px;
  color: var(--zs-color-text-muted);
  line-height: 1.6;
  text-align: center;
}

.error-message {
  border-color: var(--zs-color-danger);
  color: var(--zs-color-danger);
}

.reminder-list {
  display: grid;
  gap: 10px;
}

.reminder-card {
  display: grid;
  gap: 8px;
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  padding: 12px;
  background: var(--zs-color-surface);
}

.reminder-card.warning {
  border-color: var(--zs-color-warning);
  background: var(--zs-color-warning-soft);
}

.reminder-card.critical {
  border-color: var(--zs-color-danger);
  background: var(--zs-color-danger-soft);
}

.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.severity {
  border-radius: 999px;
  padding: 2px 7px;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
  font-size: 0.72rem;
  font-weight: 800;
}

.severity.warning {
  background: var(--zs-color-warning-soft);
  color: var(--zs-color-warning);
}

.severity.critical {
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
}

.scope-label {
  color: var(--zs-color-text-faint);
  font-size: 0.72rem;
  font-weight: 700;
}

.reminder-card h3 {
  color: var(--zs-color-text);
  font-size: 0.9rem;
}

.message {
  color: var(--zs-color-text);
  font-size: 0.82rem;
  line-height: 1.65;
}

.advice-block {
  display: grid;
  gap: 6px;
  border-top: 1px solid var(--zs-color-border-soft);
  padding-top: 8px;
}

.advice-row {
  display: grid;
  gap: 4px;
  color: var(--zs-color-text);
  font-size: 0.8rem;
  line-height: 1.6;
}

.advice-key {
  color: var(--zs-color-text-muted);
  font-size: 0.72rem;
  font-weight: 800;
}

.context-summary {
  color: var(--zs-color-text-faint);
  font-size: 0.76rem;
  line-height: 1.5;
}

.target-link {
  justify-self: start;
  color: var(--zs-color-primary);
  font-size: 0.8rem;
  font-weight: 800;
  text-decoration: none;
}

.target-link:hover {
  text-decoration: underline;
}
</style>
