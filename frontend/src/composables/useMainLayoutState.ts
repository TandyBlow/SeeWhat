import { ref, shallowRef, computed } from 'vue'
import type { Ref, ComputedRef, ShallowRef } from 'vue'
import { useOfficialTransition } from './useOfficialTransition'

/**
 * View states that render as content-direct panels (no outer content-glass).
 * Each panel component supplies its own GlassWrapper to avoid nested active areas.
 * When adding a new official knowledge point, add its viewState here.
 */
export const CONTENT_DIRECT_STATES = ['add', 'daily_quiz', 'tree_overview', 'official_content']

// Content slide animation timing (ms) — behavior-critical, single-sourced here.
export const CONTENT_SINK_MS = 240
export const CONTENT_SLIDE_MS = 280
export const CONTENT_RISE_MS = 240
export const TREE_MASK_FADE_MS = 380

export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

export type EntrancePhase = 'idle' | 'prep' | 'sliding' | 'rising'
export type CompactAnimPhase = 'idle' | 'sinking' | 'nav-slide-out' | 'nav-slide-in-prep' | 'nav-slide-in' | 'rising'

export interface MainLayoutState {
  logoRef: Ref<HTMLElement | null>
  breadcrumbsRef: Ref<HTMLElement | null>
  navigationRef: Ref<HTMLElement | null>
  contentAreaRef: Ref<HTMLElement | null>
  contentGlassRef: Ref<HTMLElement | null>
  knobRef: Ref<HTMLElement | null>
  treeCurtainDrawn: Ref<boolean>
  treeCanvasRef: Ref<{ sceneReady: boolean } | null>
  treeMaskVisible: Ref<boolean>
  treeOverlayActive: Ref<boolean>
  treeMaskRef: Ref<HTMLElement | null>
  isTooSmall: Ref<boolean>
  initialRender: Ref<boolean>
  entrancePhase: Ref<EntrancePhase>
  compactAnimPhase: Ref<CompactAnimPhase>
  contentPhase: Ref<string>
  contentAnimToken: Ref<number>
  contentAnimating: Ref<boolean>
  displayedKey: Ref<string>
  displayedShowTree: Ref<boolean>
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  displayedNonTreeContent: ShallowRef<any>
  displayedSkipContentGlass: Ref<boolean>
  treeWasVisible: Ref<boolean>
  isPageAnimating: ComputedRef<boolean>
}

/**
 * Single shared-state module created once in the entry and threaded into
 * every other composable. Owns ALL shared refs, template refs, phase refs,
 * displayed refs, timing constants, sleep(), and the isPageAnimating computed.
 */
export function createMainLayoutState(): MainLayoutState {
  // Region refs for page transition system
  const logoRef = ref<HTMLElement | null>(null)
  const breadcrumbsRef = ref<HTMLElement | null>(null)
  const navigationRef = ref<HTMLElement | null>(null)
  const contentAreaRef = ref<HTMLElement | null>(null)
  const contentGlassRef = ref<HTMLElement | null>(null)
  const knobRef = ref<HTMLElement | null>(null)

  // Tree curtain
  const treeCurtainDrawn = ref(false)
  const treeCanvasRef = ref<{ sceneReady: boolean } | null>(null)

  // Tree mask
  const treeMaskVisible = ref(false)
  const treeOverlayActive = ref(false)
  const treeMaskRef = ref<HTMLElement | null>(null)

  // Compact layout tracking
  const isTooSmall = ref(false)

  // Initial page load: content starts sunken (only bottom areas visible),
  // then animates slide-in + rise after initialization.
  const initialRender = ref(true)

  // Entrance animation: coordinates slide-in for nav/breadcrumbs/knob
  // Phases: idle | prep | sliding | rising
  const entrancePhase = ref<EntrancePhase>('idle')

  // Compact toggle animation
  const compactAnimPhase = ref<CompactAnimPhase>('idle')

  const contentPhase = ref('idle')
  const contentAnimToken = ref(0)
  const contentAnimating = ref(false)

  const displayedKey = ref('')
  const displayedShowTree = ref(false)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const displayedNonTreeContent = shallowRef<any>(null)

  const displayedSkipContentGlass = ref(false)
  const treeWasVisible = ref(false)

  // Global click shield: block all pointer events while any CSS animation is playing.
  // CSS animations are timer/transition-driven, so they don't need pointer events.
  // Excludes 'tree-mask' phase: waitForSceneReady can take seconds while the tree
  // loads, and the mask itself already has pointer-events: none.
  // Excludes isTransitioning: data fetching is not an animation and can hang
  // indefinitely if the backend is unreachable (fetch has no default timeout).
  const { animating: otAnimating } = useOfficialTransition()
  const isPageAnimating = computed(() =>
    (contentPhase.value !== 'idle' && contentPhase.value !== 'tree-mask') ||
    compactAnimPhase.value !== 'idle' ||
    otAnimating.value ||
    entrancePhase.value !== 'idle'
  )

  return {
    logoRef,
    breadcrumbsRef,
    navigationRef,
    contentAreaRef,
    contentGlassRef,
    knobRef,
    treeCurtainDrawn,
    treeCanvasRef,
    treeMaskVisible,
    treeOverlayActive,
    treeMaskRef,
    isTooSmall,
    initialRender,
    entrancePhase,
    compactAnimPhase,
    contentPhase,
    contentAnimToken,
    contentAnimating,
    displayedKey,
    displayedShowTree,
    displayedNonTreeContent,
    displayedSkipContentGlass,
    treeWasVisible,
    isPageAnimating,
  }
}
