<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  coverUrl: string | null
  defaultCoverUrl: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  'select-file': [file: File]
  'clear-cover': []
}>()

const MAX_SIZE = 5 * 1024 * 1024
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const acceptAttr = '.jpg,.jpeg,.png,.webp'

const sizeError = ref('')

function handleFileChange(event: Event) {
  sizeError.value = ''
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) {
    return
  }

  if (!ACCEPTED_TYPES.includes(file.type)) {
    sizeError.value = '只支持 JPG、PNG、WebP 格式的图片。'
    input.value = ''
    return
  }

  if (file.size > MAX_SIZE) {
    sizeError.value = '图片大小不能超过 5MB。'
    input.value = ''
    return
  }

  emit('select-file', file)
  input.value = ''
}

function handleClear() {
  sizeError.value = ''
  emit('clear-cover')
}
</script>

<template>
  <div class="cover-uploader">
    <div class="cover-preview">
      <img
        :src="coverUrl || defaultCoverUrl"
        alt="封面预览"
        class="cover-image"
      />
      <span v-if="!coverUrl" class="default-badge">默认封面</span>
    </div>

    <div class="cover-actions">
      <label v-if="!disabled" class="cover-file-label">
        <input
          type="file"
          :accept="acceptAttr"
          @change="handleFileChange"
        />
        选择图片
      </label>
      <button
        v-if="!disabled && coverUrl"
        type="button"
        class="cover-clear-button"
        @click="handleClear"
      >
        恢复默认封面
      </button>
    </div>

    <p v-if="sizeError" class="cover-error">{{ sizeError }}</p>
    <p class="cover-hint">支持 JPG、PNG、WebP，不超过 5MB</p>
  </div>
</template>

<style scoped>
.cover-uploader {
  display: grid;
  gap: 10px;
}

.cover-preview {
  position: relative;
  width: 120px;
  aspect-ratio: 3 / 4.2;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--zs-color-border);
  background: var(--zs-color-bg);
}

.cover-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.default-badge {
  position: absolute;
  bottom: 4px;
  left: 4px;
  border-radius: 4px;
  padding: 2px 6px;
  background: rgb(0 0 0 / 50%);
  color: var(--zs-color-overlay-text);
  font-size: 0.7rem;
  font-weight: 700;
}

.cover-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.cover-file-label {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  padding: 0 12px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font-weight: 700;
  font-size: 0.86rem;
  cursor: pointer;
}

.cover-file-label input[type='file'] {
  display: none;
}

.cover-clear-button {
  min-height: 34px;
  border: 1px solid var(--zs-color-danger);
  border-radius: 6px;
  padding: 0 12px;
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
  font: inherit;
  font-weight: 700;
  font-size: 0.86rem;
  cursor: pointer;
}

.cover-error {
  margin: 0;
  color: var(--zs-color-danger);
  font-size: 0.82rem;
  font-weight: 600;
}

.cover-hint {
  margin: 0;
  color: var(--zs-color-text-faint);
  font-size: 0.78rem;
}
</style>
