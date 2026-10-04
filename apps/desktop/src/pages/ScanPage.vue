<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '../stores/app'

const store = useAppStore()
const filled = computed(() => Math.min(224, Math.max(12, Math.floor(store.scanChecked / 10))))
</script>

<template>
  <div class="page scan-page">
    <div class="scan-matrix" aria-hidden="true">
      <i v-for="index in 224" :key="index" :class="{ hit: index < filled, match: index % 19 === 0 && index < filled }" />
    </div>
    <h1>{{ store.profile.presetType === 'duplicates' ? '正在查找重复文件' : '正在扫描' }}</h1>
    <div class="scan-count"><strong>{{ store.scanChecked.toLocaleString() }}</strong><span>个文件已检查</span></div>
    <div class="scan-current"><small>当前位置</small><code>{{ store.scanPath }}</code></div>
    <div v-if="store.profile.presetType === 'duplicates'" class="scan-stages"><span class="done">按大小筛选</span><span class="active">比对部分内容</span><span>比对完整内容</span></div>
    <p>扫描只读取文件信息，不会改动任何文件。</p>
    <footer class="action-bar"><button class="button secondary" @click="store.cancelScan">取消扫描</button><span>取消后回到方案设置，不会留下任何改动。</span></footer>
  </div>
</template>
