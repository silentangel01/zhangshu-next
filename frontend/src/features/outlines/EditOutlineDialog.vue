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
  <div class="zs-dialog" role="presentation" @click.self="emit('close')">
    <section class="zs-dialog-content outline-edit-dialog">
      <header class="zs-dialog-header">
        <h2>编辑大纲</h2>
        <button class="zs-icon-button" type="button" aria-label="关闭" @click="emit('close')">×</button>
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
h2 {
  margin: 0;
  font-size: 1.25rem;
}

.outline-edit-dialog {
  max-width: min(720px, calc(100vw - 32px));
}
</style>
