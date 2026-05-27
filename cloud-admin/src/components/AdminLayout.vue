<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { adminLogout, adminMe } from '@/entities/admin-auth/api'
import type { AdminMeResponse } from '@/entities/admin-auth/types'

const router = useRouter()
const me = ref<AdminMeResponse | null>(null)

onMounted(async () => {
  try {
    me.value = await adminMe()
  } catch {
    router.push('/login')
  }
})

async function logout() {
  try {
    await adminLogout()
  } catch {
    /* ignore */
  }
  sessionStorage.removeItem('zs_admin_logged_in')
  router.push('/login')
}
</script>

<template>
  <div class="admin-layout">
    <aside class="sidebar">
      <div class="sidebar-brand">
        <strong>章枢</strong> 管理后台
      </div>
      <nav class="sidebar-nav">
        <RouterLink to="/" class="nav-link" active-class="active" :exact="true">
          概览
        </RouterLink>
        <RouterLink to="/feedback" class="nav-link" active-class="active">
          反馈管理
        </RouterLink>
        <RouterLink to="/users" class="nav-link" active-class="active">
          用户列表
        </RouterLink>
        <RouterLink to="/announcements" class="nav-link" active-class="active">
          公告管理
        </RouterLink>
        <RouterLink to="/monitoring" class="nav-link" active-class="active">
          运维监控
        </RouterLink>
      </nav>
      <div class="sidebar-footer">
        <span class="admin-name">{{ me?.display_name ?? me?.email ?? '' }}</span>
        <button class="btn-logout" @click="logout">退出</button>
      </div>
    </aside>
    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
}
.sidebar {
  width: 220px;
  background: var(--ca-surface);
  border-right: 1px solid var(--ca-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.sidebar-brand {
  padding: var(--ca-space-5);
  border-bottom: 1px solid var(--ca-border);
  font-size: 15px;
}
.sidebar-nav {
  flex: 1;
  padding: var(--ca-space-3);
  display: flex;
  flex-direction: column;
  gap: var(--ca-space-1);
}
.nav-link {
  display: block;
  padding: var(--ca-space-2) var(--ca-space-3);
  border-radius: var(--ca-radius);
  color: var(--ca-text-muted);
  font-size: 14px;
}
.nav-link:hover {
  background: var(--ca-bg);
  color: var(--ca-text);
  text-decoration: none;
}
.nav-link.active {
  background: #eff6ff;
  color: var(--ca-primary);
  font-weight: 500;
}
.sidebar-footer {
  padding: var(--ca-space-4);
  border-top: 1px solid var(--ca-border);
  display: flex;
  flex-direction: column;
  gap: var(--ca-space-2);
  font-size: 13px;
}
.admin-name {
  color: var(--ca-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.btn-logout {
  padding: var(--ca-space-1) var(--ca-space-3);
  border: 1px solid var(--ca-border);
  border-radius: var(--ca-radius);
  background: var(--ca-surface);
  color: var(--ca-text-muted);
  font-size: 13px;
}
.btn-logout:hover {
  border-color: var(--ca-danger);
  color: var(--ca-danger);
}
.main-content {
  flex: 1;
  padding: var(--ca-space-6);
  overflow-y: auto;
}
</style>
