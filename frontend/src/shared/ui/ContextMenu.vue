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
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 6px;
  background: #ffffff;
  box-shadow: 0 18px 44px rgb(20 24 31 / 16%);
}

button {
  border: 0;
  border-radius: 6px;
  padding: 9px 12px;
  background: transparent;
  color: #111827;
  font: inherit;
  font-size: 0.86rem;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
}

button:hover,
button:focus-visible {
  background: #eff6ff;
  outline: none;
}

button.danger {
  color: #b42318;
}

button:disabled {
  color: #94a3b8;
  cursor: not-allowed;
}
</style>
