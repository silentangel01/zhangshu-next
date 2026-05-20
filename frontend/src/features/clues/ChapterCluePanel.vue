<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

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

const props = defineProps<{
  projectId: string
  chapterId: string | null
}>()

const links = ref<ChapterClueLink[]>([])
const projectClues = ref<Clue[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const showBindForm = ref(false)
const editingLinkId = ref('')

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

onMounted(() => {
  void refreshPanel()
})

watch(
  () => props.chapterId,
  () => {
    resetForm()
    editingLinkId.value = ''
    void refreshPanel()
  },
)

async function refreshPanel() {
  if (!props.chapterId) {
    links.value = []
    await loadProjectClues()
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    const [chapterLinks] = await Promise.all([listChapterClues(props.chapterId), loadProjectClues()])
    links.value = chapterLinks
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

function startEdit(link: ChapterClueLink) {
  editingLinkId.value = link.id
  editForm.relation_type = link.relation_type
  editForm.note = link.note
}

async function handleUpdateLink(link: ChapterClueLink) {
  isSaving.value = true
  errorMessage.value = ''

  try {
    await updateChapterClue(link.id, {
      relation_type: editForm.relation_type,
      note: editForm.note,
    })
    editingLinkId.value = ''
    await refreshPanel()
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
        <h2>伏笔追踪</h2>
      </div>
      <RouterLink class="library-link" :to="`/projects/${projectId}/clues`">打开伏笔库</RouterLink>
    </header>

    <p v-if="!chapterId" class="state-message">请选择章节后查看本章伏笔。</p>

    <template v-else>
      <div class="panel-actions">
        <button class="secondary-button" type="button" @click="showBindForm = !showBindForm">
          {{ showBindForm ? '收起绑定' : '绑定伏笔' }}
        </button>
      </div>

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
          <span>关系类型</span>
          <select v-model="form.relation_type">
            <option v-for="relation in relationTypes" :key="relation" :value="relation">
              {{ chapterClueRelationLabels[relation] }}
            </option>
          </select>
        </label>

        <label>
          <span>备注</span>
          <textarea v-model="form.note" rows="3" placeholder="例如：本章首次埋下旧地图线索。" />
        </label>

        <button class="primary-button" type="submit" :disabled="isSaving || !form.clue_id">
          {{ isSaving ? '正在保存…' : '保存绑定' }}
        </button>
      </form>

      <p v-if="isLoading" class="state-message">正在加载本章伏笔…</p>
      <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      <p v-else-if="links.length === 0" class="state-message">本章尚未绑定伏笔。</p>

      <ul v-else class="clue-list">
        <li v-for="link in links" :key="link.id" class="clue-card">
          <header>
            <div>
              <h3>{{ link.clue.title }}</h3>
              <p class="meta">
                {{ chapterClueRelationLabels[link.relation_type] }} ·
                {{ clueStatusLabels[link.clue.status] }} ·
                {{ clueVisibilityLabels[link.clue.visibility] }} ·
                {{ clueImportanceLabels[link.clue.importance] }}
              </p>
            </div>
            <div class="card-actions">
              <button class="secondary-button compact" type="button" :disabled="isSaving" @click="startEdit(link)">
                编辑
              </button>
              <button class="remove-button compact" type="button" :disabled="isSaving" @click="handleRemoveLink(link)">
                移除
              </button>
            </div>
          </header>

          <p v-if="link.clue.description" class="summary">{{ link.clue.description }}</p>
          <p v-if="link.clue.payoff_plan" class="summary">回收计划：{{ link.clue.payoff_plan }}</p>
          <p v-if="link.note" class="note">备注：{{ link.note }}</p>

          <form v-if="editingLinkId === link.id" class="edit-form" @submit.prevent="handleUpdateLink(link)">
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
              <textarea v-model="editForm.note" rows="3" />
            </label>
            <div class="edit-actions">
              <button class="secondary-button" type="button" @click="editingLinkId = ''">取消</button>
              <button class="primary-button" type="submit" :disabled="isSaving">保存</button>
            </div>
          </form>
        </li>
      </ul>
    </template>
  </section>
</template>

<style scoped>
.chapter-clue-panel {
  display: grid;
  gap: 12px;
}

.panel-header,
.clue-card header,
.edit-actions {
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

.bind-form,
.edit-form {
  display: grid;
  gap: 10px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 12px;
  background: #fbfcfe;
}

label {
  display: grid;
  gap: 6px;
  color: #4b5563;
  font-size: 0.9rem;
  font-weight: 800;
}

select,
textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 9px 10px;
  color: #111827;
  font: inherit;
}

textarea {
  resize: vertical;
  line-height: 1.6;
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

.clue-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.clue-card {
  display: grid;
  gap: 8px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
}

.card-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 6px;
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

button {
  min-height: 34px;
  border-radius: 6px;
  border: 1px solid transparent;
  padding: 0 10px;
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

.remove-button {
  border-color: #fecaca;
  background: #fff7f7;
  color: #b42318;
}

.compact {
  min-height: 30px;
  padding: 0 8px;
}
</style>
