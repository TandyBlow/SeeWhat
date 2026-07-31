import { onMounted, onUnmounted, inject } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import type { NodeRecord } from '../../types/node'
import type { NavItem } from './NavigationTypes'
import type { NavigationState } from './NavigationState'

export function useNavigationInteract(
  state: NavigationState,
  anim: { animateSmallLayoutAdd: () => Promise<void> },
) {
  const startSmallLayoutOfficialTransition = inject<(item: NavItem, rowEl: HTMLElement) => void>(
    'startSmallLayoutOfficialTransition',
    () => {},
  )

  function onRowClick(nodeId: string): void {
    if (state.isAnimating.value || state.navAnimating.value || state.otAnimating.value) return
    if (state.actionNodeId.value === nodeId) return
    openNode(nodeId)
  }

  function onContextMenu(nodeId: string): void {
    if (state.isAnimating.value || state.navAnimating.value || state.otAnimating.value) return
    toggleActions(nodeId)
  }

  function openNode(nodeId: string): void {
    if (state.pressedNodeId.value || state.navAnimating.value || state.otAnimating.value) return
    state.actionNodeId.value = null
    state.pressedNodeId.value = nodeId

    // Record navigation transition (fire-and-forget)
    const fromId = state.store.activeNode?.id ?? null
    if (fromId && fromId !== nodeId) {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:7860'
      const token = localStorage.getItem('acacia_backend_token')
      fetch(`${backendUrl}/context/record-transition`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          from_node_id: fromId,
          to_node_id: nodeId,
          transition_type: 'navigation',
          reason: '',
        }),
      }).catch(() => {})
    }

    setTimeout(() => {
      state.store.loadNode(nodeId).catch(() => {
        state.pressedNodeId.value = null
      })
      // 安全超时：若 childNodes 未变化（watcher 未触发），3s 后强制重置
      setTimeout(() => {
        if (state.pressedNodeId.value === nodeId) {
          state.pressedNodeId.value = null
        }
      }, 3000)
    }, 200)
  }

  function onAddClick(): void {
    if (state.addPressed.value) {
      state.store.cancelOperation()
      return
    }
    if (state.layoutType.value === 'small') {
      anim.animateSmallLayoutAdd()
    } else {
      state.store.startAdd()
    }
  }

  function onOfficialClick(item: NavItem): void {
    if (state.pressedOfficialId.value === item.id) {
      state.resetOfficialTransition()
      state.store.cancelOperation()
    } else if (state.layoutType.value === 'small') {
      const rowEl = getRowElement(item.id)
      if (rowEl) {
        startSmallLayoutOfficialTransition(item, rowEl as HTMLElement)
      }
    } else {
      item.action!()
    }
  }

  function getRowElement(itemId: string): Element | null {
    const inst = state.nodeListRef.value
    if (!inst) return null
    const el = '$el' in inst ? (inst as ComponentPublicInstance).$el : inst
    if (!(el instanceof HTMLElement)) return null
    return el.querySelector(`[data-item-id="${itemId}"]`) ?? null
  }

  function onAnchorOfficialClick(): void {
    state.resetOfficialTransition()
    state.store.cancelOperation()
  }

  function toggleActions(nodeId: string): void {
    state.actionNodeId.value = state.actionNodeId.value === nodeId ? null : nodeId
  }

  function onDocumentClick(e: MouseEvent): void {
    if (state.actionNodeId.value === null) return
    if ((e.target as HTMLElement).closest('.inline-actions')) return
    state.actionNodeId.value = null
  }

  onMounted(() => document.addEventListener('click', onDocumentClick, true))
  onUnmounted(() => document.removeEventListener('click', onDocumentClick, true))

  async function moveNode(node: NodeRecord): Promise<void> {
    state.actionNodeId.value = null
    if (state.layoutType.value === 'small') {
      state.compactMode.value = 'content'
    }
    await state.store.startMove(node)
  }

  async function deleteNode(node: NodeRecord): Promise<void> {
    state.actionNodeId.value = null
    if (state.layoutType.value === 'small') {
      state.compactMode.value = 'content'
    }
    await state.store.startDelete(node)
  }

  return { onRowClick, onContextMenu, onOfficialClick, onAnchorOfficialClick, onAddClick, moveNode, deleteNode }
}
