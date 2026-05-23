import { API_BASE_URL, ApiError, apiRequest } from '@/shared/api/client'

import type { CreateProjectPayload, Project, UpdateProjectPayload } from './types'

export function listProjects(): Promise<Project[]> {
  return apiRequest<Project[]>('/api/projects')
}

export function getProject(projectId: string): Promise<Project> {
  return apiRequest<Project>(`/api/projects/${projectId}`)
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

export function getProjectCoverUrl(projectId: string, version?: number): string {
  const params = version !== undefined ? `?v=${version}` : ''
  return `${API_BASE_URL}/api/projects/${projectId}/cover${params}`
}

export async function uploadProjectCover(projectId: string, file: File): Promise<Project> {
  const form = new FormData()
  form.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/cover`, {
    method: 'POST',
    body: form,
  })

  if (!response.ok) {
    let message = `Cover upload failed: ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: unknown }
      if (typeof payload.detail === 'string') {
        message = payload.detail
      }
    } catch {
      // Keep status-based message.
    }
    throw new ApiError(message, response.status)
  }

  return (await response.json()) as Project
}

export async function deleteProjectCover(projectId: string): Promise<Project> {
  return apiRequest<Project>(`/api/projects/${projectId}/cover`, {
    method: 'DELETE',
  })
}
