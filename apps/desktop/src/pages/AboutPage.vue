<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, pickDiagnosticPath, revealLocalPath } from '../api'
import PageHeader from '../components/PageHeader.vue'
import appIcon from '../assets/app-icon.png'

const versions = ref({ engine: '—', organize: '—' })
const dataDir = ref('')
const exportStatus = ref('')
onMounted(async () => {
  const [loadedVersions, initial] = await Promise.all([
    api.request<{ engine: string; organize: string }>('app.version'),
    api.request<{ dataDir: string }>('app.initialize'),
  ])
  versions.value = loadedVersions
  dataDir.value = initial.dataDir
})
async function exportDiagnostics() {
  const destination = await pickDiagnosticPath()
  if (!destination) return
  const result = await api.request<{ path: string }>('diagnostics.export', { destination })
  exportStatus.value = `已保存到 ${result.path}`
}
</script>

<template>
  <div class="page scroll-page narrow-page">
    <PageHeader title="关于与诊断" description="版本、隐私和本地诊断工具。" />
    <section class="about-hero panel"><span class="about-app-icon"><img :src="appIcon" alt="" /></span><div><h2>organize</h2><p>安全、可预览、可撤销的文件整理助手</p></div><dl><dt>应用版本</dt><dd>0.1.0</dd><dt>整理引擎</dt><dd>{{ versions.engine }}</dd><dt>organize</dt><dd>{{ versions.organize }}</dd></dl></section>
    <section class="settings-group"><h2>诊断</h2><div><span><b>应用数据文件夹</b><small>{{ dataDir || '正在读取…' }}</small></span><button class="button secondary" :disabled="!dataDir" @click="revealLocalPath(dataDir)">打开</button></div><div><span><b>导出诊断包</b><small>{{ exportStatus || '只保存在你的电脑上，不会自动上传' }}</small></span><button class="button primary" @click="exportDiagnostics">导出</button></div></section>
    <section class="settings-group"><h2>说明</h2><button class="link-row"><span><b>隐私说明</b><small>应用不上传任何文件或文件名</small></span><i>›</i></button><button class="link-row"><span><b>开源许可证</b><small>查看 organize 及其他组件的许可信息</small></span><i>›</i></button></section>
  </div>
</template>
