<script setup lang="ts">
import type { Chapter } from '@/entities/chapter/types'
import type { OutlineItem, OutlineItemUpdatePayload } from '@/entities/outline/types'
import type { Volume } from '@/entities/volume/types'
import OutlineEditor from './OutlineEditor.vue'

defineProps<{
  outline: OutlineItem
  outlines: OutlineItem[]
  volumes: Volume[]
  chapters: Chapter[]
  isSaving: boolean
}>()

const emit = defineEmits<{
  close: []
  save: [payload: OutlineItemUpdatePayload]
  delete: []
}>()
</script>

<template>
  <div class="dialog-backdrop" role="presentation" @click.self="emit('close')">
    <section class="dialog">
      <header class="dialog-header">
        <h2>编辑大纲</h2>
        <button class="icon-button" type="button" aria-label="关闭" @click="emit('close')">×</button>
      </header>
      <OutlineEditor
        :outline="outline"
        :outlines="outlines"
        :volumes="volumes"
        :chapters="chapters"
        :is-saving="isSaving"
        @save="emit('save', $event)"
        @delete="emit('delete')"
      />
    </section>
  </div>
</template>

<style scoped>
.dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgb(15 23 42 / 42%);
}

.dialog {
  width: min(820px, 100%);
  max-height: min(90vh, 780px);
  overflow: auto;
  box-sizing: border-box;
  border-radius: 8px;
  padding: 22px;
  background: #ffffff;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

h2 {
  margin: 0;
  font-size: 1.25rem;
}

.icon-button {
  width: 36px;
  min-height: 36px;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 0;
  background: #ffffff;
  color: #374151;
  font: inherit;
  font-size: 1.2rem;
  font-weight: 800;
  cursor: pointer;
}
</style>
