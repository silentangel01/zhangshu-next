<script setup lang="ts">
import type { ImportPreview } from '@/entities/import/types'

withDefaults(defineProps<{
  preview: ImportPreview
  projectTitle: string
  isConfirming: boolean
  showProjectTitle?: boolean
}>(), {
  showProjectTitle: true,
})

const emit = defineEmits<{
  'update:projectTitle': [value: string]
  confirm: []
}>()
</script>

<template>
  <section class="preview-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">导入报告</p>
        <h2>预览导入</h2>
      </div>
      <button
        class="primary-button"
        type="button"
        :disabled="!preview.can_import || isConfirming"
        @click="emit('confirm')"
      >
        {{ isConfirming ? '正在导入…' : '确认导入' }}
      </button>
    </header>

    <label v-if="showProjectTitle" class="title-field">
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
        <dt>文件数</dt>
        <dd>{{ preview.report.files_detected.length }}</dd>
      </div>
      <div>
        <dt>分卷数</dt>
        <dd>{{ preview.volume_count }}</dd>
      </div>
      <div>
        <dt>章节数</dt>
        <dd>{{ preview.chapter_count }}</dd>
      </div>
      <div>
        <dt>总字数</dt>
        <dd>{{ preview.total_word_count }}</dd>
      </div>
    </dl>

    <section class="text-block">
      <h3>预览结构</h3>
      <ul>
        <li v-for="volume in preview.volumes" :key="volume.temp_id">
          {{ volume.order_index + 1 }}. {{ volume.title }}（{{ volume.chapter_count }} 章）
          <ul>
            <li v-for="chapter in volume.chapters" :key="chapter">{{ chapter }}</li>
          </ul>
        </li>
        <li v-if="preview.unassigned_chapters.length">
          未分卷章节（{{ preview.unassigned_chapters.length }} 章）
          <ul>
            <li v-for="chapter in preview.unassigned_chapters" :key="chapter">{{ chapter }}</li>
          </ul>
        </li>
      </ul>
    </section>

    <section class="text-block">
      <h3>导入报告</h3>
      <dl class="report-grid">
        <div>
          <dt>检测文件</dt>
          <dd>{{ preview.report.files_detected.length }}</dd>
        </div>
        <div>
          <dt>跳过文件</dt>
          <dd>{{ preview.report.files_skipped.length }}</dd>
        </div>
        <div>
          <dt>编码问题</dt>
          <dd>{{ preview.report.encoding_issues.length }}</dd>
        </div>
        <div>
          <dt>空文件</dt>
          <dd>{{ preview.report.empty_files.length }}</dd>
        </div>
        <div>
          <dt>重复标题</dt>
          <dd>{{ preview.report.duplicate_titles.length }}</dd>
        </div>
        <div>
          <dt>不支持文件</dt>
          <dd>{{ preview.report.unsupported_files.length }}</dd>
        </div>
      </dl>
    </section>

    <section v-if="preview.warnings.length" class="text-block warning">
      <h3>警告</h3>
      <ul>
        <li v-for="warning in preview.warnings" :key="warning">{{ warning }}</li>
      </ul>
    </section>

    <section v-if="preview.report.unsupported_files.length" class="text-block">
      <h3>不支持的文件</h3>
      <ul>
        <li v-for="item in preview.report.unsupported_files" :key="item">{{ item }}</li>
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
  gap: var(--zs-space-4);
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-5);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--zs-space-4);
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--zs-color-success);
  font-size: 0.78rem;
  font-weight: 800;
}

h2,
h3 {
  margin: 0;
  color: var(--zs-color-text);
}

h2 {
  font-size: 1.25rem;
}

h3 {
  font-size: 1rem;
}

.title-field {
  display: grid;
  gap: var(--zs-space-2);
  color: var(--zs-color-text-muted);
  font-weight: 800;
}

input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 10px 12px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
}

.stats-grid,
.report-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--zs-space-3);
  margin: 0;
}

.stats-grid div,
.report-grid div {
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  padding: 12px;
  background: var(--zs-color-surface-soft);
}

dt {
  margin: 0 0 4px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
}

dd {
  margin: 0;
  color: var(--zs-color-text);
  font-weight: 800;
}

.text-block {
  display: grid;
  gap: 8px;
}

.text-block ul {
  margin: 0;
  color: var(--zs-color-text-muted);
  line-height: 1.7;
}

.warning h3 {
  color: var(--zs-color-warning);
}

.error h3 {
  color: var(--zs-color-danger);
}

button {
  min-height: 38px;
  border-radius: var(--zs-radius-sm);
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
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}
</style>
