<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import { useAppStore } from '../stores/app'
import { fileName, formatBytes } from '../utils'
import PageHeader from '../components/PageHeader.vue'

const store = useAppStore()
const selected = ref(new Set<string>())
watchEffect(() => {
  selected.value = new Set(
    (store.undoPreview?.items ?? []).filter((item) => item.selected).map((item) => item.operationId),
  )
})
const items = computed(() => store.undoPreview?.items ?? [])
const restorable = computed(() => items.value.filter((item) => ['ready', 'rename'].includes(item.state)))
function toggle(id: string) {
  const next = new Set(selected.value)
  next.has(id) ? next.delete(id) : next.add(id)
  selected.value = next
}
</script>

<template>
  <div class="page scroll-page undo-page">
    <PageHeader title="撤销预览" description="只恢复下面选中的文件。已变化或找不到的文件会保持原样。" />
    <section class="summary-card compact">
      <div><strong>{{ restorable.length }}</strong><span>个可以恢复</span></div>
      <div><strong>{{ items.length - restorable.length }}</strong><span>个需要保留现状</span></div>
      <div><strong>{{ formatBytes(items.filter(item => selected.has(item.operationId)).reduce((n, item) => n + item.size, 0)) }}</strong><span>本次恢复</span></div>
    </section>
    <section class="panel undo-list">
      <button v-for="item in items" :key="item.operationId" :disabled="!['ready','rename'].includes(item.state)" @click="toggle(item.operationId)">
        <span class="check" :class="{ on: selected.has(item.operationId) }">{{ selected.has(item.operationId) ? '✓' : '' }}</span>
        <span><b>{{ fileName(item.currentPath) }}</b><small>{{ item.currentPath }} → {{ item.restorePath }}</small></span>
        <span class="op-badge" :class="item.state === 'ready' ? 'ok' : item.state === 'rename' ? 'warn' : 'fail'">
          {{ item.state === 'ready' ? '可恢复' : item.state === 'rename' ? '原位置有文件，将改名' : item.state === 'changed' ? '文件已变化' : '文件不存在' }}
        </span>
      </button>
    </section>
    <footer class="action-bar"><button class="button secondary" @click="store.go('history')">← 返回历史</button><span>恢复不会覆盖原位置已有文件。</span><button class="button undo" :disabled="!selected.size || store.busy" @click="store.executeUndo([...selected])">↶ 恢复 {{ selected.size }} 个文件</button></footer>
  </div>
</template>
