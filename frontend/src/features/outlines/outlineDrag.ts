import type { OutlineItem, OutlineReorderItem, OutlineTreeNodeData } from '@/entities/outline/types'

export type DropPosition = 'before' | 'after' | 'inside'

export function buildOutlineTree(items: OutlineItem[]): OutlineTreeNodeData[] {
  const nodeMap = new Map<string, OutlineTreeNodeData>()
  const roots: OutlineTreeNodeData[] = []

  for (const item of items) {
    nodeMap.set(item.id, { item, children: [] })
  }

  const sorted = [...items].sort(
    (a, b) => a.order_index - b.order_index || a.created_at.localeCompare(b.created_at),
  )

  for (const item of sorted) {
    const node = nodeMap.get(item.id)
    if (!node) continue

    if (item.parent_id && nodeMap.has(item.parent_id)) {
      nodeMap.get(item.parent_id)!.children.push(node)
    } else {
      roots.push(node)
    }
  }

  return roots
}

export function isDescendant(
  nodeId: string,
  potentialAncestorId: string,
  items: OutlineItem[],
): boolean {
  const parentMap = new Map<string, string | null>()
  for (const item of items) {
    parentMap.set(item.id, item.parent_id)
  }

  let current = parentMap.get(nodeId)
  const visited = new Set<string>()
  while (current !== null && current !== undefined) {
    if (current === potentialAncestorId) return true
    if (visited.has(current)) break
    visited.add(current)
    current = parentMap.get(current)
  }
  return false
}

export function flattenTree(
  nodes: OutlineTreeNodeData[],
  result: OutlineItem[] = [],
): OutlineItem[] {
  for (const node of nodes) {
    result.push(node.item)
    flattenTree(node.children, result)
  }
  return result
}

export interface DropTarget {
  targetId: string | null
  position: DropPosition
}

export function buildReorderPayload(
  draggedId: string,
  dropTarget: DropTarget,
  allItems: OutlineItem[],
): OutlineReorderItem[] | null {
  const tree = buildOutlineTree(allItems)
  const flat = flattenTree(tree)

  // Prevent dropping onto self or descendant.
  if (
    dropTarget.targetId !== null &&
    dropTarget.position === 'inside' &&
    (dropTarget.targetId === draggedId ||
      isDescendant(dropTarget.targetId, draggedId, allItems))
  ) {
    return null
  }

  let newParentId: string | null = null
  let siblings: OutlineItem[] = []

  if (dropTarget.position === 'inside' && dropTarget.targetId !== null) {
    newParentId = dropTarget.targetId
    siblings = flat.filter((item) => item.parent_id === newParentId && item.id !== draggedId)
    const items: OutlineReorderItem[] = [
      { outline_id: draggedId, parent_id: newParentId, order_index: siblings.length },
    ]
    return items
  }

  // Before/after: same parent as target.
  const targetItem = dropTarget.targetId !== null
    ? flat.find((item) => item.id === dropTarget.targetId)
    : null
  newParentId = targetItem?.parent_id ?? null
  siblings = flat.filter(
    (item) => item.parent_id === newParentId && item.id !== draggedId,
  )

  const targetIndex = dropTarget.targetId !== null
    ? siblings.findIndex((item) => item.id === dropTarget.targetId)
    : -1

  if (targetIndex === -1 && siblings.length > 0) return null

  const insertIndex = dropTarget.position === 'before'
    ? targetIndex
    : targetIndex + 1

  const reordered = [
    ...siblings.slice(0, insertIndex),
    flat.find((item) => item.id === draggedId)!,
    ...siblings.slice(insertIndex),
  ]

  return reordered.map((item, index) => ({
    outline_id: item.id,
    parent_id: newParentId,
    order_index: index,
  }))
}
