<script setup lang="ts">
import { useAppStore } from '../stores/app'
import PageHeader from '../components/PageHeader.vue'
import type { PresetType } from '../types'
import { formatDate } from '../utils'

const store = useAppStore()
const presentation: Record<PresetType, { icon: string; safety: string; tone: string; flow: string[] }> = {
  'by-type': { icon: '↓', safety: '只移动，不删除', tone: 'move', flow: ['下载', '文档', '图片', '视频', '+4'] },
  'by-date': { icon: '▣', safety: '只移动，不删除', tone: 'move', flow: ['图片', '2026年', '10月'] },
  'old-installers': { icon: '◇', safety: '进入隔离区，可恢复', tone: 'quarantine', flow: ['超过 90 天的安装包', '隔离区'] },
  duplicates: { icon: '▦', safety: '由你选择保留哪一份', tone: 'undo', flow: ['下载', '桌面', '重复组', '隔离区'] },
}
</script>

<template>
  <div class="page scroll-page">
    <PageHeader title="今天想整理哪里？" description="选一个方案。应用会先扫描并给出预览，你确认后才会移动文件。" />
    <div class="home-grid">
      <div>
        <div class="preset-grid">
          <button
            v-for="preset in store.presets"
            :key="preset.id"
            class="preset-card"
            :class="presentation[preset.id].tone"
            @click="store.choosePreset(preset.id)"
          >
            <div class="preset-top">
              <span class="preset-icon">{{ presentation[preset.id].icon }}</span>
              <div><h2>{{ preset.name }}</h2><p>{{ preset.description }}</p></div>
            </div>
            <div class="flow-preview">
              <template v-for="(segment, index) in presentation[preset.id].flow" :key="`${segment}-${index}`">
                <span>{{ segment }}</span><i v-if="index < presentation[preset.id].flow.length - 1">→</i>
              </template>
            </div>
            <div class="preset-footer"><span class="safety-chip">{{ presentation[preset.id].safety }}</span><span>开始设置 ›</span></div>
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
  </div>
</template>
