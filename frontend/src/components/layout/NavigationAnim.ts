import { nextTick } from 'vue'
import { NAV_SINK_MS, NAV_SLIDE_MS, NAV_RISE_MS } from './NavigationTypes'
import type { NavigationState } from './NavigationState'

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

export function useNavigationAnim(state: NavigationState) {
  // ================================================================
  // 4-phase page navigation animation (mirrors breadcrumbs)
  // Sink → slide-out-left → commit DOM → slide-in-from-left → rise
  // ================================================================
  async function animateNavPageTransition() {
    state.transitionName.value = 'none'

    if (state.navAnimating.value) {
      state.navAnimToken++
      state.navPhase.value = 'idle'
      state.navAnimating.value = false
      state.pressedNodeId.value = null
      state.displayItems.value = state.scrollSource.value.slice(0, state.maxVisible.value)
      nextTick(() => { state.transitionName.value = 'cell' })
      return
    }

    state.navAnimating.value = true
    const token = ++state.navAnimToken
    const el = state.nodeListRef.value as HTMLElement | null

    // Phase 1: Sink — all glass items become pressed/sunken
    state.navPhase.value = 'sinking'
    await nextTick()
    if (token !== state.navAnimToken) return
    await sleep(NAV_SINK_MS)
    if (token !== state.navAnimToken) return

    // Phase 2: Slide out left — old content slides left behind the page
    state.navPhase.value = 'sliding-out'
    await sleep(NAV_SLIDE_MS)
    if (token !== state.navAnimToken) return

    // Commit new DOM in prep position (off-screen left, no transition)
    state.showOfficialNodes.value = state.visibleOfficialNodes.value.length > 0 && !state.activeNode.value
    state.pressedNodeId.value = null
    state.displayItems.value = state.scrollSource.value.slice(0, state.maxVisible.value)
    state.navPhase.value = 'sliding-in-prep'

    await nextTick()
    if (token !== state.navAnimToken) return

    // Force reflow so prep position is painted, then trigger slide-in
    if (el) void el.offsetHeight
    state.navPhase.value = 'sliding-in'

    // Phase 3: Slide in from left — new content arrives from behind the page
    await sleep(NAV_SLIDE_MS)
    if (token !== state.navAnimToken) return

    // Phase 4: Rise — glass items regain shadow
    state.navPhase.value = 'rising'
    await nextTick()
    if (token !== state.navAnimToken) return
    await sleep(NAV_RISE_MS)

    state.navPhase.value = 'idle'
    state.navAnimating.value = false
    nextTick(() => { state.transitionName.value = 'cell' })
  }

  // ================================================================
  // Small layout add animation — reuse navPhase state machine
  // Add: sink → node list slides out left (add button stays) → startAdd
  // ================================================================
  async function animateSmallLayoutAdd() {
    if (state.navAnimating.value) {
      state.navAnimToken++
      state.navPhase.value = 'idle'
      state.navAnimating.value = false
      state.hideNodeList.value = false
    }

    state.navAnimating.value = true
    const token = ++state.navAnimToken

    state.navPhase.value = 'sinking'
    await nextTick()
    await sleep(NAV_SINK_MS)
    if (token !== state.navAnimToken) return

    state.navPhase.value = 'sliding-out'
    await sleep(NAV_SLIDE_MS)
    if (token !== state.navAnimToken) return

    state.hideNodeList.value = true
    state.navPhase.value = 'idle'
    state.navAnimating.value = false

    state.store.startAdd()
  }

  return {
    navPhase: state.navPhase,
    navAnimating: state.navAnimating,
    animateNavPageTransition,
    animateSmallLayoutAdd,
  }
}
