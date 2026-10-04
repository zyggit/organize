<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAppStore } from '../stores/app'
import { fileName } from '../utils'
import CareVisual from '../components/CareVisual.vue'

const store = useAppStore()
const stopping = ref(false)
const total = computed(() => store.selectedItems.length)
const percent = computed(() => total.value ? Math.min(100, Math.round(store.runCompleted / total.value * 100)) : 0)
async function stop() { stopping.value = true; await store.cancelRun() }
</script>

<template>
  <div class="page execution-page" aria-busy="true">
    <section class="execution-card">
      <CareVisual mode="working" :progress="percent" />
      <header><h1>{{ stopping ? '正在安全停止' : '文件正在各归其位' }}</h1></header>
      <div class="progress" role="progressbar" aria-label="整理进度" :aria-valuenow="percent" aria-valuemin="0" aria-valuemax="100"><i :class="{ stopping }" :style="{ width: `${percent}%` }" /></div>
      <div class="progress-meta"><span>{{ store.runCompleted }} / {{ total }} 个文件</span><span>{{ stopping ? '将在当前文件完成后停止' : '请保持应用运行' }}</span></div>
      <div class="current-file"><small>{{ stopping ? '正在完成当前文件' : '当前文件' }}</small><b>{{ fileName(store.runCurrent) || '准备中…' }}</b><code>{{ store.runCurrent }}</code></div>
      <div v-if="stopping" class="banner warn">正在完成当前文件，完成后停止。中途停止可能留下不完整文件，所以会先安全完成它。</div>
      <div class="stat-grid"><div><strong>{{ store.runCompleted }}</strong><span>已完成</span></div><div><strong>0</strong><span>已跳过</span></div><div><strong>0</strong><span>失败</span></div></div>
      <p>不会覆盖任何已有文件。每一步都记录在整理历史里。</p>
    </section>
    <footer class="action-bar"><span /><span>已完成的文件可以在整理历史中撤销。</span><button class="button danger" :disabled="stopping" @click="stop">{{ stopping ? '正在停止…' : '停止整理' }}</button></footer>
  </div>
</template>
