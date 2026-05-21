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
  border-top: 1px solid #e2e8f0;
  padding-top: 12px;
}

h2 {
  margin: 0;
  color: #111827;
  font-size: 0.96rem;
}

label {
  display: grid;
  gap: 6px;
}

span {
  color: #475569;
  font-size: 0.78rem;
  font-weight: 800;
}

select,
button {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  padding: 8px 10px;
  background: #ffffff;
  color: #111827;
  font: inherit;
  font-size: 0.84rem;
}

button {
  background: #2563eb;
  color: #ffffff;
  font-weight: 800;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
</style>
