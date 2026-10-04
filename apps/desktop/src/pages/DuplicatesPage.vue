<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAppStore } from '../stores/app'
import { fileName, formatBytes } from '../utils'
import type { PlanItem } from '../types'

const store = useAppStore()
const confirm = ref(false)
const groups = computed(() => {
  const result = new Map<string, PlanItem[]>()
  for (const item of store.plan?.items ?? []) {
    const key = item.groupId ?? 'unknown'
    if (!result.has(key)) result.set(key, [])
    result.get(key)!.push(item)
  }
  return [...result.entries()]
})
const decided = computed(() => groups.value.filter(([, items]) => items.some((item) => item.metadata.decision === 'keep')).length)

function applyRecommended() {
  for (const [groupId, items] of groups.value) {
    const keep = items.find((item) => item.metadata.recommendedKeep)
    if (keep) store.selectDuplicateKeep(groupId, keep.itemId)
  }
}
</script>

<template>
  <div class="page scroll-page duplicate-page">
    <header class="page-header"><div><h1>选择每组要保留的文件</h1><p>内容完全相同才会出现在这里。没有选择前不会处理。</p></div><button class="button secondary" @click="applyRecommended">全部采用推荐</button></header>
    <section class="summary-card compact"><div><strong>{{ groups.length }}</strong><span>组重复文件</span></div><div class="dup-stats"><span>已决定 <b>{{ decided }} / {{ groups.length }}</b></span><span>将进入隔离区 <b>{{ store.selectedItems.length }}</b></span></div></section>
    <section v-for="([groupId, items], index) in groups" :key="groupId" class="panel duplicate-group" :class="{ undecided: !items.some((item) => item.metadata.decision === 'keep') }">
      <div class="panel-title"><span>第 {{ index + 1 }} 组 · {{ items.length }} 个内容完全相同的文件，每个 {{ formatBytes(items[0]?.size ?? 0) }}</span><span class="op-badge" :class="items.some((item) => item.metadata.decision === 'keep') ? 'ok' : 'warn'">{{ items.some((item) => item.metadata.decision === 'keep') ? '已决定' : '请选择保留哪一份' }}</span></div>
      <button v-for="item in items" :key="item.itemId" class="duplicate-row" @click="store.selectDuplicateKeep(groupId, item.itemId)">
        <span class="radio" :class="{ on: item.metadata.decision === 'keep' }" /><span><b>{{ fileName(item.sourcePath) }}</b><small>{{ item.sourcePath }}</small></span><span v-if="item.metadata.recommendedKeep" class="op-badge undo">推荐保留：最早的一份</span><strong>{{ item.metadata.decision === 'keep' ? '保留' : item.metadata.decision === 'quarantine' ? '进入隔离区' : '待选择' }}</strong>
      </button>
    </section>
    <footer class="action-bar"><button class="button secondary" @click="store.go('config')">← 返回修改方案</button><span>{{ decided < groups.length ? `还有 ${groups.length - decided} 组没有选择保留项。` : `将隔离 ${store.selectedItems.length} 个重复文件。` }}</span><button class="button primary" :disabled="decided < groups.length" @click="confirm = true">隔离 {{ store.selectedItems.length }} 个重复文件</button></footer>
    <div v-if="confirm" class="modal-backdrop" @click.self="confirm = false"><section class="dialog"><h2>隔离 {{ store.selectedItems.length }} 个重复文件？</h2><p>保留项不会改动，其余文件会进入隔离区，并且可以恢复。</p><div><button class="button secondary" @click="confirm = false">再看看</button><button class="button primary" @click="confirm = false; store.executePlan()">开始整理</button></div></section></div>
  </div>
</template>
