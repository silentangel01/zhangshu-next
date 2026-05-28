<script setup lang="ts">
import { useToast } from '@/shared/composables/useToast'

const { toasts, remove } = useToast()

const iconMap: Record<string, string> = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ',
}
</script>

<template>
  <div class="toast-container">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="['toast', `toast-${toast.type}`]"
        @click="remove(toast.id)"
      >
        <span class="toast-icon">{{ iconMap[toast.type] }}</span>
        <span class="toast-msg">{{ toast.message }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: var(--ca-radius);
  background: var(--ca-surface);
  border: 1px solid var(--ca-border);
  border-left: 4px solid var(--ca-border);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  cursor: pointer;
  pointer-events: auto;
  max-width: 380px;
  font-size: 13px;
  line-height: 1.4;
}

.toast-success {
  border-left-color: var(--ca-success);
}
.toast-error {
  border-left-color: var(--ca-danger);
}
.toast-warning {
  border-left-color: var(--ca-warning);
}
.toast-info {
  border-left-color: var(--ca-primary);
}

.toast-icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
}
.toast-success .toast-icon {
  background: #d1fae5;
  color: #065f46;
}
.toast-error .toast-icon {
  background: #fee2e2;
  color: #991b1b;
}
.toast-warning .toast-icon {
  background: #fef3c7;
  color: #92400e;
}
.toast-info .toast-icon {
  background: #dbeafe;
  color: #1d4ed8;
}

.toast-msg {
  color: var(--ca-text);
}

.toast-enter-active {
  transition: all 0.3s ease;
}
.toast-leave-active {
  transition: all 0.2s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(60px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(60px);
}
.toast-move {
  transition: transform 0.2s ease;
}
</style>
