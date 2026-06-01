<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getUserDetail, toggleUserActive, forceLogoutUser, changeAdminRole } from '@/entities/admin-user/api'
import type { AdminUserDetail } from '@/entities/admin-user/types'
import { useToast } from '@/shared/composables/useToast'
import { useAdminSession } from '@/shared/composables/useAdminSession'
import RiskActionDialog from '@/components/RiskActionDialog.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { hasPermission } = useAdminSession()
const user = ref<AdminUserDetail | null>(null)
const loading = ref(true)
const actionLoading = ref(false)

// Dialog state
const showDialog = ref(false)
const dialogAction = ref<'toggle' | 'logout' | 'role'>('toggle')
const dialogRef = ref<InstanceType<typeof RiskActionDialog> | null>(null)

// Role change state
const newRole = ref<string | null>(null)

const ADMIN_ROLES = [
  { value: 'owner', label: 'Owner (最高权限)' },
  { value: 'admin', label: 'Admin (日常管理)' },
  { value: 'support', label: 'Support (客服/反馈)' },
  { value: 'ops', label: 'Ops (运维/监控)' },
  { value: 'readonly', label: 'Readonly (只读)' },
  { value: '', label: '移除管理权限' },
]

const dialogConfig = {
  toggle: {
    title: '禁用/启用用户',
    message: '此操作将切换用户的启用状态。禁用用户将同时撤销其所有活跃会话。',
    variant: 'warning' as const,
    confirmLabel: '确认',
  },
  logout: {
    title: '强制下线',
    message: '此操作将撤销该用户的所有活跃会话，用户需要重新登录。',
    variant: 'danger' as const,
    confirmLabel: '强制下线',
  },
  role: {
    title: '变更管理员角色',
    message: '此操作将变更用户的管理员角色。变更后该用户的所有会话将被撤销，需要重新登录。',
    variant: 'critical' as const,
    confirmLabel: '变更角色',
    confirmText: '确认变更角色',
  },
}

onMounted(async () => {
  try {
    user.value = await getUserDetail(route.params.id as string)
  } catch {
    router.push('/users')
  } finally {
    loading.value = false
  }
})

function openToggleDialog() {
  if (!user.value) return
  dialogAction.value = 'toggle'
  showDialog.value = true
}

function openLogoutDialog() {
  if (!user.value) return
  dialogAction.value = 'logout'
  showDialog.value = true
}

function openRoleDialog(role: string | null) {
  if (!user.value) return
  newRole.value = role
  dialogAction.value = 'role'
  showDialog.value = true
}

async function handleDialogConfirm(payload: { reason: string; confirm_text: string }) {
  if (!user.value) return
  dialogRef.value?.setLoading(true)
  try {
    if (dialogAction.value === 'toggle') {
      const res = await toggleUserActive(user.value.id, payload.reason)
      user.value.is_active = res.is_active
      const action = res.is_active ? '启用' : '禁用'
      toast.success(`已${action}用户`)
    } else if (dialogAction.value === 'logout') {
      const res = await forceLogoutUser(user.value.id, payload.reason)
      toast.success(`已强制下线，撤销 ${res.tokens_revoked} 个会话`)
    } else if (dialogAction.value === 'role') {
      const res = await changeAdminRole(
        user.value.id,
        newRole.value || null,
        payload.reason,
        payload.confirm_text,
      )
      user.value.admin_role = res.admin_role
      toast.success('管理员角色已变更')
    }
    showDialog.value = false
  } catch (e: unknown) {
    toast.error(e instanceof Error ? e.message : '操作失败')
  } finally {
    dialogRef.value?.setLoading(false)
  }
}

function effectiveRoleLabel(): string {
  if (!user.value) return '-'
  if (user.value.admin_role) {
    const found = ADMIN_ROLES.find((r) => r.value === user.value!.admin_role)
    return found ? found.label : user.value.admin_role
  }
  if (user.value.is_admin) return 'Owner (bootstrap)'
  return '-'
}

function formatDate(d: string | null): string {
  if (!d) return '-'
  try {
    return new Date(d).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return d
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}
</script>

<template>
  <div>
    <button class="btn back-btn" @click="router.push('/users')">&larr; 返回列表</button>
    <p v-if="loading" class="loading-text">加载中...</p>
    <template v-else-if="user">
      <div class="card profile-card">
        <h2>{{ user.display_name }}</h2>
        <p class="email">{{ user.email }}</p>
        <p v-if="user.signature" class="signature">{{ user.signature }}</p>
        <div class="info-grid">
          <div><strong>注册时间</strong><span>{{ formatDate(user.created_at) }}</span></div>
          <div><strong>最后登录</strong><span>{{ formatDate(user.last_login_at) }}</span></div>
          <div><strong>登录次数</strong><span>{{ user.login_count }}</span></div>
          <div><strong>密码修改</strong><span>{{ formatDate(user.password_changed_at) }}</span></div>
          <div><strong>管理角色</strong><span class="role-badge">{{ effectiveRoleLabel() }}</span></div>
          <div><strong>状态</strong><span :class="user.is_active ? 'text-success' : 'text-danger'">{{ user.is_active ? '正常' : '已禁用' }}</span></div>
          <div><strong>云项目</strong><span>{{ user.cloud_project_count }}</span></div>
          <div><strong>云备份</strong><span>{{ user.cloud_backup_count }}</span></div>
          <div><strong>存储用量</strong><span>{{ formatBytes(user.total_storage_bytes) }}</span></div>
          <div><strong>反馈数</strong><span>{{ user.feedback_count }}</span></div>
        </div>
      </div>

      <div v-if="hasPermission('users:toggle_active') || hasPermission('users:force_logout')" class="card section-card">
        <h3>管理操作</h3>
        <div class="admin-actions">
          <button
            v-if="hasPermission('users:toggle_active')"
            class="btn"
            :class="user.is_active ? 'btn-warning' : 'btn-success'"
            :disabled="actionLoading"
            @click="openToggleDialog"
          >
            {{ user.is_active ? '禁用用户' : '启用用户' }}
          </button>
          <button
            v-if="hasPermission('users:force_logout')"
            class="btn btn-danger"
            :disabled="actionLoading"
            @click="openLogoutDialog"
          >
            强制下线
          </button>
        </div>
      </div>

      <div v-if="hasPermission('admin_roles:manage')" class="card section-card">
        <h3>角色管理</h3>
        <p class="role-hint">变更角色后用户将被强制下线，需要重新登录。</p>
        <div class="role-buttons">
          <button
            v-for="role in ADMIN_ROLES"
            :key="role.value"
            class="btn btn-sm"
            :class="{ 'btn-sm-active': user.admin_role === (role.value || null) }"
            :disabled="actionLoading"
            @click="openRoleDialog(role.value || null)"
          >
            {{ role.label }}
          </button>
        </div>
      </div>

      <div v-if="user.recent_activity.length" class="card section-card">
        <h3>最近活动</h3>
        <ul class="activity-list">
          <li v-for="(a, i) in user.recent_activity" :key="i">
            <span class="event-type">{{ a.event_type }}</span>
            <span class="event-time">{{ formatDate(a.created_at) }}</span>
          </li>
        </ul>
      </div>

      <div v-if="user.recent_feedback.length" class="card section-card">
        <h3>最近反馈</h3>
        <ul class="feedback-list">
          <li v-for="f in user.recent_feedback" :key="f.id">
            <RouterLink :to="`/feedback/${f.id}`">{{ f.title }}</RouterLink>
            <span class="badge badge-info">{{ f.status }}</span>
          </li>
        </ul>
      </div>
    </template>

    <RiskActionDialog
      v-if="showDialog"
      ref="dialogRef"
      :title="dialogConfig[dialogAction].title"
      :message="dialogConfig[dialogAction].message"
      :variant="dialogConfig[dialogAction].variant"
      :confirm-label="dialogConfig[dialogAction].confirmLabel"
      :confirm-text="'confirmText' in dialogConfig[dialogAction] ? (dialogConfig[dialogAction] as any).confirmText : undefined"
      :require-reason="true"
      @confirm="handleDialogConfirm"
      @cancel="showDialog = false"
    />
  </div>
</template>

<style scoped>
.back-btn { margin-bottom: var(--ca-space-4); }
.loading-text { color: var(--ca-text-muted); }
.profile-card { margin-bottom: var(--ca-space-4); }
.profile-card h2 { font-size: 18px; margin-bottom: var(--ca-space-1); }
.email { color: var(--ca-text-muted); margin-bottom: var(--ca-space-3); }
.signature { font-style: italic; color: var(--ca-text-muted); margin-bottom: var(--ca-space-4); }
.info-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: var(--ca-space-3); }
.info-grid div { display: flex; justify-content: space-between; padding: var(--ca-space-2) 0; border-bottom: 1px solid var(--ca-border); }
.info-grid strong { color: var(--ca-text-muted); font-weight: 500; }
.section-card { margin-bottom: var(--ca-space-4); }
.section-card h3 { font-size: 15px; margin-bottom: var(--ca-space-3); }
.activity-list, .feedback-list { list-style: none; }
.activity-list li, .feedback-list li { display: flex; justify-content: space-between; padding: var(--ca-space-2) 0; border-bottom: 1px solid var(--ca-border); font-size: 13px; }
.event-type { font-weight: 500; }
.event-time { color: var(--ca-text-muted); }
.admin-actions { display: flex; gap: var(--ca-space-3); }
.btn-warning { background: var(--ca-warning, #f59e0b); color: #fff; border-color: var(--ca-warning, #f59e0b); }
.btn-warning:hover { opacity: 0.9; }
.btn-success { background: var(--ca-success, #22c55e); color: #fff; border-color: var(--ca-success, #22c55e); }
.btn-success:hover { opacity: 0.9; }
.btn-danger { background: var(--ca-danger, #ef4444); color: #fff; border-color: var(--ca-danger, #ef4444); }
.btn-danger:hover { opacity: 0.9; }
.role-badge { font-weight: 500; color: var(--ca-primary, #3b82f6); }
.text-success { color: var(--ca-success); }
.text-danger { color: var(--ca-danger); }
.role-hint { font-size: 12px; color: var(--ca-text-muted); margin-bottom: var(--ca-space-3); }
.role-buttons { display: flex; flex-wrap: wrap; gap: var(--ca-space-2); }
.btn-sm { padding: 4px 10px; font-size: 12px; border: 1px solid var(--ca-border); border-radius: 4px; background: var(--ca-surface, #fff); cursor: pointer; color: var(--ca-text); }
.btn-sm:hover { border-color: var(--ca-primary, #3b82f6); color: var(--ca-primary, #3b82f6); }
.btn-sm-active { background: var(--ca-primary, #3b82f6); color: #fff; border-color: var(--ca-primary, #3b82f6); }
.btn-sm-active:hover { opacity: 0.9; color: #fff; }
</style>
