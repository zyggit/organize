<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { useAppStore } from '../stores/app'
import { pickDirectories } from '../api'
import { ruleIssues, stableStringify, type RuleIssue } from '../profiles'
import AppIcon from '../components/AppIcon.vue'
import ProfileMenu from '../components/ProfileMenu.vue'
import SwitchToggle from '../components/SwitchToggle.vue'
import TypeRulesEditor from '../components/TypeRulesEditor.vue'

const store = useAppStore()
const validating = ref(false)
const serverIssues = ref<Array<Record<string, unknown>>>([])
const expandedRule = ref<string>()

const PRESETS = {
  'by-type': { label: '分类整理', icon: 'folder', description: '按扩展名把文件放进对应的子文件夹。' },
  'by-date': { label: '按日期归档', icon: 'image', description: '按文件修改日期放进“年/月”文件夹。' },
  'old-installers': { label: '旧安装包清理', icon: 'download', description: '把长期没用的安装包移到隔离区，可以随时恢复。' },
  duplicates: { label: '重复文件查找', icon: 'duplicate', description: '找出内容完全相同的文件，由你决定保留哪一份。' },
} as const
const preset = computed(() => PRESETS[store.profile.presetType])
const params = computed(() => store.profile.parameters)
const isByType = computed(() => store.profile.presetType === 'by-type')
const fixedTarget = computed(() => ['old-installers', 'duplicates'].includes(store.profile.presetType))
const baseName = (path: string) => path.replace(/\/+$/, '').split('/').at(-1) || path
const targetPath = computed(() => fixedTarget.value ? store.settings.quarantineFolder || '应用隔离区' : store.profile.targetFolder)
const targetName = computed(() => fixedTarget.value ? '隔离区' : baseName(store.profile.targetFolder))

const savedEntry = computed(() => store.savedProfiles.find((profile) => profile.id === store.profile.id))
const saveState = computed(() => !savedEntry.value ? 'new' : stableStringify(savedEntry.value) === stableStringify(store.profile) ? 'saved' : 'dirty')
const SAVE_LABELS = { new: '未保存', saved: '已保存', dirty: '有未保存的改动' }

const SERVER_LABELS: Record<string, string> = {
  SOURCE_NOT_FOUND: '来源文件夹不存在', SOURCE_NOT_READABLE: '来源文件夹无法读取', TARGET_NOT_WRITABLE: '目标文件夹无法写入',
  SOURCE_TARGET_OVERLAP: '目标文件夹不能放在来源里面', QUARANTINE_OVERLAP: '来源文件夹不能与隔离区重叠',
  INVALID_RULE_NAME: '分类名称不能为空', INVALID_RULE_FOLDER: '子文件夹名称不合法', INVALID_RULE_EXTENSIONS: '扩展名无效',
  DUPLICATE_EXTENSION: '扩展名同时属于多个分类', NO_CATEGORIES: '至少启用一个分类，或把未匹配的文件归入其他文件夹',
  INVALID_TYPE_RULES: '分类规则格式不正确', INVALID_UNMATCHED_ACTION: '未匹配文件的处理方式不正确',
}
const RULE_FIELDS: Record<string, RuleIssue['field']> = {
  INVALID_RULE_NAME: 'name', INVALID_RULE_FOLDER: 'folder', INVALID_RULE_EXTENSIONS: 'extensions', DUPLICATE_EXTENSION: 'extensions',
}
const serverLabel = (issue: Record<string, unknown>) => {
  const label = SERVER_LABELS[String(issue.code)] ?? String(issue.code)
  const detail = issue.extension ? `“${issue.extension}”` : issue.path ? `：${issue.path}` : ''
  return `${label}${detail}`
}

const issues = computed<RuleIssue[]>(() => {
  if (!isByType.value) return []
  const local = ruleIssues(store.profile)
  const rules = params.value.typeRules ?? []
  for (const issue of serverIssues.value) {
    const field = String(issue.field ?? '')
    const index = /^parameters\.typeRules\.(\d+)/.exec(field)?.[1]
    const ruleId = index === undefined ? undefined : rules[Number(index)]?.id
    const mapped: RuleIssue['field'] | undefined = RULE_FIELDS[String(issue.code)] ?? (field === 'parameters.otherFolder' ? 'other' : undefined)
    if (mapped && !local.some((item) => item.ruleId === ruleId && item.field === mapped)) local.push({ ruleId, field: mapped, message: serverLabel(issue) })
  }
  return local
})
const environmentIssues = computed(() => serverIssues.value.filter((issue) => !String(issue.code).startsWith('INVALID_RULE') && !['DUPLICATE_EXTENSION', 'NO_CATEGORIES', 'INVALID_TYPE_RULES', 'INVALID_UNMATCHED_ACTION'].includes(String(issue.code)) && issue.field !== 'parameters.otherFolder'))

const normalized = (path: string) => path.replace(/\/+$/, '')
const targetInsideSource = computed(() => !fixedTarget.value && store.profile.sourceFolders.some((source) => {
  const target = normalized(store.profile.targetFolder)
  return target === normalized(source) || target.startsWith(`${normalized(source)}/`)
}))
const blockers = computed(() => (store.profile.sourceFolders.length ? 0 : 1) + (targetInsideSource.value ? 1 : 0) + issues.value.length)

const enabledRules = computed(() => (params.value.typeRules ?? []).map((rule, index) => ({ rule, index })).filter(({ rule }) => rule.enabled))
const now = new Date()
const summary = computed(() => {
  const sources = `${store.profile.sourceFolders.length} 个来源`
  if (isByType.value) return `${sources} → ${enabledRules.value.length} 个分类${params.value.unmatchedAction === 'keep' ? '，未匹配的文件留在原处' : ''}`
  if (store.profile.presetType === 'by-date') return `${sources} → 按“年/月”归档`
  if (store.profile.presetType === 'old-installers') return `${sources} → 超过 ${params.value.olderThanDays ?? 90} 天的安装包移到隔离区`
  return `${sources} → 找出重复文件，逐组确认`
})

async function addSource() {
  for (const value of await pickDirectories(true)) {
    if (!store.profile.sourceFolders.includes(value)) store.profile.sourceFolders.push(value)
  }
}
async function replaceSource(index: number) {
  const [value] = await pickDirectories(false)
  if (value && !store.profile.sourceFolders.some((source, i) => source === value && i !== index)) store.profile.sourceFolders[index] = value
}
async function changeTarget() {
  const [value] = await pickDirectories(false)
  if (value) store.profile.targetFolder = value
}
async function focusRule(ruleId?: string) {
  if (!ruleId) return
  expandedRule.value = ruleId
  await nextTick()
  document.querySelector(`[data-rule="${ruleId}"]`)?.scrollIntoView({ block: 'center', behavior: 'smooth' })
}
async function scan() {
  validating.value = true
  try {
    const result = await store.validateProfile()
    serverIssues.value = result.issues
    if (result.valid) await store.createPlan()
  } catch (caught) { store.report(caught) } finally { validating.value = false }
}
</script>

<template>
  <div class="page flow-page config-page">
    <header class="config-header">
      <div class="config-title">
        <span class="config-kicker"><AppIcon :name="preset.icon" :size="14" />{{ preset.label }}</span>
        <label class="title-field" title="点击修改方案名称">
          <input v-model="store.profile.name" maxlength="80" aria-label="方案名称" placeholder="给这个方案起个名字" />
          <AppIcon name="edit" :size="15" />
        </label>
        <p>{{ preset.description }}</p>
      </div>
      <div class="config-tools">
        <span class="save-state" :class="saveState"><i />{{ SAVE_LABELS[saveState] }}</span>
        <ProfileMenu :saved="Boolean(savedEntry)" @loaded="serverIssues = []; expandedRule = undefined" />
        <button class="button secondary" :disabled="saveState === 'saved' || !store.profile.name.trim()" @click="store.saveProfile">保存方案</button>
      </div>
    </header>

    <div class="config-grid">
      <div class="config-main">
        <section class="panel config-section route-panel">
          <header class="section-head">
            <div class="section-title"><h2>整理范围</h2><p>扫描只读取文件信息，不会改动任何文件</p></div>
            <div class="section-actions"><button class="button secondary small" @click="addSource"><AppIcon name="plus" :size="15" />添加来源</button></div>
          </header>
          <div class="route">
            <div class="route-label">来源</div>
            <div v-for="(source, index) in store.profile.sourceFolders" :key="`${source}-${index}`" class="path-row">
              <span class="path-icon"><AppIcon name="folder" :size="17" /></span>
              <span class="path-text"><b>{{ baseName(source) }}</b><code :title="source">{{ source }}</code></span>
              <span class="path-actions">
                <button class="icon-button" title="更换文件夹" :aria-label="`更换来源 ${baseName(source)}`" @click="replaceSource(index)"><AppIcon name="swap" :size="15" /></button>
                <button class="icon-button danger" title="移除" :aria-label="`移除来源 ${baseName(source)}`" @click="store.profile.sourceFolders.splice(index, 1)"><AppIcon name="close" :size="15" /></button>
              </span>
            </div>
            <button v-if="!store.profile.sourceFolders.length" class="path-row empty" @click="addSource">
              <span class="path-icon"><AppIcon name="plus" :size="17" /></span><span class="path-text"><b>添加要整理的文件夹</b><code>可以添加多个，扫描前会检查读取权限</code></span>
            </button>
            <div class="route-option">
              <span><b>包含子文件夹里的文件</b><small>{{ store.profile.includeSubfolders ? '会逐层查看所有子文件夹' : '只查看所选文件夹的第一层' }}</small></span>
              <SwitchToggle v-model="store.profile.includeSubfolders" label="包含子文件夹里的文件" />
            </div>
            <div class="route-label target">{{ fixedTarget ? '移到隔离区' : '整理到' }}</div>
            <div class="path-row target" :class="{ fixed: fixedTarget, error: targetInsideSource }">
              <span class="path-icon"><AppIcon :name="fixedTarget ? 'shield' : 'folder'" :size="17" /></span>
              <span class="path-text"><b>{{ targetName }}</b><code :title="targetPath">{{ targetPath }}</code></span>
              <span class="path-actions">
                <span v-if="fixedTarget" class="fixed-badge"><AppIcon name="lock" :size="13" />由应用管理</span>
                <button v-else class="button ghost small" @click="changeTarget"><AppIcon name="swap" :size="14" />更换</button>
              </span>
            </div>
          </div>
        </section>

        <TypeRulesEditor v-if="isByType" :key="store.profile.id" v-model:expanded="expandedRule" :issues="issues" :target-name="targetName" />

        <section v-else-if="store.profile.presetType === 'old-installers'" class="panel config-section">
          <header class="section-head"><div class="section-title"><h2>隔离条件</h2><p>只处理 dmg、pkg、exe、msi 等安装包</p></div></header>
          <div class="option-list">
            <div class="option-row">
              <span><b>多久没修改的安装包</b><small>按文件最后修改时间判断</small></span>
              <div class="segments compact" role="radiogroup" aria-label="未修改天数">
                <button v-for="days in [30, 60, 90, 180]" :key="days" role="radio" :aria-checked="params.olderThanDays === days" :class="{ active: params.olderThanDays === days }" @click="params.olderThanDays = days">{{ days }} 天</button>
              </div>
            </div>
            <div class="option-row">
              <span><b>同时包含 ZIP 压缩包</b><small>压缩包里可能有其他文件，默认关闭</small></span>
              <SwitchToggle :model-value="Boolean(params.includeArchives)" label="同时包含 ZIP 压缩包" @update:model-value="params.includeArchives = $event" />
            </div>
          </div>
        </section>

        <section v-else class="panel config-section">
          <header class="section-head"><div class="section-title"><h2>{{ store.profile.presetType === 'by-date' ? '归档方式' : '处理方式' }}</h2></div></header>
          <div v-if="store.profile.presetType === 'by-date'" class="banner quarantine inset"><AppIcon name="info" :size="16" />按文件修改日期归档。修改日期不一定等于照片的拍摄日期。</div>
          <div v-else class="banner undo inset"><AppIcon name="info" :size="16" />找到的重复文件不会自动处理。扫描后由你逐组选择保留哪一份，其余移到隔离区。</div>
        </section>
      </div>

      <aside class="config-aside">
        <section class="panel aside-card">
          <h3>整理后会是这样</h3>
          <div class="tree">
            <div class="tree-root"><AppIcon :name="fixedTarget ? 'shield' : 'folder'" :size="15" /><b>{{ targetName }}/</b></div>
            <template v-if="isByType">
              <button v-for="{ rule, index } in enabledRules" :key="rule.id" class="tree-node" :class="`tone-${index % 8}`" @click="focusRule(rule.id)">
                <i class="tone-dot" /><span>{{ rule.folderName || '…' }}/</span><small>{{ rule.extensions.length }} 种</small>
              </button>
              <div v-if="params.unmatchedAction !== 'keep'" class="tree-node muted"><i class="tone-dot" /><span>{{ params.otherFolder || '…' }}/</span><small>其余</small></div>
              <p v-else class="tree-note">未匹配的文件留在原处</p>
              <p v-if="!enabledRules.length && params.unmatchedAction === 'keep'" class="tree-note">还没有启用的分类</p>
            </template>
            <template v-else-if="store.profile.presetType === 'by-date'">
              <div class="tree-node"><i class="tone-dot" /><span>{{ now.getFullYear() }}年/</span></div>
              <div class="tree-node deep"><i class="tone-dot" /><span>{{ now.getMonth() + 1 }}月/</span></div>
            </template>
            <p v-else class="tree-note">每个文件都会记录原始位置，可以一键恢复</p>
          </div>
        </section>

        <section class="panel aside-card">
          <h3>扫描前检查<span v-if="blockers" class="count-badge fail">{{ blockers }}</span></h3>
          <ul class="checklist">
            <li :class="store.profile.sourceFolders.length ? 'ok' : 'fail'">
              <AppIcon :name="store.profile.sourceFolders.length ? 'check' : 'alert'" :size="14" />
              {{ store.profile.sourceFolders.length ? `已选择 ${store.profile.sourceFolders.length} 个来源文件夹` : '至少添加一个来源文件夹' }}
            </li>
            <li v-if="!fixedTarget" :class="targetInsideSource ? 'fail' : 'ok'">
              <AppIcon :name="targetInsideSource ? 'alert' : 'check'" :size="14" />{{ targetInsideSource ? '目标文件夹在来源里面，请更换' : '目标文件夹不在来源里面' }}
            </li>
            <template v-if="isByType">
              <li v-if="!issues.length" class="ok"><AppIcon name="check" :size="14" />分类规则没有冲突</li>
              <li v-for="(issue, index) in issues" :key="index" class="fail" :class="{ link: issue.ruleId }" @click="focusRule(issue.ruleId)">
                <AppIcon name="alert" :size="14" />
                <span><b v-if="issue.ruleId">{{ params.typeRules?.find((rule) => rule.id === issue.ruleId)?.name || '未命名分类' }}</b>{{ issue.message }}</span>
              </li>
            </template>
            <li v-for="(issue, index) in environmentIssues" :key="`env-${index}`" class="fail"><AppIcon name="alert" :size="14" /><span>{{ serverLabel(issue) }}</span></li>
          </ul>
        </section>

        <section class="panel aside-card subtle">
          <h3>自动跳过</h3>
          <p>还没下载完的文件、系统文件、软链接，以及无法安全读取的文件。</p>
        </section>
      </aside>
    </div>

    <footer class="action-bar config-actions">
      <button class="button secondary" @click="store.go('home')">← 返回首页</button>
      <span class="action-summary" :class="{ fail: blockers }">
        <template v-if="blockers"><AppIcon name="alert" :size="15" />还有 {{ blockers }} 个问题需要处理，处理后才能扫描</template>
        <template v-else><AppIcon name="check" :size="15" />{{ summary }}</template>
      </span>
      <button class="button primary" :disabled="validating || store.busy || blockers > 0" @click="scan">{{ validating ? '正在检查…' : '开始扫描' }}<AppIcon name="arrow" :size="16" /></button>
    </footer>
  </div>
</template>
