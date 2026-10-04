<script setup lang="ts">
import { computed, ref } from 'vue'
import type { PlanItem } from '../types'
import { formatBytes, fileName, folderName } from '../utils'

const props = defineProps<{ items: PlanItem[] }>()
const emit = defineEmits<{ toggle: [itemId: string] }>()
const search = ref('')
const filter = ref<'all' | 'conflict' | 'skip' | 'excluded'>('all')
const scrollTop = ref(0)
const rowHeight = 54
const viewportHeight = 430

const filtered = computed(() => props.items.filter((item) => {
  if (search.value && !fileName(item.sourcePath).toLocaleLowerCase().includes(search.value.toLocaleLowerCase())) return false
  if (filter.value === 'conflict') return item.warningCode === 'TARGET_CONFLICT'
  if (filter.value === 'skip') return item.status === 'skipped'
  if (filter.value === 'excluded') return item.status !== 'skipped' && !item.selected
  return true
}))
const start = computed(() => Math.max(0, Math.floor(scrollTop.value / rowHeight) - 4))
const end = computed(() => Math.min(filtered.value.length, start.value + Math.ceil(viewportHeight / rowHeight) + 8))
const visible = computed(() => filtered.value.slice(start.value, end.value))
</script>

<template>
  <section class="plan-list">
    <div class="plan-tools">
      <label class="search-box">⌕<input v-model="search" placeholder="搜索文件名" /></label>
      <div class="segments">
        <button :class="{ active: filter === 'all' }" @click="filter = 'all'">全部 {{ items.length }}</button>
        <button :class="{ active: filter === 'conflict' }" @click="filter = 'conflict'">重名</button>
        <button :class="{ active: filter === 'skip' }" @click="filter = 'skip'">跳过</button>
        <button :class="{ active: filter === 'excluded' }" @click="filter = 'excluded'">已排除</button>
      </div>
    </div>
    <div class="table-head"><span>选择</span><span>文件</span><span>位置变化</span><span>操作</span><span>大小</span><span>说明</span></div>
    <div class="virtual-scroll" :style="{ height: `${viewportHeight}px` }" @scroll="scrollTop = ($event.target as HTMLElement).scrollTop">
      <div :style="{ height: `${filtered.length * rowHeight}px`, position: 'relative' }">
        <div class="virtual-inner" :style="{ transform: `translateY(${start * rowHeight}px)` }">
          <button
            v-for="item in visible"
            :key="item.itemId"
            class="plan-row"
            :class="{ excluded: !item.selected && item.status !== 'skipped' }"
            @click="emit('toggle', item.itemId)"
          >
            <span class="check" :class="{ on: item.selected, disabled: item.status === 'skipped' }">{{ item.selected ? '✓' : '' }}</span>
            <span class="file-cell"><b>{{ fileName(item.sourcePath) }}</b><small>{{ item.sourcePath }}</small></span>
            <span class="path-change"><em>{{ folderName(item.sourcePath) }}</em><i>→</i><em v-if="item.targetPath" class="target">{{ folderName(item.targetPath) }}</em><em v-else>保持不动</em></span>
            <span><span class="op-badge" :class="item.warningCode ? 'warn' : item.operation">{{ item.status === 'skipped' ? '跳过' : item.warningCode ? '移动并改名' : item.operation === 'quarantine' ? '隔离' : '移动' }}</span></span>
            <span class="number">{{ formatBytes(item.size) }}</span>
            <span class="reason">{{ item.reason ?? (item.warningCode ? `重名，将使用新名称` : '—') }}</span>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
