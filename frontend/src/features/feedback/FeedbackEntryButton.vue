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
    <span class="feedback-mark" aria-hidden="true"></span>
    <span class="feedback-label">意见反馈</span>
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
  gap: 8px;
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid var(--zs-color-border, #ddd);
  border-radius: var(--zs-radius-sm, 4px);
  background: var(--zs-color-surface, #fff);
  cursor: pointer;
  font-size: 0.8125rem;
  color: var(--zs-color-text-muted);
  transition:
    border-color var(--zs-duration-fast) var(--zs-ease-standard),
    color var(--zs-duration-fast) var(--zs-ease-standard);
}

.feedback-entry-btn:hover {
  border-color: var(--zs-color-border-strong);
  color: var(--zs-color-text);
}

.feedback-mark {
  width: 8px;
  height: 8px;
  border: 1px solid currentColor;
  transform: rotate(45deg);
}

@media (max-width: 720px) {
  .feedback-entry-btn {
    bottom: calc(var(--zs-space-4) + 48px);
    right: var(--zs-space-4);
  }
}
</style>
