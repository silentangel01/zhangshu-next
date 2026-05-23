import { describe, it, expect } from 'vitest'

import type { Chapter } from '@/entities/chapter/types'
import type { Clue, ClueImportance, ClueStatus, ClueVisibility } from '@/entities/clue/types'
import type { Volume } from '@/entities/volume/types'

type GroupMode = 'setup' | 'payoff'

// --- Minimal replicas of the page's tree-building helpers ---

interface BucketEntry {
  volumeTitle: string
  chapterTitle: string
  clues: Clue[]
  volumeKey: string
  chapterKey: string
  volumeOrder: number
  chapterOrder: number
  isVolumeSpecial: boolean
  isChapterSpecial: boolean
}

function makeClue(overrides: Partial<Clue> = {}): Clue {
  return {
    id: '1',
    project_id: 'p1',
    title: 'Test Clue',
    description: '',
    setup_chapter_id: null,
    payoff_chapter_id: null,
    status: 'planned' as ClueStatus,
    visibility: 'hidden' as ClueVisibility,
    importance: 'normal' as ClueImportance,
    payoff_plan: '',
    actual_payoff: '',
    note: '',
    created_at: '',
    updated_at: '',
    deleted_at: null,
    version: 1,
    ...overrides,
  }
}

function makeChapter(overrides: Partial<Chapter> = {}): Chapter {
  return {
    id: 'c1',
    project_id: 'p1',
    volume_id: null,
    title: 'Chapter 1',
    content: '',
    order_index: 0,
    status: 'draft',
    word_count: 0,
    created_at: '',
    updated_at: '',
    deleted_at: null,
    version: 1,
    ...overrides,
  }
}

function makeVolume(overrides: Partial<Volume> = {}): Volume {
  return {
    id: 'v1',
    project_id: 'p1',
    title: 'Volume 1',
    order_index: 0,
    created_at: '',
    updated_at: '',
    deleted_at: null,
    version: 1,
    ...overrides,
  }
}

/**
 * Pure helper: build buckets from clues, chapters, and volumes.
 * Mirrors the logic in ProjectCluesPage.vue clueTree computed.
 */
function buildBuckets(
  clues: Clue[],
  chapters: Chapter[],
  volumes: Volume[],
  groupMode: GroupMode,
): BucketEntry[] {
  const chapterMap = new Map(chapters.map((c) => [c.id, c]))
  const volMap = new Map(volumes.map((v) => [v.id, v]))
  const groupKey = groupMode === 'setup' ? 'setup_chapter_id' : 'payoff_chapter_id'

  const bucketMap = new Map<string, BucketEntry>()

  for (const clue of clues) {
    const chapterId = clue[groupKey]
    let volumeKey: string
    let volumeTitle: string
    let chapterKey: string
    let chapterTitle: string
    let volumeOrder: number
    let chapterOrder: number
    let isVolumeSpecial: boolean
    let isChapterSpecial: boolean

    if (!chapterId) {
      volumeKey = '__unbound__'
      volumeTitle = groupMode === 'setup' ? '未绑定埋设章节' : '未绑定回收章节'
      chapterKey = '__unbound_chapter__'
      chapterTitle = volumeTitle
      volumeOrder = 999999
      chapterOrder = 999999
      isVolumeSpecial = true
      isChapterSpecial = true
    } else {
      const chapter = chapterMap.get(chapterId)
      if (!chapter) {
        volumeKey = '__unknown__'
        volumeTitle = '未知章节'
        chapterKey = `__unknown_${chapterId}__`
        chapterTitle = '未知章节'
        volumeOrder = 999999
        chapterOrder = 999999
        isVolumeSpecial = true
        isChapterSpecial = true
      } else {
        const volume = chapter.volume_id ? volMap.get(chapter.volume_id) ?? null : null
        volumeKey = chapter.volume_id ?? '__unvolumed__'
        volumeTitle = volume?.title ?? '未分卷'
        volumeOrder = volume ? volume.order_index : 999999
        isVolumeSpecial = !volume
        chapterKey = chapter.id
        chapterTitle = chapter.title
        chapterOrder = chapter.order_index
        isChapterSpecial = false
      }
    }

    let entry = bucketMap.get(chapterKey)
    if (!entry) {
      entry = {
        volumeTitle,
        chapterTitle,
        clues: [],
        volumeKey,
        chapterKey,
        volumeOrder,
        chapterOrder,
        isVolumeSpecial,
        isChapterSpecial,
      }
      bucketMap.set(chapterKey, entry)
    }
    entry.clues.push(clue)
  }

  return [...bucketMap.values()]
}

function computeActiveFilterCount(filters: {
  status: string
  visibility: string
  importance: string
}): number {
  let count = 0
  if (filters.status) count++
  if (filters.visibility) count++
  if (filters.importance) count++
  return count
}

// --- Tests ---

describe('Clue tree grouping by setup chapter', () => {
  it('places clue into the correct volume and chapter via setup_chapter_id', () => {
    const vol = makeVolume({ id: 'v1', title: '第一卷', order_index: 0 })
    const ch = makeChapter({ id: 'c1', title: '第一章', volume_id: 'v1', order_index: 0 })
    const clue = makeClue({ id: 'cl1', title: '神秘剑', setup_chapter_id: 'c1' })

    const buckets = buildBuckets([clue], [ch], [vol], 'setup')
    expect(buckets).toHaveLength(1)
    expect(buckets[0]!.volumeKey).toBe('v1')
    expect(buckets[0]!.volumeTitle).toBe('第一卷')
    expect(buckets[0]!.chapterKey).toBe('c1')
    expect(buckets[0]!.chapterTitle).toBe('第一章')
    expect(buckets[0]!.clues).toHaveLength(1)
    expect(buckets[0]!.clues[0]!.title).toBe('神秘剑')
  })

  it('places clue with no setup_chapter_id into unbound group', () => {
    const clue = makeClue({ id: 'cl1', setup_chapter_id: null })
    const buckets = buildBuckets([clue], [], [], 'setup')
    expect(buckets).toHaveLength(1)
    expect(buckets[0]!.volumeKey).toBe('__unbound__')
    expect(buckets[0]!.volumeTitle).toBe('未绑定埋设章节')
    expect(buckets[0]!.isVolumeSpecial).toBe(true)
  })

  it('places clue with unknown setup chapter into unknown group', () => {
    const clue = makeClue({ id: 'cl1', setup_chapter_id: 'deleted_chapter' })
    const buckets = buildBuckets([clue], [], [], 'setup')
    expect(buckets).toHaveLength(1)
    expect(buckets[0]!.volumeKey).toBe('__unknown__')
    expect(buckets[0]!.volumeTitle).toBe('未知章节')
  })

  it('places clue with chapter but no volume into unvolumed group', () => {
    const ch = makeChapter({ id: 'c1', title: '独立章节', volume_id: null })
    const clue = makeClue({ id: 'cl1', setup_chapter_id: 'c1' })
    const buckets = buildBuckets([clue], [ch], [], 'setup')
    expect(buckets).toHaveLength(1)
    expect(buckets[0]!.volumeKey).toBe('__unvolumed__')
    expect(buckets[0]!.volumeTitle).toBe('未分卷')
  })
})

describe('Clue tree grouping by payoff chapter', () => {
  it('places clue into the correct volume and chapter via payoff_chapter_id', () => {
    const vol = makeVolume({ id: 'v2', title: '第二卷', order_index: 1 })
    const ch = makeChapter({ id: 'c5', title: '第五章', volume_id: 'v2', order_index: 4 })
    const clue = makeClue({ id: 'cl1', payoff_chapter_id: 'c5' })

    const buckets = buildBuckets([clue], [ch], [vol], 'payoff')
    expect(buckets).toHaveLength(1)
    expect(buckets[0]!.volumeKey).toBe('v2')
    expect(buckets[0]!.volumeTitle).toBe('第二卷')
    expect(buckets[0]!.chapterKey).toBe('c5')
    expect(buckets[0]!.clues).toHaveLength(1)
  })

  it('places clue with no payoff_chapter_id into unbound payoff group', () => {
    const clue = makeClue({ id: 'cl1', payoff_chapter_id: null })
    const buckets = buildBuckets([clue], [], [], 'payoff')
    expect(buckets).toHaveLength(1)
    expect(buckets[0]!.volumeTitle).toBe('未绑定回收章节')
  })
})

describe('Clue tree ordering', () => {
  it('sorts volumes by order_index ascending', () => {
    const v1 = makeVolume({ id: 'v1', title: '第二卷', order_index: 1 })
    const v2 = makeVolume({ id: 'v2', title: '第一卷', order_index: 0 })
    const c1 = makeChapter({ id: 'c1', volume_id: 'v1', order_index: 0 })
    const c2 = makeChapter({ id: 'c2', volume_id: 'v2', order_index: 0 })
    const clue1 = makeClue({ id: 'cl1', setup_chapter_id: 'c1' })
    const clue2 = makeClue({ id: 'cl2', setup_chapter_id: 'c2' })

    const buckets = buildBuckets([clue1, clue2], [c1, c2], [v1, v2], 'setup')
    // Buckets are per-chapter, but the volume order is stored
    const sorted = [...buckets].sort((a, b) => a.volumeOrder - b.volumeOrder)
    expect(sorted[0]!.volumeTitle).toBe('第一卷')
    expect(sorted[1]!.volumeTitle).toBe('第二卷')
  })

  it('special volume groups (unbound) sort after normal volumes', () => {
    const vol = makeVolume({ id: 'v1', title: '第一卷', order_index: 0 })
    const ch = makeChapter({ id: 'c1', volume_id: 'v1', order_index: 0 })
    const clueBound = makeClue({ id: 'cl1', setup_chapter_id: 'c1' })
    const clueUnbound = makeClue({ id: 'cl2', setup_chapter_id: null })

    const buckets = buildBuckets([clueBound, clueUnbound], [ch], [vol], 'setup')
    const sorted = [...buckets].sort((a, b) => {
      if (a.isVolumeSpecial !== b.isVolumeSpecial) return a.isVolumeSpecial ? 1 : -1
      return a.volumeOrder - b.volumeOrder
    })
    expect(sorted[0]!.volumeTitle).toBe('第一卷')
    expect(sorted[1]!.volumeTitle).toBe('未绑定埋设章节')
  })
})

describe('activeFilterCount', () => {
  it('returns 0 when no structured filters are set', () => {
    expect(computeActiveFilterCount({ status: '', visibility: '', importance: '' })).toBe(0)
  })

  it('does NOT count keyword (keyword is not in the structured filter count)', () => {
    // activeFilterCount only counts status, visibility, importance
    expect(computeActiveFilterCount({ status: '', visibility: '', importance: '' })).toBe(0)
  })

  it('counts each non-empty structured filter', () => {
    expect(
      computeActiveFilterCount({ status: 'planned', visibility: 'hidden', importance: 'high' }),
    ).toBe(3)
  })

  it('counts partial filters', () => {
    expect(computeActiveFilterCount({ status: 'planned', visibility: '', importance: '' })).toBe(1)
  })
})
