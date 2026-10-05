<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NModal } from 'naive-ui'
import { openLegalResource } from '../api'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ 'update:show': [value: boolean] }>()
type LegalData = typeof import('../generated/legal-notices.json')
const data = ref<LegalData>()
const search = ref('')
const status = ref('')
const tab = ref<'project' | 'components' | 'sources' | 'brand'>('project')
const tabs = [
  { id: 'project', label: '项目许可' }, { id: 'components', label: '第三方组件' },
  { id: 'sources', label: 'MPL 源码' }, { id: 'brand', label: '独立品牌' },
] as const
watch(() => props.show, async (show) => {
  if (!show || data.value) return
  try { data.value = (await import('../generated/legal-notices.json')).default }
  catch { status.value = '许可材料加载失败，请查看安装包 Contents/Resources/legal 或重新安装。' }
}, { immediate: true })
const components = computed(() => (data.value?.components ?? []).filter((p) =>
  `${p.name} ${p.version} ${p.license} ${p.ecosystem}`.toLocaleLowerCase().includes(search.value.toLocaleLowerCase()),
))
async function open(resource: 'licenses' | 'mpl-sources') {
  try {
    status.value = await openLegalResource(resource)
      ? '已打开安装包内的许可资源。'
      : '当前是浏览器演示。桌面安装包附带全部材料；开发者可查看仓库 legal/generated。'
  } catch (error) { status.value = error instanceof Error ? error.message : String(error) }
}
</script>

<template>
  <NModal :show="show" preset="card" title="开源许可证与源码" :style="{ width: 'min(900px, calc(100vw - 48px))' }" :bordered="false" @update:show="emit('update:show', $event)">
    <div class="license-actions"><button class="button secondary" @click="open('licenses')">打开许可文件夹</button><button class="button secondary" @click="open('mpl-sources')">打开 MPL 源码归档</button></div>
    <p v-if="status" class="license-status" role="status">{{ status }}</p>
    <nav class="license-tabs" aria-label="许可说明分类"><button v-for="item in tabs" :key="item.id" :class="{ active: tab === item.id }" :aria-pressed="tab === item.id" @click="tab = item.id">{{ item.label }}</button></nav>
    <div class="license-content" tabindex="0" aria-label="许可全文，可滚动">
      <template v-if="data">
        <template v-if="tab === 'project'"><h3>Organize · 独立桌面衍生项目</h3><p>基于 Thomas Feldmann 的 organize，保留上游 MIT 许可与署名。新增桌面代码和原创图标按 MIT 提供；第三方组件分别遵守其许可证。软件许可不授予第三方商标权。</p><pre>{{ data.mit }}</pre></template>
        <template v-else-if="tab === 'components'">
          <label class="license-search">搜索组件、版本或许可<input v-model="search" type="search" placeholder="例如 option-ext / MPL / Python" /></label>
          <p>{{ components.length }} 个结果 · {{ data.target }}。清单保守涵盖运行与构建依赖，不代表全部链接进应用。</p>
          <details v-for="p in components" :key="`${p.ecosystem}:${p.name}@${p.version}`"><summary>{{ p.name }} {{ p.version }} · {{ p.license }}</summary><p>{{ p.ecosystem }} · {{ p.scope }}</p><p class="license-source">{{ p.source }}</p><section v-for="file in p.files" :key="file.name"><h4>{{ file.name }}</h4><pre>{{ file.text }}</pre></section></details>
          <p v-if="!components.length">未找到匹配组件。</p>
        </template>
        <pre v-else-if="tab === 'sources'">{{ data.sources }}</pre>
        <pre v-else>{{ data.brand }}</pre>
      </template>
      <p v-else>正在加载许可材料…</p>
    </div>
  </NModal>
</template>

<style scoped>
.license-actions, .license-tabs { display: flex; gap: 10px; flex-wrap: wrap; }
.license-tabs { margin: 18px 0 12px; border-bottom: 1px solid var(--border, #ddd); padding-bottom: 10px; }
.license-tabs button { cursor: pointer; border: 0; border-radius: 8px; padding: 8px 14px; background: transparent; color: inherit; }
.license-tabs button.active { background: #218d8320; color: #228f84; }
.license-content { max-height: min(58vh, 560px); overflow: auto; padding-right: 8px; line-height: 1.65; }
.license-content pre { white-space: pre-wrap; overflow-wrap: anywhere; font: 12px/1.75 ui-monospace, monospace; }
.license-content details { padding: 12px 0; border-bottom: 1px solid var(--border, #ddd); }
.license-content summary { cursor: pointer; overflow-wrap: anywhere; }
.license-search { display: grid; gap: 6px; }
.license-search input { padding: 10px 12px; border: 1px solid #8a9b9d66; border-radius: 8px; color: inherit; background: transparent; }
.license-source, .license-status { overflow-wrap: anywhere; }
</style>
