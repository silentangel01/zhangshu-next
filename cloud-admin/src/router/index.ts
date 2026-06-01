import { createRouter, createWebHistory } from 'vue-router'

import LoginPage from '@/pages/LoginPage.vue'
import AdminLayout from '@/components/AdminLayout.vue'
import DashboardPage from '@/pages/DashboardPage.vue'
import FeedbackListPage from '@/pages/FeedbackListPage.vue'
import FeedbackDetailPage from '@/pages/FeedbackDetailPage.vue'
import UsersPage from '@/pages/UsersPage.vue'
import UserDetailPage from '@/pages/UserDetailPage.vue'
import AnnouncementsPage from '@/pages/AnnouncementsPage.vue'
import MonitoringPage from '@/pages/MonitoringPage.vue'
import { useAdminSession } from '@/shared/composables/useAdminSession'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginPage },
    {
      path: '/',
      component: AdminLayout,
      children: [
        {
          path: '',
          name: 'dashboard',
          component: DashboardPage,
          meta: { permissions: ['dashboard:view'] },
        },
        {
          path: 'feedback',
          name: 'feedback-list',
          component: FeedbackListPage,
          meta: { permissions: ['feedback:view'] },
        },
        {
          path: 'feedback/:id',
          name: 'feedback-detail',
          component: FeedbackDetailPage,
          meta: { permissions: ['feedback:view'] },
        },
        {
          path: 'users',
          name: 'users',
          component: UsersPage,
          meta: { permissions: ['users:view'] },
        },
        {
          path: 'users/:id',
          name: 'user-detail',
          component: UserDetailPage,
          meta: { permissions: ['users:view'] },
        },
        {
          path: 'announcements',
          name: 'announcements',
          component: AnnouncementsPage,
          meta: { permissions: ['announcements:view'] },
        },
        {
          path: 'monitoring',
          name: 'monitoring',
          component: MonitoringPage,
          meta: { permissions: ['monitoring:view'] },
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  if (to.name === 'login') {
    const { me } = useAdminSession()
    if (me.value) return { name: 'dashboard' }
    return
  }

  const loggedIn = sessionStorage.getItem('zs_admin_logged_in') === '1'
  if (!loggedIn) return { name: 'login' }

  // Validate real session via API (not just sessionStorage)
  const { ensureSession, hasPermission, clearSession } = useAdminSession()
  const session = await ensureSession()

  if (!session) {
    // Session expired or invalid — clear and redirect
    sessionStorage.removeItem('zs_admin_logged_in')
    clearSession()
    return { name: 'login' }
  }

  // Check page-level permission
  const required = to.meta.permissions as string[] | undefined
  if (required?.length && !required.some((p) => hasPermission(p))) {
    // User lacks permission for this page — redirect to dashboard
    return { name: 'dashboard' }
  }
})
