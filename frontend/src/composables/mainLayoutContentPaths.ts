import { nextTick } from 'vue'
import { applyDisplayedState, applyEmptyBackground, applyRise } from './mainLayoutContentContext'
import { CONTENT_DIRECT_STATES, CONTENT_RISE_MS, CONTENT_SLIDE_MS, TREE_MASK_FADE_MS, sleep } from './useMainLayoutState'
import type { MainLayoutContentCtx } from './mainLayoutContentContext'

// TREE EXIT PATH: mask fade-in → DOM swap → slide-in
export async function handleTreeExit(ctx: MainLayoutContentCtx, token: number, oldKey: string): Promise<void> {
  const { state } = ctx

  // Only apply pending data for node navigations, not for viewState
  // transitions (CONTENT_DIRECT_STATES). For viewState transitions,
  // executeDataLoading already set the target viewState and
  // pendingNodeContext may carry stale data from a previous navigation.
  if (!CONTENT_DIRECT_STATES.includes(ctx.nodeStore.viewState)) {
    ctx.nodeStore.applyPendingData()
  }

  // If account became empty, skip to background
  if (ctx.display.showEmptyBackground.value) {
    applyEmptyBackground(ctx)
    return
  }

  const willShowTree = ctx.display.showTree.value

  if (willShowTree) {
    // Staying in tree — just rise
    state.treeMaskVisible.value = false
    state.treeOverlayActive.value = true
    state.contentPhase.value = 'rising'
    await nextTick()
    if (token !== state.contentAnimToken.value) return
    await sleep(CONTENT_RISE_MS)
    if (token !== state.contentAnimToken.value) return
    state.contentPhase.value = 'idle'
    state.contentAnimating.value = false
    return
  }

  // Mask fades in, covering the tree
  state.treeMaskVisible.value = true
  state.contentPhase.value = 'tree-mask'
  await sleep(TREE_MASK_FADE_MS)
  if (token !== state.contentAnimToken.value) return

  if (ctx.display.contentKey.value === oldKey) {
    state.treeMaskVisible.value = false
    state.treeOverlayActive.value = false
    state.contentPhase.value = 'rising'
    await nextTick()
    if (token !== state.contentAnimToken.value) return
    await sleep(CONTENT_RISE_MS)
    if (token !== state.contentAnimToken.value) return
    state.contentPhase.value = 'idle'
    state.contentAnimating.value = false
    return
  }

  // Swap DOM behind mask — tree unmounts, new content in slide-in-prep position
  applyDisplayedState(ctx)
  state.contentPhase.value = 'slide-in-prep'

  await nextTick()
  if (token !== state.contentAnimToken.value) return
  const reflowEl = state.contentGlassRef.value || document.querySelector('.content-direct')
  void reflowEl?.offsetHeight

  // Snap mask off (content is invisible at prep position, no visual change)
  const maskEl = state.treeMaskRef.value
  if (maskEl) maskEl.style.transition = 'none'
  state.treeMaskVisible.value = false
  state.treeOverlayActive.value = false

  await nextTick()
  void reflowEl?.offsetHeight
  if (maskEl) maskEl.style.transition = ''

  // Trigger slide-in from right
  state.contentPhase.value = 'slide-in'
  await sleep(CONTENT_SLIDE_MS)
  if (token !== state.contentAnimToken.value) return

  await applyRise(ctx, token)
}

// NON-TREE PATH: slide-out → (tree enter OR standard slide-in)
export async function handleNonTreePath(ctx: MainLayoutContentCtx, token: number, oldKey: string): Promise<void> {
  const { state } = ctx

  // Phase 2: Slide out — old content leaves
  state.contentPhase.value = 'slide-out'
  await sleep(CONTENT_SLIDE_MS)
  if (token !== state.contentAnimToken.value) return

  // Apply pending data NOW — viewState is updated, so showTree is current.
  // Skip for special state entry to avoid reverting viewState to 'display'.
  if (!CONTENT_DIRECT_STATES.includes(ctx.nodeStore.viewState)) {
    ctx.nodeStore.applyPendingData()
  }

  // If account became empty (last node deleted), skip to background
  if (ctx.display.showEmptyBackground.value) {
    applyEmptyBackground(ctx)
    return
  }

  const willShowTree = ctx.display.showTree.value

  // Content didn't change — skip slide, just rise
  if (ctx.display.contentKey.value === oldKey) {
    state.treeMaskVisible.value = false
    state.contentPhase.value = 'rising'
    await nextTick()
    if (token !== state.contentAnimToken.value) return
    await sleep(CONTENT_RISE_MS)
    if (token !== state.contentAnimToken.value) return
    state.contentPhase.value = 'idle'
    state.contentAnimating.value = false
    return
  }

  if (willShowTree) {
    // ---- TREE ENTER: non-tree → tree ----

    // Snap mask to visible instantly (no fade-in) — looks like empty area
    state.treeOverlayActive.value = true
    const maskEl = state.treeMaskRef.value
    if (maskEl) maskEl.style.transition = 'none'
    state.treeMaskVisible.value = true

    await nextTick()
    if (token !== state.contentAnimToken.value) return
    const enterReflowEl = state.contentGlassRef.value || document.querySelector('.content-direct')
    void enterReflowEl?.offsetHeight // force reflow so opacity:1 is painted
    if (maskEl) maskEl.style.transition = '' // re-enable transition for fade-out

    // Now swap DOM: tree loads under the fully opaque mask
    applyDisplayedState(ctx)
    state.contentPhase.value = 'tree-mask'

    // Wait for tree scene to be ready, then fade mask out
    await nextTick()
    await ctx.waitForSceneReady(token)
    if (token !== state.contentAnimToken.value) return
    state.treeMaskVisible.value = false
    await sleep(TREE_MASK_FADE_MS)
    if (token !== state.contentAnimToken.value) return
  } else {
    // ---- NON-TREE: standard slide-in from right ----

    // Swap the wrapper first so the new wrapper type is mounted before new
    // content is placed, avoiding a flash of new content in the old wrapper.
    applyDisplayedState(ctx)
    state.contentPhase.value = 'slide-in-prep'

    await nextTick()
    if (token !== state.contentAnimToken.value) return

    // Force reflow so prep position is painted, then trigger slide-in.
    // When entering a special state content-glass is replaced by content-direct.
    const reflowEl = state.contentGlassRef.value || document.querySelector('.content-direct')
    void reflowEl?.offsetHeight
    state.contentPhase.value = 'slide-in'

    await sleep(CONTENT_SLIDE_MS)
    if (token !== state.contentAnimToken.value) return
  }

  await applyRise(ctx, token)
}
