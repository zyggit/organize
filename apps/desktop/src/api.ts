import type { EngineEvent, Plan, PlanItem, Preset, Profile, RunResult } from './types'

type EventHandler = (event: EngineEvent) => void

function camelPlan(raw: any): Plan {
  const item = (value: any): PlanItem => ({
    itemId: value.itemId ?? value.item_id,
    sequence: value.sequence ?? value.seq,
    groupId: value.groupId ?? value.group_id,
    operation: value.operation,
    sourcePath: value.sourcePath ?? value.source_path,
    targetPath: value.targetPath ?? value.target_path,
    size: value.size,
    selected: Boolean(value.selected),
    status: value.status,
    warningCode: value.warningCode ?? value.warning_code,
    reason: value.reason,
    metadata: value.metadata ?? {},
  })
  return {
    planId: raw.planId ?? raw.plan_id,
    status: raw.status,
    createdAt: raw.createdAt ?? raw.created_at,
    expiresAt: raw.expiresAt ?? raw.expires_at,
    profile: raw.profile,
    summary: raw.summary,
    items: (raw.items ?? []).map(item),
  }
}

const sampleFiles = [
  ['2026 年度预算.xlsx', '文档', 1_240_000],
  ['合同扫描件（盖章版）.pdf', '文档', 4_800_000],
  ['报价单.pdf', '文档', 312_000],
  ['会议纪要 10-02.docx', '文档', 86_000],
  ['IMG_2041.HEIC', '图片', 8_420_000],
  ['发布会录屏.mp4', '视频', 612_000_000],
  ['素材包.zip', '压缩包', 42_000_000],
]

class DemoApi {
  private handlers = new Set<EventHandler>()
  private plan?: Plan
  private history: any[] = []
  private quarantine: any[] = []
  private profiles: Profile[] = []
  private settings = { theme: 'system', retentionDays: 30, historyLimit: 200, redactPaths: true, notifyOnComplete: true, onboardingCompleted: false, defaultTargetFolder: '~/Documents/整理', quarantineFolder: '应用数据/quarantine' }

  onEvent(handler: EventHandler) {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }

  private emit(event: string, payload: Record<string, unknown>) {
    this.handlers.forEach((handler) => handler({ event, payload }))
  }

  async request<T>(method: string, params: Record<string, unknown> = {}): Promise<T> {
    if (method === 'app.initialize') {
      return { engineVersion: '0.1.0-demo', firstLaunch: !this.settings.onboardingCompleted, dataDir: '应用数据/organize-gui', recoverableRuns: this.history.length, quarantineCount: this.quarantine.length } as T
    }
    if (method === 'app.version') return { engine: '0.2.0-demo', organize: '3.3.0' } as T
    if (method === 'preset.list') {
      return [
        { id: 'by-type', name: '文件按类型整理', description: '自选文件夹和分类规则，文档、图片各归一处。', operation: 'move' },
        { id: 'by-date', name: '图片按日期归档', description: '按年和月整理照片与截图。', operation: 'move' },
        { id: 'old-installers', name: '旧安装包清理', description: '腾出被旧安装包占用的空间。', operation: 'quarantine' },
        { id: 'duplicates', name: '重复文件查找', description: '内容逐字节相同才算重复。', operation: 'quarantine' },
      ] as T
    }
    if (method === 'profile.validate') return { valid: true, issues: [] } as T
    if (method === 'profile.list') return this.profiles as T
    if (method === 'profile.save') {
      const profile = JSON.parse(JSON.stringify(params.profile)) as Profile
      this.profiles = [profile, ...this.profiles.filter((item) => item.id !== profile.id)]
      return profile as T
    }
    if (method === 'profile.delete') { this.profiles = this.profiles.filter((item) => item.id !== params.profileId); return { deleted: true } as T }
    if (method === 'plan.create') {
      const profile = params.profile as Profile
      for (let checked = 320; checked <= 1920; checked += 320) {
        await new Promise((resolve) => setTimeout(resolve, 90))
        this.emit('plan.progress', { checked, path: `${profile.sourceFolders[0]}/示例文件-${checked}.pdf` })
      }
      const items: PlanItem[] = sampleFiles.map(([name, folder, size], index) => ({
        itemId: `demo-${index}`,
        sequence: index,
        operation: profile.presetType === 'old-installers' || profile.presetType === 'duplicates' ? 'quarantine' : 'move',
        sourcePath: `${profile.sourceFolders[0]}/${name}`,
        targetPath: `${profile.targetFolder}/${folder}/${index === 2 ? '报价单 2.pdf' : name}`,
        size: Number(size),
        selected: profile.presetType !== 'duplicates',
        status: 'planned',
        warningCode: index === 2 ? 'TARGET_CONFLICT' : null,
        reason: null,
        groupId: profile.presetType === 'duplicates' ? `group-${Math.floor(index / 2)}` : null,
        metadata: profile.presetType === 'duplicates' ? { recommendedKeep: index % 2 === 0, decision: 'undecided' } : {},
      }))
      this.plan = {
        planId: crypto.randomUUID(), status: 'ready', createdAt: new Date().toISOString(),
        expiresAt: new Date(Date.now() + 30 * 60_000).toISOString(), profile,
        summary: {
          total: items.length, selected: items.filter((x) => x.selected).length,
          selectedBytes: items.filter((x) => x.selected).reduce((n, x) => n + x.size, 0),
          move: items.filter((x) => x.selected && x.operation === 'move').length,
          quarantine: items.filter((x) => x.selected && x.operation === 'quarantine').length,
          skip: 0, conflict: 1, groups: profile.presetType === 'duplicates' ? 4 : 0,
        }, items,
      }
      this.emit('plan.completed', { planId: this.plan.planId, summary: this.plan.summary })
      return this.plan as T
    }
    if (method === 'plan.excludeItems') {
      const selected = new Set(params.selectedItemIds as string[])
      this.plan!.items.forEach((item) => { item.selected = selected.has(item.itemId) })
      this.plan!.summary.selected = selected.size
      this.plan!.summary.selectedBytes = this.plan!.items.filter((x) => x.selected).reduce((n, x) => n + x.size, 0)
      return this.plan as T
    }
    if (method === 'run.execute') {
      const selected = this.plan!.items.filter((item) => item.selected)
      for (let index = 0; index < selected.length; index++) {
        await new Promise((resolve) => setTimeout(resolve, 180))
        this.emit('run.item', { status: 'applied', index: index + 1, total: selected.length, item: selected[index] })
      }
      const result: RunResult = {
        runId: crypto.randomUUID(), planId: this.plan!.planId, status: 'completed',
        total: selected.length, success: selected.length, skipped: 0, failed: 0,
        successBytes: selected.reduce((sum, item) => sum + item.size, 0),
        endedAt: new Date().toISOString(),
      }
      this.history.unshift({ ...result, undoable_count: selected.length, run_id: result.runId, plan_id: result.planId, profile: this.plan!.profile, started_at: new Date().toISOString() })
      if (this.plan!.profile.presetType === 'old-installers' || this.plan!.profile.presetType === 'duplicates') {
        this.quarantine.unshift(...selected.map((item) => ({
          quarantine_id: `q-${item.itemId}`, operation_id: item.itemId,
          original_path: item.sourcePath, quarantine_path: item.targetPath,
          reason: item.reason ?? '按方案进入隔离区', size: item.size,
          quarantined_at: new Date().toISOString(), retention_until: new Date(Date.now() + 30 * 86400_000).toISOString(), status: 'active',
        })))
      }
      this.emit('run.completed', { result })
      return result as T
    }
    if (method === 'run.cancel' || method === 'plan.cancel') return { accepted: true } as T
    if (method === 'history.list') return this.history as T
    if (method === 'history.detail') {
      const run = this.history.find((item) => item.run_id === params.runId)
      return { ...run, operations: (this.plan?.items ?? []).filter((item) => item.selected).map((item) => ({
        operation_id: item.itemId, operation: item.operation, source_path: item.sourcePath,
        target_path: item.targetPath, state: 'applied', error_code: null, error_detail: null,
      })) } as T
    }
    if (method === 'history.undoPlan') {
      return { runId: params.runId, items: (this.plan?.items ?? []).filter((item) => item.selected).map((item) => ({ operationId: item.itemId, currentPath: item.targetPath, restorePath: item.sourcePath, size: item.size, state: 'ready', selected: true })) } as T
    }
    if (method === 'history.undo') return { runId: params.runId, restored: (params.operationIds as string[]).length, failed: 0 } as T
    if (method === 'quarantine.list') return this.quarantine as T
    if (method === 'quarantine.restore' || method === 'quarantine.moveToTrash') {
      const ids = new Set(params.quarantineIds as string[])
      this.quarantine = this.quarantine.filter((item) => !ids.has(item.quarantine_id))
      return { requested: ids.size, restored: ids.size, moved: ids.size, failed: 0 } as T
    }
    if (method === 'settings.get') return this.settings as T
    if (method === 'settings.update') {
      this.settings = { ...this.settings, ...(params.values as typeof this.settings) }
      return this.settings as T
    }
    if (method === 'diagnostics.export') return { path: params.destination, size: 2048 } as T
    throw new Error(`Demo API 尚未实现：${method}`)
  }
}

class TauriApi {
  private handlers = new Set<EventHandler>()
  private listening = false

  onEvent(handler: EventHandler) {
    this.handlers.add(handler)
    void this.ensureListener()
    return () => this.handlers.delete(handler)
  }

  private async ensureListener() {
    if (this.listening) return
    this.listening = true
    const { listen } = await import('@tauri-apps/api/event')
    await listen<EngineEvent>('engine-event', ({ payload }) => {
      this.handlers.forEach((handler) => handler(payload))
    })
  }

  async request<T>(method: string, params: Record<string, unknown> = {}): Promise<T> {
    const { invoke } = await import('@tauri-apps/api/core')
    try {
      const raw = await invoke<any>('engine_request', { method, params })
      if (method === 'plan.create' || method === 'plan.get' || method === 'plan.excludeItems') return camelPlan(raw) as T
      return raw as T
    } catch (caught) {
      if (caught && typeof caught === 'object') {
        const value = caught as Record<string, unknown>
        throw new Error(`${String(value.message ?? '整理引擎请求失败')} (${String(value.code ?? 'UNKNOWN')})`)
      }
      throw caught
    }
  }
}

export interface AppApi {
  request<T>(method: string, params?: Record<string, unknown>): Promise<T>
  onEvent(handler: EventHandler): () => void
}

const isTauri = '__TAURI_INTERNALS__' in window
export const api: AppApi = isTauri ? new TauriApi() : new DemoApi()

export async function pickDirectories(multiple = false): Promise<string[]> {
  if (isTauri) {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const result = await open({ directory: true, multiple })
    if (!result) return []
    return Array.isArray(result) ? result : [result]
  }
  const value = window.prompt(multiple ? '输入文件夹路径（多个路径用逗号分隔）' : '输入文件夹路径')
  return value ? value.split(',').map((item) => item.trim()).filter(Boolean) : []
}

export async function pickDiagnosticPath(): Promise<string | undefined> {
  if (isTauri) {
    const { save } = await import('@tauri-apps/plugin-dialog')
    return await save({
      defaultPath: `organize-diagnostics-${new Date().toISOString().slice(0, 10)}.zip`,
      filters: [{ name: 'ZIP 压缩包', extensions: ['zip'] }],
    }) ?? undefined
  }
  return '/tmp/organize-diagnostics.zip'
}

export async function revealLocalPath(path: string): Promise<void> {
  if (!isTauri) return
  const { invoke } = await import('@tauri-apps/api/core')
  await invoke('reveal_path', { path })
}

export async function notifyCompletion(result: RunResult): Promise<void> {
  if (!isTauri) return
  const { isPermissionGranted, sendNotification } = await import('@tauri-apps/plugin-notification')
  if (!await isPermissionGranted()) throw new Error('系统通知未授权')
  sendNotification({ title: 'Organize · 整理结束', body: `${result.success} 个完成，${result.skipped} 个跳过，${result.failed} 个失败。` })
}

export async function requestNotificationPermission(): Promise<boolean> {
  if (!isTauri) return true
  const { isPermissionGranted, requestPermission } = await import('@tauri-apps/plugin-notification')
  return await isPermissionGranted() || await requestPermission() === 'granted'
}

export async function openLegalResource(resource: 'licenses' | 'mpl-sources'): Promise<boolean> {
  if (!isTauri) return false
  const { invoke } = await import('@tauri-apps/api/core')
  await invoke('open_legal_resource', { resource })
  return true
}
