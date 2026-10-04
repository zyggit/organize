<script setup lang="ts">
import { useAppStore } from '../stores/app'
import type { ViewName } from '../types'
import AppIcon from './AppIcon.vue'
import appIcon from '../assets/app-icon.png'
import type { PresetType } from '../types'
import { computed } from 'vue'

const store = useAppStore()
const items: Array<{ view: ViewName; icon: string; label: string }> = [
  { view: 'history', icon: 'history', label: '整理历史' },
  { view: 'quarantine', icon: 'shield', label: '隔离区' },
]
const modules: Array<{ id: PresetType; icon: string; label: string; tone: string }> = [
  { id: 'by-type', icon: 'folder', label: '分类整理', tone: 'mint' },
  { id: 'by-date', icon: 'image', label: '照片归档', tone: 'blue' },
  { id: 'old-installers', icon: 'archive', label: '旧安装包', tone: 'peach' },
  { id: 'duplicates', icon: 'duplicate', label: '重复文件', tone: 'pink' },
]
const locked = computed(() => store.view === 'executing' || store.view === 'scan')
const inFlow = computed(() => ['config', 'scan', 'preview', 'duplicates', 'executing', 'result'].includes(store.view))

function navigate(view: ViewName) {
  if (locked.value) return
  store.go(view)
  if (view === 'history' || view === 'quarantine') void store.refreshCollections()
}
</script>

<template>
  <aside class="sidebar" :class="{ locked }">
    <div class="sidebar-brand"><span class="brand-icon"><img :src="appIcon" alt="" /></span><div><strong>organize</strong><small>让文件各归其位</small></div></div>
    <nav>
      <button class="nav-item smart-nav" :class="{ active: store.view === 'home' }" :disabled="locked" @click="navigate('home')"><span class="nav-icon mint"><AppIcon name="sparkle" /></span><span>智能整理</span></button>
      <div class="nav-section-label">整理工具</div>
      <button v-for="module in modules" :key="module.id" class="nav-item" :class="{ active: inFlow && store.profile.presetType === module.id }" :disabled="locked" @click="store.choosePreset(module.id)"><span class="nav-icon" :class="module.tone"><AppIcon :name="module.icon" /></span><span>{{ module.label }}</span></button>
      <div class="nav-section-label">资料库</div>
      <button
        v-for="item in items"
        :key="item.view"
        class="nav-item"
        :class="{ active: store.view === item.view }"
        :disabled="locked"
        @click="navigate(item.view)"
      >
        <span class="nav-icon muted"><AppIcon :name="item.icon" /></span>
        <span>{{ item.label }}</span>
        <span v-if="item.view === 'quarantine' && store.quarantine.length" class="nav-count">{{ store.quarantine.length }}</span>
      </button>
    </nav>
    <section class="guard-card">
      <h3><AppIcon name="shield" :size="16" />安心整理</h3>
      <p>先预览，再整理。每一步都有迹可循。</p>
      <button :disabled="locked" @click="navigate('history')"><span>整理记录</span><strong>{{ store.history.length }} 次</strong></button>
      <button :disabled="locked" @click="navigate('quarantine')"><span>隔离文件</span><strong>{{ store.quarantine.length }} 个</strong></button>
      <div><span>永久删除</span><strong>从不</strong></div>
    </section>
    <div class="sidebar-bottom"><button :disabled="locked" aria-label="设置" @click="navigate('settings')"><AppIcon name="settings" :size="18" />设置</button><button :disabled="locked" aria-label="关于" @click="navigate('about')"><AppIcon name="info" :size="18" /></button></div>
  </aside>
</template>
