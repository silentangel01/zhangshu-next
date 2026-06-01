<script setup lang="ts">
import { ref } from 'vue'

import FeedbackDialog from './FeedbackDialog.vue'

const showDialog = ref(false)

function openDialog() {
  showDialog.value = true
}

function closeDialog() {
  showDialog.value = false
}
</script>

<template>
  <button class="feedback-entry-btn" type="button" title="提交反馈" @click="openDialog">
    <span class="feedback-icon">💬</span>
    <span class="feedback-label">反馈</span>
  </button>

  <FeedbackDialog v-if="showDialog" @close="closeDialog" />
</template>

<style scoped>
.feedback-entry-btn {
  position: fixed;
  bottom: var(--zs-space-4, 16px);
  right: calc(var(--zs-space-4, 16px) + 48px);
  z-index: 89;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: 1px solid var(--zs-color-border, #ddd);
  border-radius: var(--zs-radius-md, 6px);
  background: var(--zs-color-surface, #fff);
  box-shadow: var(--zs-shadow-sm, 0 1px 3px rgba(0, 0, 0, 0.1));
  cursor: pointer;
  font-size: 0.8125rem;
  color: inherit;
  transition: box-shadow 0.2s;
}

.feedback-entry-btn:hover {
  box-shadow: var(--zs-shadow-md, 0 4px 12px rgba(0, 0, 0, 0.1));
}

.feedback-icon {
  font-size: 1rem;
}

@media (max-width: 720px) {
  .feedback-entry-btn {
    bottom: calc(var(--zs-space-4) + 48px);
    right: var(--zs-space-4);
  }
}
</style>
