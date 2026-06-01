<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  title: string
  message: string
  confirmLabel?: string
  confirmText?: string
  requireReason?: boolean
  variant?: 'warning' | 'danger' | 'critical'
}>()

const emit = defineEmits<{
  confirm: [payload: { reason: string; confirm_text: string }]
  cancel: []
}>()

const reason = ref('')
const confirmInput = ref('')
const loading = ref(false)

const needsConfirmText = computed(() => !!props.confirmText)
const canSubmit = computed(() => {
  if (props.requireReason && !reason.value.trim()) return false
  if (needsConfirmText.value && confirmInput.value !== props.confirmText) return false
  return true
})

function handleConfirm() {
  if (!canSubmit.value) return
  emit('confirm', { reason: reason.value.trim(), confirm_text: confirmInput.value })
}

function handleCancel() {
  reason.value = ''
  confirmInput.value = ''
  emit('cancel')
}

function setLoading(v: boolean) {
  loading.value = v
}

defineExpose({ setLoading })
</script>

<template>
  <Teleport to="body">
    <div class="dialog-overlay" @click.self="handleCancel">
      <div class="dialog-card" :class="`variant-${variant || 'warning'}`">
        <h3 class="dialog-title">{{ title }}</h3>
        <p class="dialog-message">{{ message }}</p>

        <div v-if="requireReason" class="dialog-field">
          <label>操作原因 <span class="required">*</span></label>
          <textarea
            v-model="reason"
            rows="3"
            placeholder="请说明执行此操作的原因..."
            class="reason-input"
          />
        </div>

        <div v-if="needsConfirmText" class="dialog-field">
          <label>
            请输入 <code>{{ confirmText }}</code> 以确认 <span class="required">*</span>
          </label>
          <input
            v-model="confirmInput"
            type="text"
            class="confirm-input"
            :placeholder="confirmText"
          />
        </div>

        <div class="dialog-actions">
          <button class="btn btn-cancel" :disabled="loading" @click="handleCancel">
            取消
          </button>
          <button
            class="btn btn-confirm"
            :disabled="!canSubmit || loading"
            @click="handleConfirm"
          >
            {{ confirmLabel || '确认' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
}

.dialog-card {
  width: 100%;
  max-width: 440px;
  margin: 0 var(--ca-space-4);
  padding: var(--ca-space-5);
  background: var(--ca-surface, #fff);
  border: 1px solid var(--ca-border);
  border-radius: 8px;
  border-top: 4px solid var(--ca-warning);
}

.variant-warning { border-top-color: var(--ca-warning); }
.variant-danger { border-top-color: var(--ca-danger); }
.variant-critical { border-top-color: #7c3aed; }

.dialog-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: var(--ca-space-2);
}

.dialog-message {
  font-size: 13px;
  color: var(--ca-text-muted);
  margin-bottom: var(--ca-space-4);
  line-height: 1.5;
}

.dialog-field {
  margin-bottom: var(--ca-space-3);
}

.dialog-field label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: var(--ca-space-1);
}

.dialog-field code {
  padding: 1px 4px;
  background: var(--ca-bg);
  border: 1px solid var(--ca-border);
  border-radius: 3px;
  font-size: 12px;
}

.required { color: var(--ca-danger); }

.reason-input,
.confirm-input {
  width: 100%;
  padding: var(--ca-space-2) var(--ca-space-3);
  border: 1px solid var(--ca-border);
  border-radius: 4px;
  font-size: 13px;
  font-family: inherit;
  color: var(--ca-text);
  background: var(--ca-bg);
  resize: vertical;
  box-sizing: border-box;
}

.reason-input:focus,
.confirm-input:focus {
  outline: none;
  border-color: var(--ca-primary, #3b82f6);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--ca-space-3);
  margin-top: var(--ca-space-4);
}

.btn-cancel {
  padding: var(--ca-space-2) var(--ca-space-4);
  border: 1px solid var(--ca-border);
  border-radius: 4px;
  background: var(--ca-surface, #fff);
  font-size: 13px;
  cursor: pointer;
  color: var(--ca-text);
}

.btn-cancel:hover { background: var(--ca-bg); }

.btn-confirm {
  padding: var(--ca-space-2) var(--ca-space-4);
  border: 1px solid var(--ca-danger);
  border-radius: 4px;
  background: var(--ca-danger);
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}

.variant-warning .btn-confirm { background: var(--ca-warning); border-color: var(--ca-warning); }
.variant-danger .btn-confirm { background: var(--ca-danger); border-color: var(--ca-danger); }
.variant-critical .btn-confirm { background: #7c3aed; border-color: #7c3aed; }

.btn-confirm:hover { opacity: 0.9; }
.btn-confirm:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancel:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
