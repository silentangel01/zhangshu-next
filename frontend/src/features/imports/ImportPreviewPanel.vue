<script setup lang="ts">
import type { ImportPreview } from '@/entities/import/types'

defineProps<{
  preview: ImportPreview
  projectTitle: string
  isConfirming: boolean
}>()

const emit = defineEmits<{
  'update:projectTitle': [value: string]
  confirm: []
}>()
</script>

<template>
  <section class="preview-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">可以导入</p>
        <h2>导入预览</h2>
      </div>
      <button
        class="primary-button"
        type="button"
        :disabled="!preview.can_import || isConfirming"
        @click="emit('confirm')"
      >
        {{ isConfirming ? '正在导入……' : '确认导入' }}
      </button>
    </header>

    <label class="title-field">
      <span>项目名覆盖（可选）</span>
      <input
        :value="projectTitle"
        type="text"
        placeholder="留空则使用检测到的项目名"
        @input="emit('update:projectTitle', ($event.target as HTMLInputElement).value)"
      />
    </label>

    <dl class="stats-grid">
      <div>
        <dt>检测到的项目名</dt>
        <dd>{{ preview.detected_project_title }}</dd>
      </div>
      <div>
        <dt>分卷数量</dt>
        <dd>{{ preview.volume_count }}</dd>
      </div>
      <div>
        <dt>章节数量</dt>
        <dd>{{ preview.chapter_count }}</dd>
      </div>
      <div>
        <dt>总字数</dt>
        <dd>{{ preview.total_word_count }}</dd>
      </div>
      <div>
        <dt>未分卷章节数量</dt>
        <dd>{{ preview.unassigned_chapter_count }}</dd>
      </div>
    </dl>

    <section v-if="preview.summary" class="text-block">
      <h3>简介</h3>
      <p>{{ preview.summary }}</p>
    </section>

    <section v-if="preview.volumes.length" class="text-block">
      <h3>分卷</h3>
      <ul>
        <li v-for="volume in preview.volumes" :key="volume.temp_id">
          {{ volume.order_index }}. {{ volume.title }}（{{ volume.chapter_count }} 章）
        </li>
      </ul>
    </section>

    <section v-if="preview.warnings.length" class="text-block warning">
      <h3>警告</h3>
      <ul>
        <li v-for="warning in preview.warnings" :key="warning">{{ warning }}</li>
      </ul>
    </section>

    <section v-if="preview.unsupported_items.length" class="text-block">
      <h3>暂不支持的内容</h3>
      <ul>
        <li v-for="item in preview.unsupported_items" :key="item">{{ item }}</li>
      </ul>
    </section>

    <section v-if="preview.failed_files.length" class="text-block error">
      <h3>失败文件</h3>
      <ul>
        <li v-for="file in preview.failed_files" :key="file">{{ file }}</li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.preview-panel {
  display: grid;
  gap: 18px;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 22px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgb(20 24 31 / 6%);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #047857;
  font-size: 0.78rem;
  font-weight: 800;
}

h2,
h3 {
  margin: 0;
  color: #111827;
}

h2 {
  font-size: 1.25rem;
}

h3 {
  font-size: 1rem;
}

.title-field {
  display: grid;
  gap: 8px;
  color: #4b5563;
  font-weight: 800;
}

input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 10px 12px;
  color: #111827;
  font: inherit;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin: 0;
}

.stats-grid div {
  border: 1px solid #edf0f5;
  border-radius: 8px;
  padding: 12px;
  background: #fbfcfe;
}

dt {
  margin: 0 0 4px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 800;
}

dd {
  margin: 0;
  color: #111827;
  font-weight: 800;
}

.text-block {
  display: grid;
  gap: 8px;
}

.text-block p,
.text-block ul {
  margin: 0;
  color: #4b5563;
  line-height: 1.7;
}

.warning h3 {
  color: #9a3412;
}

.error h3 {
  color: #b42318;
}

button {
  min-height: 38px;
  border-radius: 6px;
  border: 1px solid transparent;
  padding: 0 14px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.primary-button {
  background: #2563eb;
  color: #ffffff;
}
</style>
