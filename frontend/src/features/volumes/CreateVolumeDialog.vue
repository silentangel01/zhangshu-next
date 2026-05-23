<script setup lang="ts">
import { reactive, ref } from 'vue'

import type { CreateVolumePayload } from '@/entities/volume/types'

const emit = defineEmits<{
  close: []
  submit: [payload: CreateVolumePayload]
}>()

const form = reactive({
  title: '',
  order_index: 0,
})

const titleError = ref('')

function handleSubmit() {
  const title = form.title.trim()

  if (!title) {
    titleError.value = '标题不能为空。'
    return
  }

  titleError.value = ''
  emit('submit', {
    title,
    order_index: Number(form.order_index),
  })
}
</script>

<template>
  <div class="zs-dialog" role="presentation">
    <section class="zs-dialog-content" role="dialog" aria-modal="true" aria-labelledby="create-volume-title">
      <header class="zs-dialog-header">
        <h2 id="create-volume-title">新建分卷</h2>
        <button class="zs-icon-button" type="button" aria-label="关闭" @click="emit('close')">x</button>
      </header>

      <form class="form" @submit.prevent="handleSubmit">
        <label class="zs-field">
          <span>标题</span>
          <input v-model="form.title" type="text" required autocomplete="off" />
        </label>
        <p v-if="titleError" class="field-error">{{ titleError }}</p>

        <label class="zs-field">
          <span>排序</span>
          <input v-model.number="form.order_index" type="number" min="0" required />
        </label>

        <footer class="zs-dialog-footer">
          <button class="zs-button zs-button-secondary" type="button" @click="emit('close')">取消</button>
          <button class="zs-button zs-button-primary" type="submit">新建</button>
        </footer>
      </form>
    </section>
  </div>
</template>

<style scoped>
h2 {
  margin: 0;
  color: var(--zs-color-text);
  font-size: 1.25rem;
}

.form {
  display: grid;
  gap: 16px;
  padding: 20px 24px 24px;
}

.field-error {
  margin: -8px 0 0;
  color: var(--zs-color-danger);
  font-size: 0.9rem;
}
</style>
