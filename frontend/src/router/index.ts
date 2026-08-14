import { createRouter, createWebHistory } from 'vue-router'

import CloudProfilePage from '@/pages/account/CloudProfilePage.vue'
import ProjectDetailPage from '@/pages/projects/ProjectDetailPage.vue'
import ProjectsPage from '@/pages/projects/ProjectsPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/projects',
    },
    {
      path: '/projects',
      name: 'projects',
      component: ProjectsPage,
    },
    {
      path: '/projects/:projectId',
      name: 'project-detail',
      component: ProjectDetailPage,
    },
    {
      path: '/projects/:projectId/outlines',
      name: 'project-outlines',
      component: () => import('@/pages/outlines/ProjectOutlinePage.vue'),
    },
    {
      path: '/projects/:projectId/characters',
      name: 'project-characters',
      component: () => import('@/pages/characters/ProjectCharactersPage.vue'),
    },
    {
      path: '/projects/:projectId/settings',
      name: 'project-settings',
      component: () => import('@/pages/settings/ProjectSettingsPage.vue'),
    },
    {
      path: '/projects/:projectId/clues',
      name: 'project-clues',
      component: () => import('@/pages/clues/ProjectCluesPage.vue'),
    },
    {
      path: '/projects/:projectId/graph',
      name: 'project-graph',
      component: () => import('@/pages/graph/ProjectGraphPage.vue'),
    },
    {
      path: '/projects/:projectId/timeline',
      name: 'project-timeline',
      component: () => import('@/pages/timeline/ProjectTimelinePage.vue'),
    },
    {
      path: '/projects/:projectId/backup',
      name: 'project-backup',
      component: () => import('@/pages/imports/ProjectBackupPage.vue'),
    },
    {
      path: '/projects/:projectId/search',
      name: 'project-search',
      component: () => import('@/pages/search/SearchPage.vue'),
    },
    {
      path: '/projects/:projectId/versions',
      name: 'project-versions',
      component: () => import('@/pages/versions/ProjectVersionsPage.vue'),
    },
    {
      path: '/projects/:projectId/review',
      name: 'project-review',
      component: () => import('@/pages/review/ReviewCheckPage.vue'),
    },
    {
      path: '/projects/:projectId/knowledge',
      name: 'project-knowledge',
      component: () => import('@/pages/knowledge/ProjectKnowledgePage.vue'),
    },
    {
      path: '/projects/:projectId/stats',
      name: 'project-stats',
      component: () => import('@/pages/stats/ProjectWritingStatsPage.vue'),
    },
    {
      path: '/backup',
      name: 'backup',
      component: () => import('@/pages/imports/ProjectBackupPage.vue'),
    },
    {
      path: '/imports',
      name: 'imports',
      component: () => import('@/pages/imports/ImportPage.vue'),
    },
    {
      path: '/account',
      name: 'cloud-account-profile',
      component: CloudProfilePage,
    },
    {
      path: '/account/feedback',
      name: 'cloud-feedback-history',
      component: () => import('@/pages/account/FeedbackHistoryPage.vue'),
    },
    {
      path: '/account/security',
      name: 'cloud-account-security',
      component: () => import('@/pages/account/AccountSecurityPage.vue'),
    },
  ],
})

export default router
