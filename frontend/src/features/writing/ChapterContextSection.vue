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
  color: var(--zs-color-text-muted);
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.count-pill {
  min-width: 24px;
  border-radius: 999px;
  padding: 2px 8px;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
  font-size: 0.74rem;
  font-weight: 800;
  text-align: center;
}
</style>
