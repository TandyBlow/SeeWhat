import type { TreeNode } from '../../types/node'

/** Depth-first push of every node id into `result`. */
export function collectAllIds(nodes: TreeNode[], result: string[]): void {
  for (const node of nodes) {
    result.push(node.id)
    collectAllIds(node.children, result)
  }
}

/** Builds an id -> set of all descendant ids map for drag-move guard. */
export function buildDescendantMap(nodes: TreeNode[], map: Map<string, Set<string>>): void {
  for (const node of nodes) {
    const arr: string[] = []
    collectAllIds(node.children, arr)
    map.set(node.id, new Set(arr))
    buildDescendantMap(node.children, map)
  }
}
