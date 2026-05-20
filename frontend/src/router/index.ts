import { createRouter, createWebHistory } from 'vue-router'

import ProjectCharactersPage from '@/pages/characters/ProjectCharactersPage.vue'
import ProjectCluesPage from '@/pages/clues/ProjectCluesPage.vue'
import ImportPage from '@/pages/imports/ImportPage.vue'
import ProjectOutlinePage from '@/pages/outlines/ProjectOutlinePage.vue'
import ProjectDetailPage from '@/pages/projects/ProjectDetailPage.vue'
import ProjectsPage from '@/pages/projects/ProjectsPage.vue'
import ProjectSettingsPage from '@/pages/settings/ProjectSettingsPage.vue'

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
      path: '/imports',
      name: 'imports',
      component: ImportPage,
    },
  ],
})

export default router
