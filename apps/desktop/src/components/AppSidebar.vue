<script setup lang="ts">
import { useAppStore } from '../stores/app'
import type { ViewName } from '../types'

const store = useAppStore()
const items: Array<{ view: ViewName; icon: string; label: string }> = [
  { view: 'home', icon: '⌂', label: '首页' },
  { view: 'history', icon: '◷', label: '整理历史' },
  { view: 'quarantine', icon: '⬡', label: '隔离区' },
  { view: 'settings', icon: '☷', label: '设置' },
  { view: 'about', icon: 'ⓘ', label: '关于' },
]

function navigate(view: ViewName) {
  if (store.view === 'executing') return
  store.go(view)
  if (view === 'history' || view === 'quarantine') void store.refreshCollections()
}
</script>

<template>
  <aside class="sidebar" :class="{ locked: store.view === 'executing' }">
    <nav>
      <button
        v-for="item in items"
        :key="item.view"
        class="nav-item"
        :class="{ active: store.view === item.view }"
        @click="navigate(item.view)"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
        <span v-if="item.view === 'quarantine' && store.quarantine.length" class="nav-count">{{ store.quarantine.length }}</span>
      </button>
    </nav>
    <section class="guard-card">
      <h3><span class="ok-dot" />你的文件受到保护</h3>
      <button @click="navigate('history')"><span>可以撤销的整理</span><strong>{{ store.history.length }} 次</strong></button>
      <button @click="navigate('quarantine')"><span>隔离区里的文件</span><strong>{{ store.quarantine.length }} 个</strong></button>
      <div><span>永久删除</span><strong>从不</strong></div>
    </section>
  </aside>
</template>
