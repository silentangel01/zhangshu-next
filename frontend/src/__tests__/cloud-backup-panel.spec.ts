/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

// Mock the cloud API module
vi.mock('@/entities/cloud/api', () => ({
  enableCloud: vi.fn(),
  getCloudAccountStatus: vi.fn(),
  getCloudStatus: vi.fn(),
  listCloudBackups: vi.fn(),
  listRemoteCloudProjects: vi.fn(),
  restoreCloudBackup: vi.fn(),
  runCloudSync: vi.fn(),
  triggerCloudBackup: vi.fn(),
}))

// Mock formatDateTime to avoid importing the module
vi.mock('@/shared/utils/formatDateTime', () => ({
  formatDateTime: (s: string | null) => s ?? '',
}))

// Mock ApiError
vi.mock('@/shared/api/client', () => {
  class MockApiError extends Error {
    status: number
    suggestion?: string
    errorKind?: string
    constructor(message: string, status: number, suggestion?: string, errorKind?: string) {
      super(message)
      this.name = 'ApiError'
      this.status = status
      this.suggestion = suggestion
      this.errorKind = errorKind
    }
  }
  return {
    ApiError: MockApiError,
    apiRequest: vi.fn(),
    apiUpload: vi.fn(),
  }
})

import {
  enableCloud,
  getCloudAccountStatus,
  getCloudStatus,
  listCloudBackups,
  listRemoteCloudProjects,
  runCloudSync,
  triggerCloudBackup,
} from '@/entities/cloud/api'
import { ApiError } from '@/shared/api/client'
import CloudBackupPanel from '@/features/cloud/CloudBackupPanel.vue'
import type { CloudRemoteProject } from '@/entities/cloud/types'

const mockGetAccountStatus = vi.mocked(getCloudAccountStatus)
const mockGetCloudStatus = vi.mocked(getCloudStatus)
const mockListBackups = vi.mocked(listCloudBackups)
const mockListRemote = vi.mocked(listRemoteCloudProjects)
const mockEnableCloud = vi.mocked(enableCloud)
const mockRunCloudSync = vi.mocked(runCloudSync)
const mockTriggerCloudBackup = vi.mocked(triggerCloudBackup)

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

  // Default: logged in, cloud not enabled
  mockGetAccountStatus.mockResolvedValue({
    logged_in: true,
    cloud_available: true,
    email: 'test@example.com',
    display_name: 'Test',
  })
  mockGetCloudStatus.mockResolvedValue({
    cloud_enabled: false,
    cloud_project_id: null,
    provider: 'zhangshu',
    last_backup_at: null,
    last_restore_at: null,
    status: 'inactive',
    last_error: null,
  })
  mockListBackups.mockResolvedValue({ items: [], total: 0 })
})

describe('CloudBackupPanel — link existing cloud project', () => {
  it('shows "关联已有云端项目" button when cloud not enabled', async () => {
    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const linkBtn = buttons.find((b) => b.text().includes('关联已有云端项目'))
    expect(linkBtn).toBeDefined()
    expect(linkBtn!.text()).toContain('关联已有云端项目')
  })

  it('clicking "关联已有云端项目" opens dialog with remote projects', async () => {
    mockListRemote.mockResolvedValue([
      makeProject({ id: 'cloud-1', title: '远端项目 A' }),
      makeProject({ id: 'cloud-2', title: '远端项目 B' }),
    ])

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const linkBtn = wrapper.findAll('button').find((b) => b.text().includes('关联已有云端项目'))!
    await linkBtn.trigger('click')
    await flushPromises()

    expect(mockListRemote).toHaveBeenCalled()
    expect(wrapper.text()).toContain('远端项目 A')
    expect(wrapper.text()).toContain('远端项目 B')
  })

  it('shows "已关联" for projects with linked_locally=true', async () => {
    mockListRemote.mockResolvedValue([
      makeProject({
        id: 'cloud-linked',
        title: '已关联项目',
        linked_locally: true,
        local_project_id: 'local-proj-1',
      }),
    ])

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const linkBtn = wrapper.findAll('button').find((b) => b.text().includes('关联已有云端项目'))!
    await linkBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('本机已有')
    const disabledBtn = wrapper.findAll('button').find((b) => b.text() === '已关联')
    expect(disabledBtn).toBeDefined()
    expect(disabledBtn!.attributes('disabled')).toBeDefined()
  })

  it('clicking "关联此项目" calls enableCloud and runs initial bidirectional sync', async () => {
    mockListRemote.mockResolvedValue([
      makeProject({ id: 'cloud-select', title: '选中项目' }),
    ])
    mockEnableCloud.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-select',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })
    mockRunCloudSync.mockResolvedValue({
      pushed: 3,
      pulled: 5,
      new_cursor: 10,
      conflicts: 0,
      errors: [],
      duration_ms: 200,
    })

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const linkBtn = wrapper.findAll('button').find((b) => b.text().includes('关联已有云端项目'))!
    await linkBtn.trigger('click')
    await flushPromises()

    const selectBtn = wrapper.findAll('button').find((b) => b.text().includes('关联此项目'))!
    await selectBtn.trigger('click')
    await flushPromises()

    expect(mockEnableCloud).toHaveBeenCalledWith('proj-1', 'cloud-select')
    expect(mockRunCloudSync).toHaveBeenCalledWith('proj-1')
    expect(wrapper.text()).toContain('上传 3 条、拉取 5 条更新')
  })

  it('shows "上传本机数据" when only pushed', async () => {
    mockListRemote.mockResolvedValue([
      makeProject({ id: 'cloud-push-only', title: '仅上传项目' }),
    ])
    mockEnableCloud.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-push-only',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })
    mockRunCloudSync.mockResolvedValue({
      pushed: 10,
      pulled: 0,
      new_cursor: 5,
      conflicts: 0,
      errors: [],
      duration_ms: 300,
    })

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const linkBtn = wrapper.findAll('button').find((b) => b.text().includes('关联已有云端项目'))!
    await linkBtn.trigger('click')
    await flushPromises()

    const selectBtn = wrapper.findAll('button').find((b) => b.text().includes('关联此项目'))!
    await selectBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('已关联并上传本机数据')
  })

  it('shows "拉取云端更新" when only pulled', async () => {
    mockListRemote.mockResolvedValue([
      makeProject({ id: 'cloud-pull-only', title: '仅拉取项目' }),
    ])
    mockEnableCloud.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-pull-only',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })
    mockRunCloudSync.mockResolvedValue({
      pushed: 0,
      pulled: 8,
      new_cursor: 12,
      conflicts: 0,
      errors: [],
      duration_ms: 150,
    })

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const linkBtn = wrapper.findAll('button').find((b) => b.text().includes('关联已有云端项目'))!
    await linkBtn.trigger('click')
    await flushPromises()

    const selectBtn = wrapper.findAll('button').find((b) => b.text().includes('关联此项目'))!
    await selectBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('已关联并拉取云端更新')
  })

  it('shows error and suggestion when backend rejects linking', async () => {
    mockListRemote.mockResolvedValue([
      makeProject({ id: 'cloud-reject', title: '不匹配项目' }),
    ])
    mockEnableCloud.mockRejectedValue(
      new ApiError(
        '该云端项目属于另一个项目',
        400,
        '云端项目与当前本地项目不是同一个项目。',
        'project_identity_mismatch',
      ),
    )

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const linkBtn = wrapper.findAll('button').find((b) => b.text().includes('关联已有云端项目'))!
    await linkBtn.trigger('click')
    await flushPromises()

    const selectBtn = wrapper.findAll('button').find((b) => b.text().includes('关联此项目'))!
    await selectBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('属于另一个项目')
    expect(wrapper.text()).toContain('不是同一个项目')
  })

  it('shows partial success when linking succeeds but sync fails', async () => {
    mockListRemote.mockResolvedValue([
      makeProject({ id: 'cloud-sync-fail', title: '同步失败项目' }),
    ])
    mockEnableCloud.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-sync-fail',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })
    mockRunCloudSync.mockRejectedValue(new Error('网络超时'))

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const linkBtn = wrapper.findAll('button').find((b) => b.text().includes('关联已有云端项目'))!
    await linkBtn.trigger('click')
    await flushPromises()

    const selectBtn = wrapper.findAll('button').find((b) => b.text().includes('关联此项目'))!
    await selectBtn.trigger('click')
    await flushPromises()

    expect(mockEnableCloud).toHaveBeenCalledWith('proj-1', 'cloud-sync-fail')
    expect(mockRunCloudSync).toHaveBeenCalled()
    // Linking succeeded
    expect(wrapper.text()).toContain('已关联云端项目')
    // But sync failed — must include safety message
    expect(wrapper.text()).toContain('首次同步失败，本机内容已保留')
  })

  it('shows partial failure when first sync resolves with errors', async () => {
    mockListRemote.mockResolvedValue([
      makeProject({ id: 'cloud-partial', title: '部分失败项目' }),
    ])
    mockEnableCloud.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-partial',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })
    mockRunCloudSync.mockResolvedValue({
      pushed: 1,
      pulled: 0,
      new_cursor: 1,
      conflicts: 0,
      errors: ['网络超时'],
      duration_ms: 200,
    })

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const linkBtn = wrapper.findAll('button').find((b) => b.text().includes('关联已有云端项目'))!
    await linkBtn.trigger('click')
    await flushPromises()

    const selectBtn = wrapper.findAll('button').find((b) => b.text().includes('关联此项目'))!
    await selectBtn.trigger('click')
    await flushPromises()

    expect(mockEnableCloud).toHaveBeenCalledWith('proj-1', 'cloud-partial')
    expect(mockRunCloudSync).toHaveBeenCalledWith('proj-1')
    // Linking succeeded
    expect(wrapper.text()).toContain('已关联云端项目')
    // Partial failure — not full success
    expect(wrapper.text()).toContain('首次同步未完全完成')
    expect(wrapper.text()).toContain('本机内容已保留')
    expect(wrapper.text()).toContain('立即同步')
    // Must NOT show full success semantics
    expect(wrapper.text()).not.toContain('已关联并同步完成')
    expect(wrapper.text()).not.toContain('本机数据已是最新')
  })

  it('does not show "关联已有云端项目" when cloud already enabled', async () => {
    mockGetCloudStatus.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-enabled',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const linkBtn = wrapper.findAll('button').find((b) => b.text().includes('关联已有云端项目'))
    expect(linkBtn).toBeUndefined()
  })
})

describe('CloudBackupPanel — sync and backup buttons', () => {
  it('shows "立即同步" and "创建完整备份" buttons when cloud enabled', async () => {
    mockGetCloudStatus.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-enabled',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const syncBtn = wrapper.findAll('button').find((b) => b.text() === '立即同步')
    expect(syncBtn).toBeDefined()

    const backupBtn = wrapper.findAll('button').find((b) => b.text() === '创建完整备份')
    expect(backupBtn).toBeDefined()
  })

  it('clicking "立即同步" calls runCloudSync and shows result', async () => {
    mockGetCloudStatus.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-enabled',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })
    mockRunCloudSync.mockResolvedValue({
      pushed: 5,
      pulled: 3,
      new_cursor: 10,
      conflicts: 0,
      errors: [],
      duration_ms: 200,
    })

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const syncBtn = wrapper.findAll('button').find((b) => b.text() === '立即同步')!
    await syncBtn.trigger('click')
    await flushPromises()

    expect(mockRunCloudSync).toHaveBeenCalledWith('proj-1')
    expect(wrapper.text()).toContain('同步完成，上传 5 条、拉取 3 条更新')
  })

  it('"立即同步" shows "数据已是最新" when nothing to sync', async () => {
    mockGetCloudStatus.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-enabled',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })
    mockRunCloudSync.mockResolvedValue({
      pushed: 0,
      pulled: 0,
      new_cursor: 0,
      conflicts: 0,
      errors: [],
      duration_ms: 100,
    })

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const syncBtn = wrapper.findAll('button').find((b) => b.text() === '立即同步')!
    await syncBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('数据已是最新')
  })

  it('"立即同步" shows error with safety message', async () => {
    mockGetCloudStatus.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-enabled',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })
    mockRunCloudSync.mockRejectedValue(new Error('网络超时'))

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const syncBtn = wrapper.findAll('button').find((b) => b.text() === '立即同步')!
    await syncBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('同步失败，本机内容已保留，可稍后重试')
    expect(wrapper.text()).not.toContain('备份失败')
  })

  it('clicking "创建完整备份" calls triggerCloudBackup', async () => {
    mockGetCloudStatus.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-enabled',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })
    mockTriggerCloudBackup.mockResolvedValue({
      id: 'backup-1',
      project_id: 'proj-1',
      cloud_backup_id: 'cb-1',
      filename: 'backup.zip',
      size_bytes: 1024,
      checksum_sha256: 'abc123',
      encryption_mode: 'none',
      status: 'success',
      error_message: null,
      created_at: '2026-05-31T00:00:00',
      uploaded_at: '2026-05-31T00:00:00',
    })

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const backupBtn = wrapper.findAll('button').find((b) => b.text() === '创建完整备份')!
    await backupBtn.trigger('click')
    await flushPromises()

    expect(mockTriggerCloudBackup).toHaveBeenCalledWith('proj-1')
    expect(wrapper.text()).toContain('云端备份成功')
  })

  it('shows "完整备份记录" heading when backups exist', async () => {
    mockGetCloudStatus.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-enabled',
      provider: 'zhangshu',
      last_backup_at: '2026-05-30T00:00:00',
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })
    mockListBackups.mockResolvedValue({
      items: [
        {
          id: 'backup-1',
          project_id: 'proj-1',
          cloud_backup_id: 'cb-1',
          filename: 'backup.zip',
          size_bytes: 1024,
          checksum_sha256: 'abc123',
          encryption_mode: 'none',
          status: 'success',
          error_message: null,
          created_at: '2026-05-30T00:00:00',
          uploaded_at: '2026-05-30T00:00:00',
        },
      ],
      total: 1,
    })

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('完整备份记录')
    expect(wrapper.text()).not.toMatch(/^备份记录$/)
  })

  it('"立即同步" with partial errors shows safety message, not pure success', async () => {
    mockGetCloudStatus.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-enabled',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })
    mockRunCloudSync.mockResolvedValue({
      pushed: 1,
      pulled: 0,
      new_cursor: 1,
      conflicts: 0,
      errors: ['push failed for entity X'],
      duration_ms: 200,
    })

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const syncBtn = wrapper.findAll('button').find((b) => b.text() === '立即同步')!
    await syncBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('部分同步未完成')
    expect(wrapper.text()).toContain('本机内容已保留')
    expect(wrapper.text()).not.toContain('数据已是最新')
    expect(wrapper.text()).not.toContain('同步完成')
  })

  it('"立即同步" with conflicts shows multi-device message', async () => {
    mockGetCloudStatus.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-enabled',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })
    mockRunCloudSync.mockResolvedValue({
      pushed: 2,
      pulled: 1,
      new_cursor: 5,
      conflicts: 2,
      errors: [],
      duration_ms: 300,
    })

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const syncBtn = wrapper.findAll('button').find((b) => b.text() === '立即同步')!
    await syncBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('多设备修改')
    expect(wrapper.text()).not.toContain('冲突')
  })

  it('"立即同步" button is disabled while syncing', async () => {
    mockGetCloudStatus.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-enabled',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })
    // Make runCloudSync hang
    let resolveSync!: () => void
    mockRunCloudSync.mockReturnValue(
      new Promise((resolve) => {
        resolveSync = () =>
          resolve({
            pushed: 0,
            pulled: 0,
            new_cursor: 0,
            conflicts: 0,
            errors: [],
            duration_ms: 100,
          })
      }),
    )

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const syncBtn = wrapper.findAll('button').find((b) => b.text() === '立即同步')!
    await syncBtn.trigger('click')
    await flushPromises()

    // Button should be disabled during sync
    const btnDuringSync = wrapper.findAll('button').find((b) => b.text().includes('正在同步'))!
    expect(btnDuringSync.attributes('disabled')).toBeDefined()

    // Resolve
    resolveSync()
    await flushPromises()
  })

  it('panel description mentions incremental sync and full backup', async () => {
    mockGetCloudStatus.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-enabled',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('增量同步')
    expect(wrapper.text()).toContain('完整备份')
  })

  it('"创建完整备份" calls triggerCloudBackup, not runCloudSync', async () => {
    mockGetCloudStatus.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-enabled',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })
    mockTriggerCloudBackup.mockResolvedValue({
      id: 'backup-2',
      project_id: 'proj-1',
      cloud_backup_id: 'cb-2',
      filename: 'backup2.zip',
      size_bytes: 2048,
      checksum_sha256: 'def456',
      encryption_mode: 'none',
      status: 'success',
      error_message: null,
      created_at: '2026-05-31T00:00:00',
      uploaded_at: '2026-05-31T00:00:00',
    })

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const backupBtn = wrapper.findAll('button').find((b) => b.text() === '创建完整备份')!
    await backupBtn.trigger('click')
    await flushPromises()

    expect(mockTriggerCloudBackup).toHaveBeenCalledWith('proj-1')
    expect(mockRunCloudSync).not.toHaveBeenCalled()
  })

  it('"立即同步" partial failure shows short error summary', async () => {
    mockGetCloudStatus.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-enabled',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })
    mockRunCloudSync.mockResolvedValue({
      pushed: 1,
      pulled: 0,
      new_cursor: 1,
      conflicts: 0,
      errors: ['网络超时'],
      duration_ms: 200,
    })

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const syncBtn = wrapper.findAll('button').find((b) => b.text() === '立即同步')!
    await syncBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('部分同步未完成')
    expect(wrapper.text()).toContain('本机内容已保留')
    expect(wrapper.text()).toContain('原因：网络超时')
    expect(wrapper.text()).not.toContain('数据已是最新')
    expect(wrapper.text()).not.toContain('同步完成')
  })

  it('"立即同步" truncates long error summary', async () => {
    mockGetCloudStatus.mockResolvedValue({
      cloud_enabled: true,
      cloud_project_id: 'cloud-enabled',
      provider: 'zhangshu',
      last_backup_at: null,
      last_restore_at: null,
      status: 'active',
      last_error: null,
    })
    const longError =
      'characters/char-12345: 这是一个非常非常长的错误信息用于测试截断功能是否正常工作，确保超长错误不会原样显示在用户界面上，避免破坏布局或暴露内部实体路径。' +
      '更多填充文本'.repeat(20)
    mockRunCloudSync.mockResolvedValue({
      pushed: 0,
      pulled: 0,
      new_cursor: 0,
      conflicts: 0,
      errors: [longError],
      duration_ms: 200,
    })

    const wrapper = mount(CloudBackupPanel, {
      props: { projectId: 'proj-1' },
    })
    await flushPromises()

    const syncBtn = wrapper.findAll('button').find((b) => b.text() === '立即同步')!
    await syncBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('同步未完全完成')
    expect(wrapper.text()).toContain('本机内容已保留')
    // Full long error must NOT appear verbatim
    expect(wrapper.text()).not.toContain('characters/char-12345')
    expect(wrapper.text()).not.toContain('更多填充文本'.repeat(5))
  })
})
