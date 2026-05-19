import { createRouter, createWebHistory } from 'vue-router'

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
  ],
})

export default router
