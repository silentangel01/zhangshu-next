<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  getAppConfig,
  setAppConfig,
  testDashScopeConnection,
  testDashScopeLlmConnection,
} from '@/entities/app-config/api'
import type {
  AppConfigMaskedValue,
  TestDashScopeResponse,
  TestLLMResponse,
} from '@/entities/app-config/types'
import { getCloudAccountStatus, cloudLogout } from '@/entities/cloud/api'
import type { CloudAccountStatus } from '@/entities/cloud/types'
import CloudNetworkDiagnosticsPanel from '@/features/cloud/CloudNetworkDiagnosticsPanel.vue'

const emit = defineEmits<{
  close: []
}>()

// --- State ---
const apiKeyInput = ref('')
const showKey = ref(false)
const savedMask = ref<AppConfigMaskedValue | null>(null)
const isLoading = ref(true)
const isSaving = ref(false)
const isTesting = ref(false)
const saveMessage = ref('')
const testResult = ref<TestDashScopeResponse | null>(null)
const errorMessage = ref('')

// LLM settings
const llmEnabled = ref(false)
const llmModel = ref('qwen-plus')
const llmBaseUrl = ref('')
const isTestingLlm = ref(false)
const llmTestResult = ref<TestLLMResponse | null>(null)

// Cloud account
const cloudStatus = ref<CloudAccountStatus | null>(null)
const isCloudLoading = ref(false)

const llmModelOptions = [
  { value: 'qwen-plus', label: 'qwen-plus（推荐）' },
  { value: 'qwen-turbo', label: 'qwen-turbo（快速）' },
  { value: 'qwen-max', label: 'qwen-max（高质量）' },
]

onMounted(async () => {
  try {
    const config = await getAppConfig()
    savedMask.value = config.dashscope_api_key ?? null
    llmEnabled.value = config.llm_enabled
    llmModel.value = config.llm_model || 'qwen-plus'
    llmBaseUrl.value = config.llm_base_url || ''
  } catch {
    errorMessage.value = '读取配置失败。'
  } finally {
    isLoading.value = false
  }

  void loadCloudStatus()
})

async function loadCloudStatus() {
  isCloudLoading.value = true
  try {
    cloudStatus.value = await getCloudAccountStatus()
  } catch {
    // Cloud not configured — silently ignore.
  } finally {
    isCloudLoading.value = false
  }
}

async function handleCloudLogout() {
  isCloudLoading.value = true
  try {
    await cloudLogout()
    cloudStatus.value = {
      logged_in: false,
      cloud_available: cloudStatus.value?.cloud_available ?? false,
      email: null,
      display_name: null,
    }
  } catch {
    errorMessage.value = '退出云账户失败。'
  } finally {
    isCloudLoading.value = false
  }
}

// --- Computed ---
const hasSavedKey = computed(() => savedMask.value?.has_value === true)
const hasDecryptError = computed(() => savedMask.value?.decrypt_error === true)
const canSave = computed(() => !isSaving.value && !isLoading.value)
const canTest = computed(
  () => !isTesting.value && !isLoading.value && apiKeyInput.value.trim().length > 0,
)
const canTestLlm = computed(
  () => !isTestingLlm.value && !isLoading.value && hasSavedKey.value,
)

const inputType = computed(() => (showKey.value ? 'text' : 'password'))

// --- Actions ---
async function handleSave() {
  if (!canSave.value) return
  isSaving.value = true
  saveMessage.value = ''
  errorMessage.value = ''

  try {
    const payload: Record<string, unknown> = {}
    if (apiKeyInput.value) {
      payload.dashscope_api_key = apiKeyInput.value
    }
    payload.llm_enabled = llmEnabled.value
    payload.llm_model = llmModel.value || null
    payload.llm_base_url = llmBaseUrl.value || null

    const config = await setAppConfig(payload)
    savedMask.value = config.dashscope_api_key ?? null
    llmEnabled.value = config.llm_enabled
    llmModel.value = config.llm_model || 'qwen-plus'
    llmBaseUrl.value = config.llm_base_url || ''
    // Clear the input after saving (the masked value is now shown)
    apiKeyInput.value = ''
    saveMessage.value = '已保存。'
  } catch {
    errorMessage.value = '保存失败，请重试。'
  } finally {
    isSaving.value = false
  }
}

async function handleTest() {
  if (!canTest.value) return
  isTesting.value = true
  testResult.value = null
  errorMessage.value = ''

  try {
    testResult.value = await testDashScopeConnection({
      api_key: apiKeyInput.value.trim(),
    })
  } catch {
    testResult.value = {
      success: false,
      model_name: '',
      vector_dim: 0,
      error: '测试请求失败，请检查网络。',
    }
  } finally {
    isTesting.value = false
  }
}

async function handleTestLlm() {
  if (!canTestLlm.value) return
  isTestingLlm.value = true
  llmTestResult.value = null
  errorMessage.value = ''

  try {
    llmTestResult.value = await testDashScopeLlmConnection({
      model: llmModel.value || null,
    })
  } catch {
    llmTestResult.value = {
      success: false,
      model_name: '',
      response_preview: '',
      error: '测试请求失败，请检查网络。',
    }
  } finally {
    isTestingLlm.value = false
  }
}

function handleClose() {
  if (isSaving.value || isTesting.value || isTestingLlm.value) return
  emit('close')
}
</script>

<template>
  <div class="zs-dialog" role="presentation" @click.self="handleClose">
    <section
      class="zs-dialog-content settings-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="app-settings-title"
    >
      <header class="zs-dialog-header">
        <h2 id="app-settings-title">应用设置</h2>
        <button
          class="zs-icon-button"
          type="button"
          aria-label="关闭"
          :disabled="isSaving || isTesting || isTestingLlm"
          @click="handleClose"
        >
          x
        </button>
      </header>

      <div class="settings-body">
        <!-- Loading state -->
        <p v-if="isLoading" class="helper-note">正在加载配置...</p>

        <template v-else>
          <!-- Error banner -->
          <section v-if="errorMessage" class="error-banner" role="alert">
            {{ errorMessage }}
          </section>

          <!-- Decrypt error warning -->
          <section v-if="hasDecryptError" class="warning-banner" role="alert">
            已存储的密钥已失效（本地加密密钥变更）。请重新输入 API Key。
          </section>

          <!-- API Key section -->
          <fieldset class="option-group">
            <legend class="option-label">DashScope API Key</legend>
            <p class="option-hint">
              用于知识索引的云端向量模型服务和 AI 问答。Key 会加密存储在本地数据库中。
            </p>

            <!-- Masked preview when key is saved -->
            <div v-if="hasSavedKey && !hasDecryptError && savedMask" class="saved-key-preview">
              <span class="saved-key-label">当前已配置：</span>
              <code class="saved-key-masked">{{ savedMask.masked }}</code>
            </div>

            <!-- Input field with show/hide toggle -->
            <div class="key-input-row">
              <input
                v-model="apiKeyInput"
                :type="inputType"
                class="key-input"
                placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
                autocomplete="off"
                spellcheck="false"
              />
              <button
                class="zs-button zs-button-secondary toggle-visibility"
                type="button"
                @click="showKey = !showKey"
              >
                {{ showKey ? '隐藏' : '显示' }}
              </button>
            </div>
            <p v-if="hasSavedKey" class="option-hint subtle">
              留空并保存将删除已存储的 Key。输入新值将覆盖现有 Key。
            </p>

            <!-- Test connection -->
            <div class="test-row">
              <button
                class="zs-button zs-button-secondary"
                type="button"
                :disabled="!canTest"
                @click="handleTest"
              >
                {{ isTesting ? '测试中...' : '测试向量连接' }}
              </button>
              <span v-if="testResult?.success" class="test-success">
                连接成功 — {{ testResult.model_name }}，{{ testResult.vector_dim }} 维
              </span>
              <span v-else-if="testResult && !testResult.success" class="test-failure">
                {{ testResult.error }}
              </span>
            </div>
          </fieldset>

          <!-- LLM settings section -->
          <fieldset class="option-group">
            <legend class="option-label">AI 问答模型</legend>
            <p class="option-hint">
              启用后，知识库问答和摘要将使用 DashScope 大语言模型生成真实回答，否则使用占位文本。
            </p>

            <label class="toggle-row">
              <input v-model="llmEnabled" type="checkbox" />
              <span>启用 AI 问答</span>
            </label>

            <template v-if="llmEnabled">
              <label class="field-label">
                <span>模型</span>
                <select v-model="llmModel" class="field-select">
                  <option v-for="opt in llmModelOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
              </label>

              <label class="field-label">
                <span>自定义 Base URL（可选）</span>
                <input
                  v-model="llmBaseUrl"
                  type="text"
                  class="field-input"
                  placeholder="留空使用默认 DashScope 地址"
                />
              </label>

              <div class="test-row">
                <button
                  class="zs-button zs-button-secondary"
                  type="button"
                  :disabled="!canTestLlm"
                  @click="handleTestLlm"
                >
                  {{ isTestingLlm ? '测试中...' : '测试问答连接' }}
                </button>
                <span v-if="llmTestResult?.success" class="test-success">
                  连接成功 — {{ llmTestResult.model_name }}
                </span>
                <span v-else-if="llmTestResult && !llmTestResult.success" class="test-failure">
                  {{ llmTestResult.error }}
                </span>
              </div>

              <p v-if="!hasSavedKey" class="option-hint subtle">
                请先配置上方 DashScope API Key 后保存，再测试问答连接。
              </p>
            </template>
          </fieldset>

          <!-- Cloud account section -->
          <fieldset class="option-group">
            <legend class="option-label">章枢云账户</legend>
            <p class="option-hint">
              登录后可为项目启用云端备份，数据会加密上传到章枢云。
            </p>

            <div v-if="isCloudLoading" class="cloud-loading">正在加载…</div>

            <div v-else-if="cloudStatus?.logged_in" class="cloud-logged-in">
              <div class="cloud-account-info">
                <span class="cloud-label">已登录</span>
                <span class="cloud-email">{{ cloudStatus.email ?? cloudStatus.display_name }}</span>
              </div>
              <button
                class="zs-button zs-button-secondary"
                type="button"
                :disabled="isCloudLoading"
                @click="handleCloudLogout"
              >
                退出登录
              </button>
            </div>

            <div v-else class="cloud-not-logged-in">
              <p v-if="!cloudStatus?.cloud_available" class="option-hint subtle">
                云服务暂未配置，请联系管理员。
              </p>
              <p v-else class="option-hint">
                尚未登录，请在项目列表页面点击"云账户"登录或注册。
              </p>
            </div>
          </fieldset>

          <!-- Network diagnostics section -->
          <fieldset class="option-group">
            <legend class="option-label">网络连接</legend>
            <CloudNetworkDiagnosticsPanel />
          </fieldset>
        </template>
      </div>

      <footer class="zs-dialog-footer">
        <button
          class="zs-button zs-button-secondary"
          type="button"
          :disabled="isSaving || isTesting || isTestingLlm"
          @click="handleClose"
        >
          关闭
        </button>
        <button
          v-if="!isLoading"
          class="zs-button zs-button-primary"
          type="button"
          :disabled="!canSave"
          @click="handleSave"
        >
          {{ isSaving ? '保存中...' : '保存' }}
        </button>
        <span v-if="saveMessage" class="save-confirm">{{ saveMessage }}</span>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.settings-dialog {
  max-width: min(540px, 90vw);
  width: min(540px, 90vw);
  margin-inline: auto;
}

.settings-body {
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

.error-banner {
  padding: var(--zs-space-2) var(--zs-space-4);
  border-radius: var(--zs-radius-md, 6px);
  background: var(--zs-color-danger-soft, #fef2f2);
  color: var(--zs-color-danger, #ef4444);
  font-size: 0.875rem;
  line-height: 1.5;
}

.warning-banner {
  padding: var(--zs-space-2) var(--zs-space-4);
  border-radius: var(--zs-radius-md, 6px);
  background: var(--zs-color-warning-soft, #fff8e1);
  color: var(--zs-color-warning, #f59e0b);
  font-size: 0.875rem;
  line-height: 1.5;
}

.option-group {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-2);
  border: none;
  padding: 0;
  margin: 0;
}

.option-label {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--zs-color-text);
}

.option-hint {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.5;
  color: var(--zs-color-text-muted);
}

.option-hint.subtle {
  font-size: 0.78rem;
  opacity: 0.8;
}

.saved-key-preview {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  padding: var(--zs-space-2) var(--zs-space-3);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface-soft);
  font-size: 0.85rem;
}

.saved-key-label {
  color: var(--zs-color-text-muted);
}

.saved-key-masked {
  font-family: ui-monospace, 'Cascadia Code', 'Fira Code', monospace;
  letter-spacing: 0.05em;
  color: var(--zs-color-text);
}

.key-input-row {
  display: flex;
  gap: var(--zs-space-2);
}

.key-input {
  flex: 1;
  min-width: 0;
  padding: var(--zs-space-2) var(--zs-space-3);
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font-family: ui-monospace, 'Cascadia Code', 'Fira Code', monospace;
  font-size: 0.85rem;
}

.key-input:focus {
  outline: none;
  border-color: var(--zs-color-primary);
  box-shadow: var(--zs-shadow-focus);
}

.toggle-visibility {
  flex-shrink: 0;
  min-width: 56px;
}

.test-row {
  display: flex;
  align-items: center;
  gap: var(--zs-space-3);
  flex-wrap: wrap;
  margin-top: var(--zs-space-1);
}

.test-success {
  font-size: 0.82rem;
  color: var(--zs-color-success, #22c55e);
}

.test-failure {
  font-size: 0.82rem;
  color: var(--zs-color-danger, #ef4444);
}

.save-confirm {
  font-size: 0.82rem;
  color: var(--zs-color-success, #22c55e);
  margin-left: var(--zs-space-2);
}

.toggle-row {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--zs-color-text);
}

.toggle-row input[type='checkbox'] {
  width: 16px;
  height: 16px;
  accent-color: var(--zs-color-primary);
  cursor: pointer;
}

.field-label {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-1);
  font-size: 0.82rem;
  color: var(--zs-color-text-muted);
}

.field-select,
.field-input {
  padding: var(--zs-space-2) var(--zs-space-3);
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font-size: 0.85rem;
}

.field-select:focus,
.field-input:focus {
  outline: none;
  border-color: var(--zs-color-primary);
  box-shadow: var(--zs-shadow-focus);
}

.cloud-loading {
  padding: var(--zs-space-2) 0;
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
}

.cloud-logged-in {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-3);
}

.cloud-account-info {
  display: grid;
  gap: 2px;
}

.cloud-label {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
}

.cloud-email {
  color: var(--zs-color-text);
  font-weight: 800;
}

.cloud-not-logged-in {
  display: grid;
  gap: var(--zs-space-2);
}
</style>
