<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAppStore } from '../stores/app'
import { formatBytes } from '../utils'
import PageHeader from '../components/PageHeader.vue'
import PlanTable from '../components/PlanTable.vue'

const store = useAppStore()
const confirming = ref(false)
const selected = computed(() => store.selectedItems.length)
const conflicts = computed(() => store.plan?.items.filter((item) => item.warningCode === 'TARGET_CONFLICT').length ?? 0)
</script>

<template>
  <div v-if="store.plan" class="page flow-page">
    <PageHeader title="确认整理计划" description="只会整理下面勾选的文件，扫描后新增的文件不会被处理。" />
    <section class="summary-card">
      <div><strong>{{ selected.toLocaleString() }}</strong><span>个文件将被整理，共 {{ formatBytes(store.selectedBytes) }}</span></div>
      <div class="summary-details">
        <div class="plan-bar"><i class="move" :style="{ flex: Math.max(1, selected) }" /><i class="warn" :style="{ flex: conflicts }" /><i class="skip" :style="{ flex: store.plan.summary.skip }" /></div>
        <div class="legend"><span>■ 移动 <b>{{ store.plan.summary.move }}</b></span><span class="warn-text">■ 重名 <b>{{ conflicts }}</b></span><span>■ 跳过 <b>{{ store.plan.summary.skip }}</b></span><span>■ 你排除的 <b>{{ store.plan.items.filter((x) => !x.selected && x.status !== 'skipped').length }}</b></span></div>
      </div>
    </section>
    <div v-if="conflicts" class="banner warn"><b>{{ conflicts }} 个文件和目标位置的文件重名。</b>它们会自动使用新名称，原有文件不会被覆盖。</div>
    <PlanTable :items="store.plan.items" @toggle="store.toggleItem" />
    <footer class="action-bar"><button class="button secondary" @click="store.go('config')">← 返回修改方案</button><span>已选 <b>{{ selected }}</b> 个文件，{{ formatBytes(store.selectedBytes) }}。不会删除或覆盖任何文件。</span><button class="button primary" :disabled="!selected" @click="confirming = true">整理 {{ selected }} 个文件</button></footer>
    <div v-if="confirming" class="modal-backdrop" @click.self="confirming = false">
      <section class="dialog"><h2>整理 {{ selected }} 个文件？</h2><p>这些文件将移动到“{{ store.profile.targetFolder }}”。重名文件会自动改名，不会覆盖任何内容。完成后可以撤销。</p><div><button class="button secondary" @click="confirming = false">再看看</button><button class="button primary" @click="confirming = false; store.executePlan()">开始整理</button></div></section>
    </div>
  </div>
</template>
