<script setup lang="ts">
const model = defineModel<boolean>({ required: true })
defineProps<{ label: string }>()
</script>

<template>
  <button type="button" role="switch" class="switch-toggle" :class="{ on: model }" :aria-checked="model" :aria-label="label" @click.stop="model = !model"><i /></button>
</template>
