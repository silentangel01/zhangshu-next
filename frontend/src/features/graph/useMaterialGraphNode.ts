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

export function graphFocusRoute(projectId: string, nodeId: string) {
  return `/projects/${projectId}/graph?focusNodeId=${encodeURIComponent(nodeId)}`
}
