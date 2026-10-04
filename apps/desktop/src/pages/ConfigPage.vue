<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAppStore } from '../stores/app'
import { pickDirectories } from '../api'
import PageHeader from '../components/PageHeader.vue'
import AppIcon from '../components/AppIcon.vue'

const store = useAppStore()
const validating = ref(false)
const issues = ref<Array<Record<string, unknown>>>([])
const categories = [
  ['documents', '文档', 'PDF、Word、Excel、PPT、TXT'],
  ['images', '图片', 'JPG、PNG、WEBP、HEIC'],
  ['videos', '视频', 'MP4、MOV、MKV、AVI'],
  ['audio', '音频', 'MP3、M4A、WAV、FLAC'],
  ['archives', '压缩包', 'ZIP、7Z、RAR、TAR'],
  ['installers', '安装包', 'EXE、MSI、DMG、PKG'],
  ['other', '其他文件', '没有归入以上类型的文件'],
] as const

const enabled = computed(() => store.profile.parameters.categories ?? [])
const fixedTarget = computed(() => ['old-installers', 'duplicates'].includes(store.profile.presetType))

function toggleCategory(id: string) {
  const current = new Set(enabled.value)
  current.has(id) ? current.delete(id) : current.add(id)
  store.profile.parameters.categories = [...current]
}

async function addSource() {
  const values = await pickDirectories(store.profile.presetType === 'duplicates')
  for (const value of values) {
    if (!store.profile.sourceFolders.includes(value)) store.profile.sourceFolders.push(value)
  }
}

async function changeTarget() {
  const [value] = await pickDirectories(false)
  if (value) store.profile.targetFolder = value
}

async function scan() {
  validating.value = true
  const result = await store.validateProfile()
  issues.value = result.issues
  validating.value = false
  if (result.valid) await store.createPlan()
}
</script>

<template>
  <div class="page flow-page">
    <PageHeader :title="store.profile.name" description="选择来源和目标。所有检查会在扫描前完成。">
      <button class="button ghost" @click="store.go('home')">换一个方案</button>
    </PageHeader>
    <div v-if="issues.length" class="banner fail">有 {{ issues.length }} 个问题需要处理后才能扫描。请检查文件夹路径和访问权限。</div>
    <div class="config-grid">
      <div class="config-main">
        <section class="panel form-section">
          <div class="panel-title"><span>要整理的文件夹</span><button class="text-button" @click="addSource">＋ 添加文件夹</button></div>
          <div class="folder-row" v-for="(source, index) in store.profile.sourceFolders" :key="`${source}-${index}`">
            <span class="folder-icon"><AppIcon name="folder" /></span><span class="folder-info"><b>{{ source.split('/').at(-1) || '文件夹' }}</b><small :title="source">{{ source }}</small></span><span class="check-ok">✓ 可以读取</span>
            <button v-if="store.profile.sourceFolders.length > 1" @click="store.profile.sourceFolders.splice(index, 1)">×</button>
          </div>
          <label class="toggle-row"><span><b>包含子文件夹里的文件</b><small>关闭时只查看所选文件夹的第一层</small></span><input v-model="store.profile.includeSubfolders" type="checkbox" /></label>
        </section>
        <section v-if="!fixedTarget" class="panel form-section">
          <div class="panel-title"><span>整理到</span><button class="text-button" @click="changeTarget">更改</button></div>
          <div class="folder-row"><span class="folder-icon target"><AppIcon name="folder" /></span><span class="folder-info"><b>整理</b><small :title="store.profile.targetFolder">{{ store.profile.targetFolder }}</small></span><span class="check-ok">✓ 可以写入</span></div>
        </section>
        <section v-if="store.profile.presetType === 'by-type'" class="panel form-section">
          <div class="panel-title">要整理的类型</div>
          <div class="category-grid">
            <button v-for="category in categories" :key="category[0]" :class="{ on: enabled.includes(category[0]) }" @click="toggleCategory(category[0])">
              <span class="check" :class="{ on: enabled.includes(category[0]) }">{{ enabled.includes(category[0]) ? '✓' : '' }}</span>
              <span><b>{{ category[1] }}</b><small>{{ category[2] }}</small></span>
            </button>
          </div>
        </section>
        <section v-if="store.profile.presetType === 'by-date'" class="banner quarantine">按文件修改日期归档。修改日期不一定等于照片拍摄日期。</section>
        <section v-if="store.profile.presetType === 'old-installers'" class="panel form-section">
          <div class="panel-title">多久没用的安装包需要隔离？</div>
          <div class="segments days"><button v-for="days in [30,60,90,180]" :class="{ active: store.profile.parameters.olderThanDays === days }" @click="store.profile.parameters.olderThanDays = days">{{ days }} 天</button></div>
          <label class="toggle-row"><span><b>同时包含 ZIP 压缩包</b><small>压缩包里可能包含其他文件，默认关闭</small></span><input v-model="store.profile.parameters.includeArchives" type="checkbox" /></label>
        </section>
        <section v-if="store.profile.presetType === 'duplicates'" class="banner undo">找到的重复文件不会自动处理。扫描后由你逐组选择保留哪一份。</section>
      </div>
      <aside class="panel outcome-card">
        <div class="panel-title">整理后会是这样</div>
        <div class="folder-tree">
          <b>{{ fixedTarget ? '隔离区' : '整理' }}/</b>
          <span v-if="store.profile.presetType === 'by-type'">├ 文档/<br>├ 图片/<br>├ 视频/<br>└ 其他文件/</span>
          <span v-else-if="store.profile.presetType === 'by-date'">└ 2026年/<br>&nbsp;&nbsp;└ 10月/</span>
          <span v-else>└ 文件会保留原始来源记录</span>
        </div>
        <div class="skip-note"><b>这些文件会自动跳过</b><p>还没下载完的文件、系统文件、软链接，以及无法安全读取的文件。</p></div>
      </aside>
    </div>
    <footer class="action-bar"><button class="button secondary" @click="store.go('home')">← 返回首页</button><span>扫描只读取文件信息，不会改动任何文件。</span><button class="button primary" :disabled="validating || (store.profile.presetType === 'by-type' && !enabled.length)" @click="scan">{{ validating ? '正在检查…' : '开始扫描' }}</button></footer>
  </div>
</template>
