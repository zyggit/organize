<script setup lang="ts">
import { useAppStore } from '../stores/app'
import AppIcon from '../components/AppIcon.vue'
import CareVisual from '../components/CareVisual.vue'
import type { PresetType } from '../types'
import { formatDate } from '../utils'

const store = useAppStore()
const today = new Date()
const presentation: Record<PresetType, { icon: string; title: string; safety: string; tone: string; flow: string[] }> = {
  'by-type': { icon: 'folder', title: '杂乱文件，有序归类', safety: '只移动，不删除', tone: 'mint', flow: ['下载文件夹', '按类型归类'] },
  'by-date': { icon: 'image', title: '让每张照片找到位置', safety: '按修改日期归档', tone: 'blue', flow: ['照片与截图', `${today.getFullYear()}年 / ${today.getMonth() + 1}月`] },
  'old-installers': { icon: 'archive', title: '给旧安装包腾个地方', safety: '移入隔离区，可恢复', tone: 'peach', flow: ['超过 90 天', '安全隔离'] },
  duplicates: { icon: 'duplicate', title: '相同的文件，只留一份', safety: '由你选择保留项', tone: 'pink', flow: ['比对文件内容', '逐组选择'] },
}
</script>

<template>
  <div class="page scroll-page home-page">
    <header class="home-heading"><div><span class="eyebrow">YOUR SPACE, ORGANIZED</span><h1>智能整理</h1></div><span class="local-pill"><AppIcon name="lock" :size="14" />文件处理全程在本机</span></header>
    <section class="home-hero">
      <div class="hero-copy"><span class="hero-kicker"><AppIcon name="sparkle" :size="16" />少一点杂乱，多一点轻松</span><h2>让文件各归其位。</h2><p>从一个文件夹开始。先看清每个文件的去向，<br>再把整理这件事，放心交给 organize。</p><button class="button primary hero-action" :disabled="!store.engineReady" @click="store.choosePreset('by-type')">开始整理<AppIcon name="arrow" :size="18" /></button><small>选择文件夹后扫描 · 确认前不会改动文件</small></div>
      <CareVisual />
    </section>
    <div class="home-section-heading"><h2>为你的文件，选择一种整理方式</h2><span>4 个工具，都以安全为先</span></div>
    <div class="home-grid">
      <div>
        <div class="preset-grid">
          <button
            v-for="preset in store.presets"
            :key="preset.id"
            class="preset-card"
            :class="presentation[preset.id].tone"
            :disabled="!store.engineReady"
            @click="store.choosePreset(preset.id)"
          >
            <div class="preset-top">
              <span class="preset-icon"><AppIcon :name="presentation[preset.id].icon" :size="30" /></span>
              <div><small>{{ preset.name }}</small><h2>{{ presentation[preset.id].title }}</h2><p>{{ preset.description }}</p></div>
            </div>
            <div class="flow-preview">
              <template v-for="(segment, index) in presentation[preset.id].flow" :key="`${segment}-${index}`">
                <span>{{ segment }}</span><i v-if="index < presentation[preset.id].flow.length - 1">→</i>
              </template>
            </div>
            <div class="preset-footer"><span class="safety-chip"><AppIcon name="check" :size="13" />{{ presentation[preset.id].safety }}</span><span class="preset-open"><AppIcon name="arrow" :size="18" /></span></div>
          </button>
        </div>
        <h3 v-if="store.history.length" class="section-title">最近任务</h3>
        <section v-if="store.history.length" class="panel recent-list">
          <button v-for="run in store.history.slice(0, 3)" :key="run.run_id" @click="store.go('history')">
            <span class="status-dot" :class="run.status" />
            <span><b>{{ run.profile.name }}</b><small>{{ formatDate(run.started_at) }}，{{ run.success }} 个已完成</small></span>
            <span class="op-badge" :class="run.status === 'completed' ? 'ok' : 'warn'">{{ run.status === 'completed' ? '完成' : '部分成功' }}</span>
          </button>
        </section>
      </div>
      <aside class="home-aside">
        <section v-if="store.history[0]" class="panel last-run">
          <div class="panel-title">↶ 上次整理 <small>{{ formatDate(store.history[0].started_at) }}</small></div>
          <div class="panel-body"><p>{{ store.history[0].profile.name }}</p><strong>{{ store.history[0].success }}</strong> 个文件已处理</div>
          <button class="button undo" @click="store.prepareUndo(store.history[0].run_id)">↶ 撤销上次整理</button>
        </section>
        <section class="panel continue-card">
          <div class="panel-title">继续上次方案</div>
          <div class="panel-body"><p>{{ store.profile.name }}</p><small>{{ store.profile.sourceFolders[0] }} → {{ store.profile.targetFolder }}</small></div>
          <button class="button secondary" @click="store.go('config')">用这个方案重新扫描</button>
        </section>
      </aside>
    </div>
    <div class="home-trust"><span><AppIcon name="shield" :size="15" />不覆盖已有文件</span><span><AppIcon name="history" :size="15" />保留操作历史</span><span><AppIcon name="lock" :size="15" />无需上传文件</span></div>
  </div>
</template>
