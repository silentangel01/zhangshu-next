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
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 6px;
  background: #ffffff;
  box-shadow: 0 18px 36px rgb(15 23 42 / 18%);
  pointer-events: auto;
}

button {
  border: 0;
  border-radius: 6px;
  padding: 8px 10px;
  background: transparent;
  color: #111827;
  font: inherit;
  font-size: 0.86rem;
  text-align: left;
  cursor: pointer;
}

button:hover {
  background: #eff6ff;
  color: #1d4ed8;
}

button.danger {
  color: #b42318;
}

button:disabled {
  color: #94a3b8;
  cursor: not-allowed;
}
</style>
