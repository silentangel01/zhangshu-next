/**
 * @vitest-environment jsdom
 */
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ChapterContextSummary from '@/features/writing/ChapterContextSummary.vue'

const api = vi.hoisted(() => ({
  listChapterOutlines: vi.fn(),
  listChapterCharacters: vi.fn(),
  listChapterSettings: vi.fn(),
  listChapterClues: vi.fn(),
  listChapterTimelineEvents: vi.fn(),
  listTimelineTracks: vi.fn(),
  listTimelineEdges: vi.fn(),
  listGraphNodes: vi.fn(),
  listGraphEdges: vi.fn(),
}))

vi.mock('@/entities/outline/api', () => ({
  listChapterOutlines: api.listChapterOutlines,
}))

vi.mock('@/entities/chapter-character/api', () => ({
  listChapterCharacters: api.listChapterCharacters,
}))

vi.mock('@/entities/chapter-setting/api', () => ({
  listChapterSettings: api.listChapterSettings,
}))

vi.mock('@/entities/chapter-clue/api', () => ({
  listChapterClues: api.listChapterClues,
}))

vi.mock('@/entities/timeline/api', () => ({
  listChapterTimelineEvents: api.listChapterTimelineEvents,
  listTimelineTracks: api.listTimelineTracks,
  listTimelineEdges: api.listTimelineEdges,
}))

vi.mock('@/entities/graph/api', () => ({
  listGraphNodes: api.listGraphNodes,
  listGraphEdges: api.listGraphEdges,
}))

function useCompleteContext() {
  api.listChapterOutlines.mockResolvedValue([
    {
      id: 'outline-1',
      title: '进入雾港',
      status: 'writing',
      importance: 'important',
      content: '主角收到海图。',
    },
  ])
  api.listChapterCharacters.mockResolvedValue([
    {
      id: 'chapter-character-1',
      character_id: 'character-1',
      relation_type: 'pov',
      note: '',
      character: {
        name: '许照川',
        role: 'protagonist',
        summary: '航标灯修理员。',
      },
    },
  ])
  api.listChapterSettings.mockResolvedValue([
    {
      id: 'chapter-setting-1',
      setting_item_id: 'setting-1',
      note: '',
      setting_item: {
        title: '雾港',
        item_type: 'location',
        canon_status: 'confirmed',
        summary: '终年被雾笼罩的港城。',
      },
    },
  ])
  api.listChapterClues.mockResolvedValue([
    {
      id: 'chapter-clue-1',
      clue_id: 'clue-1',
      relation_type: 'setup',
      note: '',
      clue: {
        title: '第七次潮汐',
        status: 'planted',
        payoff_plan: '在白鸥号靠岸时回收。',
        description: '',
      },
    },
  ])
  api.listChapterTimelineEvents.mockResolvedValue([
    {
      id: 'event-1',
      title: '白鸥号返航',
      track_id: 'track-1',
      story_date: '第七日',
      story_time: '夜',
      note: '',
      description: '失踪十二年的船重新出现。',
    },
  ])
  api.listTimelineTracks.mockResolvedValue([
    {
      id: 'track-1',
      title: '主时间轴',
    },
  ])
  api.listTimelineEdges.mockResolvedValue([])
  api.listGraphNodes.mockResolvedValue([
    {
      id: 'node-1',
      title: '许照川',
      node_type: 'character',
      visibility: 'normal',
      bound_type: 'character',
      bound_id: 'character-1',
      summary: '主角节点',
    },
  ])
  api.listGraphEdges.mockResolvedValue([])
}

function useEmptyContext() {
  api.listChapterOutlines.mockResolvedValue([])
  api.listChapterCharacters.mockResolvedValue([])
  api.listChapterSettings.mockResolvedValue([])
  api.listChapterClues.mockResolvedValue([])
  api.listChapterTimelineEvents.mockResolvedValue([])
  api.listTimelineTracks.mockResolvedValue([])
  api.listTimelineEdges.mockResolvedValue([])
  api.listGraphNodes.mockResolvedValue([])
  api.listGraphEdges.mockResolvedValue([])
}

function mountOverview(chapterId = 'chapter-1') {
  return mount(ChapterContextSummary, {
    props: {
      projectId: 'project-1',
      chapterId,
      kind: 'overview',
    },
    global: {
      stubs: {
        RouterLink: true,
      },
    },
  })
}

describe('ChapterContextSummary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useEmptyContext()
  })

  it('汇总六类完整关联，并显示对应资料名称', async () => {
    useCompleteContext()

    const wrapper = mountOverview()
    await flushPromises()

    expect(wrapper.text()).toContain('已关联 6 / 6 类资料')
    expect(wrapper.text()).toContain('进入雾港')
    expect(wrapper.text()).toContain('许照川')
    expect(wrapper.text()).toContain('雾港')
    expect(wrapper.text()).toContain('第七次潮汐')
    expect(wrapper.text()).toContain('白鸥号返航')
    expect(wrapper.findAll('button.overview-card')).toHaveLength(6)
  })

  it('显示缺失关联提示，并从卡片发出分类切换事件', async () => {
    const wrapper = mountOverview()
    await flushPromises()

    expect(wrapper.text()).toContain('已关联 0 / 6 类资料')
    expect(wrapper.text()).toContain('可考虑补充本章关联：细纲、人物、设定、伏笔、时间、关系')
    expect(wrapper.text()).toContain('查看细纲')

    await wrapper.find('button.overview-card').trigger('click')

    expect(wrapper.emitted('selectContext')).toEqual([['outline']])
  })

  it('快速切换章节时忽略较早请求的迟到结果', async () => {
    let resolveFirstOutline: ((value: unknown[]) => void) | undefined
    const firstOutline = new Promise<unknown[]>((resolve) => {
      resolveFirstOutline = resolve
    })

    api.listChapterOutlines
      .mockImplementationOnce(() => firstOutline)
      .mockResolvedValueOnce([
        {
          id: 'outline-b',
          title: '第二章细纲',
          status: 'planned',
          importance: 'normal',
          content: '',
        },
      ])

    const wrapper = mountOverview('chapter-a')
    await wrapper.setProps({ chapterId: 'chapter-b' })
    await flushPromises()

    expect(wrapper.text()).toContain('第二章细纲')

    resolveFirstOutline?.([
      {
        id: 'outline-a',
        title: '第一章迟到细纲',
        status: 'planned',
        importance: 'normal',
        content: '',
      },
    ])
    await flushPromises()

    expect(wrapper.text()).toContain('第二章细纲')
    expect(wrapper.text()).not.toContain('第一章迟到细纲')
  })

  it('任一资料接口失败时显示统一错误状态', async () => {
    api.listChapterCharacters.mockRejectedValueOnce(new Error('network failure'))

    const wrapper = mountOverview()
    await flushPromises()

    expect(wrapper.text()).toContain('章节资料加载失败，请稍后重试。')
  })
})
