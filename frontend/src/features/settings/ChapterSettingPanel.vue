<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'

import {
  addChapterSetting,
  deleteChapterSetting,
  listChapterSettings,
  updateChapterSetting,
} from '@/entities/chapter-setting/api'
import type {
  ChapterSettingLink,
  ChapterSettingRelationType,
} from '@/entities/chapter-setting/types'
import { chapterSettingRelationLabels } from '@/entities/chapter-setting/types'
import { listProjectSettings } from '@/entities/setting/api'
import type { SettingItem } from '@/entities/setting/types'
import {
  settingCanonStatusLabels,
  settingImportanceLabels,
  settingItemTypeLabels,
} from '@/entities/setting/types'

const props = defineProps<{
  projectId: string
  chapterId: string | null
}>()

const links = ref<ChapterSettingLink[]>([])
const projectSettings = ref<SettingItem[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const showBindForm = ref(false)
const selectedLinkId = ref<string | null>(null)
const selectedLink = ref<ChapterSettingLink | null>(null)

const relationTypes: ChapterSettingRelationType[] = [
  'referenced',
  'appears',
  'explained',
  'changed',
  'conflict_check',
]

const form = reactive({
  setting_item_id: '',
  relation_type: 'referenced' as ChapterSettingRelationType,
  note: '',
})

const editForm = reactive({
  relation_type: 'referenced' as ChapterSettingRelationType,
  note: '',
})

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
    await loadProjectSettings()
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    const [chapterLinks] = await Promise.all([
      listChapterSettings(props.chapterId),
      loadProjectSettings(),
    ])
    links.value = chapterLinks
    selectedLink.value = chapterLinks.find((link) => link.id === selectedLinkId.value) ?? null
    if (!selectedLink.value) {
      selectedLinkId.value = null
    }
  } catch (error) {
    void error
    errorMessage.value = '加载本章设定失败。'
  } finally {
    isLoading.value = false
  }
}

async function loadProjectSettings() {
  if (!props.projectId) {
    return
  }
  projectSettings.value = await listProjectSettings(props.projectId)
}

function selectLink(link: ChapterSettingLink) {
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
  if (!props.chapterId || !form.setting_item_id) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    await addChapterSetting(props.chapterId, {
      setting_item_id: form.setting_item_id,
      relation_type: form.relation_type,
      note: form.note,
    })
    resetForm()
    showBindForm.value = false
    await refreshPanel()
  } catch (error) {
    void error
    errorMessage.value = '绑定设定失败。'
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
    const updated = await updateChapterSetting(selectedLink.value.id, {
      relation_type: editForm.relation_type,
      note: editForm.note,
    })
    links.value = links.value.map((link) => (link.id === updated.id ? updated : link))
    selectedLink.value = updated
  } catch (error) {
    void error
    errorMessage.value = '更新设定关联失败。'
  } finally {
    isSaving.value = false
  }
}

async function handleRemoveLink(link: ChapterSettingLink) {
  const confirmed = window.confirm('确认从本章移除该设定关联吗？')
  if (!confirmed) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    await deleteChapterSetting(link.id)
    await refreshPanel()
    if (selectedLinkId.value === link.id) {
      backToList()
    }
  } catch (error) {
    void error
    errorMessage.value = '移除设定关联失败。'
  } finally {
    isSaving.value = false
  }
}

function resetForm() {
  form.setting_item_id = ''
  form.relation_type = 'referenced'
  form.note = ''
}
</script>

<template>
  <section class="chapter-setting-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">本章设定</p>
        <h2>设定卡</h2>
      </div>
      <button class="secondary-button" type="button" @click="showBindForm = !showBindForm">
        {{ showBindForm ? '收起绑定' : '绑定设定' }}
      </button>
    </header>

    <p class="hint">这里显示的是本书内部设定，不是外部素材。</p>
    <p v-if="!chapterId" class="state-message">请选择章节后查看本章设定。</p>

    <template v-else>
      <form v-if="showBindForm" class="bind-form" @submit.prevent="handleAddLink">
        <label>
          <span>设定条目</span>
          <select v-model="form.setting_item_id" required>
            <option value="">请选择设定</option>
            <option v-for="setting in projectSettings" :key="setting.id" :value="setting.id">
              {{ setting.title }}
            </option>
          </select>
        </label>

        <label>
          <span>本章关联</span>
          <select v-model="form.relation_type">
            <option v-for="relation in relationTypes" :key="relation" :value="relation">
              {{ chapterSettingRelationLabels[relation] }}
            </option>
          </select>
        </label>

        <label>
          <span>备注</span>
          <textarea v-model="form.note" rows="3" placeholder="例如：这里会说明角色所处城池的规则。"></textarea>
        </label>

        <button class="primary-button" type="submit" :disabled="isSaving || !form.setting_item_id">
          {{ isSaving ? '正在保存……' : '保存绑定' }}
        </button>
      </form>

      <p v-if="isLoading" class="state-message">正在加载本章设定……</p>
      <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>

      <template v-else-if="selectedLink">
        <article class="setting-card">
          <header class="setting-header">
            <div>
              <p class="setting-eyebrow">设定摘要</p>
              <h3>{{ selectedLink.setting_item.title }}</h3>
            </div>
            <button class="text-button" type="button" @click="backToList">返回列表</button>
          </header>

          <div class="summary-grid">
            <div>
              <span class="field-label">类型</span>
              <strong>{{ settingItemTypeLabels[selectedLink.setting_item.item_type] }}</strong>
            </div>
            <div>
              <span class="field-label">确认状态</span>
              <strong>{{ settingCanonStatusLabels[selectedLink.setting_item.canon_status] }}</strong>
            </div>
            <div>
              <span class="field-label">重要程度</span>
              <strong>{{ settingImportanceLabels[selectedLink.setting_item.importance] }}</strong>
            </div>
          </div>

          <section class="setting-section">
            <p class="section-label">详细设定</p>
            <p v-if="selectedLink.setting_item.summary" class="text-block">{{ selectedLink.setting_item.summary }}</p>
            <p v-else class="muted-block">暂无简介。</p>
            <p v-if="selectedLink.setting_item.detail" class="detail-block">{{ selectedLink.setting_item.detail }}</p>
          </section>

          <section class="setting-section">
            <p class="section-label">本章关联</p>
            <div class="relation-grid">
              <label>
                <span>关系类型</span>
                <select v-model="editForm.relation_type">
                  <option v-for="relation in relationTypes" :key="relation" :value="relation">
                    {{ chapterSettingRelationLabels[relation] }}
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
        <p v-if="links.length === 0" class="state-message">本章暂无设定</p>

        <ul v-else class="setting-list">
          <li v-for="link in links" :key="link.id">
            <button
              class="setting-card list-card"
              type="button"
              :class="{ active: selectedLinkId === link.id }"
              @click="selectLink(link)"
            >
              <span class="name">{{ link.setting_item.title }}</span>
              <span class="meta">
                {{ settingItemTypeLabels[link.setting_item.item_type] }} ·
                {{ settingCanonStatusLabels[link.setting_item.canon_status] }} ·
                {{ settingImportanceLabels[link.setting_item.importance] }}
              </span>
              <span class="summary">{{ link.setting_item.summary || '暂无简介' }}</span>
            </button>
          </li>
        </ul>
      </template>
    </template>
  </section>
</template>

<style scoped>
.chapter-setting-panel {
  display: grid;
  gap: 12px;
}

.panel-header,
.setting-header,
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

.hint {
  border: 1px solid #dbeafe;
  border-radius: 8px;
  padding: 10px;
  background: #eff6ff;
  color: #1e40af;
  font-size: 0.86rem;
  line-height: 1.6;
}

.secondary-button,
.danger-button,
.text-button,
.primary-button {
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

.primary-button {
  border-color: transparent;
  background: #2563eb;
  color: #ffffff;
}

.bind-form,
.setting-card {
  display: grid;
  gap: 12px;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 14px;
  background: #fbfcfe;
}

.setting-card {
  background: #ffffff;
}

.setting-eyebrow,
.field-label,
.section-label {
  color: #64748b;
  font-size: 0.78rem;
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

.setting-section {
  display: grid;
  gap: 8px;
}

.text-block,
.muted-block,
.detail-block {
  color: #334155;
  line-height: 1.7;
  white-space: pre-wrap;
}

.muted-block {
  color: #94a3b8;
}

.detail-block {
  border-left: 3px solid #dbeafe;
  padding-left: 10px;
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

.setting-list {
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
  border-color: #2563eb;
  background: #eff6ff;
}

.name {
  color: #111827;
  font-weight: 800;
}

.meta,
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
