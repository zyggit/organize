<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '../stores/app'
import { formatBytes } from '../utils'
import CareVisual from '../components/CareVisual.vue'

const store = useAppStore()
const title = computed(() => {
  if (!store.result) return '整理结束'
  if (store.result.status === 'completed') return `整理完成，${store.result.success} 个文件已处理`
  if (store.result.status === 'cancelled') return `已停止整理，${store.result.success} 个文件已完成`
  return `整理完成，${store.result.failed} 个文件没有成功`
})
</script>

<template>
  <div v-if="store.result" class="page result-page">
    <section class="result-hero"><CareVisual v-if="store.result.status === 'completed'" mode="success" /><span v-else :class="store.result.status">!</span><div><span class="eyebrow">{{ store.result.status === 'completed' ? 'A LITTLE MORE ORDER' : 'YOUR FILES, YOUR CONTROL' }}</span><h1>{{ title }}</h1><p>没有成功的文件会留在原位置，不会产生额外改动。</p></div></section>
    <div class="result-stats"><div><strong>{{ store.result.success }}</strong><span>已完成</span></div><div><strong>{{ store.result.skipped }}</strong><span>跳过</span></div><div><strong>{{ store.result.failed }}</strong><span>失败</span></div><div><strong>{{ formatBytes(store.result.successBytes ?? 0) }}</strong><span>已处理大小</span></div></div>
    <div class="result-grid"><section class="panel"><div class="panel-title">处理结果</div><div class="empty-success">✓ 每个成功操作都已写入整理历史。</div></section><section class="panel undo-card"><div class="panel-title">↶ 这次整理可以撤销</div><div class="panel-body"><p>撤销前会先显示预览，你可以只恢复部分文件。</p></div><button class="button undo" @click="store.prepareUndo(store.result.runId)">撤销本次整理</button></section></div>
    <footer class="action-bar"><button class="button secondary" @click="store.go('home')">返回首页</button><button class="button ghost" @click="store.go('config')">再运行一次</button><span /><button class="button primary" @click="store.go('history')">查看整理记录</button></footer>
  </div>
</template>
