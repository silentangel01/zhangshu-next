<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getCloudAccountProfile } from '@/entities/cloud/api'
import type { CloudAccountProfile } from '@/entities/cloud/types'
import CloudPasswordChangePanel from './CloudPasswordChangePanel.vue'

const router = useRouter()

const profile = ref<CloudAccountProfile | null>(null)
const loading = ref(true)
const errorMessage = ref('')
const successMessage = ref('')

onMounted(async () => {
  try {
    profile.value = await getCloudAccountProfile()
  } catch {
    errorMessage.value = '无法加载账户信息。'
  } finally {
    loading.value = false
  }
})

function handlePasswordSuccess() {
  router.push('/projects')
}

function handleError(msg: string) {
  errorMessage.value = msg
  setTimeout(() => {
    errorMessage.value = ''
  }, 5000)
}

function formatDate(d: string | null): string {
  if (!d) return '-'
  try {
    return new Date(d).toLocaleDateString('zh-CN')
  } catch {
    return d
  }
}
</script>

<template>
  <div class="security-page">
    <header class="page-header">
      <button class="btn-back" @click="router.push('/account')">&larr; 返回账户</button>
      <h1 class="page-title">账号安全</h1>
    </header>

    <p v-if="loading" class="loading-text">加载中...</p>

    <template v-else>
      <div v-if="errorMessage" class="message message-error">{{ errorMessage }}</div>
      <div v-if="successMessage" class="message message-success">{{ successMessage }}</div>

      <section class="card password-info-section">
        <div class="info-row">
          <span class="info-label">密码修改时间</span>
          <span class="info-value">{{ formatDate(profile?.password_changed_at ?? null) }}</span>
        </div>
      </section>

      <section class="card password-change-section">
        <CloudPasswordChangePanel
          @success="handlePasswordSuccess"
          @error="handleError"
        />
      </section>
    </template>
  </div>
</template>

<style scoped>
.security-page {
  max-width: 600px;
  margin: 0 auto;
  padding: var(--zs-space-5);
}

.page-header {
  margin-bottom: var(--zs-space-5);
}

.btn-back {
  padding: var(--zs-space-2) 0;
  border: none;
  background: transparent;
  color: var(--zs-color-text-muted);
  font-size: 0.9rem;
  cursor: pointer;
  margin-bottom: var(--zs-space-2);
}

.btn-back:hover {
  color: var(--zs-color-primary);
}

.page-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
}

.loading-text {
  color: var(--zs-color-text-muted);
  text-align: center;
  padding: var(--zs-space-6);
}

.message {
  padding: var(--zs-space-3) var(--zs-space-4);
  border-radius: var(--zs-radius-sm);
  margin-bottom: var(--zs-space-4);
  font-size: 0.9rem;
}

.message-error {
  background: var(--zs-color-danger-soft, #fef2f2);
  color: var(--zs-color-danger);
}

.message-success {
  background: var(--zs-color-success-soft, #f0fdf4);
  color: var(--zs-color-success);
}

.card {
  background: var(--zs-color-surface);
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-4) var(--zs-space-5);
  margin-bottom: var(--zs-space-4);
}

.password-info-section {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-3);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--zs-space-2) 0;
}

.info-label {
  color: var(--zs-color-text-muted);
  font-size: 0.9rem;
}

.info-value {
  font-weight: 500;
  font-size: 0.9rem;
}
</style>
