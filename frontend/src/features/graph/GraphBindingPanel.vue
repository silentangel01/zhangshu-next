<script setup lang="ts">
import { computed, reactive } from 'vue'

import type { GraphNodeBoundType } from '@/entities/graph/types'
import { graphNodeBoundTypeLabels } from '@/entities/graph/types'

export interface BindingOption {
  id: string
  label: string
  summary: string
}

const props = defineProps<{
  options: Record<'character' | 'setting' | 'clue' | 'timeline_event', BindingOption[]>
}>()

const emit = defineEmits<{
  createFromBinding: [boundType: Exclude<GraphNodeBoundType, 'custom'>, boundId: string]
}>()

const form = reactive({
  boundType: 'character' as Exclude<GraphNodeBoundType, 'custom'>,
  boundId: '',
})

const sourceTypes: Array<Exclude<GraphNodeBoundType, 'custom'>> = [
  'character',
  'setting',
  'clue',
  'timeline_event',
]

const currentOptions = computed(() => props.options[form.boundType])

function submit() {
  if (!form.boundId) {
    return
  }
  emit('createFromBinding', form.boundType, form.boundId)
}
</script>

<template>
  <section class="binding-panel">
    <header class="binding-header">
      <p>快速创建</p>
      <h2>从资料创建节点</h2>
    </header>
    <label>
      <span>来源</span>
      <select v-model="form.boundType" @change="form.boundId = ''">
        <option v-for="type in sourceTypes" :key="type" :value="type">
          {{ graphNodeBoundTypeLabels[type] }}
        </option>
      </select>
    </label>
    <label>
      <span>对象</span>
      <select v-model="form.boundId">
        <option value="">请选择绑定对象</option>
        <option v-for="item in currentOptions" :key="item.id" :value="item.id">{{ item.label }}</option>
      </select>
    </label>
    <button type="button" :disabled="!form.boundId" @click="submit">创建节点</button>
  </section>
</template>

<style scoped>
.binding-panel {
  display: grid;
  gap: 10px;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-3);
  background: var(--zs-color-surface-soft);
}

.binding-header {
  display: grid;
  gap: 4px;
  margin-bottom: 2px;
}

h2,
p {
  margin: 0;
}

p {
  color: var(--zs-color-text-faint);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.03em;
}

h2 {
  color: var(--zs-color-text);
  font-size: 0.92rem;
  font-weight: 700;
}

label {
  display: grid;
  gap: 4px;
}

label > span {
  color: var(--zs-color-text-faint);
  font-size: 0.74rem;
  font-weight: 700;
}

select,
button {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 7px 10px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.84rem;
}

select:focus {
  border-color: var(--zs-color-primary);
  outline: none;
}

button {
  min-height: 34px;
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
  font-weight: 700;
  cursor: pointer;
  transition: background var(--zs-duration-fast) var(--zs-ease-standard);
}

button:hover:not(:disabled) {
  background: var(--zs-color-primary-hover);
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
</style>
