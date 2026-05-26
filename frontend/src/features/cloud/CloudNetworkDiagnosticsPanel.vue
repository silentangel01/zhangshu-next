<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  getCloudNetworkSettings,
  runCloudNetworkDiagnostics,
  setCloudNetworkSettings,
} from '@/entities/cloud/api'
import type {
  CloudNetworkDiagnosticReport,
  CloudNetworkDiagnosticStep,
  CloudNetworkMode,
  CloudNetworkSettings,
} from '@/entities/cloud/types'

const settings = ref<CloudNetworkSettings | null>(null)
const report = ref<CloudNetworkDiagnosticReport | null>(null)
const isDiagnosing = ref(false)
const isSavingMode = ref(false)
const errorMessage = ref('')
const showAdvanced = ref(false)

const MODE_LABELS: Record<CloudNetworkMode, string> = {
  auto: '自动',
  secure_direct: '安全直连',
  system_proxy: '系统代理',
  compat_no_sni: '兼容模式',
}

const MODE_DESCRIPTIONS: Record<CloudNetworkMode, string> = {
  auto: '自动尝试安全直连、代理、兼容模式',
  secure_direct: '完整 TLS 验证，不使用系统代理',
  system_proxy: '完整 TLS 验证，允许系统代理',
  compat_no_sni: 'IP 直连，跳过证书验证（校园/公司网拦截时使用）',
}

const STEP_LABELS: Record<string, string> = {
  config_check: '配置检查',
  https_policy_check: 'HTTPS 策略',
  dns_check: 'DNS 解析',
  tcp_check: 'TCP 连接',
  secure_https_check: '安全 HTTPS',
  system_proxy_check: '系统代理',
  compat_no_sni_check: '兼容模式',
}

onMounted(async () => {
  try {
    settings.value = await getCloudNetworkSettings()
  } catch {
    errorMessage.value = '读取网络设置失败。'
  }
})

async function handleDiagnose() {
  isDiagnosing.value = true
  report.value = null
  errorMessage.value = ''

  try {
    report.value = await runCloudNetworkDiagnostics()
  } catch {
    errorMessage.value = '诊断请求失败。'
  } finally {
    isDiagnosing.value = false
  }
}

async function handleModeChange(mode: CloudNetworkMode) {
  if (!settings.value || settings.value.mode === mode) return
  isSavingMode.value = true
  errorMessage.value = ''

  try {
    settings.value = await setCloudNetworkSettings(mode)
  } catch {
    errorMessage.value = '保存连接模式失败。'
  } finally {
    isSavingMode.value = false
  }
}

function stepLabel(name: string): string {
  return STEP_LABELS[name] ?? name
}
</script>

<template>
  <div class="network-diagnostics-panel">
    <!-- Current mode display -->
    <div v-if="settings" class="mode-status">
      <span class="mode-label">当前连接模式：</span>
      <span class="mode-value">{{ MODE_LABELS[settings.mode] }}</span>
      <span v-if="settings.last_working_mode" class="last-working">
        (上次成功: {{ MODE_LABELS[settings.last_working_mode] }})
      </span>
    </div>

    <!-- Diagnose button -->
    <button
      class="diagnose-button"
      type="button"
      :disabled="isDiagnosing"
      @click="handleDiagnose"
    >
      {{ isDiagnosing ? '正在检测...' : '检测云服务连接' }}
    </button>

    <!-- Diagnostic report -->
    <div v-if="report" class="diagnostic-report">
      <div :class="['report-summary', report.ok ? 'ok' : 'failed']">
        {{ report.summary }}
      </div>

      <!-- Recommended mode suggestion -->
      <div v-if="!report.ok && report.recommended_mode !== settings?.mode" class="recommendation">
        <span>建议使用：</span>
        <button
          class="recommend-button"
          type="button"
          :disabled="isSavingMode"
          @click="handleModeChange(report.recommended_mode)"
        >
          {{ MODE_LABELS[report.recommended_mode] }}
        </button>
      </div>

      <!-- Step details -->
      <ul class="step-list">
        <li v-for="step in report.steps" :key="step.name" class="step-item">
          <div class="step-header">
            <span :class="['step-icon', step.ok ? 'ok' : 'failed']">
              {{ step.ok ? 'OK' : '!!' }}
            </span>
            <span class="step-name">{{ stepLabel(step.name) }}</span>
            <span v-if="step.latency_ms !== null" class="step-latency">
              {{ step.latency_ms }}ms
            </span>
          </div>
          <p v-if="step.message" class="step-message">{{ step.message }}</p>
          <p v-if="!step.ok && step.suggestion" class="step-suggestion">
            {{ step.suggestion }}
          </p>
        </li>
      </ul>
    </div>

    <!-- Advanced mode selector -->
    <div class="advanced-section">
      <button
        class="advanced-toggle"
        type="button"
        @click="showAdvanced = !showAdvanced"
      >
        {{ showAdvanced ? '收起高级设置' : '高级设置' }}
      </button>

      <div v-if="showAdvanced" class="mode-options">
        <p class="mode-hint">
          手动选择连接模式。推荐使用"自动"。
        </p>
        <label
          v-for="mode in (['auto', 'secure_direct', 'system_proxy', 'compat_no_sni'] as CloudNetworkMode[])"
          :key="mode"
          :class="['mode-option', { active: settings?.mode === mode }]"
        >
          <input
            type="radio"
            :value="mode"
            :checked="settings?.mode === mode"
            name="cloud-network-mode"
            :disabled="isSavingMode"
            @change="handleModeChange(mode)"
          />
          <div class="mode-info">
            <span class="mode-name">{{ MODE_LABELS[mode] }}</span>
            <span class="mode-desc">{{ MODE_DESCRIPTIONS[mode] }}</span>
          </div>
        </label>
        <p v-if="settings?.mode === 'compat_no_sni'" class="compat-warning">
          兼容模式会降低证书校验强度，仅在普通连接失败时使用。
        </p>
      </div>
    </div>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
  </div>
</template>

<style scoped>
.network-diagnostics-panel {
  display: grid;
  gap: var(--zs-space-3);
}

.mode-status {
  font-size: 0.85rem;
  color: var(--zs-color-text-muted);
}

.mode-label {
  font-weight: 800;
}

.mode-value {
  color: var(--zs-color-text);
  font-weight: 800;
}

.last-working {
  font-size: 0.78rem;
  opacity: 0.7;
}

.diagnose-button {
  min-height: 34px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  padding: 0 14px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.diagnose-button:disabled {
  opacity: 0.65;
  cursor: wait;
}

.report-summary {
  padding: var(--zs-space-2) var(--zs-space-3);
  border-radius: var(--zs-radius-md);
  font-size: 0.85rem;
  line-height: 1.5;
}

.report-summary.ok {
  background: var(--zs-color-success-soft, #f0fdf4);
  color: var(--zs-color-success, #22c55e);
}

.report-summary.failed {
  background: var(--zs-color-danger-soft, #fef2f2);
  color: var(--zs-color-danger, #ef4444);
}

.recommendation {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
  font-size: 0.85rem;
  color: var(--zs-color-text-muted);
}

.recommend-button {
  min-height: 28px;
  border: 1px solid var(--zs-color-primary);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
  padding: 0 10px;
  font: inherit;
  font-size: 0.82rem;
  font-weight: 800;
  cursor: pointer;
}

.step-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--zs-space-2);
}

.step-item {
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  padding: 8px 10px;
  background: var(--zs-color-surface-soft);
}

.step-header {
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
}

.step-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: var(--zs-radius-sm);
  font-size: 0.72rem;
  font-weight: 800;
}

.step-icon.ok {
  background: var(--zs-color-success-soft, #f0fdf4);
  color: var(--zs-color-success, #22c55e);
}

.step-icon.failed {
  background: var(--zs-color-danger-soft, #fef2f2);
  color: var(--zs-color-danger, #ef4444);
}

.step-name {
  font-weight: 800;
  font-size: 0.85rem;
  color: var(--zs-color-text);
}

.step-latency {
  margin-left: auto;
  font-size: 0.78rem;
  color: var(--zs-color-text-muted);
}

.step-message {
  margin: 4px 0 0;
  font-size: 0.82rem;
  color: var(--zs-color-text-muted);
  line-height: 1.4;
}

.step-suggestion {
  margin: 4px 0 0;
  font-size: 0.78rem;
  color: var(--zs-color-warning, #f59e0b);
  line-height: 1.4;
}

.advanced-section {
  border-top: 1px solid var(--zs-color-border-soft);
  padding-top: var(--zs-space-2);
}

.advanced-toggle {
  border: none;
  background: none;
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  cursor: pointer;
  padding: 0;
}

.mode-options {
  display: grid;
  gap: var(--zs-space-2);
  margin-top: var(--zs-space-2);
}

.mode-hint {
  margin: 0;
  font-size: 0.78rem;
  color: var(--zs-color-text-muted);
}

.mode-option {
  display: flex;
  align-items: flex-start;
  gap: var(--zs-space-2);
  padding: 8px 10px;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  cursor: pointer;
}

.mode-option.active {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft, #eff6ff);
}

.mode-option input[type='radio'] {
  margin-top: 2px;
  accent-color: var(--zs-color-primary);
}

.mode-info {
  display: grid;
  gap: 2px;
}

.mode-name {
  font-weight: 800;
  font-size: 0.85rem;
  color: var(--zs-color-text);
}

.mode-desc {
  font-size: 0.78rem;
  color: var(--zs-color-text-muted);
}

.compat-warning {
  margin: 0;
  font-size: 0.78rem;
  color: var(--zs-color-warning, #f59e0b);
  padding: var(--zs-space-2);
  background: var(--zs-color-warning-soft, #fff8e1);
  border-radius: var(--zs-radius-sm);
}

.error-text {
  margin: 0;
  color: var(--zs-color-danger);
  font-weight: 800;
  font-size: 0.85rem;
}
</style>
