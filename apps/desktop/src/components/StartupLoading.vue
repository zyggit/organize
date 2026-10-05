<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{ state: 'loading' | 'ready' | 'error'; error?: string }>()
defineEmits<{ retry: [] }>()
const failed = computed(() => props.state === 'error')
const slow = ref(false)
let slowTimer: ReturnType<typeof setTimeout> | undefined
watch(() => props.state, (state) => {
  clearTimeout(slowTimer)
  slow.value = false
  if (state === 'loading') slowTimer = setTimeout(() => { slow.value = true }, 8000)
}, { immediate: true })
onBeforeUnmount(() => clearTimeout(slowTimer))
</script>

<template>
  <section class="startup-screen" :class="{ 'startup-screen--failed': failed }" :role="failed ? 'alert' : 'status'" :aria-busy="!failed" aria-live="polite" aria-atomic="true">
    <div class="startup-mark" aria-hidden="true">
      <span class="startup-halo" />
      <svg class="startup-o" viewBox="0 0 112 112" fill="none"><ellipse cx="56" cy="56" rx="29" ry="37" stroke="currentColor" stroke-width="9" /></svg>
    </div>
    <h1 class="startup-title">{{ failed ? '暂时无法启动智能整理' : '正在准备智能整理' }}</h1>
    <p v-if="failed" class="startup-detail startup-error">{{ error || '整理引擎未能启动，请重试。' }}</p>
    <p v-else class="startup-detail">{{ slow ? '首次启动可能需要一点时间，请稍候…' : '正在启动本地引擎，请稍候…' }}</p>
    <button v-if="failed" class="startup-retry" @click="$emit('retry')">重新加载</button>
  </section>
</template>
