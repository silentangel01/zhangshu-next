<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import {
  createCharacter,
  deleteCharacter,
  getCharacter,
  listProjectCharacters,
  updateCharacter,
} from '@/entities/character/api'
import type {
  Character,
  CharacterImportance,
  CharacterProfileDimension,
  CharacterProfileSection,
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
import { cloudSyncManager } from '@/features/cloud/cloudSyncManager'
import {
  createDefaultProfileDimensions,
  legacyFieldsToSections,
  sectionsToLegacyFields,
} from '@/features/characters/characterProfileDefaults'
import {
  FACTION_INPUT_DELIMITERS,
  formatFactionDisplay,
  formatFactionTags,
  parseFactionTags,
} from '@/features/characters/characterFactionTags'
import CharacterDimensionRadar from '@/features/characters/CharacterDimensionRadar.vue'
import CharacterProfileSections from '@/features/characters/CharacterProfileSections.vue'
import { ensureMaterialGraphNode, graphFocusRoute } from '@/features/graph/useMaterialGraphNode'
import MaterialLinkPanel from '@/features/material-links/MaterialLinkPanel.vue'
import { useDebouncedAutosave } from '@/shared/composables/useDebouncedAutosave'

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
  profile_sections: [] as CharacterProfileSection[],
  profile_dimensions: [] as CharacterProfileDimension[],
})

let isApplyingForm = false
let lastSavedPayload = ''
let initialQueryHandled = false

// ---------------------------------------------------------------------------
// Filter menu (task #30)
// ---------------------------------------------------------------------------

const isFilterMenuOpen = ref(false)
const filterMenuRef = ref<HTMLElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)

const activeFilterCount = computed(() => {
  let count = 0
  if (filters.role) count++
  if (filters.importance) count++
  if (filters.status) count++
  return count
})

function toggleFilterMenu() {
  isFilterMenuOpen.value = !isFilterMenuOpen.value
}

async function handleApplyFiltersFromMenu() {
  isFilterMenuOpen.value = false
  await handleApplyFilters()
}

function handleResetSecondaryFilters() {
  filters.role = ''
  filters.importance = ''
  filters.status = ''
}

function handleFilterMenuClickOutside(event: MouseEvent) {
  if (!isFilterMenuOpen.value) return
  const el = filterMenuRef.value
  if (el && !el.contains(event.target as Node)) {
    isFilterMenuOpen.value = false
  }
}

async function handleSearchSubmit() {
  await handleApplyFilters()
}

// ---------------------------------------------------------------------------
// Panel collapse (task #32)
// ---------------------------------------------------------------------------

const isLeftPanelCollapsed = ref(false)
const isRightPanelCollapsed = ref(false)

function toggleLeftPanel() {
  isLeftPanelCollapsed.value = !isLeftPanelCollapsed.value
}

function toggleRightPanel() {
  isRightPanelCollapsed.value = !isRightPanelCollapsed.value
}

const layoutClasses = computed(() => ({
  'left-collapsed': isLeftPanelCollapsed.value,
  'right-collapsed': isRightPanelCollapsed.value,
}))

// ---------------------------------------------------------------------------
// Grouped characters (task #31)
// ---------------------------------------------------------------------------

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

const collapsedGroups = reactive<Record<string, boolean>>({})

const groupedCharacters = computed(() => {
  const groups: Array<{ role: CharacterRole; label: string; characters: Character[] }> = []
  for (const role of roles) {
    const items = characters.value.filter((c) => c.role === role)
    if (items.length > 0) {
      groups.push({ role, label: characterRoleLabels[role], characters: items })
    }
  }
  return groups
})

function isGroupCollapsed(role: string): boolean {
  return collapsedGroups[role] === true
}

function toggleGroup(role: string) {
  collapsedGroups[role] = !collapsedGroups[role]
}

// ---------------------------------------------------------------------------
// Faction tags (task #33)
// ---------------------------------------------------------------------------

const factionTags = ref<string[]>([])
const factionInput = ref('')
const factionInputRef = ref<HTMLInputElement | null>(null)

function syncFactionTagsFromForm() {
  factionTags.value = parseFactionTags(form.faction)
  factionInput.value = ''
}

function commitFactionTags() {
  form.faction = formatFactionTags(factionTags.value) ?? ''
}

function addFactionTag(raw: string) {
  const tag = raw.trim()
  if (!tag) return
  if (factionTags.value.includes(tag)) return
  factionTags.value.push(tag)
  factionInput.value = ''
  commitFactionTags()
}

function removeFactionTag(index: number) {
  factionTags.value.splice(index, 1)
  commitFactionTags()
}

function handleFactionKeydown(event: KeyboardEvent) {
  if (FACTION_INPUT_DELIMITERS.includes(event.key)) {
    event.preventDefault()
    addFactionTag(factionInput.value)
  }
}

function handleFactionBlur() {
  if (factionInput.value.trim()) {
    addFactionTag(factionInput.value)
  }
}

function getCharacterFactionDisplay(character: Character) {
  return formatFactionDisplay(parseFactionTags(character.faction))
}

// ---------------------------------------------------------------------------
// Form & data
// ---------------------------------------------------------------------------

function buildCharacterPayload() {
  const legacyFromSections = sectionsToLegacyFields(form.profile_sections)
  return {
    name: form.name,
    role: form.role,
    importance: form.importance,
    status: form.status,
    faction: form.faction.trim() || null,
    summary: form.summary,
    biography: form.biography,
    appearance: legacyFromSections.appearance ?? form.appearance,
    personality: legacyFromSections.personality ?? form.personality,
    background: legacyFromSections.background ?? form.background,
    ability: legacyFromSections.ability ?? form.ability,
    motivation: legacyFromSections.motivation ?? form.motivation,
    secret: legacyFromSections.secret ?? form.secret,
    arc: legacyFromSections.arc ?? form.arc,
    notes: legacyFromSections.notes ?? form.notes,
    profile_sections: form.profile_sections,
    profile_dimensions: form.profile_dimensions,
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

const projectId = computed<string>(() => {
  const value = route.params.projectId
  return (Array.isArray(value) ? value[0] : value) ?? ''
})

onMounted(() => {
  document.addEventListener('click', handleFilterMenuClickOutside, true)
  void loadWorkspace()
})

onUnmounted(() => {
  document.removeEventListener('click', handleFilterMenuClickOutside, true)
})

watch(projectId, () => {
  autosave.cancel()
  selectedCharacter.value = null
  lastSavedPayload = ''
  resetForm()
  initialQueryHandled = false
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

    if (!initialQueryHandled) {
      initialQueryHandled = true
      const queryId = route.query.characterId
      if (typeof queryId === 'string' && queryId) {
        const target = characters.value.find(c => c.id === queryId)
        if (target) {
          await handleSelectCharacter(target)
        }
      }
    }
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

  const confirmed = window.confirm(`确认删除人物"${selectedCharacter.value.name}"吗？`)
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
    await router.push(
      graphFocusRoute(projectId.value, node.id, {
        returnTo: 'characters',
        returnId: selectedCharacter.value!.id,
        returnLabel: selectedCharacter.value!.name,
      }),
    )
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

  if (character.profile_sections && character.profile_sections.length > 0) {
    form.profile_sections = character.profile_sections
  } else {
    form.profile_sections = legacyFieldsToSections(character)
  }

  if (character.profile_dimensions && character.profile_dimensions.length > 0) {
    form.profile_dimensions = character.profile_dimensions
  } else {
    form.profile_dimensions = createDefaultProfileDimensions()
  }

  syncFactionTagsFromForm()
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
  form.profile_sections = []
  form.profile_dimensions = createDefaultProfileDimensions()
  syncFactionTagsFromForm()
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
      <div class="header-toolbar">
        <form class="header-search" @submit.prevent="handleSearchSubmit">
          <input
            ref="searchInputRef"
            v-model="filters.keyword"
            type="search"
            placeholder="搜索姓名、简介、资料、势力"
            class="search-input"
          />
        </form>
        <div ref="filterMenuRef" class="filter-menu-wrapper">
          <button
            class="secondary-button filter-toggle"
            type="button"
            :disabled="isSaving"
            @click.stop="toggleFilterMenu"
          >
            筛选
            <span v-if="activeFilterCount > 0" class="filter-badge">{{ activeFilterCount }}</span>
          </button>
          <div v-if="isFilterMenuOpen" class="filter-menu">
            <label class="filter-field">
              <span>角色定位</span>
              <select v-model="filters.role">
                <option value="">全部</option>
                <option v-for="role in roles" :key="role" :value="role">
                  {{ characterRoleLabels[role] }}
                </option>
              </select>
            </label>
            <label class="filter-field">
              <span>重要程度</span>
              <select v-model="filters.importance">
                <option value="">全部</option>
                <option v-for="imp in importances" :key="imp" :value="imp">
                  {{ characterImportanceLabels[imp] }}
                </option>
              </select>
            </label>
            <label class="filter-field">
              <span>状态</span>
              <select v-model="filters.status">
                <option value="">全部</option>
                <option v-for="st in statuses" :key="st" :value="st">
                  {{ characterStatusLabels[st] }}
                </option>
              </select>
            </label>
            <div class="filter-actions">
              <button
                class="secondary-button"
                type="button"
                @click="handleResetSecondaryFilters"
              >
                重置
              </button>
              <button class="primary-button" type="button" @click="handleApplyFiltersFromMenu">
                应用
              </button>
            </div>
          </div>
        </div>
        <button
          class="primary-button"
          type="button"
          :disabled="isSaving"
          @click="handleNewCharacter"
        >
          新建人物
        </button>
      </div>
    </header>

    <section v-if="errorMessage" class="error-banner" role="alert">{{ errorMessage }}</section>
    <section v-if="successMessage" class="success-banner" role="status">{{ successMessage }}</section>
    <section v-if="isLoading" class="state-message">正在加载人物库……</section>

    <section v-else class="characters-layout material-layout" :class="layoutClasses">
      <!-- Left panel: character list / rail -->
      <Transition name="panel-fold" mode="out-in">
      <aside v-if="!isLeftPanelCollapsed" key="left-panel" class="list-panel material-list-panel">
        <header class="panel-header">
          <span class="panel-title">人物列表</span>
          <span class="panel-count">{{ characters.length }}</span>
          <button class="collapse-btn" type="button" title="收起列表" @click="toggleLeftPanel">◀</button>
        </header>

        <div class="character-tree-scroll">
          <p v-if="characters.length === 0" class="empty-state">暂无人物，请先新建人物。</p>

          <template v-else>
            <div v-for="group in groupedCharacters" :key="group.role" class="character-group">
              <button
                class="group-header"
                type="button"
                @click="toggleGroup(group.role)"
              >
                <span class="group-arrow" :class="{ collapsed: isGroupCollapsed(group.role) }">▾</span>
                <span class="group-label">{{ group.label }}</span>
                <span class="group-count">{{ group.characters.length }}</span>
              </button>

              <Transition name="group-expand">
                <ul v-if="!isGroupCollapsed(group.role)" class="character-list">
                  <li v-for="character in group.characters" :key="character.id">
                    <button
                      class="character-card"
                      type="button"
                      :class="{ active: selectedCharacter?.id === character.id }"
                      @click="handleSelectCharacter(character)"
                    >
                      <div class="card-top">
                        <span class="name">{{ character.name }}</span>
                        <span class="card-tags">
                          <span class="tag tag-role">{{ characterRoleLabels[character.role] }}</span>
                          <span class="tag tag-importance">{{ characterImportanceLabels[character.importance] }}</span>
                          <span class="tag tag-status">{{ characterStatusLabels[character.status] }}</span>
                        </span>
                      </div>
                      <div v-if="character.faction" class="card-faction">
                        <span
                          v-for="tag in getCharacterFactionDisplay(character).visible"
                          :key="tag"
                          class="faction-chip"
                        >{{ tag }}</span>
                        <span v-if="getCharacterFactionDisplay(character).overflow > 0" class="faction-chip faction-overflow">
                          +{{ getCharacterFactionDisplay(character).overflow }}
                        </span>
                      </div>
                      <span class="summary">{{ character.summary || '暂无简介' }}</span>
                    </button>
                  </li>
                </ul>
              </Transition>
            </div>
          </template>
        </div>
      </aside>
      <aside v-else key="left-rail" class="panel-rail left-rail" @click="toggleLeftPanel">
        <span class="rail-label">人物</span>
        <span class="rail-count">{{ characters.length }}</span>
        <button class="collapse-btn" type="button" title="展开列表">▶</button>
      </aside>
      </Transition>

      <!-- Center: editor -->
      <form class="editor-panel material-editor-panel" @submit.prevent="handleSaveCharacter">
        <header class="editor-header">
          <div>
            <p class="eyebrow">{{ isCreating ? '新建人物' : '人物卡' }}</p>
            <h2>{{ form.name || '未命名人物' }}</h2>
          </div>
          <span v-if="selectedCharacter" class="version">v{{ selectedCharacter.version }}</span>
        </header>

        <div class="basic-fields">
          <label class="field-compact">
            <span>姓名</span>
            <input v-model.trim="form.name" type="text" required />
          </label>
          <label class="field-compact">
            <span>角色定位</span>
            <select v-model="form.role">
              <option v-for="role in roles" :key="role" :value="role">{{ characterRoleLabels[role] }}</option>
            </select>
          </label>
          <label class="field-compact">
            <span>重要程度</span>
            <select v-model="form.importance">
              <option v-for="importance in importances" :key="importance" :value="importance">
                {{ characterImportanceLabels[importance] }}
              </option>
            </select>
          </label>
          <label class="field-compact">
            <span>状态</span>
            <select v-model="form.status">
              <option v-for="status in statuses" :key="status" :value="status">
                {{ characterStatusLabels[status] }}
              </option>
            </select>
          </label>
          <div class="field-faction">
            <span class="field-label">所属势力/组织</span>
            <div class="faction-input-container" @click="factionInputRef?.focus()">
              <span
                v-for="(tag, idx) in factionTags"
                :key="tag + idx"
                class="faction-chip"
              >
                {{ tag }}
                <button
                  type="button"
                  class="chip-remove"
                  :disabled="isSaving"
                  @click.stop="removeFactionTag(idx)"
                >✕</button>
              </span>
              <input
                ref="factionInputRef"
                v-model="factionInput"
                type="text"
                class="faction-text-input"
                placeholder="添加势力或组织"
                :disabled="isSaving"
                @keydown="handleFactionKeydown"
                @blur="handleFactionBlur"
              />
            </div>
          </div>
        </div>

        <label class="field-summary">
          <span>简介</span>
          <input v-model="form.summary" type="text" placeholder="一句话简介" />
        </label>

        <label class="field-biography">
          <span>人物记录</span>
          <textarea v-model="form.biography" rows="4" placeholder="自由记录人物备忘、经历、想法等……" />
        </label>

        <CharacterProfileSections
          v-model="form.profile_sections"
          :disabled="isSaving"
        />

        <CharacterDimensionRadar
          v-model="form.profile_dimensions"
          :disabled="isSaving"
        />

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

      <!-- Right panel: related materials / rail -->
      <Transition name="panel-fold" mode="out-in">
      <aside v-if="!isRightPanelCollapsed" key="right-panel" class="material-related-panel">
        <header class="panel-header">
          <span class="panel-title">关联资料</span>
          <button class="collapse-btn" type="button" title="收起关联" @click="toggleRightPanel">▶</button>
        </header>
        <MaterialLinkPanel
          v-if="selectedCharacter"
          :project-id="projectId"
          source-type="character"
          :source-id="selectedCharacter.id"
          :source-title="selectedCharacter.name"
          :compact="true"
        />
        <article v-else class="empty-state related-empty">暂无关联资料</article>
      </aside>
      <aside v-else key="right-rail" class="panel-rail right-rail" @click="toggleRightPanel">
        <button class="collapse-btn" type="button" title="展开关联">◀</button>
        <span class="rail-label">关联</span>
      </aside>
      </Transition>
    </section>
  </main>
</template>

<style scoped>
.characters-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: var(--zs-space-6);
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.page-header,
.error-banner,
.success-banner,
.state-message,
.characters-layout {
  max-width: 1480px;
  margin-right: auto;
  margin-left: auto;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--zs-space-4);
  margin-bottom: var(--zs-space-4);
}

.back-link {
  display: inline-flex;
  margin-bottom: var(--zs-space-2);
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
  font-size: 1.6rem;
}

h2 {
  font-size: 1.35rem;
}

/* --- Header toolbar (task #30) --- */

.header-toolbar {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  flex-shrink: 0;
}

.header-search {
  display: flex;
}

.search-input {
  width: 220px;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 8px 12px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.86rem;
}

.search-input::placeholder {
  color: var(--zs-color-text-muted);
}

.search-input:focus {
  border-color: var(--zs-color-primary);
  outline: none;
}

.filter-menu-wrapper {
  position: relative;
}

.filter-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.filter-badge {
  display: inline-grid;
  place-items: center;
  min-width: 18px;
  height: 18px;
  border-radius: 999px;
  padding: 0 5px;
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
  font-size: 0.72rem;
  font-weight: 800;
}

.filter-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 30;
  display: grid;
  gap: 10px;
  min-width: 220px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-3);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-md);
}

.filter-field {
  display: grid;
  gap: 4px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.filter-field select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 7px 10px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.86rem;
}

.filter-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.filter-actions button {
  min-height: 32px;
  padding: 0 12px;
  font-size: 0.82rem;
}

/* --- Error / success banners --- */

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
  min-height: 180px;
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  text-align: center;
}

/* --- Three-column layout with collapse (task #32) --- */

.characters-layout {
  display: grid;
  grid-template-columns: minmax(280px, 340px) minmax(0, 1fr) minmax(280px, 320px);
  gap: var(--zs-space-4);
  align-items: start;
  transition: grid-template-columns 0.25s ease;
}

.characters-layout.left-collapsed {
  grid-template-columns: 48px minmax(0, 1fr) minmax(280px, 320px);
}

.characters-layout.right-collapsed {
  grid-template-columns: minmax(280px, 340px) minmax(0, 1fr) 48px;
}

.characters-layout.left-collapsed.right-collapsed {
  grid-template-columns: 48px minmax(0, 1fr) 48px;
}

/* --- Panel header & rail --- */

.panel-header {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  margin-bottom: var(--zs-space-3);
}

.panel-title {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.panel-count {
  border-radius: 999px;
  padding: 1px 8px;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
  font-size: 0.72rem;
  font-weight: 800;
}

.collapse-btn {
  margin-left: auto;
  width: 28px;
  height: 28px;
  min-height: 0;
  display: grid;
  place-items: center;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0;
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  font-size: 0.72rem;
  cursor: pointer;
}

.collapse-btn:hover {
  border-color: var(--zs-color-primary);
  color: var(--zs-color-primary);
}

.panel-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--zs-space-2);
  min-height: 200px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-3) var(--zs-space-1);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
  cursor: pointer;
  transition: background 0.15s;
}

.panel-rail:hover {
  background: var(--zs-color-bg);
}

.rail-label {
  writing-mode: vertical-rl;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.rail-count {
  border-radius: 999px;
  padding: 1px 6px;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
  font-size: 0.68rem;
  font-weight: 800;
}

.panel-rail .collapse-btn {
  margin-left: 0;
}

/* --- Left list panel (task #31) --- */

.list-panel,
.editor-panel {
  min-width: 0;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-4);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
}

.character-tree-scroll {
  overflow-y: auto;
  max-height: calc(100vh - 260px);
  padding-right: 4px;
}

/* Group */

.character-group {
  margin-bottom: var(--zs-space-2);
}

.group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  min-height: 32px;
  border: none;
  border-radius: var(--zs-radius-sm);
  padding: 4px 8px;
  background: transparent;
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s;
}

.group-header:hover {
  background: var(--zs-color-bg);
}

.group-arrow {
  display: inline-block;
  transition: transform 0.2s;
  font-size: 0.72rem;
  color: var(--zs-color-text-muted);
}

.group-arrow.collapsed {
  transform: rotate(-90deg);
}

.group-label {
  flex: 1;
}

.group-count {
  color: var(--zs-color-text-muted);
  font-size: 0.74rem;
  font-weight: 600;
}

/* Group expand/collapse transition */

.group-expand-enter-active,
.group-expand-leave-active {
  overflow: hidden;
  transition: all 0.2s ease;
  max-height: 2000px;
  opacity: 1;
}

.group-expand-enter-from,
.group-expand-leave-to {
  max-height: 0;
  opacity: 0;
}

/* Panel fold transition (left/right panel ↔ rail) */

.panel-fold-enter-active,
.panel-fold-leave-active {
  transition: opacity 0.2s var(--zs-ease-standard), transform 0.2s var(--zs-ease-standard);
}

.panel-fold-enter-from {
  opacity: 0;
  transform: scaleX(0.96);
}

.panel-fold-leave-to {
  opacity: 0;
  transform: scaleX(0.96);
}

/* Character list & compact card */

.character-list {
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 0;
  padding-left: 8px;
  list-style: none;
}

.character-card {
  display: grid;
  gap: 4px;
  width: 100%;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 8px 10px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.character-card:hover {
  border-color: var(--zs-color-primary);
}

.character-card.active {
  border-left: 3px solid var(--zs-color-primary);
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.name {
  font-size: 0.9rem;
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-tags {
  display: flex;
  gap: 3px;
  flex-shrink: 0;
}

.tag {
  display: inline-block;
  border-radius: 3px;
  padding: 0 5px;
  font-size: 0.66rem;
  font-weight: 700;
  line-height: 1.6;
  white-space: nowrap;
}

.tag-role {
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-primary);
}

.tag-importance {
  background: var(--zs-color-warning-soft);
  color: var(--zs-color-warning);
}

.tag-status {
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
}

.card-faction {
  display: flex;
  gap: 3px;
  flex-wrap: wrap;
}

.faction-chip {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  border-radius: 3px;
  padding: 0 6px;
  background: var(--zs-color-bg);
  border: 1px solid var(--zs-color-border);
  color: var(--zs-color-text-muted);
  font-size: 0.68rem;
  font-weight: 600;
  line-height: 1.7;
  white-space: nowrap;
}

.faction-overflow {
  border-style: dashed;
}

.summary {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* --- Editor panel --- */

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

.basic-fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
}

.field-compact {
  display: grid;
  gap: 4px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.field-compact input,
.field-compact select {
  padding: 7px 10px;
  font-size: 0.86rem;
}

/* --- Faction chip input (task #33) --- */

.field-faction {
  display: grid;
  gap: 4px;
}

.field-label {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.faction-input-container {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
  min-height: 36px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 4px 8px;
  background: var(--zs-color-surface);
  cursor: text;
}

.faction-input-container:focus-within {
  border-color: var(--zs-color-primary);
}

.faction-input-container .faction-chip {
  font-size: 0.78rem;
  line-height: 1.8;
  padding: 0 4px 0 8px;
  background: var(--zs-color-primary-soft);
  border-color: var(--zs-color-primary);
  color: var(--zs-color-primary);
}

.chip-remove {
  width: 16px;
  height: 16px;
  min-height: 0;
  display: inline-grid;
  place-items: center;
  border: none;
  border-radius: 50%;
  padding: 0;
  background: transparent;
  color: var(--zs-color-text-muted);
  font-size: 0.66rem;
  cursor: pointer;
  transition: color 0.15s;
}

.chip-remove:hover {
  color: var(--zs-color-danger);
}

.faction-text-input {
  flex: 1;
  min-width: 80px;
  border: none;
  padding: 2px 0;
  background: transparent;
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.82rem;
  outline: none;
}

.faction-text-input::placeholder {
  color: var(--zs-color-text-muted);
}

.field-summary {
  display: grid;
  gap: 4px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.field-summary input {
  padding: 7px 10px;
  font-size: 0.86rem;
}

.field-biography {
  display: grid;
  gap: 4px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.field-biography textarea {
  min-height: 72px;
  font-size: 0.86rem;
}

input,
select,
textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 10px 12px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
}

textarea {
  resize: vertical;
  line-height: 1.7;
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
  border-radius: var(--zs-radius-sm);
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

.autosave-status {
  margin-right: auto;
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
}

/* --- Related panel --- */

.related-empty {
  min-height: 120px;
}

/* --- Responsive --- */

@media (max-width: 1366px) {
  .characters-page {
    padding: var(--zs-space-4);
  }
}

@media (max-width: 900px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-toolbar {
    flex-wrap: wrap;
  }

  .search-input {
    width: 100%;
  }

  .characters-layout,
  .characters-layout.left-collapsed,
  .characters-layout.right-collapsed,
  .characters-layout.left-collapsed.right-collapsed {
    grid-template-columns: 1fr;
  }

  .panel-rail {
    flex-direction: row;
    min-height: 0;
    padding: var(--zs-space-2);
  }

  .rail-label {
    writing-mode: horizontal-tb;
  }
}
</style>
