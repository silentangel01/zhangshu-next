<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { adminLogout, adminMe, adminRefresh } from '@/entities/admin-auth/api'
import type { AdminMeResponse } from '@/entities/admin-auth/types'
import { apiRequest } from '@/shared/api/client'
import ToastContainer from '@/shared/ui/ToastContainer.vue'
import { useToast } from '@/shared/composables/useToast'

const router = useRouter()
const toast = useToast()
const me = ref<AdminMeResponse | null>(null)

const REFRESH_INTERVAL = 25 * 60 * 1000 // 25 minutes
let refreshTimer: ReturnType<typeof setInterval> | null = null

// ── Global search ──────────────────────────────────────────────────────
interface SearchResult {
  id: string
  title?: string
  email?: string
  display_name?: string
  status?: string
}
interface SearchResults {
  users: SearchResult[]
  feedback: SearchResult[]
  announcements: SearchResult[]
}

const searchQuery = ref('')
const searchResults = ref<SearchResults | null>(null)
const showSearchDropdown = ref(false)
let searchTimer: ReturnType<typeof setTimeout> | null = null

watch(searchQuery, (val) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (!val.trim()) {
    searchResults.value = null
    showSearchDropdown.value = false
    return
  }
  searchTimer = setTimeout(() => doSearch(val.trim()), 300)
})

async function doSearch(q: string) {
  try {
    searchResults.value = await apiRequest<SearchResults>(
      `/api/admin/search?q=${encodeURIComponent(q)}`,
    )
    showSearchDropdown.value = true
  } catch {
    searchResults.value = null
  }
}

function navigateTo(path: string) {
  showSearchDropdown.value = false
  searchQuery.value = ''
  searchResults.value = null
  router.push(path)
}

function hasResults(): boolean {
  if (!searchResults.value) return false
  const r = searchResults.value
  return r.users.length > 0 || r.feedback.length > 0 || r.announcements.length > 0
}

function closeSearch() {
  // Delay to allow click events on dropdown items
  setTimeout(() => {
    showSearchDropdown.value = false
  }, 200)
}

onMounted(async () => {
  try {
    me.value = await adminMe()
  } catch {
    router.push('/login')
    return
  }
  refreshTimer = setInterval(doRefresh, REFRESH_INTERVAL)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  if (searchTimer) {
    clearTimeout(searchTimer)
  }
})

async function doRefresh() {
  try {
    await adminRefresh()
  } catch {
    toast.error('会话已过期，请重新登录')
    sessionStorage.removeItem('zs_admin_logged_in')
    router.push('/login')
  }
}

async function logout() {
  try {
    await adminLogout()
  } catch {
    /* best effort */
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
      <div class="sidebar-search">
        <input
          v-model="searchQuery"
          class="input search-input"
          placeholder="搜索用户、反馈、公告..."
          @focus="searchResults && (showSearchDropdown = true)"
          @blur="closeSearch"
        />
        <div v-if="showSearchDropdown" class="search-dropdown">
          <div v-if="!hasResults()" class="search-empty">无匹配结果</div>
          <template v-else>
            <div v-if="searchResults!.users.length" class="search-group">
              <div class="search-group-label">用户</div>
              <a
                v-for="u in searchResults!.users"
                :key="u.id"
                href="#"
                class="search-item"
                @mousedown.prevent="navigateTo(`/users/${u.id}`)"
              >
                {{ u.display_name || u.email }}
                <span class="search-item-sub">{{ u.email }}</span>
              </a>
            </div>
            <div v-if="searchResults!.feedback.length" class="search-group">
              <div class="search-group-label">反馈</div>
              <a
                v-for="f in searchResults!.feedback"
                :key="f.id"
                href="#"
                class="search-item"
                @mousedown.prevent="navigateTo(`/feedback/${f.id}`)"
              >
                {{ f.title }}
                <span class="search-item-sub badge badge-info">{{ f.status }}</span>
              </a>
            </div>
            <div v-if="searchResults!.announcements.length" class="search-group">
              <div class="search-group-label">公告</div>
              <a
                v-for="a in searchResults!.announcements"
                :key="a.id"
                href="#"
                class="search-item"
                @mousedown.prevent="navigateTo('/announcements')"
              >
                {{ a.title }}
                <span class="search-item-sub badge badge-info">{{ a.status }}</span>
              </a>
            </div>
          </template>
        </div>
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
    <ToastContainer />
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
.sidebar-search {
  position: relative;
  padding: var(--ca-space-3);
  border-bottom: 1px solid var(--ca-border);
}
.search-input {
  width: 100%;
  padding: var(--ca-space-2) var(--ca-space-3);
  font-size: 13px;
  border: 1px solid var(--ca-border);
  border-radius: var(--ca-radius);
  background: var(--ca-bg);
}
.search-input:focus {
  outline: none;
  border-color: var(--ca-primary);
}
.search-dropdown {
  position: absolute;
  top: 100%;
  left: var(--ca-space-3);
  right: var(--ca-space-3);
  background: var(--ca-surface);
  border: 1px solid var(--ca-border);
  border-radius: var(--ca-radius);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 100;
  max-height: 360px;
  overflow-y: auto;
}
.search-empty {
  padding: var(--ca-space-4);
  text-align: center;
  color: var(--ca-text-muted);
  font-size: 13px;
}
.search-group { border-top: 1px solid var(--ca-border); }
.search-group:first-child { border-top: none; }
.search-group-label {
  padding: var(--ca-space-2) var(--ca-space-3);
  font-size: 11px;
  color: var(--ca-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  background: var(--ca-bg);
}
.search-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--ca-space-2) var(--ca-space-3);
  font-size: 13px;
  color: var(--ca-text);
  text-decoration: none;
  cursor: pointer;
}
.search-item:hover {
  background: var(--ca-bg);
  text-decoration: none;
}
.search-item-sub {
  font-size: 11px;
  color: var(--ca-text-muted);
  margin-left: var(--ca-space-2);
  flex-shrink: 0;
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
