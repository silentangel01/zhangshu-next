<script setup lang="ts">
import { ref, computed } from 'vue'

import {
  checkForUpdateWithFallback,
  downloadUpdate,
  installUpdate,
} from '@/entities/update/api'
import type { UpdateManifest, UpdatePhase } from '@/entities/update/types'

const version =
  import.meta.env.VITE_APP_VERSION ||
  (typeof __ZHANGSHU_APP_VERSION__ !== 'undefined'
    ? __ZHANGSHU_APP_VERSION__
    : 'dev')

const phase = ref<UpdatePhase>('idle')
const manifest = ref<UpdateManifest | null>(null)
const errorMessage = ref('')
/** The manifest URL that actually succeeded during check, used for download. */
const activeManifestUrl = ref<string | null>(null)
const errorExpanded = ref(false)
const copied = ref(false)

const isLoading = computed(() =>
  ['checking', 'downloading', 'installing'].includes(phase.value),
)

const hasUpdate = computed(() => phase.value === 'available')
const isDownloaded = computed(() => phase.value === 'downloaded')
const hasLongError = computed(() => errorMessage.value.length > 100)

async function copyDiagnostics() {
  try {
    await navigator.clipboard.writeText(errorMessage.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    /* clipboard API may fail in some environments */
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

async function handleCheckUpdate() {
  phase.value = 'checking'
  errorMessage.value = ''
  manifest.value = null
  activeManifestUrl.value = null
  errorExpanded.value = false

  try {
    const result = await checkForUpdateWithFallback()
    if (result.error) {
      phase.value = 'checkFailed'
      errorMessage.value = result.error
      return
    }
    activeManifestUrl.value = result.activeManifestUrl

    if (result.requiresManualDownload) {
      manifest.value = result.manifest
      phase.value = 'requiresManualUpdate'
      errorMessage.value =
        '当前版本过旧，无法自动更新，请前往官网下载最新版本安装包'
      return
    }

    if (!result.hasUpdate) {
      phase.value = 'upToDate'
      return
    }
    manifest.value = result.manifest
    phase.value = 'available'
  } catch (e) {
    phase.value = 'checkFailed'
    errorMessage.value =
      e instanceof Error ? e.message : '无法连接更新服务器'
  }
}

async function handleDownload() {
  if (!manifest.value || !activeManifestUrl.value) return

  phase.value = 'downloading'
  errorMessage.value = ''

  try {
    const result = await downloadUpdate(
      activeManifestUrl.value,
      manifest.value.version,
    )
    if (!result.success) {
      phase.value = 'downloadFailed'
      errorMessage.value = result.error ?? '下载失败'
      return
    }
    phase.value = 'downloaded'
  } catch (e) {
    phase.value = 'downloadFailed'
    errorMessage.value =
      e instanceof Error ? e.message : '下载失败'
  }
}

const showInstallConfirm = ref(false)

function handleInstallClick() {
  showInstallConfirm.value = true
}

async function confirmInstall() {
  if (!manifest.value) return

  showInstallConfirm.value = false
  phase.value = 'installing'
  errorMessage.value = ''

  try {
    const result = await installUpdate(manifest.value.version)
    if (!result.success) {
      phase.value = 'installFailed'
      errorMessage.value = result.error ?? '启动安装器失败'
    }
    // If successful, the updater helper will close the app and install.
    // We should not reach here in the success case.
  } catch (e) {
    phase.value = 'installFailed'
    errorMessage.value =
      e instanceof Error ? e.message : '启动安装器失败'
  }
}

function cancelInstall() {
  showInstallConfirm.value = false
}

const statusText = computed(() => {
  switch (phase.value) {
    case 'checking':
      return '正在检查更新…'
    case 'upToDate':
      return '当前已是最新版本'
    case 'requiresManualUpdate':
      return '当前版本过旧，需手动下载最新安装包'
    case 'downloading':
      return '正在下载新版本，请勿关闭…'
    case 'downloaded':
      return '下载完成，可以安装'
    case 'installing':
      return '正在启动安装器…'
    case 'checkFailed':
      return '检查更新失败'
    case 'downloadFailed':
      return '下载失败'
    case 'installFailed':
      return '安装失败'
    default:
      return ''
  }
})
</script>

<template>
  <div class="version-panel">
    <div class="version-row">
      <span class="version-label">软件版本</span>
      <span class="version-value">v{{ version }}</span>
    </div>

    <!-- Update status message (always rendered to reserve space, avoids layout shift) -->
    <div class="update-status" :class="phase">
      <span class="status-text">{{ statusText }}</span>
    </div>

    <!-- Error detail (always rendered to reserve space, avoids layout shift) -->
    <div class="error-detail" :class="{ visible: !!errorMessage, expanded: errorExpanded }">
      <span v-if="errorMessage">{{ errorMessage }}</span>
      <div v-if="errorMessage" class="error-actions">
        <button
          v-if="hasLongError"
          class="btn-text btn-text-sm"
          @click="errorExpanded = !errorExpanded"
        >
          {{ errorExpanded ? '收起详情' : '展开详情' }}
        </button>
        <button class="btn-text btn-text-sm" @click="copyDiagnostics">
          {{ copied ? '已复制' : '复制诊断信息' }}
        </button>
      </div>
    </div>

    <!-- New version info -->
    <div v-if="manifest && (hasUpdate || isDownloaded)" class="update-info">
      <div class="update-header">
        <span class="new-version">新版本 v{{ manifest.version }}</span>
        <span class="update-size">{{ formatSize(manifest.installer.sizeBytes) }}</span>
      </div>
      <ul v-if="manifest.releaseNotes.length > 0" class="release-notes">
        <li v-for="(note, i) in manifest.releaseNotes" :key="i">{{ note }}</li>
      </ul>
    </div>

    <!-- Action buttons -->
    <div class="update-actions">
      <button
        v-if="phase === 'idle' || phase === 'upToDate' || phase === 'checkFailed' || phase === 'downloadFailed' || phase === 'installFailed' || phase === 'requiresManualUpdate'"
        class="btn btn-secondary btn-sm"
        :disabled="isLoading"
        @click="handleCheckUpdate"
      >
        检查更新
      </button>
      <button
        v-if="hasUpdate"
        class="btn btn-primary btn-sm"
        :disabled="isLoading"
        @click="handleDownload"
      >
        下载新版本
      </button>
      <button
        v-if="isDownloaded"
        class="btn btn-primary btn-sm"
        :disabled="isLoading"
        @click="handleInstallClick"
      >
        安装并重启
      </button>
    </div>

    <!-- Install confirmation dialog -->
    <div v-if="showInstallConfirm" class="confirm-overlay" @click.self="cancelInstall">
      <div class="confirm-dialog">
        <h4 class="confirm-title">安装更新</h4>
        <p class="confirm-body">
          安装过程中将<strong>关闭章枢</strong>并运行安装程序。
        </p>
        <p class="confirm-body confirm-warning">
          请确保已保存所有编辑内容。安装过程可能触发 Windows 安全提示（UAC）。
        </p>
        <div class="confirm-actions">
          <button class="btn btn-secondary btn-sm" @click="cancelInstall">取消</button>
          <button class="btn btn-primary btn-sm" @click="confirmInstall">确认安装</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.version-panel {
  position: relative;
  padding: var(--zs-space-3) var(--zs-space-4);
  background: var(--zs-color-surface-soft);
  border-radius: var(--zs-radius-sm);
}

.version-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.version-label {
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
}

.version-value {
  font-weight: 600;
  font-size: 0.9rem;
  font-family: monospace;
}

.update-status {
  min-height: 1.4em;
  margin-top: var(--zs-space-2);
  font-size: 0.82rem;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.update-status.idle {
  opacity: 0;
}

.update-status.upToDate {
  color: var(--zs-color-success);
  opacity: 1;
}

.update-status.checking,
.update-status.downloading,
.update-status.installing {
  color: var(--zs-color-info);
  opacity: 1;
}

.update-status.requiresManualUpdate {
  color: var(--zs-color-warning);
  opacity: 1;
}

.update-status.checkFailed,
.update-status.downloadFailed,
.update-status.installFailed {
  color: var(--zs-color-danger);
  opacity: 1;
}

.error-detail {
  margin-top: var(--zs-space-1);
  font-size: 0.8rem;
  color: var(--zs-color-danger);
  min-height: 0;
  opacity: 0;
  max-height: 0;
  overflow: hidden;
  transition:
    max-height 0.2s ease,
    opacity 0.2s ease;
}

.error-detail.visible {
  padding: var(--zs-space-2);
  background: var(--zs-color-danger-soft);
  border-radius: var(--zs-radius-sm);
  max-height: 6em;
  opacity: 1;
}

.error-detail.expanded {
  max-height: 20em;
  overflow-y: auto;
}

.error-actions {
  display: flex;
  gap: var(--zs-space-2);
  margin-top: var(--zs-space-1);
}

.btn-text {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--zs-color-text-muted);
  padding: 0;
  text-decoration: underline;
}

.btn-text:hover {
  color: var(--zs-color-text);
}

.btn-text-sm {
  font-size: 0.75rem;
}

.update-info {
  margin-top: var(--zs-space-3);
  padding: var(--zs-space-2) var(--zs-space-3);
  background: var(--zs-color-surface);
  border-radius: var(--zs-radius-sm);
  border: 1px solid var(--zs-color-border-soft);
}

.update-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--zs-space-2);
}

.new-version {
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--zs-color-primary);
}

.update-size {
  font-size: 0.78rem;
  color: var(--zs-color-text-muted);
}

.release-notes {
  margin: 0;
  padding-left: var(--zs-space-4);
  font-size: 0.8rem;
  color: var(--zs-color-text-muted);
  line-height: 1.6;
}

.update-actions {
  display: flex;
  gap: var(--zs-space-2);
  margin-top: var(--zs-space-3);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: var(--zs-radius-sm);
  cursor: pointer;
  font-size: 0.82rem;
  transition:
    background 0.15s,
    opacity 0.15s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm {
  padding: var(--zs-space-1) var(--zs-space-3);
}

.btn-primary {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.btn-primary:hover:not(:disabled) {
  background: var(--zs-color-primary-hover);
}

.btn-secondary {
  background: var(--zs-color-surface-muted);
  color: var(--zs-color-text);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--zs-color-border);
}

/* Install confirmation dialog */
.confirm-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--zs-color-backdrop);
  z-index: 1000;
}

.confirm-dialog {
  background: var(--zs-color-surface);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-5);
  max-width: 400px;
  width: 90%;
  box-shadow: 0 8px 30px rgb(0 0 0 / 15%);
}

.confirm-title {
  margin: 0 0 var(--zs-space-3);
  font-size: 1rem;
  font-weight: 600;
}

.confirm-body {
  margin: 0 0 var(--zs-space-2);
  font-size: 0.85rem;
  line-height: 1.6;
  color: var(--zs-color-text);
}

.confirm-warning {
  color: var(--zs-color-warning);
}

.confirm-actions {
  display: flex;
  gap: var(--zs-space-2);
  justify-content: flex-end;
  margin-top: var(--zs-space-4);
}
</style>
