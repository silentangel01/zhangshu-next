<script setup lang="ts">
import { ref } from 'vue'
import { changeCloudPassword, cloudLogout } from '@/entities/cloud/api'

const emit = defineEmits<{
  success: []
  error: [message: string]
}>()

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const isSubmitting = ref(false)
const showWarning = ref(false)

function validate(): string | null {
  if (!oldPassword.value || !newPassword.value) {
    return '请输入当前密码和新密码。'
  }
  if (oldPassword.value === newPassword.value) {
    return '新密码不能与当前密码相同。'
  }
  if (newPassword.value.length < 10) {
    return '新密码至少需要 10 个字符。'
  }
  if (newPassword.value !== confirmPassword.value) {
    return '两次输入的新密码不一致。'
  }
  return null
}

function proceedToChange() {
  const error = validate()
  if (error) {
    emit('error', error)
    return
  }
  showWarning.value = true
}

async function submitChange() {
  const error = validate()
  if (error) {
    emit('error', error)
    return
  }

  isSubmitting.value = true
  try {
    await changeCloudPassword(oldPassword.value, newPassword.value)
    // Clear local tokens after successful change
    await cloudLogout()
    emit('success')
  } catch (e) {
    emit('error', e instanceof Error ? e.message : '修改密码失败。')
  } finally {
    isSubmitting.value = false
    showWarning.value = false
  }
}

function cancelWarning() {
  showWarning.value = false
}
</script>

<template>
  <div class="password-panel">
    <h4 class="panel-title">修改密码</h4>
    <p class="panel-hint">
      密码至少 10 个字符，建议包含字母和数字。修改后所有设备将需要重新登录。
    </p>

    <form @submit.prevent="proceedToChange">
      <label class="field">
        <span>当前密码</span>
        <input v-model="oldPassword" type="password" required />
      </label>
      <label class="field">
        <span>新密码</span>
        <input v-model="newPassword" type="password" required minlength="10" />
      </label>
      <label class="field">
        <span>确认新密码</span>
        <input v-model="confirmPassword" type="password" required />
      </label>
      <button type="submit" class="btn-primary" :disabled="isSubmitting">
        修改密码
      </button>
    </form>

    <!-- Warning confirmation -->
    <div v-if="showWarning" class="warning-overlay" @click.self="cancelWarning">
      <div class="warning-dialog">
        <h5>确认修改密码？</h5>
        <p>
          修改密码后，您需要在所有设备上重新登录。确定要继续吗？
        </p>
        <div class="warning-actions">
          <button type="button" class="btn-secondary" @click="cancelWarning">取消</button>
          <button
            type="button"
            class="btn-danger"
            :disabled="isSubmitting"
            @click="submitChange"
          >
            {{ isSubmitting ? '修改中...' : '确认修改' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.password-panel {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-3);
}

.panel-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.panel-hint {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
  line-height: 1.5;
}

form {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-3);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-1);
  font-size: 0.85rem;
  color: var(--zs-color-text-muted);
}

.field input {
  width: 100%;
  box-sizing: border-box;
  padding: var(--zs-space-2) var(--zs-space-3);
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
}

.field input:focus {
  outline: none;
  border-color: var(--zs-color-primary);
}

.btn-primary,
.btn-secondary,
.btn-danger {
  padding: var(--zs-space-2) var(--zs-space-4);
  border-radius: var(--zs-radius-sm);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}

.btn-primary {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
  align-self: flex-start;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  border-color: var(--zs-color-border);
}

.btn-danger {
  background: var(--zs-color-danger);
  color: white;
}

.btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.warning-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
}

.warning-dialog {
  background: var(--zs-color-surface);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-5);
  max-width: 400px;
  width: calc(100% - 32px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.warning-dialog h5 {
  margin: 0 0 var(--zs-space-3);
  font-size: 1.1rem;
}

.warning-dialog p {
  margin: 0 0 var(--zs-space-4);
  color: var(--zs-color-text-muted);
  line-height: 1.5;
}

.warning-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--zs-space-3);
}
</style>
