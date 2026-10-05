<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { localFileUrl } from '../api'
import { useAppStore } from '../stores/app'
import { fileName, formatBytes } from '../utils'
import type { KeepRule, PlanItem } from '../types'

const store = useAppStore()
const confirm = ref(false)
const thumbs = ref<Record<string, string>>({})
const photos = computed(() => store.profile.presetType === 'similar-photos')
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
const warnings = computed(() => store.plan?.summary.warnings ?? [])
const rules: Array<{ id: KeepRule; label: string }> = [
  { id: 'resolution', label: '保留分辨率最高' },
  { id: 'largest', label: '保留文件最大' },
  { id: 'newest', label: '保留最新修改' },
  { id: 'shortest', label: '保留路径最短' },
]
const ruleNames: Record<KeepRule, string> = {
  resolution: '分辨率最高',
  largest: '文件最大',
  newest: '最新修改',
  shortest: '路径最短',
}

function pixels(item: PlanItem) {
  return Number(item.metadata.width ?? 0) * Number(item.metadata.height ?? 0)
}
function better(candidate: PlanItem, current: PlanItem, rule: KeepRule) {
  const rank = (item: PlanItem) => {
    const area = pixels(item)
    const modified = Number(item.metadata.modifiedMs ?? 0)
    if (rule === 'largest') return [item.size, area, modified, -item.sourcePath.length]
    if (rule === 'newest') return [modified, area, item.size, -item.sourcePath.length]
    if (rule === 'shortest') return [-item.sourcePath.length, area, item.size, modified]
    return [area, item.size, modified, -item.sourcePath.length]
  }
  const left = rank(candidate)
  const right = rank(current)
  for (let index = 0; index < left.length; index += 1) {
    if (left[index] !== right[index]) return left[index] > right[index]
  }
  return candidate.sourcePath < current.sourcePath
}
function applyRule(rule: KeepRule) {
  for (const [groupId, items] of groups.value) {
    const keep = items.reduce((chosen, item) => better(item, chosen, rule) ? item : chosen)
    store.selectDuplicateKeep(groupId, keep.itemId)
  }
}
function applyRecommended() {
  for (const [groupId, items] of groups.value) {
    const keep = items.find((item) => item.metadata.recommendedKeep)
    if (keep) store.selectDuplicateKeep(groupId, keep.itemId)
  }
}
function kindLabel(items: PlanItem[]) {
  return items.some((item) => item.metadata.kind === 'similar') ? '看起来相似' : '内容完全相同'
}
watch(() => store.plan?.planId, async () => {
  const next: Record<string, string> = {}
  for (const item of store.plan?.items ?? []) {
    const path = String(item.metadata.previewPath || item.sourcePath || '')
    if (path) next[item.itemId] = await localFileUrl(path)
  }
  thumbs.value = next
}, { immediate: true })
</script>

<template>
  <div class="page scroll-page duplicate-page">
    <header class="page-header">
      <div>
        <h1>{{ photos ? '选择每组要保留的照片' : '选择每组要保留的文件' }}</h1>
        <p>{{ photos ? '相似照片默认不会标记删除。先为每组选一张保留，或用规则一次标好，再逐张调整。' : '内容完全相同才会出现在这里。没有选择前不会处理。' }}</p>
      </div>
      <div class="rule-actions" v-if="photos">
        <button v-for="rule in rules" :key="rule.id" class="button secondary" @click="applyRule(rule.id)">{{ rule.label }}</button>
      </div>
      <button v-else class="button secondary" @click="applyRecommended">全部采用推荐</button>
    </header>
    <p v-if="warnings.length" class="banner undo inset scan-warning">{{ warnings.includes('HEIC_DECODE_UNAVAILABLE') ? '这台电脑不能解码 HEIC，相似比较会跳过这些照片；字节完全相同的 HEIC 仍会列出来。' : warnings[0] }}</p>
    <section class="summary-card compact">
      <div><strong>{{ groups.length }}</strong><span>{{ photos ? '组照片' : '组重复文件' }}</span></div>
      <div class="dup-stats"><span>已决定 <b>{{ decided }} / {{ groups.length }}</b></span><span>将进入隔离区 <b>{{ store.selectedItems.length }}</b></span></div>
    </section>
    <section v-if="!groups.length" class="empty-state">
      <h2>{{ photos ? '没有找到重复或相似的照片' : '没有找到重复文件' }}</h2>
      <p>没有文件被移动。可以返回修改文件夹或扫描条件。</p>
    </section>
    <section v-for="([groupId, items], index) in groups" :key="groupId" class="panel duplicate-group" :class="{ undecided: !items.some((item) => item.metadata.decision === 'keep') }">
      <div class="panel-title">
        <span>第 {{ index + 1 }} 组 · {{ items.length }} 个{{ kindLabel(items) }}的文件</span>
        <span class="op-badge" :class="items.some((item) => item.metadata.decision === 'keep') ? 'ok' : 'warn'">{{ items.some((item) => item.metadata.decision === 'keep') ? '已决定' : '请选择保留哪一份' }}</span>
      </div>
      <div v-if="photos" class="photo-grid">
        <button v-for="item in items" :key="item.itemId" class="photo-card" :class="{ keep: item.metadata.decision === 'keep' }" @click="store.selectDuplicateKeep(groupId, item.itemId)">
          <img v-if="thumbs[item.itemId]" :src="thumbs[item.itemId]" :alt="fileName(item.sourcePath)" />
          <span v-else class="photo-fallback">{{ fileName(item.sourcePath) }}</span>
          <span class="photo-meta">
            <b>{{ fileName(item.sourcePath) }}</b>
            <small>{{ item.sourcePath }}</small>
            <small>{{ item.metadata.width && item.metadata.height ? `${item.metadata.width}×${item.metadata.height} · ` : '' }}{{ formatBytes(item.size) }}{{ item.metadata.kind === 'similar' ? ` · 距离 ${item.metadata.difference ?? 0}` : '' }}</small>
          </span>
          <strong>{{ item.metadata.decision === 'keep' ? '保留' : item.metadata.decision === 'quarantine' ? '进入隔离区' : '待选择' }}</strong>
          <em v-if="item.metadata.recommendedKeep">推荐：{{ ruleNames[(item.metadata.recommendedRule as KeepRule) || 'resolution'] }}</em>
        </button>
      </div>
      <button v-else v-for="item in items" :key="item.itemId" class="duplicate-row" @click="store.selectDuplicateKeep(groupId, item.itemId)">
        <span class="radio" :class="{ on: item.metadata.decision === 'keep' }" /><span><b>{{ fileName(item.sourcePath) }}</b><small>{{ item.sourcePath }}</small></span><span v-if="item.metadata.recommendedKeep" class="op-badge undo">推荐保留：最早的一份</span><strong>{{ item.metadata.decision === 'keep' ? '保留' : item.metadata.decision === 'quarantine' ? '进入隔离区' : '待选择' }}</strong>
      </button>
    </section>
    <footer class="action-bar">
      <button class="button secondary" @click="store.go('config')">← 返回修改方案</button>
      <span>{{ !groups.length ? '没有需要隔离的文件。' : decided < groups.length ? `还有 ${groups.length - decided} 组没有选择保留项。` : `将隔离 ${store.selectedItems.length} 个文件。` }}</span>
      <button class="button primary" :disabled="!groups.length || decided < groups.length" @click="confirm = true">隔离 {{ store.selectedItems.length }} 个文件</button>
    </footer>
    <div v-if="confirm" class="modal-backdrop" @click.self="confirm = false">
      <section class="dialog">
        <h2>隔离 {{ store.selectedItems.length }} 个文件？</h2>
        <p>保留项不会改动。其余文件进入隔离区，可以恢复。不会永久删除，也不会送进系统废纸篓。</p>
        <div><button class="button secondary" @click="confirm = false">再看看</button><button class="button primary" @click="confirm = false; store.executePlan()">开始整理</button></div>
      </section>
    </div>
  </div>
</template>
