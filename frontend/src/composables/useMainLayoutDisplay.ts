import { computed } from 'vue'
import type { ComputedRef } from 'vue'
import { storeToRefs } from 'pinia'
import { useNodeStore } from '../stores/nodeStore'
import { useAuthStore } from '../stores/authStore'
import { useKnobDispatch } from './useKnobDispatch'
import { CONTENT_DIRECT_STATES } from './useMainLayoutState'
import AuthPanel from '../components/auth/AuthPanel.vue'
import GlobalTree from '../components/tree/GlobalTree.vue'
import TreeOverview from '../components/tree/TreeOverview.vue'
import ConfirmPanel from '../components/ui/ConfirmPanel.vue'
import DailyQuizPanel from '../components/official/DailyQuizPanel.vue'
import OfficialContentPanel from '../components/official/OfficialContentPanel.vue'
import MarkdownEditor from '../components/editor/MarkdownEditor.vue'
import type { MainLayoutState } from './useMainLayoutState'

export interface MainLayoutDisplay {
  layoutClasses: ComputedRef<Record<string, boolean>>
  showEmptyBackground: ComputedRef<boolean>
  showTree: ComputedRef<boolean>
  nonTreeContent: ComputedRef<unknown>
  contentKey: ComputedRef<string>
  skipContentGlass: ComputedRef<boolean>
}

/**
 * All display-state computeds plus the initial displayed-ref sync.
 * Computes which content (tree vs panel vs editor) should show.
 */
export function useMainLayoutDisplay(state: MainLayoutState): MainLayoutDisplay {
  const nodeStore = useNodeStore()
  const authStore = useAuthStore()
  const { activeNode, isEmpty } = storeToRefs(nodeStore)
  const {
    mode: authMode,
    isAuthenticated,
    initialized,
  } = storeToRefs(authStore)
  const { layoutType, compactMode } = useKnobDispatch()

  const isSmallLayoutMixed = computed(() => {
    if (layoutType.value !== 'small' || compactMode.value !== 'nav') return false
    return CONTENT_DIRECT_STATES.includes(nodeStore.viewState)
  })

  // In CONTENT_DIRECT_STATES, skip the outer content-glass active area.
  // The content components bring their own GlassWrappers, which become direct
  // children of the content-inset bottom area — avoiding nested active areas.
  const skipContentGlass = computed(() => {
    return CONTENT_DIRECT_STATES.includes(nodeStore.viewState)
  })

  const layoutClasses = computed(() => ({
    'large': layoutType.value === 'large',
    'medium': layoutType.value === 'medium',
    'compact': layoutType.value === 'small',
    'compact-content': layoutType.value === 'small' && compactMode.value === 'content',
    'compact-nav': layoutType.value === 'small' && compactMode.value === 'nav',
    'compact-mixed': isSmallLayoutMixed.value,
    'is-too-small': state.isTooSmall.value,
    'page-animating': state.isPageAnimating.value,
    'initial-loading': state.initialRender.value,
  }))

  const showEmptyBackground = computed(() =>
    isEmpty.value && !nodeStore.activeNode && nodeStore.viewState === 'display'
  )

  const showTree = computed(() => {
    return isAuthenticated.value && !activeNode.value && !nodeStore.isConfirmState && !nodeStore.isDailyQuizState && !nodeStore.isOfficialContentState && !nodeStore.isTreeOverviewState && !isEmpty.value
  })

  const nonTreeContent = computed(() => {
    if (!initialized.value) {
      return null
    }
    if (!isAuthenticated.value) {
      return AuthPanel
    }
    if (nodeStore.isTreeOverviewState) {
      return TreeOverview
    }
    if (nodeStore.isTreeState) {
      return GlobalTree
    }
    if (nodeStore.isConfirmState) {
      return ConfirmPanel
    }
    if (nodeStore.isDailyQuizState) {
      return DailyQuizPanel
    }
    if (nodeStore.isOfficialContentState) {
      return OfficialContentPanel
    }
    return MarkdownEditor
  })

  const contentKey = computed(() => {
    if (!initialized.value) {
      return 'loading'
    }
    if (!isAuthenticated.value) {
      return `auth:${authMode.value}`
    }
    const viewState = nodeStore.viewState
    return `${viewState}:${activeNode.value?.id ?? 'editor'}`
  })

  // Initialize displayed refs with current values
  state.displayedKey.value = contentKey.value
  state.displayedShowTree.value = showTree.value
  state.displayedNonTreeContent.value = nonTreeContent.value
  state.displayedSkipContentGlass.value = skipContentGlass.value
  state.treeOverlayActive.value = showTree.value

  return {
    layoutClasses,
    showEmptyBackground,
    showTree,
    nonTreeContent,
    contentKey,
    skipContentGlass,
  }
}
