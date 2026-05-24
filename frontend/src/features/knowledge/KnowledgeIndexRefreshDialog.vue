<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  listEmbeddingProviders,
  refreshKnowledgeIndex,
} from '@/entities/knowledge/api'
import type {
  EmbeddingProviderInfo,
  KnowledgeChunkSize,
  KnowledgeIndexRefreshScope,
  RefreshKnowledgeIndexResponse,
} from '@/entities/knowledge/types'
import {
  knowledgeChunkSizeDescriptions,
  knowledgeChunkSizeLabels,
} from '@/entities/knowledge/types'

const props = defineProps<{
  projectId: string
  selectedSourceId: string | null
  selectedSourceTitle: string | null
  hasUnsavedChanges: boolean
  currentProviderId: string | null
}>()

const emit = defineEmits<{
  close: []
  refreshed: []
}>()

type RefreshStep = 'configure' | 'refreshing' | 'result'

interface RefreshProgressState {
  total: number
  completed: number
  currentTitle: string
  chunkCount: number
  indexedCount: number
  warnings: string[]
}

const step = ref<RefreshStep>('configure')
const scope = ref<KnowledgeIndexRefreshScope>('project')
const chunkSize = ref<KnowledgeChunkSize>('medium')
const errorMessage = ref('')
const result = ref<RefreshKnowledgeIndexResponse | null>(null)
const progress = ref<RefreshProgressState>({
  total: 0,
  completed: 0,
  currentTitle: '',
  chunkCount: 0,
  indexedCount: 0,
  warnings: [],
})

// --- Provider state ---
const providerList = ref<EmbeddingProviderInfo[]>([])
const defaultProviderId = ref('')
const selectedProviderId = ref('')
const privacyConfirmed = ref(false)
const providersLoading = ref(true)

onMounted(async () => {
  try {
    const res = await listEmbeddingProviders(props.projectId)
    providerList.value = res.providers
    defaultProviderId.value = res.default_provider_id
    selectedProviderId.value = props.currentProviderId || res.default_provider_id
  } catch {
    // Fallback: use default provider ID
    selectedProviderId.value = 'local_basic_hash'
    defaultProviderId.value = 'local_basic_hash'
  } finally {
    providersLoading.value = false
  }
})

const canUseSourceScope = computed(() => !!props.selectedSourceId)

const scopeOptions: { value: KnowledgeIndexRefreshScope; label: string }[] = [
  { value: 'project', label: '全部资料' },
  { value: 'source', label: '当前资料' },
]

const chunkSizeOptions: { value: KnowledgeChunkSize; label: string; recommended?: boolean }[] = [
  { value: 'small', label: knowledgeChunkSizeLabels.small },
  { value: 'medium', label: `${knowledgeChunkSizeLabels.medium}（推荐）`, recommended: true },
  { value: 'large', label: knowledgeChunkSizeLabels.large },
]

const currentDescription = computed(() => knowledgeChunkSizeDescriptions[chunkSize.value])

const scopeDescription = computed(() => {
  if (scope.value === 'source' && props.selectedSourceTitle) {
    return `仅刷新资料「${props.selectedSourceTitle}」的索引。`
  }
  return '刷新项目下所有资料的索引。'
})

const isRefreshing = computed(() => step.value === 'refreshing')

const selectedProvider = computed(() =>
  providerList.value.find((p) => p.id === selectedProviderId.value) ?? null,
)
const isCloudProvider = computed(() => selectedProvider.value?.provider_type === 'cloud')
const needsPrivacyConfirm = computed(
  () => isCloudProvider.value && !privacyConfirmed.value,
)
const providerChanged = computed(
  () =>
    !!props.currentProviderId &&
    selectedProviderId.value !== props.currentProviderId,
)

const canSubmit = computed(() => {
  if (isRefreshing.value || props.hasUnsavedChanges) return false
  if (needsPrivacyConfirm.value) return false
  if (selectedProvider.value && !selectedProvider.value.available) return false
  if (providersLoading.value) return false
  if (providerChanged.value && scope.value === 'source') return false
  return true
})

const progressPercent = computed(() => {
  const { total, completed } = progress.value
  if (total <= 0) return 0
  return Math.round((completed / total) * 100)
})

const progressText = computed(() => {
  const { total, completed } = progress.value
  if (total <= 0) return '正在准备...'
  return `${completed} / ${total}（${progressPercent.value}%）`
})

const hasProgress = computed(() => progress.value.total > 0)
const isIndeterminate = computed(() => step.value === 'refreshing' && progress.value.total === 0)

function selectScope(value: KnowledgeIndexRefreshScope) {
  if (value === 'source' && !canUseSourceScope.value) return
  scope.value = value
}

function selectChunkSize(value: KnowledgeChunkSize) {
  chunkSize.value = value
}

function selectProvider(providerId: string) {
  const provider = providerList.value.find((p) => p.id === providerId)
  if (provider && !provider.available) return
  selectedProviderId.value = providerId
  // Reset privacy confirmation when switching providers
  if (!provider || provider.provider_type !== 'cloud') {
    privacyConfirmed.value = false
  }
}

async function handleRefresh() {
  if (!canSubmit.value) return

  step.value = 'refreshing'
  errorMessage.value = ''
  progress.value = {
    total: 0,
    completed: 0,
    currentTitle: '',
    chunkCount: 0,
    indexedCount: 0,
    warnings: [],
  }

  try {
    if (scope.value === 'source') {
      await refreshSourceScope(props.selectedSourceId!, props.selectedSourceTitle ?? '')
    } else {
      await refreshProjectScope()
    }
    step.value = 'result'
    // Notify parent to reload index status, chunks, sources — but keep dialog open
    emit('refreshed')
  } catch (err: unknown) {
    const status =
      (err as { status?: number })?.status ??
      (err as { response?: { status?: number } })?.response?.status
    if (status === 409) {
      errorMessage.value = '模型冲突：请使用「全部资料」范围刷新来切换索引模型。'
    } else if (status === 403) {
      errorMessage.value = '请确认数据隐私条款后再使用云端索引。'
    } else if (status === 422) {
      errorMessage.value =
        (err as { message?: string })?.message ?? '所选索引模式不可用。'
    } else if (status === 502) {
      errorMessage.value = '云端 Embedding 服务调用失败，请稍后重试。'
    } else if (status === 503) {
      errorMessage.value = '云端 Embedding 服务不可用：API Key 未配置。'
    } else {
      errorMessage.value = '刷新知识索引失败，请稍后重试。'
    }
    step.value = 'configure'
  }
}

async function refreshProjectScope() {
  // Show indeterminate progress — backend handles all sources in one call
  progress.value = {
    total: 0,
    completed: 0,
    currentTitle: '',
    chunkCount: 0,
    indexedCount: 0,
    warnings: [],
  }

  const res = await refreshKnowledgeIndex(props.projectId, {
    scope: 'project',
    chunk_size: chunkSize.value,
    provider_id: selectedProviderId.value || undefined,
    privacy_confirmed: isCloudProvider.value ? privacyConfirmed.value : undefined,
  })

  progress.value = {
    total: 1,
    completed: 1,
    currentTitle: '',
    chunkCount: res.chunk_count,
    indexedCount: res.indexed_count,
    warnings: res.warnings,
  }

  result.value = {
    source_count: res.source_count,
    chunk_count: res.chunk_count,
    indexed_count: res.indexed_count,
    chunk_size: res.chunk_size,
    model_name: res.model_name,
    provider_id: res.provider_id,
    warnings: res.warnings,
  }
}

async function refreshSourceScope(sourceId: string, sourceTitle: string) {
  progress.value = {
    total: 1,
    completed: 0,
    currentTitle: sourceTitle,
    chunkCount: 0,
    indexedCount: 0,
    warnings: [],
  }

  const res = await refreshKnowledgeIndex(props.projectId, {
    scope: 'source',
    source_id: sourceId,
    chunk_size: chunkSize.value,
    provider_id: selectedProviderId.value || undefined,
    privacy_confirmed: isCloudProvider.value ? privacyConfirmed.value : undefined,
  })

  progress.value.completed = 1
  progress.value.chunkCount = res.chunk_count
  progress.value.indexedCount = res.indexed_count
  progress.value.warnings = [...res.warnings]

  result.value = {
    source_count: 1,
    chunk_count: res.chunk_count,
    indexed_count: res.indexed_count,
    chunk_size: chunkSize.value,
    model_name: res.model_name,
    provider_id: res.provider_id,
    warnings: res.warnings,
  }
}

function handleClose() {
  if (isRefreshing.value) return
  emit('close')
}
</script>

<template>
  <div class="zs-dialog" role="presentation" @click.self="handleClose">
    <section
      class="zs-dialog-content refresh-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="knowledge-refresh-title"
    >
      <header class="zs-dialog-header">
        <h2 id="knowledge-refresh-title">刷新知识索引</h2>
        <button
          class="zs-icon-button"
          type="button"
          aria-label="关闭"
          :disabled="isRefreshing"
          @click="handleClose"
        >
          x
        </button>
      </header>

      <div class="refresh-body">
        <!-- Unsaved changes warning -->
        <section v-if="hasUnsavedChanges" class="warning-banner" role="alert">
          当前资料有未保存内容。请先保存后再刷新索引，否则索引仍基于上一次保存的正文。
        </section>

        <!-- Error message -->
        <section v-if="errorMessage" class="error-banner" role="alert">
          {{ errorMessage }}
        </section>

        <!-- Step: Configure -->
        <div v-if="step === 'configure'" class="step-configure">
          <p class="helper-note">
            当你导入、修改了资料，或搜索/问答没有命中新内容时，可以刷新知识索引。
            刷新会重新整理资料片段并更新检索结果。
          </p>

          <!-- Scope selection -->
          <fieldset class="option-group">
            <legend class="option-label">刷新范围</legend>
            <div class="segmented-control">
              <button
                v-for="option in scopeOptions"
                :key="option.value"
                type="button"
                class="segmented-option"
                :class="{
                  active: scope === option.value,
                  disabled: option.value === 'source' && !canUseSourceScope,
                }"
                :disabled="option.value === 'source' && !canUseSourceScope"
                @click="selectScope(option.value)"
              >
                {{ option.label }}
              </button>
            </div>
            <p class="option-hint">{{ scopeDescription }}</p>
            <p v-if="!canUseSourceScope" class="option-hint subtle">
              提示：在左侧列表中选中一条资料后，可以选择只刷新当前资料。
            </p>
          </fieldset>

          <!-- Chunk size selection -->
          <fieldset class="option-group">
            <legend class="option-label">索引片段大小</legend>
            <div class="segmented-control">
              <button
                v-for="option in chunkSizeOptions"
                :key="option.value"
                type="button"
                class="segmented-option"
                :class="{ active: chunkSize === option.value }"
                @click="selectChunkSize(option.value)"
              >
                {{ option.label }}
              </button>
            </div>
            <p class="option-hint">{{ currentDescription }}</p>
          </fieldset>

          <!-- Provider selection -->
          <fieldset v-if="providerList.length > 0" class="option-group">
            <legend class="option-label">索引模式</legend>
            <div class="provider-list">
              <button
                v-for="provider in providerList"
                :key="provider.id"
                type="button"
                class="provider-option"
                :class="{
                  active: selectedProviderId === provider.id,
                  disabled: !provider.available,
                }"
                :disabled="!provider.available"
                @click="selectProvider(provider.id)"
              >
                <span class="provider-main">
                  <span class="provider-radio">
                    <span
                      v-if="selectedProviderId === provider.id"
                      class="provider-radio-dot"
                    />
                  </span>
                  <span class="provider-info">
                    <span class="provider-name">{{ provider.display_name }}</span>
                    <span class="provider-badges">
                      <span class="provider-badge quality">{{ provider.quality_label }}</span>
                      <span
                        v-if="provider.provider_type === 'cloud'"
                        class="provider-badge cloud"
                      >
                        云端
                      </span>
                    </span>
                  </span>
                </span>
                <span class="provider-desc">{{ provider.description }}</span>
                <span v-if="!provider.available" class="provider-reason">
                  {{ provider.reason }}
                </span>
              </button>
            </div>
            <p
              v-if="providerChanged && scope === 'source'"
              class="option-hint warning-hint"
            >
              切换索引模型需要选择「全部资料」范围进行全量刷新。
            </p>
          </fieldset>

          <!-- Privacy confirmation (cloud provider only) -->
          <label v-if="isCloudProvider" class="privacy-confirm">
            <input
              v-model="privacyConfirmed"
              type="checkbox"
              class="privacy-checkbox"
            />
            <span>
              我了解选择云端索引模式会将资料片段发送到服务商用于生成向量索引。
            </span>
          </label>

          <p class="confirm-note">
            刷新期间请不要关闭页面。资料较多时可能需要一些时间。
          </p>
        </div>

        <!-- Step: Refreshing -->
        <div v-else-if="step === 'refreshing'" class="step-refreshing">
          <div class="refreshing-indicator">
            <span class="spinner" />
            <span>{{ isIndeterminate ? '正在刷新全部资料…' : '正在刷新索引...' }}</span>
          </div>

          <!-- Indeterminate progress bar -->
          <div
            v-if="isIndeterminate"
            class="refresh-progress indeterminate"
            role="progressbar"
          >
            <div class="refresh-progress-bar indeterminate-bar" />
          </div>

          <!-- Determinate progress bar -->
          <div
            v-else-if="hasProgress"
            class="refresh-progress"
            role="progressbar"
            :aria-valuenow="progressPercent"
            aria-valuemin="0"
            aria-valuemax="100"
          >
            <div
              class="refresh-progress-bar"
              :style="{ width: `${progressPercent}%` }"
            />
          </div>
          <p v-if="hasProgress" class="progress-text">{{ progressText }}</p>
          <p v-if="progress.currentTitle" class="progress-current">
            正在处理：{{ progress.currentTitle }}
          </p>

          <p class="confirm-note">
            刷新期间请不要关闭页面。资料较多时可能需要一些时间。
          </p>
        </div>

        <!-- Step: Result -->
        <div v-else-if="step === 'result' && result" class="step-result">
          <p class="result-summary">
            已刷新 <strong>{{ result.source_count }}</strong> 条资料，
            整理出 <strong>{{ result.chunk_count }}</strong> 个索引片段。
          </p>
          <ul v-if="result.warnings.length > 0" class="result-warnings">
            <li v-for="(warning, index) in result.warnings" :key="index">
              {{ warning }}
            </li>
          </ul>
        </div>
      </div>

      <footer class="zs-dialog-footer">
        <button
          class="zs-button zs-button-secondary"
          type="button"
          :disabled="isRefreshing"
          @click="handleClose"
        >
          {{ step === 'result' ? '关闭' : '取消' }}
        </button>
        <button
          v-if="step === 'configure'"
          class="zs-button zs-button-primary"
          type="button"
          :disabled="!canSubmit"
          @click="handleRefresh"
        >
          开始刷新
        </button>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.refresh-dialog {
  max-width: min(520px, 90vw);
  width: min(520px, 90vw);
  margin-inline: auto;
}

.refresh-body {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-4);
  padding: var(--zs-space-4) var(--zs-space-5);
}

.helper-note {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--zs-color-text-muted);
}

.warning-banner {
  padding: var(--zs-space-2) var(--zs-space-4);
  border-radius: var(--zs-radius-md, 6px);
  background: var(--zs-color-warning-soft, #fff8e1);
  color: var(--zs-color-warning, #f59e0b);
  font-size: 0.875rem;
  line-height: 1.5;
}

.error-banner {
  padding: var(--zs-space-2) var(--zs-space-4);
  border-radius: var(--zs-radius-md, 6px);
  background: var(--zs-color-danger-soft, #fef2f2);
  color: var(--zs-color-danger, #ef4444);
  font-size: 0.875rem;
  line-height: 1.5;
}

.option-group {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-1);
  border: none;
  padding: 0;
  margin: 0;
}

.option-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--zs-color-text);
  margin-bottom: var(--zs-space-1);
}

.segmented-control {
  display: flex;
  gap: 0;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md, 6px);
  overflow: hidden;
}

.segmented-option {
  flex: 1;
  padding: var(--zs-space-2) var(--zs-space-4);
  border: none;
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  font-size: 0.875rem;
  cursor: pointer;
  transition:
    background 0.15s,
    color 0.15s;
}

.segmented-option:not(:last-child) {
  border-right: 1px solid var(--zs-color-border);
}

.segmented-option:hover:not(.disabled):not(.active) {
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-text);
}

.segmented-option.active {
  background: var(--zs-color-primary);
  color: #fff;
}

.segmented-option.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.option-hint {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--zs-color-text-muted);
}

.option-hint.subtle {
  font-size: 0.75rem;
  opacity: 0.8;
}

.confirm-note {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--zs-color-text-muted);
}

.step-configure {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-4);
}

.step-refreshing {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--zs-space-3);
  padding: var(--zs-space-5) 0;
}

.refreshing-indicator {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  font-size: 0.9375rem;
  color: var(--zs-color-text);
}

.spinner {
  display: inline-block;
  width: 18px;
  height: 18px;
  border: 2px solid var(--zs-color-border);
  border-top-color: var(--zs-color-primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Progress bar */
.refresh-progress {
  width: 100%;
  height: 8px;
  background: var(--zs-color-border);
  border-radius: 4px;
  overflow: hidden;
}

.refresh-progress-bar {
  height: 100%;
  background: var(--zs-color-primary);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.refresh-progress.indeterminate {
  overflow: hidden;
}

.refresh-progress-bar.indeterminate-bar {
  width: 40%;
  animation: indeterminate-slide 1.5s ease-in-out infinite;
}

@keyframes indeterminate-slide {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(350%);
  }
}

.progress-text {
  margin: 0;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--zs-color-text);
}

.progress-current {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--zs-color-text-muted);
  text-align: center;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.step-result {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-2);
}

.result-summary {
  margin: 0;
  font-size: 0.9375rem;
  line-height: 1.6;
  color: var(--zs-color-text);
}

.result-summary strong {
  color: var(--zs-color-primary);
}

.result-warnings {
  margin: 0;
  padding-left: 1.25rem;
  font-size: 0.8125rem;
  line-height: 1.6;
  color: var(--zs-color-warning, #f59e0b);
}

/* Provider selection */
.provider-list {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-2);
}

.provider-option {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-1);
  padding: var(--zs-space-3) var(--zs-space-4);
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md, 6px);
  background: var(--zs-color-surface);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.15s,
    background 0.15s;
}

.provider-option:hover:not(.disabled):not(.active) {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-surface-soft);
}

.provider-option.active {
  border-color: var(--zs-color-primary);
  background: color-mix(in srgb, var(--zs-color-primary) 6%, var(--zs-color-surface));
}

.provider-option.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.provider-main {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
}

.provider-radio {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border: 2px solid var(--zs-color-border);
  border-radius: 50%;
  flex-shrink: 0;
}

.provider-option.active .provider-radio {
  border-color: var(--zs-color-primary);
}

.provider-radio-dot {
  display: block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--zs-color-primary);
}

.provider-info {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  flex-wrap: wrap;
}

.provider-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--zs-color-text);
}

.provider-badges {
  display: flex;
  gap: var(--zs-space-1);
}

.provider-badge {
  padding: 1px 6px;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-text-muted);
}

.provider-badge.quality {
  background: color-mix(in srgb, var(--zs-color-primary) 12%, transparent);
  color: var(--zs-color-primary);
}

.provider-badge.cloud {
  background: color-mix(in srgb, var(--zs-color-info, #3b82f6) 12%, transparent);
  color: var(--zs-color-info, #3b82f6);
}

.provider-desc {
  font-size: 0.78rem;
  line-height: 1.4;
  color: var(--zs-color-text-muted);
  padding-left: 24px;
}

.provider-reason {
  font-size: 0.75rem;
  color: var(--zs-color-warning, #f59e0b);
  padding-left: 24px;
}

.warning-hint {
  color: var(--zs-color-warning, #f59e0b);
}

/* Privacy confirmation */
.privacy-confirm {
  display: flex;
  align-items: flex-start;
  gap: var(--zs-space-2);
  padding: var(--zs-space-3) var(--zs-space-4);
  border: 1px solid var(--zs-color-warning, #f59e0b);
  border-radius: var(--zs-radius-md, 6px);
  background: var(--zs-color-warning-soft, #fff8e1);
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--zs-color-text);
  cursor: pointer;
}

.privacy-checkbox {
  margin-top: 2px;
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  accent-color: var(--zs-color-primary);
}

@media (max-width: 560px) {
  .refresh-body {
    padding-inline: var(--zs-space-3);
  }
}
</style>
