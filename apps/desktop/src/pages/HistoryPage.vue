<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useAppStore } from '../stores/app'
import { formatDate } from '../utils'
import PageHeader from '../components/PageHeader.vue'

const store = useAppStore()
const activeId = ref<string>()
const active = computed(() => store.history.find((run) => run.run_id === activeId.value) ?? store.history[0])
watch(() => active.value?.run_id, (runId) => { if (runId) void store.loadHistoryDetail(runId) }, { immediate: true })
</script>

<template>
  <div class="page scroll-page">
    <PageHeader title="整理历史" description="每次整理都记录了每个文件的去向。可以撤销的整理会标出来。">
      <div class="segments"><button class="active">全部</button><button>可撤销</button><button>部分成功</button><button>失败</button></div>
    </PageHeader>
    <div v-if="!store.history.length" class="empty-state"><span>◷</span><h2>还没有整理记录</h2><p>整理完成后，每个文件的去向都会记录在这里。</p><button class="button primary" @click="store.go('home')">去首页选择方案</button></div>
    <div v-else class="history-grid">
      <div class="history-list">
        <button v-for="run in store.history" :key="run.run_id" :class="{ active: active?.run_id === run.run_id }" @click="activeId = run.run_id">
          <span class="history-icon">↓</span><span><b>{{ run.profile.name }}</b><small>{{ formatDate(run.started_at) }}，来源：{{ run.profile.sourceFolders[0] }}</small><em><i class="op-badge" :class="run.status === 'completed' ? 'ok' : 'warn'">{{ run.status === 'completed' ? '完成' : '部分成功' }}</i><i class="op-badge undo">可撤销</i></em></span><strong>{{ run.total }} 个文件</strong>
        </button>
      </div>
      <section v-if="active" class="panel history-detail">
        <div class="panel-title"><span>{{ active.profile.name }}</span><span class="op-badge" :class="active.status === 'completed' ? 'ok' : 'warn'">{{ active.status === 'completed' ? '完成' : '部分成功' }}</span></div>
        <div class="profile-snapshot"><small>方案快照 · 当时的设置</small><dl><dt>来源</dt><dd>{{ active.profile.sourceFolders.join('、') }}</dd><dt>整理到</dt><dd>{{ active.profile.targetFolder }}</dd><dt>处理结果</dt><dd>{{ active.success }} 成功，{{ active.skipped }} 跳过，{{ active.failed }} 失败</dd></dl></div>
        <div class="detail-tabs"><button class="active">移动 {{ active.success }}</button><button>跳过 {{ active.skipped }}</button><button>失败 {{ active.failed }}</button></div>
        <div class="history-operations">
          <div v-if="!store.historyDetail?.operations.length" class="history-placeholder">这次整理没有已记录的文件操作。</div>
          <div v-for="operation in store.historyDetail?.operations ?? []" :key="operation.operation_id" class="history-operation">
            <span class="op-badge" :class="operation.operation === 'quarantine' ? 'quarantine' : 'move'">{{ operation.operation === 'quarantine' ? '隔离' : '移动' }}</span>
            <span><b>{{ operation.source_path.split('/').at(-1) }}</b><small>{{ operation.source_path }} → {{ operation.target_path }}</small></span>
            <span class="op-badge" :class="operation.state === 'applied' ? 'ok' : operation.state === 'undone' ? 'undo' : 'fail'">{{ operation.state === 'applied' ? '已完成' : operation.state === 'undone' ? '已撤销' : '失败' }}</span>
          </div>
        </div>
        <footer><span /><button class="button undo" :disabled="store.busy" @click="store.prepareUndo(active.run_id)">↶ 撤销这次整理</button></footer>
      </section>
    </div>
  </div>
</template>
