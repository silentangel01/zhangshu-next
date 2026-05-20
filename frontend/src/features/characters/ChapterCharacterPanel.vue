<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'

import {
  addChapterCharacter,
  deleteChapterCharacter,
  listChapterCharacters,
  updateChapterCharacter,
} from '@/entities/chapter-character/api'
import type {
  ChapterCharacterLink,
  ChapterCharacterRelationType,
} from '@/entities/chapter-character/types'
import { chapterCharacterRelationLabels } from '@/entities/chapter-character/types'
import { listProjectCharacters } from '@/entities/character/api'
import type { Character } from '@/entities/character/types'
import {
  characterImportanceLabels,
  characterRoleLabels,
  characterStatusLabels,
} from '@/entities/character/types'

const props = defineProps<{
  projectId: string
  chapterId: string | null
}>()

const links = ref<ChapterCharacterLink[]>([])
const projectCharacters = ref<Character[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const showBindForm = ref(false)
const selectedLinkId = ref<string | null>(null)

const relationTypes: ChapterCharacterRelationType[] = [
  'appears',
  'mentioned',
  'pov',
  'conflict',
  'supports',
]

const form = reactive({
  character_id: '',
  relation_type: 'appears' as ChapterCharacterRelationType,
  note: '',
})

const editForm = reactive({
  relation_type: 'appears' as ChapterCharacterRelationType,
  note: '',
})

const selectedLink = ref<ChapterCharacterLink | null>(null)

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
    await loadProjectCharacters()
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    const [chapterLinks] = await Promise.all([
      listChapterCharacters(props.chapterId),
      loadProjectCharacters(),
    ])
    links.value = chapterLinks
    selectedLink.value = chapterLinks.find((link) => link.id === selectedLinkId.value) ?? null
    if (!selectedLink.value) {
      selectedLinkId.value = null
    }
  } catch (error) {
    void error
    errorMessage.value = '加载本章人物失败。'
  } finally {
    isLoading.value = false
  }
}

async function loadProjectCharacters() {
  if (!props.projectId) {
    return
  }
  projectCharacters.value = await listProjectCharacters(props.projectId)
}

function selectLink(link: ChapterCharacterLink) {
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
  if (!props.chapterId || !form.character_id) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    await addChapterCharacter(props.chapterId, {
      character_id: form.character_id,
      relation_type: form.relation_type,
      note: form.note,
    })
    resetForm()
    showBindForm.value = false
    await refreshPanel()
  } catch (error) {
    void error
    errorMessage.value = '绑定人物失败。'
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
    const updated = await updateChapterCharacter(selectedLink.value.id, {
      relation_type: editForm.relation_type,
      note: editForm.note,
    })
    links.value = links.value.map((link) => (link.id === updated.id ? updated : link))
    selectedLink.value = updated
  } catch (error) {
    void error
    errorMessage.value = '更新人物关联失败。'
  } finally {
    isSaving.value = false
  }
}

async function handleRemoveLink(link: ChapterCharacterLink) {
  const confirmed = window.confirm('确认从本章移除该人物关联吗？')
  if (!confirmed) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    await deleteChapterCharacter(link.id)
    await refreshPanel()
    if (selectedLinkId.value === link.id) {
      backToList()
    }
  } catch (error) {
    void error
    errorMessage.value = '移除人物关联失败。'
  } finally {
    isSaving.value = false
  }
}

function resetForm() {
  form.character_id = ''
  form.relation_type = 'appears'
  form.note = ''
}
</script>

<template>
  <section class="chapter-character-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">本章人物</p>
        <h2>人物卡</h2>
      </div>
      <button class="secondary-button" type="button" @click="showBindForm = !showBindForm">
        {{ showBindForm ? '收起绑定' : '绑定人物' }}
      </button>
    </header>

    <p v-if="!chapterId" class="state-message">请选择章节后查看本章人物。</p>

    <template v-else>
      <form v-if="showBindForm" class="bind-form" @submit.prevent="handleAddLink">
        <label>
          <span>人物</span>
          <select v-model="form.character_id" required>
            <option value="">请选择人物</option>
            <option v-for="character in projectCharacters" :key="character.id" :value="character.id">
              {{ character.name }}
            </option>
          </select>
        </label>

        <label>
          <span>本章关联</span>
          <select v-model="form.relation_type">
            <option v-for="relation in relationTypes" :key="relation" :value="relation">
              {{ chapterCharacterRelationLabels[relation] }}
            </option>
          </select>
        </label>

        <label>
          <span>备注</span>
          <textarea v-model="form.note" rows="3" placeholder="例如：本章首次正面出场。"></textarea>
        </label>

        <button class="primary-button" type="submit" :disabled="isSaving || !form.character_id">
          {{ isSaving ? '正在保存……' : '保存绑定' }}
        </button>
      </form>

      <p v-if="isLoading" class="state-message">正在加载本章人物……</p>
      <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>

      <template v-else-if="selectedLink">
        <article class="profile-card">
          <header class="profile-header">
            <div>
              <p class="profile-eyebrow">人物小传摘要</p>
              <h3>{{ selectedLink.character.name }}</h3>
            </div>
            <button class="text-button" type="button" @click="backToList">返回列表</button>
          </header>

          <div class="profile-summary">
            <div>
              <span class="field-label">姓名</span>
              <strong>{{ selectedLink.character.name }}</strong>
            </div>
            <div>
              <span class="field-label">角色定位</span>
              <strong>{{ characterRoleLabels[selectedLink.character.role] }}</strong>
            </div>
            <div>
              <span class="field-label">所属势力</span>
              <strong>{{ selectedLink.character.faction || '未设置' }}</strong>
            </div>
          </div>

          <section class="profile-section">
            <p class="section-label">基本信息</p>
            <p v-if="selectedLink.character.summary" class="text-block">{{ selectedLink.character.summary }}</p>
            <p v-else class="muted-block">暂无简介。</p>
            <p class="tiny-meta">
              {{ characterImportanceLabels[selectedLink.character.importance] }} ·
              {{ characterStatusLabels[selectedLink.character.status] }}
            </p>
          </section>

          <section class="profile-section">
            <p class="section-label">人物小传</p>
            <p v-if="selectedLink.character.biography" class="text-block">{{ selectedLink.character.biography }}</p>
            <p v-else class="muted-block">暂无人物小传摘要。</p>
          </section>

          <section class="profile-section">
            <p class="section-label">本章关联</p>
            <div class="relation-grid">
              <label>
                <span>关系类型</span>
                <select v-model="editForm.relation_type">
                  <option v-for="relation in relationTypes" :key="relation" :value="relation">
                    {{ chapterCharacterRelationLabels[relation] }}
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
        <p v-if="links.length === 0" class="state-message">本章暂无人物</p>

        <ul v-else class="character-list">
          <li v-for="link in links" :key="link.id">
            <button
              class="character-card"
              type="button"
              :class="{ active: selectedLinkId === link.id }"
              @click="selectLink(link)"
            >
              <span class="name">{{ link.character.name }}</span>
              <span class="meta">
                {{ characterRoleLabels[link.character.role] }} ·
                {{ chapterCharacterRelationLabels[link.relation_type] }}
              </span>
              <span v-if="link.character.faction" class="faction">{{ link.character.faction }}</span>
              <span class="summary">{{ link.character.summary || '暂无简介' }}</span>
            </button>
          </li>
        </ul>
      </template>
    </template>
  </section>
</template>

<style scoped>
.chapter-character-panel {
  display: grid;
  gap: 12px;
}

.panel-header,
.profile-header,
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

.secondary-button,
.danger-button,
.text-button {
  min-height: 34px;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 0 10px;
  background: #ffffff;
  font: inherit;
  font-size: 0.8rem;
  font-weight: 800;
  cursor: pointer;
}

.secondary-button,
.text-button {
  color: #2563eb;
}

.danger-button {
  border-color: #fecaca;
  color: #b42318;
}

.bind-form,
.profile-card {
  display: grid;
  gap: 12px;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 14px;
  background: #fbfcfe;
}

.profile-card {
  background: #ffffff;
}

.profile-eyebrow,
.field-label,
.section-label,
.tiny-meta {
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 800;
}

.profile-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 10px;
}

.profile-summary div {
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 10px;
  background: #fbfcfe;
}

.field-label {
  display: block;
  margin-bottom: 4px;
}

.profile-summary strong {
  color: #111827;
  font-size: 0.9rem;
}

.profile-section {
  display: grid;
  gap: 8px;
}

.section-label {
  color: #0f172a;
}

.text-block,
.muted-block {
  color: #334155;
  line-height: 1.7;
  white-space: pre-wrap;
}

.muted-block {
  color: #94a3b8;
}

.relation-grid {
  display: grid;
  gap: 10px;
}

.relation-grid label,
.bind-form label {
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

.character-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.character-card {
  display: grid;
  gap: 4px;
  width: 100%;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
  text-align: left;
}

.character-card.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.name {
  color: #111827;
  font-weight: 800;
}

.meta,
.faction,
.summary {
  color: #64748b;
  font-size: 0.82rem;
}

.summary {
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

.relation-actions {
  justify-content: flex-end;
}
</style>
