<script setup lang="ts">
import { ref, watch } from 'vue'
import { updateCloudAccountProfile } from '@/entities/cloud/api'

const props = defineProps<{
  signature: string | null
}>()

const emit = defineEmits<{
  updated: []
  error: [message: string]
}>()

const MAX_LENGTH = 160

const draft = ref(props.signature ?? '')
const isSaving = ref(false)
const isDirty = ref(false)

watch(() => props.signature, (val) => {
  if (!isDirty.value) {
    draft.value = val ?? ''
  }
})

watch(draft, () => {
  isDirty.value = draft.value !== (props.signature ?? '')
})

async function save() {
  if (draft.value === (props.signature ?? '')) return

  isSaving.value = true
  try {
    await updateCloudAccountProfile({ signature: draft.value })
    isDirty.value = false
    emit('updated')
  } catch (e) {
    emit('error', e instanceof Error ? e.message : '保存签名失败。')
  } finally {
    isSaving.value = false
  }
}

function cancel() {
  draft.value = props.signature ?? ''
  isDirty.value = false
}
</script>

<template>
  <div class="signature-editor">
    <label class="field-label">个性签名</label>
    <textarea
      v-model="draft"
      class="signature-input"
      :maxlength="MAX_LENGTH"
      rows="2"
      placeholder="写一句介绍自己的话..."
    />
    <div class="signature-footer">
      <span class="char-count" :class="{ 'char-warn': draft.length > MAX_LENGTH * 0.9 }">
        {{ draft.length }} / {{ MAX_LENGTH }}
      </span>
      <div v-if="isDirty" class="signature-actions">
        <button type="button" class="btn-secondary" @click="cancel">取消</button>
        <button
          type="button"
          class="btn-primary"
          :disabled="isSaving || draft.length > MAX_LENGTH"
          @click="save"
        >
          {{ isSaving ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.signature-editor {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-2);
}

.field-label {
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
  font-weight: 600;
}

.signature-input {
  width: 100%;
  box-sizing: border-box;
  padding: var(--zs-space-2) var(--zs-space-3);
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  resize: vertical;
  min-height: 60px;
}

.signature-input:focus {
  outline: none;
  border-color: var(--zs-color-primary);
}

.signature-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.char-count {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
}

.char-warn {
  color: var(--zs-color-warning);
}

.signature-actions {
  display: flex;
  gap: var(--zs-space-2);
}

.btn-primary,
.btn-secondary {
  padding: 4px 12px;
  border-radius: var(--zs-radius-sm);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}

.btn-primary {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
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
</style>
