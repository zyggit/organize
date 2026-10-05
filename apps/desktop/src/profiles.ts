import type { Profile, TypeRule } from './types'

const rule = (id: string, name: string, extensions: string): TypeRule => ({
  id, name, folderName: name, extensions: extensions.split(' '), enabled: true,
})
export function classificationTemplate(template = 'standard'): TypeRule[] {
  if (template === 'office') return [
    rule('text', '文稿', 'doc docx txt md'), rule('pdf', 'PDF资料', 'pdf'),
    rule('sheets', '表格', 'xls xlsx csv'), rule('slides', '演示文稿', 'ppt pptx'),
  ]
  if (template === 'media') return [
    rule('photos', '照片', 'jpg jpeg heic tif tiff'), rule('graphics', '图像素材', 'png gif webp svg psd ai'),
    rule('videos', '视频', 'mp4 mov mkv avi webm m4v'), rule('audio', '音频', 'mp3 m4a wav flac aac ogg'),
  ]
  return [rule('documents', '文档', 'pdf doc docx xls xlsx ppt pptx txt md csv'),
    rule('images', '图片', 'jpg jpeg png gif webp heic tif tiff'),
    rule('videos', '视频', 'mp4 mov mkv avi webm m4v'), rule('audio', '音频', 'mp3 m4a wav flac aac ogg'),
    rule('archives', '压缩包', 'zip 7z rar tar gz bz2 xz'), rule('installers', '安装包', 'exe msi msix dmg pkg')]
}

export const CLASSIFICATION_TEMPLATES = [
  { id: 'standard', name: '通用分类', description: '文档、图片、视频、音频、压缩包、安装包' },
  { id: 'office', name: '办公资料', description: '文稿、PDF、表格、演示文稿分开存放' },
  { id: 'media', name: '媒体素材', description: '照片、图像素材、视频、音频' },
] as const

export function ensureClassification(profile: Profile) {
  if (!profile.parameters.typeRules) {
    profile.parameters.typeRules = classificationTemplate().map((rule) => ({ ...rule,
      enabled: !profile.parameters.categories || profile.parameters.categories.includes(rule.id),
    }))
    profile.parameters.unmatchedAction = !profile.parameters.categories || profile.parameters.categories.includes('other') ? 'other' : 'keep'
    profile.parameters.otherFolder = '其他文件'
  }
}

export function parseExtensions(value: string): string[] {
  return value.split(/[\s,，、;；]+/).map((part) => part.replace(/^\.+/, '').toLowerCase()).filter(Boolean)
}

export function newRuleName(rules: TypeRule[]): string {
  const names = new Set(rules.map((item) => item.name))
  if (!names.has('新分类')) return '新分类'
  let index = 2
  while (names.has(`新分类 ${index}`)) index++
  return `新分类 ${index}`
}

// Mirrors engine/src/organize_gui/profiles.py so problems show while editing, before profile.validate.
export function validFolderName(value: unknown): boolean {
  return typeof value === 'string'
    && Boolean(value.trim())
    && !['.', '..'].includes(value.trim())
    && value.length <= 120
    && !/[/\\<>:"|?*\u0000-\u001f]/.test(value)
    && !/[. ]$/.test(value)
}

const EXTENSION = /^[a-z0-9][a-z0-9_+-]*$/

export function validExtension(value: string): boolean {
  return EXTENSION.test(value)
}

export interface RuleIssue {
  ruleId?: string
  field: 'name' | 'folder' | 'extensions' | 'other' | 'rules'
  message: string
}

/** Extension → names of the enabled rules that claim it, in rule order. */
export function extensionOwners(rules: TypeRule[]): Map<string, string[]> {
  const owners = new Map<string, string[]>()
  for (const item of rules) {
    if (!item.enabled) continue
    for (const extension of new Set(item.extensions)) owners.set(extension, [...(owners.get(extension) ?? []), item.name || '未命名分类'])
  }
  return owners
}

export function ruleIssues(profile: Profile): RuleIssue[] {
  const rules = profile.parameters.typeRules ?? []
  const issues: RuleIssue[] = []
  const claimed = new Map<string, string>()
  for (const item of rules) {
    if (!item.enabled) continue
    if (!item.name.trim()) issues.push({ ruleId: item.id, field: 'name', message: '分类名称不能为空' })
    if (!validFolderName(item.folderName)) issues.push({ ruleId: item.id, field: 'folder', message: '子文件夹名称不能为空，也不能包含 / \\ : * ? " < > |' })
    if (!item.extensions.length) issues.push({ ruleId: item.id, field: 'extensions', message: '至少添加一个扩展名' })
    for (const extension of item.extensions) {
      if (!validExtension(extension)) issues.push({ ruleId: item.id, field: 'extensions', message: `“${extension}”不是有效的扩展名` })
      else if (claimed.has(extension)) issues.push({ ruleId: item.id, field: 'extensions', message: `“${extension}”已属于“${claimed.get(extension)}”` })
      else claimed.set(extension, item.name || '未命名分类')
    }
  }
  const unmatched = profile.parameters.unmatchedAction ?? 'other'
  if (unmatched === 'other' && !validFolderName(profile.parameters.otherFolder)) issues.push({ field: 'other', message: '其他文件夹名称不合法' })
  if (!rules.some((item) => item.enabled) && unmatched !== 'other') issues.push({ field: 'rules', message: '至少启用一个分类，或把未匹配的文件归入其他文件夹' })
  return issues
}

/** JSON with sorted keys, so a profile round-tripped through the engine compares equal. */
export function stableStringify(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().filter((key) => (value as Record<string, unknown>)[key] !== undefined)
      .map((key) => `${JSON.stringify(key)}:${stableStringify((value as Record<string, unknown>)[key])}`).join(',')}}`
  }
  return JSON.stringify(value)
}
