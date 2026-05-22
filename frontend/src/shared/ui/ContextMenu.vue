<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

export interface ContextMenuItem {
  id: string
  label: string
  danger?: boolean
  disabled?: boolean
}

const props = defineProps<{
  visible: boolean
  x: number
  y: number
  items: ContextMenuItem[]
}>()

const emit = defineEmits<{
  close: []
  select: [item: ContextMenuItem]
}>()

const menuRef = ref<HTMLElement | null>(null)

const menuStyle = computed(() => ({
  left: `${props.x}px`,
  top: `${props.y}px`,
}))

function handleDocumentPointerDown(event: PointerEvent) {
  const target = event.target as Node | null
  if (target && menuRef.value?.contains(target)) {
    return
  }
  emit('close')
}

function handleDocumentKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    emit('close')
  }
}

function handleSelect(item: ContextMenuItem) {
  if (item.disabled) {
    return
  }

  emit('select', item)
  emit('close')
}

watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      return
    }
    window.setTimeout(() => {
      menuRef.value?.focus()
    }, 0)
  },
)

onMounted(() => {
  document.addEventListener('pointerdown', handleDocumentPointerDown)
  document.addEventListener('keydown', handleDocumentKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
  document.removeEventListener('keydown', handleDocumentKeydown)
})
</script>

<template>
  <teleport to="body">
    <div
      v-if="visible"
      ref="menuRef"
      class="context-menu"
      role="menu"
      tabindex="-1"
      :style="menuStyle"
    >
      <button
        v-for="item in items"
        :key="item.id"
        type="button"
        :class="{ danger: item.danger }"
        :disabled="item.disabled"
        role="menuitem"
        @click="handleSelect(item)"
      >
        {{ item.label }}
      </button>
    </div>
  </teleport>
</template>

<style scoped>
.context-menu {
  position: fixed;
  z-index: 80;
  display: grid;
  min-width: 180px;
  gap: 4px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: 6px;
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-md);
}

button {
  border: 0;
  border-radius: var(--zs-radius-sm);
  padding: 9px 12px;
  background: transparent;
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.86rem;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
}

button:hover,
button:focus-visible {
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-primary);
  outline: none;
}

button.danger {
  color: var(--zs-color-danger);
}

button:disabled {
  color: var(--zs-color-text-faint);
  cursor: not-allowed;
}
</style>
