<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  modelValue: string[]
  suggestions: string[]
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const newTag = ref('')

const availableSuggestions = computed(() => {
  const selected = new Set(props.modelValue)
  return props.suggestions.filter((tag) => !selected.has(tag))
})

function addTag(tag: string) {
  const trimmed = tag.trim()
  if (!trimmed || props.modelValue.includes(trimmed)) {
    return
  }
  emit('update:modelValue', [...props.modelValue, trimmed])
  newTag.value = ''
}

function removeTag(tag: string) {
  emit(
    'update:modelValue',
    props.modelValue.filter((t) => t !== tag),
  )
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    event.preventDefault()
    addTag(newTag.value)
  }
}
</script>

<template>
  <div class="tag-input-root" :class="{ disabled }">
    <div class="tag-chips">
      <span v-for="tag in modelValue" :key="tag" class="tag-chip">
        {{ tag }}
        <button
          v-if="!disabled"
          type="button"
          class="chip-remove"
          :aria-label="`移除标签 ${tag}`"
          @click="removeTag(tag)"
        >
          &times;
        </button>
      </span>
    </div>

    <div v-if="!disabled" class="tag-add-row">
      <input
        v-model="newTag"
        type="text"
        placeholder="输入新标签，回车添加"
        class="tag-text-input"
        autocomplete="off"
        maxlength="24"
        @keydown="handleKeydown"
      />
      <button
        type="button"
        class="tag-add-button"
        :disabled="!newTag.trim()"
        @click="addTag(newTag)"
      >
        添加
      </button>
    </div>

    <div v-if="!disabled && availableSuggestions.length > 0" class="tag-suggestions">
      <span class="suggestions-label">标签库</span>
      <div class="suggestion-chips">
        <button
          v-for="tag in availableSuggestions"
          :key="tag"
          type="button"
          class="suggestion-chip"
          @click="addTag(tag)"
        >
          {{ tag }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tag-input-root {
  display: grid;
  gap: 10px;
}

.tag-input-root.disabled {
  opacity: 0.7;
}

.tag-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 4px;
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border-radius: 999px;
  padding: 4px 10px;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
  font-size: 0.82rem;
  font-weight: 700;
}

.chip-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border: none;
  border-radius: 50%;
  padding: 0;
  background: transparent;
  color: var(--zs-color-info);
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
}

.chip-remove:hover {
  background: var(--zs-color-primary-soft);
}

.tag-add-row {
  display: flex;
  gap: 8px;
}

.tag-text-input {
  flex: 1;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  padding: 8px 10px;
  color: var(--zs-color-text);
  font: inherit;
}

.tag-text-input:focus {
  border-color: var(--zs-color-primary);
  outline: 3px solid var(--zs-focus-ring);
}

.tag-add-button {
  min-height: 36px;
  border-radius: 6px;
  border: 1px solid var(--zs-color-border);
  padding: 0 12px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.tag-add-button:disabled {
  opacity: 0.5;
  cursor: default;
}

.tag-suggestions {
  display: grid;
  gap: 6px;
}

.suggestions-label {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.suggestion-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.suggestion-chip {
  border: 1px solid var(--zs-color-border);
  border-radius: 999px;
  padding: 3px 10px;
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}

.suggestion-chip:hover {
  border-color: var(--zs-color-border-strong);
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
}
</style>
