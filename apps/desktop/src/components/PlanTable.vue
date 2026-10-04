<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { NModal } from 'naive-ui'
import type { PlanItem } from '../types'
import { formatBytes, fileName, folderName } from '../utils'

const props = defineProps<{ items: PlanItem[] }>()
const emit = defineEmits<{ toggle: [itemId: string] }>()
const search = ref('')
const filter = ref<'all' | 'conflict' | 'skip' | 'excluded'>('all')
const scrollTop = ref(0)
const scrollContainer = ref<HTMLDivElement>()
const viewportHeight = ref(0)
const rowHeight = 64
const headerHeight = 42
const detailItem = ref<PlanItem>()
const detailOpen = ref(false)
let resizeObserver: ResizeObserver | undefined

onMounted(() => {
  const container = scrollContainer.value
  if (!container) return
  const measure = () => { viewportHeight.value = Math.max(0, container.clientHeight - headerHeight) }
  resizeObserver = new ResizeObserver(measure)
  resizeObserver.observe(container)
  measure()
})
onBeforeUnmount(() => resizeObserver?.disconnect())

function resetScroll() {
  scrollTop.value = 0
  if (scrollContainer.value) scrollContainer.value.scrollTop = 0
}
watch([search, filter, () => props.items.length], resetScroll, { flush: 'post' })

const filtered = computed(() => props.items.filter((item) => {
  if (search.value && !`${item.sourcePath} ${item.targetPath ?? ''}`.toLocaleLowerCase().includes(search.value.toLocaleLowerCase())) return false
  if (filter.value === 'conflict') return item.warningCode === 'TARGET_CONFLICT'
  if (filter.value === 'skip') return item.status === 'skipped'
  if (filter.value === 'excluded') return item.status !== 'skipped' && !item.selected
  return true
}))
const start = computed(() => Math.min(Math.max(0, filtered.value.length - 1), Math.max(0, Math.floor(scrollTop.value / rowHeight) - 4)))
const end = computed(() => Math.min(filtered.value.length, start.value + Math.ceil(viewportHeight.value / rowHeight) + 9))
const visible = computed(() => filtered.value.slice(start.value, end.value))

function operationLabel(item: PlanItem) {
  if (item.status === 'skipped') return '跳过'
  const label = item.operation === 'quarantine' ? '隔离' : '移动'
  return item.warningCode === 'TARGET_CONFLICT' ? `${label}并改名` : label
}

function reasonLabel(item: PlanItem) {
  return item.reason || (item.warningCode === 'TARGET_CONFLICT' ? '重名，将使用新名称' : '—')
}

function showDetails(item: PlanItem) {
  detailItem.value = item
  detailOpen.value = true
}
</script>

<template>
  <section class="plan-list">
    <div class="plan-tools">
      <label class="search-box">⌕<input v-model="search" aria-label="搜索文件名或路径" placeholder="搜索文件名或路径" /></label>
      <div class="segments">
        <button :class="{ active: filter === 'all' }" @click="filter = 'all'">全部 {{ items.length }}</button>
        <button :class="{ active: filter === 'conflict' }" @click="filter = 'conflict'">重名</button>
        <button :class="{ active: filter === 'skip' }" @click="filter = 'skip'">跳过</button>
        <button :class="{ active: filter === 'excluded' }" @click="filter = 'excluded'">已排除</button>
      </div>
    </div>
    <div ref="scrollContainer" class="virtual-scroll" role="region" aria-label="整理预览列表，可横向和纵向滚动" tabindex="0" @scroll="scrollTop = ($event.target as HTMLElement).scrollTop">
      <div class="plan-table-content" role="table" aria-label="整理预览" :aria-rowcount="filtered.length + 1">
        <div class="table-head" role="row"><span role="columnheader">选择</span><span role="columnheader">文件</span><span role="columnheader">位置变化</span><span role="columnheader">操作</span><span role="columnheader">大小</span><span role="columnheader">说明</span><span role="columnheader">详情</span></div>
        <div v-if="!filtered.length" class="plan-empty">{{ items.length ? '没有匹配的文件，请调整搜索或筛选条件。' : '没有需要整理的文件。' }}</div>
        <div :style="{ height: `${filtered.length * rowHeight}px`, position: 'relative' }">
        <div class="virtual-inner" :style="{ transform: `translateY(${start * rowHeight}px)` }">
          <div
            v-for="(item, index) in visible"
            :key="item.itemId"
            class="plan-row"
            :class="{ excluded: !item.selected && item.status !== 'skipped' }"
            role="row"
            :aria-rowindex="start + index + 2"
            @click="emit('toggle', item.itemId)"
          >
            <span role="cell"><input type="checkbox" class="plan-checkbox" :checked="item.selected" :disabled="item.status === 'skipped'" :aria-label="`选择文件 ${fileName(item.sourcePath)}`" @click.stop @change="emit('toggle', item.itemId)" /></span>
            <span class="file-cell" role="cell"><b :title="fileName(item.sourcePath)">{{ fileName(item.sourcePath) }}</b><small :title="item.sourcePath">{{ item.sourcePath }}</small></span>
            <span class="destination-cell" role="cell" :title="item.targetPath ?? '保持不动'"><span class="path-change"><em :title="item.sourcePath">{{ folderName(item.sourcePath) }}</em><i>→</i><em v-if="item.targetPath" class="target">{{ folderName(item.targetPath) }}</em><em v-else>保持不动</em></span><small v-if="item.targetPath" :title="fileName(item.targetPath)">{{ fileName(item.targetPath) }}</small></span>
            <span role="cell"><span class="op-badge" :class="item.warningCode ? 'warn' : item.operation">{{ operationLabel(item) }}</span></span>
            <span class="number" role="cell">{{ formatBytes(item.size) }}</span>
            <span class="reason" role="cell" :title="reasonLabel(item)">{{ reasonLabel(item) }}</span>
            <span role="cell"><button class="text-button" :aria-label="`查看文件详情 ${fileName(item.sourcePath)}`" @click.stop="showDetails(item)">详情</button></span>
          </div>
        </div>
        </div>
      </div>
    </div>
    <div class="plan-list-footer">显示 {{ filtered.length }} / {{ items.length }} 个文件 · 长文件名、完整路径及说明可点击“详情”查看</div>
  </section>
  <NModal v-model:show="detailOpen">
    <section v-if="detailItem" class="dialog plan-detail" role="dialog" aria-modal="true" aria-labelledby="plan-detail-title">
      <h2 id="plan-detail-title">文件详情</h2>
      <dl>
        <dt>文件名</dt><dd>{{ fileName(detailItem.sourcePath) }}</dd>
        <dt>原始路径</dt><dd>{{ detailItem.sourcePath }}</dd>
        <dt>目标路径</dt><dd>{{ detailItem.targetPath ?? '保持不动' }}</dd>
        <dt>操作</dt><dd>{{ operationLabel(detailItem) }}</dd>
        <dt>大小</dt><dd>{{ formatBytes(detailItem.size) }}（{{ detailItem.size.toLocaleString() }} 字节）</dd>
        <dt>说明</dt><dd>{{ reasonLabel(detailItem) }}</dd>
      </dl>
      <div><button class="button secondary" @click="detailOpen = false">关闭</button></div>
    </section>
  </NModal>
</template>
