<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { adminLogin } from '@/entities/admin-auth/api'

const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await adminLogin({ email: email.value, password: password.value })
    sessionStorage.setItem('zs_admin_logged_in', '1')
    router.push('/')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card card">
      <h1 class="login-title">章枢云管理后台</h1>
      <p class="login-subtitle">仅限管理员使用</p>
      <form class="login-form" @submit.prevent="submit">
        <label>
          <span>邮箱</span>
          <input v-model="email" type="email" class="input" required autocomplete="username" />
        </label>
        <label>
          <span>密码</span>
          <input v-model="password" type="password" class="input" required autocomplete="current-password" />
        </label>
        <p v-if="error" class="login-error">{{ error }}</p>
        <button type="submit" class="btn btn-primary login-btn" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--ca-bg);
}
.login-card {
  width: 380px;
  max-width: calc(100vw - 32px);
}
.login-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: var(--ca-space-1);
}
.login-subtitle {
  font-size: 13px;
  color: var(--ca-text-muted);
  margin-bottom: var(--ca-space-5);
}
.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--ca-space-4);
}
.login-form label {
  display: flex;
  flex-direction: column;
  gap: var(--ca-space-1);
  font-size: 13px;
  color: var(--ca-text-muted);
}
.login-error {
  color: var(--ca-danger);
  font-size: 13px;
}
.login-btn {
  width: 100%;
  justify-content: center;
  padding: var(--ca-space-3);
}
</style>
