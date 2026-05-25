import { createRouter, createWebHistory } from 'vue-router'

import ProjectCharactersPage from '@/pages/characters/ProjectCharactersPage.vue'
import ProjectCluesPage from '@/pages/clues/ProjectCluesPage.vue'
import ImportPage from '@/pages/imports/ImportPage.vue'
import ProjectBackupPage from '@/pages/imports/ProjectBackupPage.vue'
import ProjectGraphPage from '@/pages/graph/ProjectGraphPage.vue'
import ProjectKnowledgePage from '@/pages/knowledge/ProjectKnowledgePage.vue'
import ProjectOutlinePage from '@/pages/outlines/ProjectOutlinePage.vue'
import ProjectDetailPage from '@/pages/projects/ProjectDetailPage.vue'
import ProjectsPage from '@/pages/projects/ProjectsPage.vue'
import ProjectTimelinePage from '@/pages/timeline/ProjectTimelinePage.vue'
import ProjectSettingsPage from '@/pages/settings/ProjectSettingsPage.vue'
import ProjectWritingStatsPage from '@/pages/stats/ProjectWritingStatsPage.vue'
import ReviewCheckPage from '@/pages/review/ReviewCheckPage.vue'
import SearchPage from '@/pages/search/SearchPage.vue'

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
      component: ProjectOutlinePage,
    },
    {
      path: '/projects/:projectId/characters',
      name: 'project-characters',
      component: ProjectCharactersPage,
    },
    {
      path: '/projects/:projectId/settings',
      name: 'project-settings',
      component: ProjectSettingsPage,
    },
    {
      path: '/projects/:projectId/clues',
      name: 'project-clues',
      component: ProjectCluesPage,
    },
    {
      path: '/projects/:projectId/graph',
      name: 'project-graph',
      component: ProjectGraphPage,
    },
    {
      path: '/projects/:projectId/timeline',
      name: 'project-timeline',
      component: ProjectTimelinePage,
    },
    {
      path: '/projects/:projectId/backup',
      name: 'project-backup',
      component: ProjectBackupPage,
    },
    {
      path: '/projects/:projectId/search',
      name: 'project-search',
      component: SearchPage,
    },
    {
      path: '/projects/:projectId/review',
      name: 'project-review',
      component: ReviewCheckPage,
    },
    {
      path: '/projects/:projectId/knowledge',
      name: 'project-knowledge',
      component: ProjectKnowledgePage,
    },
    {
      path: '/projects/:projectId/stats',
      name: 'project-stats',
      component: ProjectWritingStatsPage,
    },
    {
      path: '/backup',
      name: 'backup',
      component: ProjectBackupPage,
    },
    {
      path: '/imports',
      name: 'imports',
      component: ImportPage,
    },
  ],
})

export default router
