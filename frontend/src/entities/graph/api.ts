import { apiRequest } from '@/shared/api/client'

import type {
  GraphEdge,
  GraphEdgeCreatePayload,
  GraphEdgeFilters,
  GraphEdgeUpdatePayload,
  GraphNode,
  GraphNodeCreatePayload,
  GraphNodeFilters,
  GraphNodeUpdatePayload,
} from './types'

function buildQuery(filters?: object): string {
  if (!filters) {
    return ''
  }

  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value))
    }
  })

  const query = params.toString()
  return query ? `?${query}` : ''
}

export function listGraphNodes(projectId: string, filters?: GraphNodeFilters): Promise<GraphNode[]> {
  return apiRequest<GraphNode[]>(`/api/projects/${projectId}/graph-nodes${buildQuery(filters)}`)
}

export function createGraphNode(
  projectId: string,
  payload: GraphNodeCreatePayload,
): Promise<GraphNode> {
  return apiRequest<GraphNode>(`/api/projects/${projectId}/graph-nodes`, {
    method: 'POST',
    body: payload,
  })
}

export function getGraphNode(nodeId: string): Promise<GraphNode> {
  return apiRequest<GraphNode>(`/api/graph-nodes/${nodeId}`)
}

export function updateGraphNode(
  nodeId: string,
  payload: GraphNodeUpdatePayload,
): Promise<GraphNode> {
  return apiRequest<GraphNode>(`/api/graph-nodes/${nodeId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteGraphNode(nodeId: string): Promise<GraphNode> {
  return apiRequest<GraphNode>(`/api/graph-nodes/${nodeId}`, {
    method: 'DELETE',
  })
}

export function listGraphEdges(projectId: string, filters?: GraphEdgeFilters): Promise<GraphEdge[]> {
  return apiRequest<GraphEdge[]>(`/api/projects/${projectId}/graph-edges${buildQuery(filters)}`)
}

export function createGraphEdge(
  projectId: string,
  payload: GraphEdgeCreatePayload,
): Promise<GraphEdge> {
  return apiRequest<GraphEdge>(`/api/projects/${projectId}/graph-edges`, {
    method: 'POST',
    body: payload,
  })
}

export function getGraphEdge(edgeId: string): Promise<GraphEdge> {
  return apiRequest<GraphEdge>(`/api/graph-edges/${edgeId}`)
}

export function updateGraphEdge(
  edgeId: string,
  payload: GraphEdgeUpdatePayload,
): Promise<GraphEdge> {
  return apiRequest<GraphEdge>(`/api/graph-edges/${edgeId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteGraphEdge(edgeId: string): Promise<GraphEdge> {
  return apiRequest<GraphEdge>(`/api/graph-edges/${edgeId}`, {
    method: 'DELETE',
  })
}
