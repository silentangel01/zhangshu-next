import { createRouter, createWebHistory } from 'vue-router'

import ImportPage from '@/pages/imports/ImportPage.vue'
import ProjectOutlinePage from '@/pages/outlines/ProjectOutlinePage.vue'
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
      component: ProjectOutlinePage,
    },
    {
      path: '/imports',
      name: 'imports',
      component: ImportPage,
    },
  ],
})

export default router
