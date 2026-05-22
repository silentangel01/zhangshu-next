<script setup lang="ts">
import { RouterLink } from 'vue-router'

import type { ImportReport } from '@/entities/import/types'

defineProps<{
  report: ImportReport
}>()
</script>

<template>
  <section class="report-panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">导入完成</p>
        <h2>导入报告</h2>
      </div>
      <RouterLink class="open-link" :to="`/projects/${report.created_project_id}`">
        打开导入的项目
      </RouterLink>
    </header>

    <dl class="stats-grid">
      <div>
        <dt>创建分卷</dt>
        <dd>{{ report.created_volume_count }}</dd>
      </div>
      <div>
        <dt>创建章节</dt>
        <dd>{{ report.created_chapter_count }}</dd>
      </div>
      <div>
        <dt>总字数</dt>
        <dd>{{ report.total_word_count }}</dd>
      </div>
      <div>
        <dt>报告路径</dt>
        <dd>{{ report.report_path }}</dd>
      </div>
    </dl>

    <section v-if="report.warnings.length" class="text-block">
      <h3>警告</h3>
      <ul>
        <li v-for="warning in report.warnings" :key="warning">{{ warning }}</li>
      </ul>
    </section>

    <section v-if="report.failed_files.length" class="text-block error">
      <h3>失败文件</h3>
      <ul>
        <li v-for="file in report.failed_files" :key="file">{{ file }}</li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.report-panel {
  display: grid;
  gap: var(--zs-space-4);
  border: 1px solid var(--zs-color-success);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-5);
  background: var(--zs-color-success-soft);
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

.open-link {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  border-radius: var(--zs-radius-sm);
  padding: 0 14px;
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
  font-weight: 800;
  text-decoration: none;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--zs-space-3);
  margin: 0;
}

.stats-grid div {
  border: 1px solid var(--zs-color-success);
  border-radius: var(--zs-radius-md);
  padding: 12px;
  background: var(--zs-color-surface);
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
  overflow-wrap: anywhere;
}

.text-block {
  display: grid;
  gap: 8px;
}

.text-block ul {
  margin: 0;
  color: var(--zs-color-text-muted);
}

.error h3 {
  color: var(--zs-color-danger);
}
</style>
