import { describe, expect, it } from 'vitest'

import type { OutlineItem } from '@/entities/outline/types'
import { buildOutlineTree, buildReorderPayload, isDescendant } from '@/features/outlines/outlineDrag'

function makeItem(overrides: Partial<OutlineItem>): OutlineItem {
  return {
    id: '',
    project_id: 'p1',
    parent_id: null,
    volume_id: null,
    chapter_id: null,
    title: '',
    content: '',
    item_type: 'note',
    status: 'planned',
    order_index: 0,
    importance: 'normal',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    deleted_at: null,
    version: 1,
    ...overrides,
  }
}

describe('buildOutlineTree', () => {
  it('builds a flat list of roots', () => {
    const items = [
      makeItem({ id: 'a', title: 'A', order_index: 0 }),
      makeItem({ id: 'b', title: 'B', order_index: 1 }),
    ]
    const tree = buildOutlineTree(items)
    expect(tree).toHaveLength(2)
    expect(tree[0]?.item.id).toBe('a')
    expect(tree[1]?.item.id).toBe('b')
  })

  it('nests children under parents', () => {
    const items = [
      makeItem({ id: 'parent', title: 'Parent', order_index: 0 }),
      makeItem({ id: 'child', title: 'Child', parent_id: 'parent', order_index: 0 }),
    ]
    const tree = buildOutlineTree(items)
    expect(tree).toHaveLength(1)
    expect(tree[0]?.children).toHaveLength(1)
    expect(tree[0]?.children[0]?.item.id).toBe('child')
  })
})

describe('isDescendant', () => {
  it('detects direct child', () => {
    const items = [
      makeItem({ id: 'a', title: 'A' }),
      makeItem({ id: 'b', title: 'B', parent_id: 'a' }),
    ]
    expect(isDescendant('b', 'a', items)).toBe(true)
  })

  it('detects grandchild', () => {
    const items = [
      makeItem({ id: 'a', title: 'A' }),
      makeItem({ id: 'b', title: 'B', parent_id: 'a' }),
      makeItem({ id: 'c', title: 'C', parent_id: 'b' }),
    ]
    expect(isDescendant('c', 'a', items)).toBe(true)
  })

  it('returns false for non-descendant', () => {
    const items = [
      makeItem({ id: 'a', title: 'A' }),
      makeItem({ id: 'b', title: 'B' }),
    ]
    expect(isDescendant('b', 'a', items)).toBe(false)
  })
})

describe('buildReorderPayload', () => {
  const items = [
    makeItem({ id: 'a', title: 'A', order_index: 0 }),
    makeItem({ id: 'b', title: 'B', order_index: 1 }),
    makeItem({ id: 'c', title: 'C', order_index: 2 }),
  ]

  it('moves item before another', () => {
    const result = buildReorderPayload('c', { targetId: 'a', position: 'before' }, items)
    expect(result).not.toBeNull()
    expect(result![0]?.outline_id).toBe('c')
    expect(result![0]?.order_index).toBe(0)
  })

  it('moves item after another', () => {
    const result = buildReorderPayload('a', { targetId: 'c', position: 'after' }, items)
    expect(result).not.toBeNull()
    const aItem = result!.find((r) => r.outline_id === 'a')
    expect(aItem?.order_index).toBe(2)
  })

  it('moves item inside another', () => {
    const result = buildReorderPayload('b', { targetId: 'a', position: 'inside' }, items)
    expect(result).not.toBeNull()
    expect(result![0]?.parent_id).toBe('a')
  })

  it('rejects moving into own descendant', () => {
    const itemsWithChild = [
      ...items,
      makeItem({ id: 'd', title: 'D', parent_id: 'b', order_index: 0 }),
    ]
    const result = buildReorderPayload('b', { targetId: 'd', position: 'inside' }, itemsWithChild)
    expect(result).toBeNull()
  })

  it('rejects moving into self', () => {
    const result = buildReorderPayload('a', { targetId: 'a', position: 'inside' }, items)
    expect(result).toBeNull()
  })
})
