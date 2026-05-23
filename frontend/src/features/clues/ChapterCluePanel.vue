<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'

import {
  addChapterClue,
  deleteChapterClue,
  listChapterClues,
  updateChapterClue,
} from '@/entities/chapter-clue/api'
import type { ChapterClueLink, ChapterClueRelationType } from '@/entities/chapter-clue/types'
import { chapterClueRelationLabels } from '@/entities/chapter-clue/types'
import { listProjectClues } from '@/entities/clue/api'
import type { Clue } from '@/entities/clue/types'
import { clueImportanceLabels, clueStatusLabels, clueVisibilityLabels } from '@/entities/clue/types'
import { listChapters } from '@/entities/chapter/api'
import type { Chapter } from '@/entities/chapter/types'

const props = defineProps<{
  projectId: string
  chapterId: string | null
}>()

const links = ref<ChapterClueLink[]>([])
const projectClues = ref<Clue[]>([])
const chapters = ref<Chapter[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const showBindForm = ref(false)
const selectedLinkId = ref<string | null>(null)
const selectedLink = ref<ChapterClueLink | null>(null)

const relationTypes: ChapterClueRelationType[] = ['setup', 'mention', 'develop', 'payoff', 'related']

const form = reactive({
  clue_id: '',
  relation_type: 'related' as ChapterClueRelationType,
  note: '',
})

const editForm = reactive({
  relation_type: 'related' as ChapterClueRelationType,
  note: '',
})

const chapterTitleMap = ref<Record<string, string>>({})

onMounted(() => {
  void refreshPanel()
})

watch(
  () => props.chapterId,
  () => {
    resetForm()
    selectedLinkId.value = null
    selectedLink.value = null
    void refreshPanel()
  },
)

async function refreshPanel() {
  if (!props.chapterId) {
    links.value = []
    await loadProjectClues()
    await loadProjectChapters()
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    const [chapterLinks] = await Promise.all([
      listChapterClues(props.chapterId),
      loadProjectClues(),
      loadProjectChapters(),
    ])
    links.value = chapterLinks
    selectedLink.value = chapterLinks.find((link) => link.id === selectedLinkId.value) ?? null
    if (!selectedLink.value) {
      selectedLinkId.value = null
    }
  } catch (error) {
    void error
    errorMessage.value = '加载本章伏笔失败。'
  } finally {
    isLoading.value = false
  }
}

async function loadProjectClues() {
  if (!props.projectId) {
    return
  }
  projectClues.value = await listProjectClues(props.projectId)
}

async function loadProjectChapters() {
  if (!props.projectId) {
    return
  }
  const projectChapters = await listChapters(props.projectId)
  chapters.value = projectChapters
  chapterTitleMap.value = projectChapters.reduce<Record<string, string>>((acc, chapter) => {
    acc[chapter.id] = chapter.title
    return acc
  }, {})
}

function getChapterTitle(chapterId: string | null) {
  if (!chapterId) {
    return '未绑定'
  }
  return chapterTitleMap.value[chapterId] ?? '未知章节'
}

function selectLink(link: ChapterClueLink) {
  selectedLinkId.value = link.id
  selectedLink.value = link
  editForm.relation_type = link.relation_type
  editForm.note = link.note
}

function backToList() {
  selectedLinkId.value = null
  selectedLink.value = null
}

async function handleAddLink() {
  if (!props.chapterId || !form.clue_id) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    await addChapterClue(props.chapterId, {
      clue_id: form.clue_id,
      relation_type: form.relation_type,
      note: form.note,
    })
    resetForm()
    showBindForm.value = false
    await refreshPanel()
  } catch (error) {
    void error
    errorMessage.value = '绑定伏笔失败。'
  } finally {
    isSaving.value = false
  }
}

async function handleUpdateLink() {
  if (!selectedLink.value) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    const updated = await updateChapterClue(selectedLink.value.id, {
      relation_type: editForm.relation_type,
      note: editForm.note,
    })
    links.value = links.value.map((link) => (link.id === updated.id ? updated : link))
    selectedLink.value = updated
  } catch (error) {
    void error
    errorMessage.value = '更新伏笔关联失败。'
  } finally {
    isSaving.value = false
  }
}

async function handleRemoveLink(link: ChapterClueLink) {
  const confirmed = window.confirm('确认从本章移除该伏笔关联吗？')
  if (!confirmed) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    await deleteChapterClue(link.id)
    await refreshPanel()
    if (selectedLinkId.value === link.id) {
      backToList()
    }
  } catch (error) {
    void error
    errorMessage.value = '移除伏笔关联失败。'
  } finally {
    isSaving.value = false
  }
}

function resetForm() {
  form.clue_id = ''
  form.relation_type = 'related'
  form.note = ''
}
</script>

<template>
  <section class="chapter-clue-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">本章伏笔</p>
        <h2>伏笔卡</h2>
      </div>
      <button class="secondary-button" type="button" @click="showBindForm = !showBindForm">
        {{ showBindForm ? '收起绑定' : '绑定伏笔' }}
      </button>
    </header>

    <div class="lifecycle-line" aria-label="伏笔生命周期">
      <span>计划中</span>
      <span>→</span>
      <span>已埋设</span>
      <span>→</span>
      <span>推进中</span>
      <span>→</span>
      <span>已回收</span>
      <span>→</span>
      <span>已废弃</span>
    </div>

    <p v-if="!chapterId" class="state-message">请选择章节后查看本章伏笔。</p>

    <template v-else>
      <form v-if="showBindForm" class="bind-form" @submit.prevent="handleAddLink">
        <label>
          <span>伏笔</span>
          <select v-model="form.clue_id" required>
            <option value="">请选择伏笔</option>
            <option v-for="clue in projectClues" :key="clue.id" :value="clue.id">
              {{ clue.title }}
            </option>
          </select>
        </label>

        <label>
          <span>本章作用</span>
          <select v-model="form.relation_type">
            <option v-for="relation in relationTypes" :key="relation" :value="relation">
              {{ chapterClueRelationLabels[relation] }}
            </option>
          </select>
        </label>

        <label>
          <span>备注</span>
          <textarea v-model="form.note" rows="3" placeholder="例如：本章首次埋下旧地图线索。"></textarea>
        </label>

        <button class="primary-button" type="submit" :disabled="isSaving || !form.clue_id">
          {{ isSaving ? '正在保存……' : '保存绑定' }}
        </button>
      </form>

      <p v-if="isLoading" class="state-message">正在加载本章伏笔……</p>
      <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>

      <template v-else-if="selectedLink">
        <article class="clue-card detail-card">
          <header class="clue-header">
            <div>
              <p class="clue-eyebrow">线索描述</p>
              <h3>{{ selectedLink.clue.title }}</h3>
            </div>
            <button class="text-button" type="button" @click="backToList">返回列表</button>
          </header>

          <div class="status-pipeline">
            <span>{{ clueStatusLabels[selectedLink.clue.status] }}</span>
            <span>·</span>
            <span>{{ clueVisibilityLabels[selectedLink.clue.visibility] }}</span>
            <span>·</span>
            <span>{{ clueImportanceLabels[selectedLink.clue.importance] }}</span>
          </div>

          <div class="summary-grid">
            <div>
              <span class="field-label">埋设章节</span>
              <strong>{{ getChapterTitle(selectedLink.clue.setup_chapter_id) }}</strong>
            </div>
            <div>
              <span class="field-label">回收章节</span>
              <strong>{{ getChapterTitle(selectedLink.clue.payoff_chapter_id) }}</strong>
            </div>
          </div>

          <section class="section-block">
            <p class="section-label">线索描述</p>
            <p v-if="selectedLink.clue.description" class="text-block">{{ selectedLink.clue.description }}</p>
            <p v-else class="muted-block">暂无描述。</p>
          </section>

          <section class="section-block">
            <p class="section-label">回收计划</p>
            <p v-if="selectedLink.clue.payoff_plan" class="text-block">{{ selectedLink.clue.payoff_plan }}</p>
            <p v-else class="muted-block">暂无回收计划。</p>
          </section>

          <section class="section-block">
            <p class="section-label">本章作用</p>
            <div class="relation-grid">
              <label>
                <span>关系类型</span>
                <select v-model="editForm.relation_type">
                  <option v-for="relation in relationTypes" :key="relation" :value="relation">
                    {{ chapterClueRelationLabels[relation] }}
                  </option>
                </select>
              </label>
              <label>
                <span>备注</span>
                <textarea v-model="editForm.note" rows="3"></textarea>
              </label>
            </div>

            <footer class="relation-actions">
              <button class="secondary-button" type="button" :disabled="isSaving" @click="handleUpdateLink">
                保存关联
              </button>
              <button class="danger-button" type="button" :disabled="isSaving" @click="handleRemoveLink(selectedLink)">
                移除
              </button>
            </footer>
          </section>
        </article>
      </template>

      <template v-else>
        <p v-if="links.length === 0" class="state-message">本章暂无伏笔</p>

        <ul v-else class="clue-list">
          <li v-for="link in links" :key="link.id">
            <button
              class="clue-card list-card"
              type="button"
              :class="{ active: selectedLinkId === link.id }"
              @click="selectLink(link)"
            >
              <span class="name">{{ link.clue.title }}</span>
              <span class="meta">
                {{ chapterClueRelationLabels[link.relation_type] }} ·
                {{ clueStatusLabels[link.clue.status] }} ·
                {{ clueVisibilityLabels[link.clue.visibility] }} ·
                {{ clueImportanceLabels[link.clue.importance] }}
              </span>
              <span class="summary">{{ link.clue.description || '暂无描述' }}</span>
              <span class="chapter-line">埋设：{{ getChapterTitle(link.clue.setup_chapter_id) }}</span>
              <span class="chapter-line">回收：{{ getChapterTitle(link.clue.payoff_chapter_id) }}</span>
            </button>
          </li>
        </ul>
      </template>
    </template>
  </section>
</template>

<style scoped>
.chapter-clue-panel {
  display: grid;
  gap: 12px;
}

.panel-header,
.clue-header,
.relation-actions {
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

h3 {
  color: var(--zs-color-text);
  font-size: 0.98rem;
}

.secondary-button,
.danger-button,
.text-button,
.primary-button {
  min-height: 34px;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  padding: 0 10px;
  background: var(--zs-color-surface);
  font: inherit;
  font-size: 0.8rem;
  font-weight: 800;
  cursor: pointer;
}

.secondary-button,
.text-button {
  color: var(--zs-color-primary);
}

.danger-button {
  border-color: var(--zs-color-danger);
  color: var(--zs-color-danger);
}

.primary-button {
  border-color: transparent;
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.lifecycle-line {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  color: var(--zs-color-text);
  font-size: 0.78rem;
  font-weight: 800;
}

.lifecycle-line span {
  padding: 3px 6px;
  border-radius: 999px;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
}

.bind-form,
.detail-card,
.clue-card {
  display: grid;
  gap: 12px;
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  padding: 14px;
  background: var(--zs-color-bg);
}

.detail-card {
  background: var(--zs-color-surface);
}

.clue-eyebrow,
.field-label,
.section-label {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
}

.status-pipeline {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  color: var(--zs-color-text);
  font-size: 0.82rem;
  font-weight: 800;
}

.status-pipeline span {
  padding: 3px 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 10px;
}

.summary-grid div {
  border: 1px solid var(--zs-color-border-soft);
  border-radius: 8px;
  padding: 10px;
  background: var(--zs-color-bg);
}

.field-label {
  display: block;
  margin-bottom: 4px;
}

.summary-grid strong {
  color: var(--zs-color-text);
  font-size: 0.9rem;
}

.section-block {
  display: grid;
  gap: 8px;
}

.text-block,
.muted-block {
  color: var(--zs-color-text);
  line-height: 1.7;
  white-space: pre-wrap;
}

.muted-block {
  color: var(--zs-color-text-faint);
}

.relation-grid {
  display: grid;
  gap: 10px;
}

.relation-grid label,
.bind-form label {
  display: grid;
  gap: 6px;
  color: var(--zs-color-text-muted);
  font-size: 0.9rem;
  font-weight: 800;
}

select,
textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  padding: 9px 10px;
  color: var(--zs-color-text);
  font: inherit;
}

textarea {
  resize: vertical;
  line-height: 1.6;
}

.clue-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.list-card {
  width: 100%;
  text-align: left;
}

.list-card.active {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
}

.name {
  color: var(--zs-color-text);
  font-weight: 800;
}

.meta,
.summary,
.chapter-line {
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
}

.summary,
.chapter-line {
  line-height: 1.6;
}

.state-message,
.error-message {
  border: 1px dashed var(--zs-color-border);
  border-radius: 8px;
  padding: 14px;
  color: var(--zs-color-text-muted);
  text-align: center;
}

.error-message {
  border-color: var(--zs-color-danger);
  color: var(--zs-color-danger);
}

.relation-actions {
  justify-content: flex-end;
}
</style>
