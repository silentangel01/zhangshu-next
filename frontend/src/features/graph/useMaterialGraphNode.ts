import { createGraphNode, listGraphNodes } from '@/entities/graph/api'
import type { GraphNodeBoundType, GraphNodeType } from '@/entities/graph/types'

type MaterialGraphNodeInput = {
  projectId: string
  boundType: Exclude<GraphNodeBoundType, 'custom'>
  boundId: string
  nodeType: GraphNodeType
  title: string
  summary: string
}

export async function ensureMaterialGraphNode(input: MaterialGraphNodeInput) {
  const existingNodes = await listGraphNodes(input.projectId, {
    bound_type: input.boundType,
    bound_id: input.boundId,
  })
  const existing = existingNodes.find((node) => node.visibility !== 'hidden')
  if (existing) {
    return existing
  }

  return createGraphNode(input.projectId, {
    title: input.title,
    node_type: input.nodeType,
    bound_type: input.boundType,
    bound_id: input.boundId,
    summary: input.summary,
    x: 320,
    y: 220,
    width: 160,
    height: 72,
    size: 2,
    visibility: 'normal',
  })
}

export type GraphReturnTarget = 'characters' | 'settings' | 'clues' | 'timeline' | 'outlines'

export interface GraphFocusRouteOptions {
  returnTo?: GraphReturnTarget
  returnId?: string
  returnLabel?: string
}

export function graphFocusRoute(projectId: string, nodeId: string, options?: GraphFocusRouteOptions) {
  const params = new URLSearchParams()
  params.set('focusNodeId', nodeId)
  if (options?.returnTo) {
    params.set('returnTo', options.returnTo)
    if (options.returnId) params.set('returnId', options.returnId)
    if (options.returnLabel) params.set('returnLabel', options.returnLabel)
  }
  return `/projects/${projectId}/graph?${params.toString()}`
}
