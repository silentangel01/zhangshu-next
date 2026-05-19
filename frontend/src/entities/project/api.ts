import { apiRequest } from '@/shared/api/client'

import type { CreateProjectPayload, Project, UpdateProjectPayload } from './types'

export function listProjects(): Promise<Project[]> {
  return apiRequest<Project[]>('/api/projects')
}

export function createProject(payload: CreateProjectPayload): Promise<Project> {
  return apiRequest<Project>('/api/projects', {
    method: 'POST',
    body: payload,
  })
}

export function updateProject(projectId: string, payload: UpdateProjectPayload): Promise<Project> {
  return apiRequest<Project>(`/api/projects/${projectId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteProject(projectId: string): Promise<Project> {
  return apiRequest<Project>(`/api/projects/${projectId}`, {
    method: 'DELETE',
  })
}
