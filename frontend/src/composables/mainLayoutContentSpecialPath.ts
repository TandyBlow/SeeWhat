import { nextTick } from 'vue'
import { applyDisplayedState, applyEmptyBackground, applyRise } from './mainLayoutContentContext'
import { CONTENT_SLIDE_MS, TREE_MASK_FADE_MS, sleep } from './useMainLayoutState'
import type { MainLayoutContentCtx } from './mainLayoutContentContext'

// Special → non-special exit: content-direct slides out right, then new
// content (in content-glass) slides in, or tree fades in.
export async function handleSpecialStateExit(ctx: MainLayoutContentCtx): Promise<void> {
  const { state } = ctx

  state.contentAnimating.value = true
  const token = ++state.contentAnimToken.value

  // Phase 1: Slide out right (content-direct slides right, fades out)
  state.contentPhase.value = 'slide-out'
  await nextTick()
  if (token !== state.contentAnimToken.value) return
  await sleep(CONTENT_SLIDE_MS)
  if (token !== state.contentAnimToken.value) return

  // Apply pending data
  ctx.nodeStore.applyPendingData()

  if (ctx.display.showEmptyBackground.value) {
    applyEmptyBackground(ctx)
    return
  }

  const willShowTree = ctx.display.showTree.value

  // Swap DOM: content-direct → content-glass, content in prep position
  applyDisplayedState(ctx)
  state.contentPhase.value = 'slide-in-prep'

  await nextTick()
  if (token !== state.contentAnimToken.value) return

  if (willShowTree) {
    // Tree enter with mask (snap mask visible, load tree, fade mask out)
    state.treeOverlayActive.value = true
    const maskEl = state.treeMaskRef.value
    if (maskEl) maskEl.style.transition = 'none'
    state.treeMaskVisible.value = true

    await nextTick()
    if (token !== state.contentAnimToken.value) return
    const reflowEl = state.contentGlassRef.value || document.querySelector('.content-direct')
    void reflowEl?.offsetHeight
    if (maskEl) maskEl.style.transition = ''

    state.contentPhase.value = 'tree-mask'

    await nextTick()
    await ctx.waitForSceneReady(token)
    if (token !== state.contentAnimToken.value) return
    state.treeMaskVisible.value = false
    await sleep(TREE_MASK_FADE_MS)
    if (token !== state.contentAnimToken.value) return
  } else {
    // Standard slide-in from right
    const reflowEl = state.contentGlassRef.value || document.querySelector('.content-direct')
    void reflowEl?.offsetHeight
    state.contentPhase.value = 'slide-in'
    await sleep(CONTENT_SLIDE_MS)
    if (token !== state.contentAnimToken.value) return
  }

  await applyRise(ctx, token)
}
