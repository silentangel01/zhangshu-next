import { describe, it, expect } from 'vitest'

import type { SettingItem, SettingItemType, SettingNodeKind } from '@/entities/setting/types'
import { settingItemTypeLabels } from '@/entities/setting/types'

function makeSetting(overrides: Partial<SettingItem> = {}): SettingItem {
  return {
    id: '1',
    project_id: 'p1',
    parent_id: null,
    title: 'Test',
    item_type: 'custom',
    canon_status: 'draft',
    summary: '',
    detail: '',
    tags: '',
    order_index: 0,
    importance: 'normal',
    node_kind: 'page',
    folder_key: null,
    folder_default_item_type: null,
    is_system: false,
    created_at: '',
    updated_at: '',
    deleted_at: null,
    version: 1,
    ...overrides,
  }
}

/**
 * Pure helper: should we prompt the user about type change when moving a page
 * to a target folder? Returns true if the target folder has a default type
 * that differs from the page's current type.
 */
function shouldConfirmTypeChange(page: SettingItem, targetFolder: SettingItem): boolean {
  if (targetFolder.node_kind !== 'folder') return false
  if (!targetFolder.folder_default_item_type) return false
  return targetFolder.folder_default_item_type !== page.item_type
}

describe('Setting types', () => {
  it('SettingItemType includes character', () => {
    const characterType: SettingItemType = 'character'
    expect(characterType).toBe('character')
    expect(settingItemTypeLabels[characterType]).toBe('人物')
  })

  it('SettingNodeKind has folder and page', () => {
    const folder: SettingNodeKind = 'folder'
    const page: SettingNodeKind = 'page'
    expect(folder).toBe('folder')
    expect(page).toBe('page')
  })

  it('settingItemTypeLabels covers all types including character', () => {
    const allTypes: SettingItemType[] = [
      'world',
      'location',
      'organization',
      'power_system',
      'history',
      'technology',
      'rule',
      'race',
      'object',
      'character',
      'custom',
    ]
    for (const t of allTypes) {
      expect(settingItemTypeLabels[t]).toBeDefined()
      expect(typeof settingItemTypeLabels[t]).toBe('string')
    }
  })
})

describe('Drag-and-drop type change confirmation', () => {
  it('should NOT confirm when types match', () => {
    const page = makeSetting({ item_type: 'character' })
    const folder = makeSetting({
      node_kind: 'folder',
      folder_default_item_type: 'character',
    })
    expect(shouldConfirmTypeChange(page, folder)).toBe(false)
  })

  it('should confirm when types differ', () => {
    const page = makeSetting({ item_type: 'character' })
    const folder = makeSetting({
      node_kind: 'folder',
      folder_default_item_type: 'world',
    })
    expect(shouldConfirmTypeChange(page, folder)).toBe(true)
  })

  it('should NOT confirm when target folder has no default type', () => {
    const page = makeSetting({ item_type: 'character' })
    const folder = makeSetting({
      node_kind: 'folder',
      folder_default_item_type: null,
    })
    expect(shouldConfirmTypeChange(page, folder)).toBe(false)
  })

  it('should NOT confirm when target is not a folder', () => {
    const page = makeSetting({ item_type: 'character' })
    const notFolder = makeSetting({ node_kind: 'page' })
    expect(shouldConfirmTypeChange(page, notFolder)).toBe(false)
  })
})
