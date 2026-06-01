/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'

// Mock the cloud API module
vi.mock('@/entities/cloud/api', () => ({
  listRemoteCloudProjects: vi.fn(),
  importRemoteCloudProject: vi.fn(),
}))

// Mock vue-router
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
}))

import { importRemoteCloudProject, listRemoteCloudProjects } from '@/entities/cloud/api'
import CloudProjectImportDialog from '@/features/cloud/CloudProjectImportDialog.vue'
import type { CloudRemoteProject } from '@/entities/cloud/types'

const mockList = vi.mocked(listRemoteCloudProjects)
const mockImport = vi.mocked(importRemoteCloudProject)

function makeProject(overrides: Partial<CloudRemoteProject> = {}): CloudRemoteProject {
  return {
    id: 'cloud-1',
    title: '远端项目',
    created_at: '2026-05-01T00:00:00',
    updated_at: '2026-05-30T00:00:00',
    linked_locally: false,
    local_project_id: null,
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  mockPush.mockReset()
})

describe('CloudProjectImportDialog', () => {
  it('shows "恢复为新项目" for unlinked projects', async () => {
    mockList.mockResolvedValue([
      makeProject({ id: 'cloud-1', title: '未关联项目' }),
    ])

    const wrapper = mount(CloudProjectImportDialog)
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const restoreBtn = buttons.find((b) => b.text().includes('恢复为新项目'))
    expect(restoreBtn).toBeDefined()
    expect(restoreBtn!.text()).toContain('恢复为新项目')
  })

  it('shows "打开本机项目" for linked projects', async () => {
    mockList.mockResolvedValue([
      makeProject({
        id: 'cloud-linked',
        title: '已关联项目',
        linked_locally: true,
        local_project_id: 'local-proj-1',
      }),
    ])

    const wrapper = mount(CloudProjectImportDialog)
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const openBtn = buttons.find((b) => b.text().includes('打开本机项目'))
    expect(openBtn).toBeDefined()
    expect(openBtn!.text()).toContain('打开本机项目')
  })

  it('clicking linked project does NOT call importRemoteCloudProject', async () => {
    mockList.mockResolvedValue([
      makeProject({
        id: 'cloud-linked',
        title: '已关联项目',
        linked_locally: true,
        local_project_id: 'local-proj-1',
      }),
    ])

    const wrapper = mount(CloudProjectImportDialog)
    await flushPromises()

    const openBtn = wrapper.findAll('button').find((b) => b.text().includes('打开本机项目'))!
    await openBtn.trigger('click')

    expect(mockImport).not.toHaveBeenCalled()
    expect(mockPush).toHaveBeenCalledWith('/projects/local-proj-1')
  })

  it('clicking unlinked project calls importRemoteCloudProject and navigates', async () => {
    mockList.mockResolvedValue([
      makeProject({ id: 'cloud-new', title: '新项目' }),
    ])
    mockImport.mockResolvedValue({
      local_project_id: 'local-new-1',
      title: '新项目',
      volumes_count: 1,
      chapters_count: 3,
      mode: 'restored_as_new',
    })

    const wrapper = mount(CloudProjectImportDialog)
    await flushPromises()

    const restoreBtn = wrapper.findAll('button').find((b) => b.text().includes('恢复为新项目'))!
    await restoreBtn.trigger('click')
    await flushPromises()

    expect(mockImport).toHaveBeenCalledWith('cloud-new')
    expect(mockPush).toHaveBeenCalledWith('/projects/local-new-1')
  })

  it('handles mode="already_exists" from backend as safety net', async () => {
    mockList.mockResolvedValue([
      makeProject({ id: 'cloud-exist', title: '已存在项目' }),
    ])
    mockImport.mockResolvedValue({
      local_project_id: 'local-existing-1',
      title: '已存在项目',
      volumes_count: 0,
      chapters_count: 0,
      mode: 'already_exists',
      message: '该云端项目已在本机存在，已打开本机项目。',
    })

    const wrapper = mount(CloudProjectImportDialog)
    await flushPromises()

    const restoreBtn = wrapper.findAll('button').find((b) => b.text().includes('恢复为新项目'))!
    await restoreBtn.trigger('click')
    await flushPromises()

    // Should still navigate to the existing project
    expect(mockPush).toHaveBeenCalledWith('/projects/local-existing-1')
  })

  it('shows "本机已有" badge for linked projects', async () => {
    mockList.mockResolvedValue([
      makeProject({
        id: 'cloud-linked',
        title: '已关联项目',
        linked_locally: true,
        local_project_id: 'local-proj-1',
      }),
    ])

    const wrapper = mount(CloudProjectImportDialog)
    await flushPromises()

    expect(wrapper.text()).toContain('本机已有')
  })

  it('title is "从云端恢复项目"', async () => {
    mockList.mockResolvedValue([])

    const wrapper = mount(CloudProjectImportDialog)
    await flushPromises()

    expect(wrapper.find('h2').text()).toBe('从云端恢复项目')
  })
})
