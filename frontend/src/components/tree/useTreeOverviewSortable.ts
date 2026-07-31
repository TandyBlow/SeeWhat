import { ref, type Ref } from 'vue'
import Sortable from 'sortablejs'
import { useNodeStore, getDataAdapter } from '../../stores/nodeStore'
import type { TreeNode } from '../../types/node'
import { buildDescendantMap } from './treeOverviewUtil'

/**
 * Owns all SortableJS wiring for TreeOverview: the sortables array, the
 * wasDragging ref, destroySortables(), and initSortables().
 */
export function useTreeOverviewSortable(opts: {
  treeRef: Ref<HTMLElement | null>
  rootZoneRef: Ref<HTMLElement | null>
  treeNodes: Ref<TreeNode[]>
}) {
  const store = useNodeStore()
  const wasDragging = ref(false)

  let sortables: Sortable[] = []

  function destroySortables(): void {
    for (const s of sortables) {
      s.destroy()
    }
    sortables = []
  }

  function initSortables(): void {
    destroySortables()

    const descendantMap = new Map<string, Set<string>>()
    buildDescendantMap(opts.treeNodes.value, descendantMap)

    const handleDragMove = (evt: Sortable.MoveEvent): boolean => {
      const nodeId = (evt.dragged as HTMLElement).dataset.nodeId
      const targetParentId = (evt.to as HTMLElement).dataset.parentId
      if (!nodeId) return true
      if (targetParentId) {
        const descendants = descendantMap.get(nodeId)
        if (descendants && descendants.has(targetParentId)) {
          return false
        }
      }
      return true
    }

    const handleDragEnd = async (evt: Sortable.SortableEvent): Promise<void> => {
      const nodeId = (evt.item as HTMLElement).dataset.nodeId
      const newParentId = (evt.to as HTMLElement).dataset.parentId ?? null
      const oldParentId = (evt.from as HTMLElement).dataset.parentId ?? null

      if (!nodeId) return

      if (newParentId === oldParentId) {
        await store.refreshTree()
        return
      }

      try {
        const adapter = getDataAdapter()
        await adapter.moveNode(nodeId, newParentId || null)
        await store.refreshTree()
      } catch (e) {
        console.error('[TreeOverview] moveNode failed:', e)
        await store.refreshTree()
      }
    }

    const rootZone = opts.rootZoneRef.value
    if (rootZone) {
      sortables.push(new Sortable(rootZone, {
        group: {
          name: 'tree-nodes',
          pull: false,
          put: true,
        },
        animation: 150,
        delay: 400,
        delayOnTouchOnly: false,
        onStart: () => {
          wasDragging.value = true
        },
        onEnd: handleDragEnd,
        onMove: handleDragMove,
      }))
    }

    const lists = opts.treeRef.value?.querySelectorAll<HTMLElement>('[data-sortable]:not(.root-zone)')
    lists?.forEach((list) => {
      sortables.push(new Sortable(list, {
        group: 'tree-nodes',
        animation: 150,
        sort: false,
        delay: 400,
        delayOnTouchOnly: false,
        touchStartThreshold: 3,
        filter: '.expand-btn',
        preventOnFilter: false,
        onStart: () => {
          wasDragging.value = true
        },
        onEnd: handleDragEnd,
        onMove: handleDragMove,
      }))
    })
  }

  return { initSortables, destroySortables, wasDragging }
}
