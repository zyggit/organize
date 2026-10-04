<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import PageHeader from '../components/PageHeader.vue'

const settings = ref({ theme: 'system', retentionDays: 30, historyLimit: 200, redactPaths: true, notifyOnComplete: true })
onMounted(async () => { settings.value = await api.request('settings.get') })
function save() { void api.request('settings.update', { values: settings.value }) }
</script>

<template>
  <div class="page scroll-page narrow-page">
    <PageHeader title="设置" description="修改会立即保存。" />
    <section class="settings-group"><h2>整理</h2><div><span><b>默认整理到</b><small>~/Documents/整理</small></span><button class="button secondary">更改</button></div><label><span><b>整理完成后通知我</b><small>窗口不在前台时，用系统通知提醒</small></span><input v-model="settings.notifyOnComplete" type="checkbox" @change="save" /></label></section>
    <section class="settings-group"><h2>安全</h2><div><span><b>隔离区位置</b><small>应用数据/organize-gui/quarantine</small></span><button class="button secondary">更改</button></div><label><span><b>隔离区提醒时间</b><small>应用不会自动清理</small></span><input v-model.number="settings.retentionDays" class="number-input" type="number" min="7" max="3650" @change="save" /> 天</label><label><span><b>保留的整理记录</b><small>更早的记录会删除，但不会影响文件</small></span><input v-model.number="settings.historyLimit" class="number-input" type="number" min="10" max="2000" @change="save" /> 次</label></section>
    <section class="settings-group"><h2>隐私</h2><label><span><b>日志中隐藏文件路径</b><small>默认只记录文件名和错误类型</small></span><input v-model="settings.redactPaths" type="checkbox" @change="save" /></label></section>
    <section class="settings-group"><h2>外观</h2><div><span><b>主题</b><small>默认跟随系统设置</small></span><div class="segments"><button v-for="theme in [['system','跟随系统'],['light','浅色'],['dark','深色']]" :class="{ active: settings.theme === theme[0] }" @click="settings.theme = theme[0]; save()">{{ theme[1] }}</button></div></div></section>
  </div>
</template>
