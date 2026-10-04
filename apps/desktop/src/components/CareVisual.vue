<script setup lang="ts">
import AppIcon from './AppIcon.vue'
withDefaults(defineProps<{ mode?: 'idle' | 'scanning' | 'working' | 'success'; progress?: number }>(), { mode: 'idle', progress: 0 })
</script>

<template>
  <div class="care-visual" :class="`care-${mode}`" aria-hidden="true">
    <div class="care-glow" />
    <div class="care-orbit" />
    <span class="floating-file file-one"><AppIcon name="file" :size="28" /></span>
    <span class="floating-file file-two"><AppIcon name="image" :size="26" /></span>
    <span class="floating-file file-three"><AppIcon name="archive" :size="24" /></span>
    <div class="care-core">
      <svg v-if="mode !== 'idle'" class="care-ring" viewBox="0 0 144 144">
        <circle class="ring-track" cx="72" cy="72" r="62" />
        <circle class="ring-progress" cx="72" cy="72" r="62" pathLength="100" :stroke-dasharray="mode === 'scanning' ? '24 76' : '100 100'" :stroke-dashoffset="mode === 'working' ? 100 - Math.max(0, Math.min(100, progress)) : 0" />
      </svg>
      <div class="care-symbol">
        <strong v-if="mode === 'working'">{{ Math.max(0, Math.min(100, progress)) }}<small>%</small></strong>
        <AppIcon v-else :name="mode === 'success' ? 'check' : mode === 'scanning' ? 'search' : 'folder'" :size="mode === 'success' ? 60 : 54" />
      </div>
    </div>
    <span class="care-spark spark-one">✦</span><span class="care-spark spark-two">✧</span>
  </div>
</template>
