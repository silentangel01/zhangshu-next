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
    <header>
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
  border-top: 1px solid var(--zs-color-border-soft);
  padding-top: 12px;
}

header {
  display: grid;
  gap: 3px;
}

h2,
p {
  margin: 0;
}

p {
  color: var(--zs-color-text-muted);
  font-size: 0.76rem;
  font-weight: 900;
}

h2 {
  color: var(--zs-color-text);
  font-size: 0.96rem;
}

label {
  display: grid;
  gap: 6px;
}

span {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
}

select,
button {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 8px 10px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.84rem;
}

button {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
  font-weight: 800;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
</style>
