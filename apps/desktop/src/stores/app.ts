import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../api'
import type { HistoryDetail, HistoryRun, Plan, Preset, PresetType, Profile, QuarantineItem, RunResult, UndoPreview, ViewName } from '../types'

const categories = ['documents', 'images', 'videos', 'audio', 'archives', 'installers', 'other']

function makeProfile(preset: PresetType): Profile {
  const names: Record<PresetType, string> = {
    'by-type': '下载文件夹按类型整理',
    'by-date': '图片按日期归档',
    'old-installers': '旧安装包清理',
    duplicates: '重复文件查找',
  }
  return {
    id: crypto.randomUUID(), name: names[preset], presetType: preset,
    sourceFolders: ['~/Downloads'], targetFolder: '~/Documents/整理',
    includeSubfolders: preset === 'duplicates', schemaVersion: 1,
    parameters: {
      categories: [...categories], olderThanDays: 90,
      includeArchives: false, minimumBytes: 1024 * 1024,
    },
  }
}

export const useAppStore = defineStore('app', () => {
  const view = ref<ViewName>('home')
  const presets = ref<Preset[]>([])
  const profile = ref<Profile>(makeProfile('by-type'))
  const plan = ref<Plan>()
  const result = ref<RunResult>()
  const undoPreview = ref<UndoPreview>()
  const history = ref<HistoryRun[]>([])
  const historyDetail = ref<HistoryDetail>()
  const quarantine = ref<QuarantineItem[]>([])
  const engineReady = ref(false)
  const error = ref<string>()
  const scanChecked = ref(0)
  const scanPath = ref('')
  const runCompleted = ref(0)
  const runCurrent = ref('')
  const busy = ref(false)
  const theme = ref<'system' | 'light' | 'dark'>('system')

  const selectedItems = computed(() => plan.value?.items.filter((item) => item.selected) ?? [])
  const selectedBytes = computed(() => selectedItems.value.reduce((sum, item) => sum + item.size, 0))

  function go(next: ViewName) {
    view.value = next
  }

  function choosePreset(id: PresetType) {
    profile.value = makeProfile(id)
    view.value = 'config'
  }

  async function initialize() {
    api.onEvent(({ event, payload }) => {
      if (event === 'plan.progress') {
        scanChecked.value = Number(payload.checked ?? payload.hashed ?? scanChecked.value)
        scanPath.value = String(payload.path ?? scanPath.value)
      }
      if (event === 'run.item') {
        runCompleted.value = Number(payload.index ?? runCompleted.value)
        const item = payload.item as Record<string, unknown> | undefined
        runCurrent.value = String(item?.sourcePath ?? item?.source_path ?? '')
      }
    })
    try {
      const [initial, loadedPresets] = await Promise.all([
        api.request<{ firstLaunch: boolean }>('app.initialize'),
        api.request<Preset[]>('preset.list'),
      ])
      presets.value = loadedPresets
      engineReady.value = true
      await refreshCollections()
      if (initial.firstLaunch && !history.value.length) view.value = 'onboarding'
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : String(caught)
    }
  }

  async function validateProfile() {
    return api.request<{ valid: boolean; issues: Array<Record<string, unknown>> }>('profile.validate', { profile: profile.value })
  }

  async function createPlan() {
    busy.value = true
    error.value = undefined
    scanChecked.value = 0
    scanPath.value = profile.value.sourceFolders[0] ?? ''
    view.value = 'scan'
    try {
      plan.value = await api.request<Plan>('plan.create', { profile: profile.value })
      view.value = profile.value.presetType === 'duplicates' ? 'duplicates' : 'preview'
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : String(caught)
      view.value = 'config'
    } finally {
      busy.value = false
    }
  }

  async function persistSelection() {
    if (!plan.value) return
    plan.value = await api.request<Plan>('plan.excludeItems', {
      planId: plan.value.planId,
      selectedItemIds: selectedItems.value.map((item) => item.itemId),
    })
  }

  function toggleItem(itemId: string) {
    const item = plan.value?.items.find((candidate) => candidate.itemId === itemId)
    if (!item || item.status === 'skipped') return
    item.selected = !item.selected
  }

  function selectDuplicateKeep(groupId: string, keepId: string) {
    plan.value?.items.filter((item) => item.groupId === groupId).forEach((item) => {
      item.selected = item.itemId !== keepId
      item.metadata.decision = item.itemId === keepId ? 'keep' : 'quarantine'
    })
  }

  async function executePlan() {
    if (!plan.value) return
    await persistSelection()
    busy.value = true
    runCompleted.value = 0
    runCurrent.value = ''
    view.value = 'executing'
    try {
      result.value = await api.request<RunResult>('run.execute', { planId: plan.value.planId })
      view.value = 'result'
      await refreshCollections()
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : String(caught)
      view.value = 'preview'
    } finally {
      busy.value = false
    }
  }

  async function cancelRun() {
    await api.request('run.cancel')
  }

  async function cancelScan() {
    await api.request('plan.cancel')
    view.value = 'config'
  }

  async function refreshCollections() {
    try {
      const [runs, items] = await Promise.all([
        api.request<HistoryRun[]>('history.list', { limit: 50 }),
        api.request<QuarantineItem[]>('quarantine.list'),
      ])
      history.value = runs
      quarantine.value = items
    } catch {
      // Demo and early engine builds may not expose every collection yet.
    }
  }

  async function completeOnboarding() {
    await api.request('settings.update', { values: { onboardingCompleted: true } })
    view.value = 'home'
  }

  async function prepareUndo(runId: string) {
    busy.value = true
    error.value = undefined
    try {
      undoPreview.value = await api.request<UndoPreview>('history.undoPlan', { runId })
      view.value = 'undo'
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : String(caught)
    } finally {
      busy.value = false
    }
  }

  async function loadHistoryDetail(runId: string) {
    try {
      historyDetail.value = await api.request<HistoryDetail>('history.detail', { runId })
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : String(caught)
    }
  }

  async function executeUndo(operationIds: string[]) {
    if (!undoPreview.value) return
    busy.value = true
    error.value = undefined
    try {
      await api.request('history.undo', { runId: undoPreview.value.runId, operationIds })
      await refreshCollections()
      view.value = 'history'
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : String(caught)
    } finally {
      busy.value = false
    }
  }

  async function restoreQuarantine(quarantineIds: string[], destinationFolder?: string) {
    await api.request('quarantine.restore', { quarantineIds, destinationFolder })
    await refreshCollections()
  }

  async function trashQuarantine(quarantineIds: string[]) {
    await api.request('quarantine.moveToTrash', { quarantineIds })
    await refreshCollections()
  }

  return {
    view, presets, profile, plan, result, undoPreview, history, historyDetail, quarantine, engineReady, error,
    scanChecked, scanPath, runCompleted, runCurrent, busy, theme,
    selectedItems, selectedBytes,
    go, choosePreset, initialize, validateProfile, createPlan, toggleItem,
    selectDuplicateKeep, persistSelection, executePlan, cancelRun, cancelScan,
    refreshCollections, completeOnboarding, prepareUndo, loadHistoryDetail, executeUndo,
    restoreQuarantine, trashQuarantine,
  }
})
