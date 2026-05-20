<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import {
  addChapterCharacter,
  deleteChapterCharacter,
  listChapterCharacters,
} from '@/entities/chapter-character/api'
import type {
  ChapterCharacterLink,
  ChapterCharacterRelationType,
} from '@/entities/chapter-character/types'
import { chapterCharacterRelationLabels } from '@/entities/chapter-character/types'
import { listProjectCharacters } from '@/entities/character/api'
import type { Character } from '@/entities/character/types'
import { characterRoleLabels } from '@/entities/character/types'

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

onMounted(() => {
  void refreshPanel()
})

watch(
  () => props.chapterId,
  () => {
    resetForm()
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
        <h2>人物资料</h2>
      </div>
      <RouterLink class="library-link" :to="`/projects/${projectId}/characters`">打开人物库</RouterLink>
    </header>

    <p v-if="!chapterId" class="state-message">请选择章节后查看本章人物。</p>

    <template v-else>
      <div class="panel-actions">
        <button class="secondary-button" type="button" @click="showBindForm = !showBindForm">
          {{ showBindForm ? '收起绑定' : '绑定人物' }}
        </button>
      </div>

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
          <span>关系类型</span>
          <select v-model="form.relation_type">
            <option v-for="relation in relationTypes" :key="relation" :value="relation">
              {{ chapterCharacterRelationLabels[relation] }}
            </option>
          </select>
        </label>

        <label>
          <span>备注</span>
          <textarea v-model="form.note" rows="3" placeholder="例如：本章首次正式出场。" />
        </label>

        <button class="primary-button" type="submit" :disabled="isSaving || !form.character_id">
          {{ isSaving ? '正在保存……' : '保存绑定' }}
        </button>
      </form>

      <p v-if="isLoading" class="state-message">正在加载本章人物……</p>
      <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      <p v-else-if="links.length === 0" class="state-message">本章尚未绑定人物。</p>

      <ul v-else class="character-list">
        <li v-for="link in links" :key="link.id" class="character-card">
          <header>
            <div>
              <h3>{{ link.character.name }}</h3>
              <p class="meta">
                {{ characterRoleLabels[link.character.role] }} ·
                {{ chapterCharacterRelationLabels[link.relation_type] }}
              </p>
            </div>
            <button class="remove-button" type="button" :disabled="isSaving" @click="handleRemoveLink(link)">
              移除
            </button>
          </header>

          <p v-if="link.character.summary" class="summary">{{ link.character.summary }}</p>
          <p v-if="link.note" class="note">备注：{{ link.note }}</p>
        </li>
      </ul>
    </template>
  </section>
</template>

<style scoped>
.chapter-character-panel {
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

.panel-actions {
  display: flex;
}

.bind-form {
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

.character-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.character-card {
  display: grid;
  gap: 8px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
}

.character-card header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
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
  flex: 0 0 auto;
  border-color: #fecaca;
  background: #fff7f7;
  color: #b42318;
}
</style>
