<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useAppStore } from '../stores/app'
import { formatDate } from '../utils'
import PageHeader from '../components/PageHeader.vue'
import AppIcon from '../components/AppIcon.vue'

const store = useAppStore()
const activeId = ref<string>()
const filter = ref('all')
const operationFilter = ref('applied')
const runs = computed(() => store.history.filter(run => filter.value === 'all' ||
  (filter.value === 'undo' ? run.undoable_count > 0 : run.status === filter.value)))
const active = computed(() => runs.value.find((run) => run.run_id === activeId.value) ?? runs.value[0])
const labels: Record<string, string> = { completed: '完成', partial: '部分成功', failed: '失败', cancelled: '已停止', running: '执行中', applied: '已完成', undone: '已撤销', skipped: '已跳过', started: '未完成' }
const operations = computed(() => store.historyDetail?.run_id === active.value?.run_id ? store.historyDetail.operations.filter(op => operationFilter.value === 'applied' ? ['applied','undone'].includes(op.state) : op.state === operationFilter.value) : [])
watch(() => active.value?.run_id, (runId) => { if (runId) void store.loadHistoryDetail(runId) }, { immediate: true })
</script>

<template>
  <div class="page scroll-page">
    <PageHeader title="整理历史" description="每次整理都记录了每个文件的去向。可以撤销的整理会标出来。">
      <div class="segments"><button v-for="[id,label] in [['all','全部'],['undo','可尝试撤销'],['partial','部分成功'],['failed','失败'],['cancelled','已停止']]" :key="id" :class="{ active: filter === id }" @click="filter = id">{{ label }}</button></div>
    </PageHeader>
    <div v-if="!runs.length" class="empty-state"><span><AppIcon name="history" :size="48" /></span><h2>{{ store.history.length ? '没有符合筛选条件的记录' : '还没有整理记录' }}</h2><p>整理完成后，每个文件的去向都会记录在这里。</p><button class="button primary" @click="store.go('home')">去首页选择方案</button></div>
    <div v-else class="history-grid">
      <div class="history-list">
        <button v-for="run in runs" :key="run.run_id" :class="{ active: active?.run_id === run.run_id }" @click="activeId = run.run_id">
          <span class="history-icon"><AppIcon name="folder" /></span><span><b>{{ run.profile.name }}</b><small>{{ formatDate(run.started_at) }}，来源：{{ run.profile.sourceFolders[0] }}</small><em><i class="op-badge" :class="run.status === 'completed' ? 'ok' : 'warn'">{{ labels[run.status] }}</i><i v-if="run.undoable_count" class="op-badge undo">可尝试撤销</i></em></span><strong>{{ run.total }} 个文件</strong>
        </button>
      </div>
      <section v-if="active" class="panel history-detail">
        <div class="panel-title"><span>{{ active.profile.name }}</span><span class="op-badge" :class="active.status === 'completed' ? 'ok' : 'warn'">{{ labels[active.status] }}</span></div>
        <div class="profile-snapshot"><small>方案快照 · 当时的设置</small><dl><dt>来源</dt><dd>{{ active.profile.sourceFolders.join('、') }}</dd><dt>整理到</dt><dd>{{ active.profile.targetFolder }}</dd><dt>处理结果</dt><dd>{{ active.success }} 成功，{{ active.skipped }} 跳过，{{ active.failed }} 失败</dd></dl></div>
        <div class="detail-tabs"><button v-for="[id,label] in [['applied','已处理'],['skipped','跳过'],['failed','失败']]" :key="id" :class="{ active: operationFilter === id }" @click="operationFilter = id">{{ label }}</button></div>
        <div class="history-operations">
          <div v-if="!operations.length" class="history-placeholder">此分类没有已记录的文件操作。</div>
          <div v-for="operation in operations" :key="operation.operation_id" class="history-operation">
            <span class="op-badge" :class="operation.operation === 'quarantine' ? 'quarantine' : 'move'">{{ operation.operation === 'quarantine' ? '隔离' : '移动' }}</span>
            <span><b>{{ operation.source_path.split('/').at(-1) }}</b><small>{{ operation.source_path }} → {{ operation.target_path }}</small><small v-if="operation.error_code">{{ operation.error_code }} {{ operation.error_detail }}</small></span>
            <span class="op-badge" :class="operation.state === 'applied' ? 'ok' : operation.state === 'undone' ? 'undo' : 'fail'">{{ labels[operation.state] }}</span>
          </div>
        </div>
        <footer><span>撤销前会检查文件是否仍可恢复</span><button class="button undo" :disabled="store.busy || !active.undoable_count" @click="store.prepareUndo(active.run_id)">↶ 撤销这次整理</button></footer>
      </section>
    </div>
  </div>
</template>
