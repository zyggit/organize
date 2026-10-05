<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAppStore } from '../stores/app'
import { fileName, formatBytes, formatDate } from '../utils'
import PageHeader from '../components/PageHeader.vue'
import AppIcon from '../components/AppIcon.vue'
import { pickDirectories } from '../api'

const store = useAppStore()
const selected = ref(new Set<string>())
const selectedSize = computed(() => store.quarantine.filter((item) => selected.value.has(item.quarantine_id)).reduce((sum, item) => sum + item.size, 0))
const expired = computed(() => store.quarantine.filter(item => Date.parse(item.retention_until) <= Date.now()).length)
function toggle(id: string) { const next = new Set(selected.value); next.has(id) ? next.delete(id) : next.add(id); selected.value = next }
async function restore(original = true) {
  const ids = [...selected.value]
  let destination: string | undefined
  if (!original) [destination] = await pickDirectories(false)
  if (!original && !destination) return
  if (await store.restoreQuarantine(ids, destination)) selected.value = new Set([...selected.value].filter(id => store.quarantine.some(item => item.quarantine_id === id)))
}
async function moveToTrash() {
  if (!window.confirm(`把选中的 ${selected.value.size} 个文件移入系统回收站？`)) return
  if (await store.trashQuarantine([...selected.value])) selected.value = new Set([...selected.value].filter(id => store.quarantine.some(item => item.quarantine_id === id)))
}
</script>

<template>
  <div class="page scroll-page quarantine-page">
    <PageHeader title="隔离区" description="这里的文件没有被删除。你可以放回原位置，或在确认不需要后移入系统回收站。" />
    <section class="quarantine-summary"><div><strong>{{ store.quarantine.length }}</strong><span>个文件</span></div><div><strong>{{ formatBytes(store.quarantine.reduce((n, item) => n + item.size, 0)) }}</strong><span>占用空间</span></div><div><strong>{{ expired }}</strong><span>已超过提醒时间</span></div><code>{{ store.settings.quarantineFolder }}（已有文件可能在旧位置）</code></section>
    <div v-if="!store.quarantine.length" class="empty-state"><span><AppIcon name="shield" :size="48" /></span><h2>隔离区是空的</h2><p>旧安装包清理和重复文件查找会把文件放在这里，你随时可以恢复。</p></div>
    <section v-else class="panel quarantine-table">
      <div class="q-head"><span>选择</span><span>文件</span><span>原位置</span><span>为什么在这里</span><span>隔离时间</span><span>大小</span></div>
      <button v-for="item in store.quarantine" :key="item.quarantine_id" @click="toggle(item.quarantine_id)"><span class="check" :class="{ on: selected.has(item.quarantine_id) }">{{ selected.has(item.quarantine_id) ? '✓' : '' }}</span><span><b>{{ fileName(item.original_path) }}</b><small>{{ item.quarantine_path }}</small></span><code>{{ item.original_path }}</code><span>{{ item.reason }}</span><span>{{ formatDate(item.quarantined_at) }}</span><strong>{{ formatBytes(item.size) }}</strong></button>
    </section>
    <footer v-if="selected.size" class="action-bar"><span>已选 {{ selected.size }} 个文件，{{ formatBytes(selectedSize) }}</span><button class="button danger" :disabled="store.busy" @click="moveToTrash">移入系统回收站</button><button class="button secondary" :disabled="store.busy" @click="restore(false)">恢复到其他位置</button><button class="button primary" :disabled="store.busy" @click="restore(true)">恢复到原位置</button></footer>
  </div>
</template>
