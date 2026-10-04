<script setup lang="ts">
import { useAppStore } from '../stores/app'
import CareVisual from '../components/CareVisual.vue'
import AppIcon from '../components/AppIcon.vue'

const store = useAppStore()
</script>

<template>
  <div class="page scan-page" aria-busy="true">
    <div class="scan-center">
    <CareVisual mode="scanning" />
    <span class="eyebrow">LOOKING CLOSER</span>
    <h1>{{ store.profile.presetType === 'duplicates' ? '正在查找重复文件' : '正在扫描' }}</h1>
    <div class="scan-count"><strong>{{ store.scanChecked.toLocaleString() }}</strong><span>个文件已检查</span></div>
    <div class="scan-current"><small>正在检查</small><code :title="store.scanPath">{{ store.scanPath }}</code></div>
    <div v-if="store.profile.presetType === 'duplicates'" class="scan-stages"><span class="done">按大小筛选</span><span class="active">比对部分内容</span><span>比对完整内容</span></div>
    <p class="scan-safety"><AppIcon name="shield" :size="16" />扫描只读取文件信息，不会改动任何文件。</p>
    </div>
    <footer class="action-bar"><button class="button secondary" @click="store.cancelScan">取消扫描</button><span>取消后回到方案设置，不会留下任何改动。</span></footer>
  </div>
</template>
