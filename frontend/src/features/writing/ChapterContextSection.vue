<script setup lang="ts">
defineProps<{
  title: string
  count?: number
}>()
</script>

<template>
  <section class="context-section">
    <header class="section-head">
      <h3>{{ title }}</h3>
      <span v-if="typeof count === 'number'" class="count-pill">{{ count }}</span>
    </header>
    <slot />
  </section>
</template>

<style scoped>
.context-section {
  display: grid;
  gap: 10px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

h3 {
  margin: 0;
  color: #111827;
  font-size: 0.92rem;
}

.count-pill {
  min-width: 24px;
  border-radius: 999px;
  padding: 2px 8px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 0.74rem;
  font-weight: 800;
  text-align: center;
}
</style>
