<script setup lang="ts">
import type { CharacterProfileSection } from '@/entities/character/types'
import { createEmptySection } from '@/features/characters/characterProfileDefaults'

const props = defineProps<{
  modelValue: CharacterProfileSection[]
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [sections: CharacterProfileSection[]]
}>()

function updateSection(index: number, patch: Partial<CharacterProfileSection>) {
  const next = props.modelValue.map((s, i) => (i === index ? { ...s, ...patch } : s))
  emit('update:modelValue', next)
}

function addSection() {
  const next = [...props.modelValue, createEmptySection(props.modelValue.length)]
  emit('update:modelValue', next)
}

function removeSection(index: number) {
  if (props.disabled) return
  const section = props.modelValue[index]
  if (!section) return
  const confirmed = window.confirm(`确认删除资料块"${section.title}"？此操作不可恢复。`)
  if (!confirmed) return
  const next = props.modelValue.filter((_, i) => i !== index).map((s, i) => ({ ...s, order: i }))
  emit('update:modelValue', next)
}

function moveSection(index: number, direction: -1 | 1) {
  const target = index + direction
  if (target < 0 || target >= props.modelValue.length) return
  const next = [...props.modelValue]
  const temp = next[index]!
  next[index] = next[target]!
  next[target] = temp
  emit('update:modelValue', next.map((s, i) => ({ ...s, order: i })))
}

function toggleCollapse(index: number) {
  const section = props.modelValue[index]
  if (!section) return
  updateSection(index, { collapsed: !section.collapsed })
}
</script>

<template>
  <section class="profile-sections" aria-label="自定义资料块">
    <header class="section-header">
      <h4 class="section-title">自定义资料</h4>
      <button
        type="button"
        class="add-button"
        :disabled="disabled || modelValue.length >= 30"
        @click="addSection"
      >
        + 新增资料块
      </button>
    </header>

    <p v-if="modelValue.length === 0" class="empty-hint">
      暂无自定义资料块，点击上方按钮新增。
    </p>

    <ul class="section-list">
      <li v-for="(section, index) in modelValue" :key="section.id" class="section-card">
        <header class="card-header" @click="toggleCollapse(index)">
          <div class="card-title-row">
            <span class="collapse-indicator">{{ section.collapsed ? '▸' : '▾' }}</span>
            <input
              type="text"
              class="title-input"
              :value="section.title"
              :disabled="disabled"
              maxlength="48"
              placeholder="资料标题"
              @input="updateSection(index, { title: ($event.target as HTMLInputElement).value })"
              @click.stop
            >
          </div>
          <div class="card-actions" @click.stop>
            <button
              type="button"
              title="上移"
              :disabled="disabled || index === 0"
              @click="moveSection(index, -1)"
            >↑</button>
            <button
              type="button"
              title="下移"
              :disabled="disabled || index === modelValue.length - 1"
              @click="moveSection(index, 1)"
            >↓</button>
            <button
              type="button"
              class="delete-button"
              title="删除"
              :disabled="disabled"
              @click="removeSection(index)"
            >✕</button>
          </div>
        </header>
        <div v-show="!section.collapsed" class="card-body">
          <textarea
            class="content-textarea"
            :value="section.content"
            :disabled="disabled"
            rows="4"
            placeholder="自由记录资料内容……"
            @input="updateSection(index, { content: ($event.target as HTMLTextAreaElement).value })"
          />
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.profile-sections {
  display: grid;
  gap: var(--zs-space-2);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-2);
}

.section-title {
  margin: 0;
  color: var(--zs-color-text-faint);
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.add-button {
  min-height: 26px;
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 var(--zs-space-2);
  background: transparent;
  color: var(--zs-color-text-muted);
  font: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}

.add-button:hover:not(:disabled) {
  border-color: var(--zs-color-primary);
  color: var(--zs-color-primary);
}

.add-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-hint {
  margin: 0;
  padding: var(--zs-space-3);
  border: 1px dashed var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  text-align: center;
}

.section-list {
  display: grid;
  gap: var(--zs-space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.section-card {
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-2);
  padding: var(--zs-space-1) var(--zs-space-2);
  cursor: pointer;
  user-select: none;
}

.card-header:hover {
  background: var(--zs-color-surface-soft);
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: var(--zs-space-1);
  min-width: 0;
  flex: 1;
}

.collapse-indicator {
  flex-shrink: 0;
  width: 14px;
  color: var(--zs-color-text-muted);
  font-size: 0.72rem;
  text-align: center;
}

.title-input {
  flex: 1;
  min-width: 0;
  border: none;
  border-bottom: 1px solid transparent;
  padding: 2px 0;
  background: transparent;
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.86rem;
  font-weight: 700;
}

.title-input:focus {
  border-bottom-color: var(--zs-color-primary);
  outline: none;
}

.title-input:disabled {
  opacity: 0.7;
}

.card-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}

.card-actions button {
  width: 24px;
  height: 24px;
  border: 1px solid transparent;
  border-radius: var(--zs-radius-sm);
  padding: 0;
  background: transparent;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  cursor: pointer;
}

.card-actions button:hover:not(:disabled) {
  border-color: var(--zs-color-border-soft);
  color: var(--zs-color-text);
}

.card-actions button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.delete-button:hover:not(:disabled) {
  color: var(--zs-color-danger) !important;
}

.card-body {
  padding: 0 var(--zs-space-2) var(--zs-space-2);
}

.content-textarea {
  display: block;
  width: 100%;
  min-height: 80px;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-1) var(--zs-space-2);
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.84rem;
  line-height: 1.6;
  resize: vertical;
}

.content-textarea:focus {
  border-color: var(--zs-color-primary);
  outline: none;
}

.content-textarea:disabled {
  opacity: 0.7;
}
</style>
