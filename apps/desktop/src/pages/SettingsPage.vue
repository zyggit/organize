<script setup lang="ts">
import { ref } from 'vue'
import { useAppStore } from '../stores/app'
import { pickDirectories, requestNotificationPermission } from '../api'
import type { Settings } from '../types'
import PageHeader from '../components/PageHeader.vue'

const store = useAppStore()
const saving = ref(false)
const draft = ref({ ...store.settings })
async function save(values: Partial<Settings>) {
  saving.value = true
  try {
    if (values.notifyOnComplete && !await requestNotificationPermission()) {
      store.notice = '系统未允许通知，请在系统设置中授权 Organize。'
      values.notifyOnComplete = false
    }
    await store.updateSettings(values)
  } catch (caught) { store.report(caught) } finally {
    draft.value = { ...store.settings }
    saving.value = false
  }
}
async function folder(key: 'defaultTargetFolder' | 'quarantineFolder') {
  try { const [path] = await pickDirectories(false); if (path) await save({ [key]: path }) }
  catch (caught) { store.report(caught) }
}
</script>

<template>
  <div class="page scroll-page narrow-page">
    <PageHeader title="设置" :description="saving ? '正在保存…' : '修改会立即保存。'" />
    <fieldset :disabled="saving" class="settings-fields">
      <section class="settings-group"><h2>整理</h2><div><span><b>默认整理到</b><small>{{ store.settings.defaultTargetFolder }}</small></span><button class="button secondary" @click="folder('defaultTargetFolder')">更改</button></div><label><span><b>整理完成后通知我</b><small>窗口不在前台时提醒，需要系统允许通知</small></span><input v-model="draft.notifyOnComplete" type="checkbox" @change="save({ notifyOnComplete: draft.notifyOnComplete })" /></label></section>
      <section class="settings-group"><h2>安全</h2><div><span><b>隔离区位置</b><small>{{ store.settings.quarantineFolder }}</small><small>仅影响新扫描；已有隔离文件不搬迁。变更后需重新扫描。</small></span><button class="button secondary" @click="folder('quarantineFolder')">更改</button></div><label><span><b>新隔离文件的提醒时间</b><small>应用不会自动删除，已有文件的提醒日期不变</small></span><input v-model.number="draft.retentionDays" class="number-input" type="number" min="7" max="3650" @change="save({ retentionDays: draft.retentionDays })" /> 天</label><label><span><b>历史列表显示数量</b><small>更早记录仍保留，不删除撤销所需日志</small></span><input v-model.number="draft.historyLimit" class="number-input" type="number" min="10" max="2000" @change="save({ historyLimit: draft.historyLimit })" /> 次</label></section>
      <section class="settings-group"><h2>隐私</h2><label><span><b>导出诊断时隐藏完整路径</b><small>仅影响导出文件；本机历史保留路径以支持撤销</small></span><input v-model="draft.redactPaths" type="checkbox" @change="save({ redactPaths: draft.redactPaths })" /></label></section>
      <section class="settings-group"><h2>外观</h2><div><span><b>主题</b><small>默认跟随系统设置</small></span><div class="segments"><button v-for="theme in (['system','light','dark'] as const)" :key="theme" :class="{ active: store.theme === theme }" @click="save({ theme })">{{ { system: '跟随系统', light: '浅色', dark: '深色' }[theme] }}</button></div></div></section>
    </fieldset>
  </div>
</template>
