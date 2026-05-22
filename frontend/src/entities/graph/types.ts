export type GraphNodeType =
  | 'character'
  | 'setting'
  | 'clue'
  | 'timeline_event'
  | 'organization'
  | 'location'
  | 'custom'

export type GraphNodeBoundType = 'character' | 'setting' | 'clue' | 'timeline_event' | 'custom'
export type GraphVisibility = 'normal' | 'subtle' | 'hidden'

export type GraphEdgeRelationType =
  | 'relationship'
  | 'conflict'
  | 'ally'
  | 'family'
  | 'belongs_to'
  | 'controls'
  | 'clue_related'
  | 'timeline_related'
  | 'setting_related'
  | 'cause'
  | 'custom'

export type GraphEdgeDirection = 'directed' | 'undirected'
export type GraphEdgeLineStyle = 'solid' | 'dashed' | 'dotted' | 'arc'

export interface GraphNode {
  id: string
  project_id: string
  title: string
  node_type: GraphNodeType
  bound_type: GraphNodeBoundType | null
  bound_id: string | null
  summary: string
  x: number
  y: number
  width: number
  height: number
  color: string | null
  size: number
  visibility: GraphVisibility
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
}

export interface GraphNodePayload {
  title: string
  node_type: GraphNodeType
  bound_type?: GraphNodeBoundType | null
  bound_id?: string | null
  summary?: string
  x?: number
  y?: number
  width?: number
  height?: number
  color?: string | null
  size?: number
  visibility?: GraphVisibility
}

export type GraphNodeCreatePayload = GraphNodePayload
export type GraphNodeUpdatePayload = Partial<GraphNodePayload>

export interface GraphEdge {
  id: string
  project_id: string
  from_node_id: string
  to_node_id: string
  relation_type: GraphEdgeRelationType
  direction: GraphEdgeDirection
  strength: number
  label: string
  note: string
  line_style: GraphEdgeLineStyle
  visibility: GraphVisibility
  created_at: string
  updated_at: string
  deleted_at: string | null
  version: number
}

export interface GraphEdgePayload {
  from_node_id: string
  to_node_id: string
  relation_type: GraphEdgeRelationType
  direction?: GraphEdgeDirection
  strength?: number
  label?: string
  note?: string
  line_style?: GraphEdgeLineStyle
  visibility?: GraphVisibility
}

export type GraphEdgeCreatePayload = GraphEdgePayload
export type GraphEdgeUpdatePayload = Partial<GraphEdgePayload>

export interface GraphNodeFilters {
  node_type?: GraphNodeType
  bound_type?: GraphNodeBoundType
  bound_id?: string
  visibility?: GraphVisibility
  keyword?: string
}

export interface GraphEdgeFilters {
  relation_type?: GraphEdgeRelationType
  visibility?: GraphVisibility
}

export const graphNodeTypeLabels: Record<GraphNodeType, string> = {
  character: '人物',
  setting: '设定',
  clue: '伏笔',
  timeline_event: '时间轴事件',
  organization: '组织',
  location: '地点',
  custom: '自定义',
}

export const graphNodeBoundTypeLabels: Record<GraphNodeBoundType, string> = {
  character: '人物',
  setting: '设定',
  clue: '伏笔',
  timeline_event: '时间轴事件',
  custom: '自定义',
}

export const graphNodeVisibilityLabels: Record<GraphVisibility, string> = {
  normal: '正常',
  subtle: '弱化',
  hidden: '隐藏',
}

export const graphEdgeRelationLabels: Record<GraphEdgeRelationType, string> = {
  relationship: '关系',
  conflict: '冲突',
  ally: '同盟',
  family: '亲属',
  belongs_to: '归属',
  controls: '控制',
  clue_related: '伏笔相关',
  timeline_related: '时间线相关',
  setting_related: '设定相关',
  cause: '因果',
  custom: '自定义',
}

export const graphEdgeDirectionLabels: Record<GraphEdgeDirection, string> = {
  directed: '有向',
  undirected: '无向',
}

export const graphEdgeLineStyleLabels: Record<GraphEdgeLineStyle, string> = {
  solid: '实线',
  dashed: '虚线',
  dotted: '点线',
  arc: '弧线',
}

export const graphVisibilityLabels = graphNodeVisibilityLabels
