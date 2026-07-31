import { ref, computed, type Ref, type ComputedRef, type ComponentPublicInstance } from 'vue'
import { storeToRefs } from 'pinia'
import { useNodeStore, type OfficialNode } from '../../stores/nodeStore'
import { useAuthStore } from '../../stores/authStore'
import { useDevStore } from '../../stores/devStore'
import { useKnobDispatch } from '../../composables/useKnobDispatch'
import { useOfficialTransition, type OfficialTransitionPhase } from '../../composables/useOfficialTransition'
import type { NodeRecord, ViewState } from '../../types/node'
import type { LayoutType, CompactMode } from '../../types/transition'
import { NAV_ROW_GAP, NAV_ANIM_MS } from '../../constants/app'
import { ROW_STEP, type NavItem, type NavPhase, type ScrollEntry } from './NavigationTypes'

export interface NavigationState {
  store: ReturnType<typeof useNodeStore>
  childNodes: Ref<NodeRecord[]>
  officialNodes: Ref<OfficialNode[]>
  activeNode: Ref<NodeRecord | null>
  viewState: Ref<ViewState>
  isAuthenticated: Ref<boolean>
  compactMode: Ref<CompactMode>
  layoutType: Ref<LayoutType>
  otPhase: Ref<OfficialTransitionPhase>
  otAnimating: Ref<boolean>
  otAnchorItemId: Ref<string | null>
  otClickedItemId: Ref<string | null>
  otAnchorDeltaY: Ref<number>
  otAnchorPrep: Ref<boolean>
  hideNonAnchorItems: Ref<boolean>
  resetOfficialTransition: () => void
  visibleOfficialNodes: ComputedRef<OfficialNode[]>
  pressedOfficialId: ComputedRef<string | null>
  showOfficialNodes: Ref<boolean>
  scrollSource: ComputedRef<NavItem[]>
  addPressed: ComputedRef<boolean>
  navPhase: Ref<NavPhase>
  navAnimating: Ref<boolean>
  navAnimToken: number
  hasInitialized: boolean
  pendingFirstData: boolean
  hideNodeList: Ref<boolean>
  anchorOfficial: Ref<NavItem | null>
  anchorSlidingDown: Ref<boolean>
  actionNodeId: Ref<string | null>
  pressedNodeId: Ref<string | null>
  nodeListRef: Ref<ComponentPublicInstance | HTMLElement | null>
  containerH: Ref<number>
  scrollOffset: Ref<number>
  isAnimating: Ref<boolean>
  displayItems: Ref<NavItem[]>
  scrollingTopId: Ref<string | null>
  scrollingBottomId: Ref<string | null>
  scrollDirection: Ref<'up' | 'down' | null>
  transitionName: Ref<string>
  devStore: ReturnType<typeof useDevStore>
  effectiveTransitionName: ComputedRef<string>
  scrollQueue: Ref<ScrollEntry[]>
  lastScrollDirection: Ref<'up' | 'down'>
  lastWheelTime: Ref<number>
  currentSpeed: Ref<number>
  currentAnimMs: Ref<number>
  scrollCancelToken: number
  maxVisible: ComputedRef<number>
}

export function useNavigationState(): NavigationState {
  const store = useNodeStore()
  const authStore = useAuthStore()
  const { childNodes, officialNodes, activeNode, viewState } = storeToRefs(store)
  const { isAuthenticated } = storeToRefs(authStore)
  const { compactMode, layoutType } = useKnobDispatch()
  const {
    phase: otPhase,
    animating: otAnimating,
    anchorItemId: otAnchorItemId,
    clickedItemId: otClickedItemId,
    anchorDeltaY: otAnchorDeltaY,
    anchorPrep: otAnchorPrep,
    hideNonAnchorItems,
    reset: resetOfficialTransition,
  } = useOfficialTransition()

  const visibleOfficialNodes = computed(() =>
    officialNodes.value.filter(n => n.visible),
  )

  const pressedOfficialId = computed<string | null>(() => {
    const state = viewState.value
    if (state === 'daily_quiz') return 'daily_quiz'
    if (state === 'tree_overview') return 'tree_overview'
    if (state === 'official_content') return store.officialNodeContent?.id ?? null
    return null
  })

  const showOfficialNodes = ref(visibleOfficialNodes.value.length > 0 && !activeNode.value)

  const scrollSource = computed<NavItem[]>(() => {
    const items: NavItem[] = []
    if (showOfficialNodes.value) {
      for (const n of visibleOfficialNodes.value) items.push({ id: n.id, name: n.name, isOfficial: true, action: n.action })
    }
    for (const n of childNodes.value) items.push({ id: n.id, name: n.name, isOfficial: false, nodeData: n })
    return items
  })

  const navPhase = ref<NavPhase>('idle')
  const navAnimating = ref(false)
  let navAnimToken = 0
  let hasInitialized = false
  let pendingFirstData = true

  const hideNodeList = ref(false)
  const anchorOfficial = ref<NavItem | null>(null)
  const anchorSlidingDown = ref(false)

  const actionNodeId = ref<string | null>(null)
  const addPressed = computed(() => store.viewState === 'add')
  const pressedNodeId = ref<string | null>(null)

  const nodeListRef = ref<ComponentPublicInstance | HTMLElement | null>(null)
  const containerH = ref(0)
  const scrollOffset = ref(0)
  const isAnimating = ref(false)
  const displayItems = ref<NavItem[]>([])
  const scrollingTopId = ref<string | null>(null)
  const scrollingBottomId = ref<string | null>(null)
  const scrollDirection = ref<'up' | 'down' | null>(null)
  const transitionName = ref('cell')
  const devStore = useDevStore()
  const effectiveTransitionName = computed(() => {
    if (!devStore.enableTransition || navAnimating.value || otAnimating.value) return 'none'
    return transitionName.value
  })

  const scrollQueue = ref<ScrollEntry[]>([])
  const lastScrollDirection = ref<'up' | 'down'>('down')
  const lastWheelTime = ref(0)
  const currentSpeed = ref(0)
  const currentAnimMs = ref(NAV_ANIM_MS)
  let scrollCancelToken = 0

  const maxVisible = computed(() => {
    if (containerH.value <= 0) return 20
    return Math.floor((containerH.value + NAV_ROW_GAP) / ROW_STEP)
  })

  return {
    store,
    childNodes,
    officialNodes,
    activeNode,
    viewState,
    isAuthenticated,
    compactMode,
    layoutType,
    otPhase,
    otAnimating,
    otAnchorItemId,
    otClickedItemId,
    otAnchorDeltaY,
    otAnchorPrep,
    hideNonAnchorItems,
    resetOfficialTransition,
    visibleOfficialNodes,
    pressedOfficialId,
    showOfficialNodes,
    scrollSource,
    addPressed,
    navPhase,
    navAnimating,
    navAnimToken,
    hasInitialized,
    pendingFirstData,
    hideNodeList,
    anchorOfficial,
    anchorSlidingDown,
    actionNodeId,
    pressedNodeId,
    nodeListRef,
    containerH,
    scrollOffset,
    isAnimating,
    displayItems,
    scrollingTopId,
    scrollingBottomId,
    scrollDirection,
    transitionName,
    devStore,
    effectiveTransitionName,
    scrollQueue,
    lastScrollDirection,
    lastWheelTime,
    currentSpeed,
    currentAnimMs,
    scrollCancelToken,
    maxVisible,
  }
}
