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

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginPage },
    {
      path: '/',
      component: AdminLayout,
      children: [
        { path: '', name: 'dashboard', component: DashboardPage },
        { path: 'feedback', name: 'feedback-list', component: FeedbackListPage },
        {
          path: 'feedback/:id',
          name: 'feedback-detail',
          component: FeedbackDetailPage,
        },
        { path: 'users', name: 'users', component: UsersPage },
        {
          path: 'users/:id',
          name: 'user-detail',
          component: UserDetailPage,
        },
        { path: 'announcements', name: 'announcements', component: AnnouncementsPage },
        { path: 'monitoring', name: 'monitoring', component: MonitoringPage },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const loggedIn = sessionStorage.getItem('zs_admin_logged_in') === '1'
  if (to.name !== 'login' && !loggedIn) {
    return { name: 'login' }
  }
  if (to.name === 'login' && loggedIn) {
    return { name: 'dashboard' }
  }
})
