<script setup lang="ts">
export interface GraphContextMenuItem {
  key: string
  label: string
  danger?: boolean
  disabled?: boolean
}

defineProps<{
  visible: boolean
  x: number
  y: number
  items: GraphContextMenuItem[]
}>()

const emit = defineEmits<{
  select: [itemKey: string]
}>()

function selectItem(item: GraphContextMenuItem) {
  if (item.disabled) {
    return
  }
  emit('select', item.key)
}
</script>

<template>
  <div
    v-if="visible"
    class="context-menu"
    data-graph-context-menu="true"
    :style="{ left: `${x}px`, top: `${y}px` }"
    role="menu"
    @pointerdown.stop
    @mousedown.stop
    @click.stop
    @contextmenu.prevent.stop
  >
    <button
      v-for="item in items"
      :key="item.key"
      type="button"
      :class="{ danger: item.danger }"
      :disabled="item.disabled"
      @pointerdown.stop
      @mousedown.stop
      @click.stop="selectItem(item)"
    >
      {{ item.label }}
    </button>
  </div>
</template>

<style scoped>
.context-menu {
  position: fixed;
  z-index: 1000;
  display: grid;
  min-width: 168px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: 6px;
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-md);
  pointer-events: auto;
}

button {
  border: 0;
  border-radius: var(--zs-radius-sm);
  padding: 8px 10px;
  background: transparent;
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.86rem;
  text-align: left;
  cursor: pointer;
}

button:hover {
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-primary);
}

button.danger {
  color: var(--zs-color-danger);
}

button:disabled {
  color: var(--zs-color-text-faint);
  cursor: not-allowed;
}
</style>
