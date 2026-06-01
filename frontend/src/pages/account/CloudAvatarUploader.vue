<script setup lang="ts">
import { ref } from 'vue'
import { uploadCloudAvatar, deleteCloudAvatar } from '@/entities/cloud/api'
import type { CloudAccountProfile } from '@/entities/cloud/types'

const props = defineProps<{
  profile: CloudAccountProfile
}>()

const emit = defineEmits<{
  updated: []
  error: [message: string]
}>()

const isUploading = ref(false)
const isDeleting = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const AVATAR_MAX_SIZE = 2 * 1024 * 1024 // 2 MB
const AVATAR_ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/webp']

function triggerFileSelect() {
  fileInput.value?.click()
}

async function handleFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  // Validate type
  if (!AVATAR_ALLOWED_TYPES.includes(file.type)) {
    emit('error', '不支持的图片格式。仅支持 PNG、JPEG、WebP。')
    input.value = ''
    return
  }

  // Validate size
  if (file.size > AVATAR_MAX_SIZE) {
    emit('error', `图片过大 (${(file.size / (1024 * 1024)).toFixed(1)} MB)。最大允许 2 MB。`)
    input.value = ''
    return
  }

  isUploading.value = true
  try {
    await uploadCloudAvatar(file)
    emit('updated')
  } catch (e) {
    emit('error', e instanceof Error ? e.message : '上传头像失败。')
  } finally {
    isUploading.value = false
    input.value = ''
  }
}

async function handleDelete() {
  if (!confirm('确定删除头像？')) return

  isDeleting.value = true
  try {
    await deleteCloudAvatar()
    emit('updated')
  } catch (e) {
    emit('error', e instanceof Error ? e.message : '删除头像失败。')
  } finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <div class="avatar-uploader">
    <div class="avatar-preview" @click="triggerFileSelect">
      <img
        v-if="profile.avatar_url"
        :src="profile.avatar_url"
        :alt="profile.display_name"
        class="avatar-image"
      />
      <div v-else class="avatar-placeholder">
        {{ profile.display_name?.charAt(0)?.toUpperCase() || '?' }}
      </div>
      <div class="avatar-overlay">
        <span>{{ isUploading ? '上传中...' : '更换' }}</span>
      </div>
    </div>
    <input
      ref="fileInput"
      type="file"
      accept="image/png,image/jpeg,image/webp"
      hidden
      @change="handleFileSelected"
    />
    <div class="avatar-actions">
      <button
        type="button"
        class="btn-text"
        :disabled="isUploading"
        @click="triggerFileSelect"
      >
        {{ isUploading ? '上传中...' : '上传头像' }}
      </button>
      <button
        v-if="profile.avatar_url"
        type="button"
        class="btn-text btn-text-danger"
        :disabled="isDeleting || isUploading"
        @click="handleDelete"
      >
        {{ isDeleting ? '删除中...' : '删除' }}
      </button>
    </div>
    <p class="avatar-hint">支持 PNG、JPEG、WebP，最大 2 MB</p>
  </div>
</template>

<style scoped>
.avatar-uploader {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--zs-space-3);
}

.avatar-preview {
  position: relative;
  width: 96px;
  height: 96px;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid var(--zs-color-border-soft);
}

.avatar-preview:hover .avatar-overlay {
  opacity: 1;
}

.avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
  font-size: 2rem;
  font-weight: 700;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  font-size: 0.85rem;
  font-weight: 600;
  opacity: 0;
  transition: opacity 0.2s;
}

.avatar-actions {
  display: flex;
  gap: var(--zs-space-3);
}

.btn-text {
  padding: 4px 8px;
  border: none;
  background: transparent;
  color: var(--zs-color-primary);
  font-size: 0.85rem;
  cursor: pointer;
}

.btn-text:hover:not(:disabled) {
  text-decoration: underline;
}

.btn-text:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-text-danger {
  color: var(--zs-color-danger);
}

.avatar-hint {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
}
</style>
