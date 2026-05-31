<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import {
  createCharacter,
  deleteCharacter,
  getCharacter,
  listProjectCharacters,
  updateCharacter,
} from '@/entities/character/api'
import { cloudSyncManager } from '@/features/cloud/cloudSyncManager'
import { useDebouncedAutosave } from '@/shared/composables/useDebouncedAutosave'
import type {
  Character,
  CharacterImportance,
  CharacterRole,
  CharacterStatus,
} from '@/entities/character/types'
import {
  characterImportanceLabels,
  characterRoleLabels,
  characterStatusLabels,
} from '@/entities/character/types'
import { getProject } from '@/entities/project/api'
import type { Project } from '@/entities/project/types'
import { ensureMaterialGraphNode, graphFocusRoute } from '@/features/graph/useMaterialGraphNode'
import MaterialLinkPanel from '@/features/material-links/MaterialLinkPanel.vue'

const route = useRoute()
const router = useRouter()

const project = ref<Project | null>(null)
const characters = ref<Character[]>([])
const selectedCharacter = ref<Character | null>(null)
const isCreating = ref(true)
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const filters = reactive({
  keyword: '',
  role: '',
  importance: '',
  status: '',
})

const form = reactive({
  name: '',
  role: 'supporting' as CharacterRole,
  importance: 'normal' as CharacterImportance,
  status: 'active' as CharacterStatus,
  faction: '',
  summary: '',
  biography: '',
  appearance: '',
  personality: '',
  background: '',
  ability: '',
  motivation: '',
  secret: '',
  arc: '',
  notes: '',
})

let isApplyingForm = false
let lastSavedPayload = ''

function buildCharacterPayload() {
  return {
    name: form.name,
    role: form.role,
    importance: form.importance,
    status: form.status,
    faction: form.faction.trim() || null,
    summary: form.summary,
    biography: form.biography,
    appearance: form.appearance,
    personality: form.personality,
    background: form.background,
    ability: form.ability,
    motivation: form.motivation,
    secret: form.secret,
    arc: form.arc,
    notes: form.notes,
  }
}

const autosave = useDebouncedAutosave({
  delayMs: 3000,
  canSave: () =>
    !isCreating.value &&
    selectedCharacter.value !== null &&
    !!projectId.value &&
    form.name.trim() !== '' &&
    !isSaving.value,
  hasChanges: () => JSON.stringify(buildCharacterPayload()) !== lastSavedPayload,
  save: async () => {
    const saved = await updateCharacter(selectedCharacter.value!.id, buildCharacterPayload())
    selectedCharacter.value = saved
    isApplyingForm = true
    applyCharacterToForm(saved)
    isApplyingForm = false
    await refreshCharacters()
    cloudSyncManager.notifyDirty(projectId.value)
    lastSavedPayload = JSON.stringify(buildCharacterPayload())
  },
})

const autosaveStatusText = computed(() => {
  switch (autosave.status.value) {
    case 'dirty': return '有未保存修改'
    case 'saving': return '正在自动保存…'
    case 'saved': return '已自动保存'
    case 'error': return '自动保存失败，请手动保存'
    default: return ''
  }
})

watch(
  () => ({ ...form }),
  () => {
    if (isApplyingForm) return
    autosave.schedule()
  },
  { deep: true },
)

const roles: CharacterRole[] = [
  'protagonist',
  'deuteragonist',
  'antagonist',
  'supporting',
  'minor',
  'unknown',
]
const importances: CharacterImportance[] = ['low', 'normal', 'high', 'critical']
const statuses: CharacterStatus[] = ['active', 'inactive', 'dead', 'missing', 'unknown']

const projectId = computed<string>(() => {
  const value = route.params.projectId
  return (Array.isArray(value) ? value[0] : value) ?? ''
})

onMounted(() => {
  void loadWorkspace()
})

watch(projectId, () => {
  autosave.cancel()
  selectedCharacter.value = null
  lastSavedPayload = ''
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
    const [projectDetail, projectCharacters] = await Promise.all([
      getProject(projectId.value),
      listProjectCharacters(projectId.value, buildFilters()),
    ])
    project.value = projectDetail
    characters.value = projectCharacters
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载人物库失败。')
  } finally {
    isLoading.value = false
  }
}

async function refreshCharacters() {
  if (!projectId.value) {
    return
  }
  characters.value = await listProjectCharacters(projectId.value, buildFilters())
  if (selectedCharacter.value) {
    selectedCharacter.value =
      characters.value.find((character) => character.id === selectedCharacter.value?.id) ?? null
  }
}

function buildFilters() {
  return {
    keyword: filters.keyword.trim() || undefined,
    role: (filters.role || undefined) as CharacterRole | undefined,
    importance: (filters.importance || undefined) as CharacterImportance | undefined,
    status: (filters.status || undefined) as CharacterStatus | undefined,
  }
}

async function handleApplyFilters() {
  await saveSafe(async () => {
    await refreshCharacters()
  }, '筛选人物失败。')
}

async function handleSelectCharacter(character: Character) {
  if (selectedCharacter.value && !isCreating.value) {
    const flushed = await autosave.flush()
    if (!flushed) return
  }

  autosave.cancel()
  errorMessage.value = ''
  successMessage.value = ''

  try {
    selectedCharacter.value = await getCharacter(character.id)
    isCreating.value = false
    isApplyingForm = true
    applyCharacterToForm(selectedCharacter.value)
    isApplyingForm = false
    lastSavedPayload = JSON.stringify(buildCharacterPayload())
    autosave.markSaved()
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '加载人物详情失败。')
  }
}

function handleNewCharacter() {
  autosave.cancel()
  selectedCharacter.value = null
  isCreating.value = true
  successMessage.value = ''
  errorMessage.value = ''
  resetForm()
  lastSavedPayload = ''
}

async function handleSaveCharacter() {
  if (!projectId.value) {
    return
  }

  autosave.cancel()

  await saveSafe(async () => {
    const payload = buildCharacterPayload()

    const saved = isCreating.value
      ? await createCharacter(projectId.value, payload)
      : await updateCharacter(selectedCharacter.value!.id, payload)

    selectedCharacter.value = saved
    isCreating.value = false
    isApplyingForm = true
    applyCharacterToForm(saved)
    isApplyingForm = false
    await refreshCharacters()
    successMessage.value = '人物已保存。'
    cloudSyncManager.notifyDirty(projectId.value)
    lastSavedPayload = JSON.stringify(buildCharacterPayload())
    autosave.markSaved()
  }, '保存人物失败。')
}

async function handleDeleteCharacter() {
  if (!selectedCharacter.value) {
    return
  }

  if (!isCreating.value) {
    const flushed = await autosave.flush()
    if (!flushed) return
  }

  const confirmed = window.confirm(`确认删除人物”${selectedCharacter.value.name}”吗？`)
  if (!confirmed) {
    return
  }

  autosave.cancel()

  await saveSafe(async () => {
    await deleteCharacter(selectedCharacter.value!.id)
    selectedCharacter.value = null
    isCreating.value = true
    resetForm()
    lastSavedPayload = ''
    await refreshCharacters()
    successMessage.value = '人物已删除。'
    cloudSyncManager.notifyDirty(projectId.value)
  }, '删除人物失败。')
}

async function handleOpenGraphNode() {
  if (!selectedCharacter.value || !projectId.value) {
    return
  }
  await saveSafe(async () => {
    const node = await ensureMaterialGraphNode({
      projectId: projectId.value,
      boundType: 'character',
      boundId: selectedCharacter.value!.id,
      nodeType: 'character',
      title: selectedCharacter.value!.name,
      summary: selectedCharacter.value!.summary || selectedCharacter.value!.biography,
    })
    cloudSyncManager.notifyDirty(projectId.value)
    await router.push(graphFocusRoute(projectId.value, node.id))
  }, '打开关系图节点失败。')
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

function applyCharacterToForm(character: Character) {
  form.name = character.name
  form.role = character.role
  form.importance = character.importance
  form.status = character.status
  form.faction = character.faction ?? ''
  form.summary = character.summary
  form.biography = character.biography
  form.appearance = character.appearance
  form.personality = character.personality
  form.background = character.background
  form.ability = character.ability
  form.motivation = character.motivation
  form.secret = character.secret
  form.arc = character.arc
  form.notes = character.notes
}

function resetForm() {
  form.name = ''
  form.role = 'supporting'
  form.importance = 'normal'
  form.status = 'active'
  form.faction = ''
  form.summary = ''
  form.biography = ''
  form.appearance = ''
  form.personality = ''
  form.background = ''
  form.ability = ''
  form.motivation = ''
  form.secret = ''
  form.arc = ''
  form.notes = ''
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}
</script>

<template>
  <main class="characters-page material-page">
    <header class="page-header">
      <div>
        <RouterLink class="back-link" :to="`/projects/${projectId}`">返回写作页</RouterLink>
        <p class="eyebrow">人物资料</p>
        <h1>人物库</h1>
        <p class="project-title">{{ project?.title || '正在加载项目……' }}</p>
      </div>
      <button class="primary-button" type="button" :disabled="isSaving" @click="handleNewCharacter">
        新建人物
      </button>
    </header>

    <section v-if="errorMessage" class="error-banner" role="alert">{{ errorMessage }}</section>
    <section v-if="successMessage" class="success-banner" role="status">{{ successMessage }}</section>
    <section v-if="isLoading" class="state-message">正在加载人物库……</section>

    <section v-else class="characters-layout material-layout">
      <aside class="list-panel material-list-panel">
        <div class="filters">
          <input v-model="filters.keyword" type="search" placeholder="搜索姓名、简介、小传、势力" />
          <select v-model="filters.role">
            <option value="">全部角色</option>
            <option v-for="role in roles" :key="role" :value="role">{{ characterRoleLabels[role] }}</option>
          </select>
          <select v-model="filters.importance">
            <option value="">全部重要程度</option>
            <option v-for="importance in importances" :key="importance" :value="importance">
              {{ characterImportanceLabels[importance] }}
            </option>
          </select>
          <select v-model="filters.status">
            <option value="">全部状态</option>
            <option v-for="status in statuses" :key="status" :value="status">
              {{ characterStatusLabels[status] }}
            </option>
          </select>
          <button class="secondary-button" type="button" :disabled="isSaving" @click="handleApplyFilters">
            筛选
          </button>
        </div>

        <p v-if="characters.length === 0" class="empty-state">暂无人物，请先新建人物。</p>

        <ul v-else class="character-list">
          <li v-for="character in characters" :key="character.id">
            <button
              class="character-card"
              type="button"
              :class="{ active: selectedCharacter?.id === character.id }"
              @click="handleSelectCharacter(character)"
            >
              <span class="name">{{ character.name }}</span>
              <span class="meta">
                {{ characterRoleLabels[character.role] }} ·
                {{ characterImportanceLabels[character.importance] }} ·
                {{ characterStatusLabels[character.status] }}
              </span>
              <span v-if="character.faction" class="faction">{{ character.faction }}</span>
              <span class="summary">{{ character.summary || '暂无简介' }}</span>
            </button>
          </li>
        </ul>
      </aside>

      <form class="editor-panel material-editor-panel" @submit.prevent="handleSaveCharacter">
        <header class="editor-header">
          <div>
            <p class="eyebrow">{{ isCreating ? '新建人物' : '人物卡' }}</p>
            <h2>{{ form.name || '未命名人物' }}</h2>
          </div>
          <span v-if="selectedCharacter" class="version">v{{ selectedCharacter.version }}</span>
        </header>

        <div class="form-grid">
          <label>
            <span>姓名</span>
            <input v-model.trim="form.name" type="text" required />
          </label>
          <label>
            <span>角色定位</span>
            <select v-model="form.role">
              <option v-for="role in roles" :key="role" :value="role">{{ characterRoleLabels[role] }}</option>
            </select>
          </label>
          <label>
            <span>重要程度</span>
            <select v-model="form.importance">
              <option v-for="importance in importances" :key="importance" :value="importance">
                {{ characterImportanceLabels[importance] }}
              </option>
            </select>
          </label>
          <label>
            <span>状态</span>
            <select v-model="form.status">
              <option v-for="status in statuses" :key="status" :value="status">
                {{ characterStatusLabels[status] }}
              </option>
            </select>
          </label>
          <label>
            <span>所属势力</span>
            <input v-model.trim="form.faction" type="text" />
          </label>
        </div>

        <label>
          <span>简介</span>
          <textarea v-model="form.summary" rows="3" />
        </label>
        <label>
          <span>人物小传</span>
          <textarea v-model="form.biography" rows="6" />
        </label>

        <div class="text-grid">
          <label><span>外貌</span><textarea v-model="form.appearance" rows="4" /></label>
          <label><span>性格</span><textarea v-model="form.personality" rows="4" /></label>
          <label><span>背景</span><textarea v-model="form.background" rows="4" /></label>
          <label><span>能力</span><textarea v-model="form.ability" rows="4" /></label>
          <label><span>动机</span><textarea v-model="form.motivation" rows="4" /></label>
          <label><span>秘密</span><textarea v-model="form.secret" rows="4" /></label>
          <label><span>成长线</span><textarea v-model="form.arc" rows="4" /></label>
          <label><span>备注</span><textarea v-model="form.notes" rows="4" /></label>
        </div>

        <footer class="editor-actions">
          <span v-if="!isCreating && autosaveStatusText" class="autosave-status">{{ autosaveStatusText }}</span>
          <button
            class="secondary-button"
            type="button"
            :disabled="isSaving || isCreating || !selectedCharacter"
            @click="handleOpenGraphNode"
          >
            在关系图中查看
          </button>
          <button
            class="danger-button"
            type="button"
            :disabled="isSaving || isCreating || !selectedCharacter"
            @click="handleDeleteCharacter"
          >
            删除人物
          </button>
          <button class="primary-button" type="submit" :disabled="isSaving || !form.name.trim()">
            {{ isSaving ? '正在保存……' : '保存人物' }}
          </button>
        </footer>
      </form>
      <aside class="material-related-panel">
        <MaterialLinkPanel
          v-if="selectedCharacter"
          :project-id="projectId"
          source-type="character"
          :source-id="selectedCharacter.id"
          :source-title="selectedCharacter.name"
        />
        <article v-else class="empty-state related-empty">暂无关联资料</article>
      </aside>
    </section>
  </main>
</template>

<style scoped>
.characters-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 32px;
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.page-header,
.error-banner,
.success-banner,
.state-message,
.characters-layout {
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
  color: var(--zs-color-primary);
  font-weight: 800;
  text-decoration: none;
}

.eyebrow,
.project-title {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-weight: 800;
}

.eyebrow {
  margin-bottom: 6px;
  font-size: 0.78rem;
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
  border: 1px solid var(--zs-color-danger);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
}

.success-banner {
  border: 1px solid var(--zs-color-success);
  background: var(--zs-color-success-soft);
  color: var(--zs-color-success);
}

.state-message,
.empty-state {
  display: grid;
  place-items: center;
  min-height: 220px;
  border: 1px dashed var(--zs-color-border);
  border-radius: 8px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  text-align: center;
}

.characters-layout {
  display: grid;
  grid-template-columns: minmax(280px, 340px) minmax(0, 1fr) minmax(280px, 320px);
  gap: 18px;
  align-items: start;
}

.list-panel,
.editor-panel {
  min-width: 0;
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  padding: 20px;
  background: var(--zs-color-surface);
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
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  padding: 10px 12px;
  color: var(--zs-color-text);
  font: inherit;
}

textarea {
  resize: vertical;
  line-height: 1.7;
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
  gap: 6px;
  width: 100%;
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  padding: 12px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.character-card.active {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
}

.name {
  font-size: 1rem;
  font-weight: 800;
}

.meta,
.faction,
.summary {
  color: var(--zs-color-text-muted);
  font-size: 0.86rem;
  line-height: 1.5;
}

.summary {
  color: var(--zs-color-text);
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

.form-grid,
.text-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

label {
  display: grid;
  gap: 7px;
  color: var(--zs-color-text-muted);
  font-weight: 800;
}

.version {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 4px 9px;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
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
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.secondary-button {
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.danger-button {
  border-color: var(--zs-color-danger);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
}

@media (max-width: 860px) {
  .characters-page {
    padding: 24px 16px;
  }

  .page-header,
  .characters-layout {
    align-items: stretch;
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }
}

.material-page {
  overflow-x: hidden;
  padding: var(--zs-space-6);
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.material-page .page-header,
.material-page .error-banner,
.material-page .success-banner,
.material-page .state-message,
.material-layout {
  max-width: 1480px;
}

.material-page .page-header {
  gap: var(--zs-space-4);
  margin-bottom: var(--zs-space-4);
}

.material-page .back-link {
  margin-bottom: var(--zs-space-2);
  color: var(--zs-color-primary);
}

.material-page .eyebrow,
.material-page .project-title,
.material-page .meta,
.material-page .faction {
  color: var(--zs-color-text-muted);
}

.material-page h1 {
  font-size: 1.6rem;
}

.material-layout {
  display: grid;
  grid-template-columns: minmax(280px, 340px) minmax(0, 1fr) minmax(280px, 320px);
  gap: var(--zs-space-4);
  align-items: start;
}

.material-list-panel,
.material-editor-panel,
.material-related-panel {
  min-width: 0;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-4);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
}

.material-page input,
.material-page select,
.material-page textarea {
  border-color: var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.material-page .character-card {
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.material-page .character-card.active {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
}

.material-page .empty-state,
.material-page .state-message {
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
}

.material-page .error-banner {
  border-color: var(--zs-color-danger);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
}

.material-page .success-banner {
  border-color: var(--zs-color-success);
  background: var(--zs-color-success-soft);
  color: var(--zs-color-success);
}

.material-page .primary-button {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.material-page .secondary-button {
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.material-page .danger-button {
  border-color: var(--zs-color-danger);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
}

.material-page .version {
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
}

@media (max-width: 1366px) {
  .material-page {
    padding: var(--zs-space-4);
  }

  .material-layout {
    grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
  }

  .material-related-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 900px) {
  .material-layout {
    grid-template-columns: 1fr;
  }
}

.autosave-status {
  margin-right: auto;
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
}
</style>
